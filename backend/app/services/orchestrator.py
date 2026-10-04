"""Central Agent Orchestrator (Section 47).

Receives a task, selects/validates the agent, checks permissions, gathers
memory context, executes through the AIProvider abstraction, stores results
and AgentRuns, enforces budgets, emits events and handles retries.
A task is only ever marked completed when the provider call truly succeeded.
"""
import logging
import time
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.permissions import agent_can
from app.core.config import get_settings
from app.core.events import EventType
from app.integrations.ai_providers import MODEL_PRICES, ProviderNotConfiguredError
from app.models.agent import Agent, AgentRun
from app.models.channel import Channel
from app.models.ops import CostRecord
from app.models.organization import Organization
from app.models.task import Task, TaskDependency
from app.services import memory_service
from app.services.event_bus import publish

logger = logging.getLogger("aihq.orchestrator")


class Orchestrator:
    def __init__(self, db: Session, provider=None):
        self.db = db
        self.settings = get_settings()
        self.provider = provider  # injectable for tests

    # ---------------------------------------------------------------- helpers

    def _fail(self, task: Task, error: str, blocked: bool = False) -> Task:
        task.status = "blocked" if blocked else "failed"
        task.error = error
        task.completed_at = datetime.now(UTC)
        publish(self.db, EventType.TASK_BLOCKED if blocked else EventType.TASK_FAILED,
                {"error": error}, org_id=task.org_id, task_id=task.id, agent_id=task.assigned_agent_id)
        self.db.commit()
        return task

    def _check_budget(self, org_id: int) -> bool:
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        spent = (self.db.query(func.sum(CostRecord.amount_usd))
                 .filter(CostRecord.org_id == org_id, CostRecord.occurred_at >= month_start).scalar() or 0.0)
        return spent >= self.settings.MONTHLY_BUDGET_USD

    def _deps_ready(self, task: Task) -> tuple[bool, str]:
        dep_ids = [d.depends_on_id for d in self.db.query(TaskDependency).filter_by(task_id=task.id).all()]
        if not dep_ids:
            return True, ""
        deps = self.db.query(Task).filter(Task.id.in_(dep_ids)).all()
        for dep in deps:
            if dep.status == "failed":
                return False, f"dependency #{dep.id} failed"
            if dep.status != "completed":
                return False, f"dependency #{dep.id} not completed (status={dep.status})"
        return True, ""

    # ---------------------------------------------------------------- execute

    def execute_task(self, task_id: int) -> Task:
        task = self.db.get(Task, task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        if task.status == "cancelled":
            return task

        org = self.db.get(Organization, task.org_id)
        settings = org.settings or {} if org else {}
        if settings.get("operations_paused"):
            return self._fail(task, "Operations are paused (global kill switch). Resume from Settings.", blocked=True)

        if task.assigned_agent_id is None:
            # Self-organizing org: route the task to the best-fit active
            # agent instead of failing. If no agent exists, fail honestly.
            from app.services.initiative_service import _pick_agent
            agent = _pick_agent(self.db, task.org_id, task)
            if agent is None:
                return self._fail(task, "Task has no assigned agent and no active agent "
                                        "is available to self-assign it. Add/activate agents first.")
            task.assigned_agent_id = agent.id
            self.db.commit()
            publish(self.db, EventType.TASK_AUTO_ASSIGNED,
                    {"task": task.title, "agent": agent.name},
                    org_id=task.org_id, task_id=task.id, agent_id=agent.id)

        agent = self.db.get(Agent, task.assigned_agent_id)
        if agent is None:
            return self._fail(task, f"Agent {task.assigned_agent_id} not found.")
        if agent.status != "active":
            return self._fail(task, f"Agent '{agent.name}' is {agent.status}. Resume it before running.", blocked=True)

        required = (task.input or {}).get("required_permission")
        if required and not agent_can(agent.permission_level, required):
            return self._fail(task, f"Agent '{agent.name}' (level={agent.permission_level}) lacks "
                                    f"permission '{required}'.", blocked=True)

        if self._check_budget(task.org_id):
            publish(self.db, EventType.BUDGET_EXCEEDED, {"budget": self.settings.MONTHLY_BUDGET_USD},
                    org_id=task.org_id)
            return self._fail(task, f"Monthly budget of ${self.settings.MONTHLY_BUDGET_USD} exceeded.",
                             blocked=True)

        ready, reason = self._deps_ready(task)
        if not ready:
            task.status = "waiting"
            task.error = f"Waiting on dependencies: {reason}"
            self.db.commit()
            return task

        provider = self.provider
        if provider is None:
            from app.integrations.ai_providers import get_ai_provider
            provider = get_ai_provider()

        task.status = "running"
        task.started_at = datetime.now(UTC)
        task.error = None
        agent.current_task_id = task.id
        self.db.commit()
        publish(self.db, EventType.TASK_STARTED, {"title": task.title},
                org_id=task.org_id, task_id=task.id, agent_id=agent.id)

        context = memory_service.build_agent_context(self.db, task, agent)
        channel = self.db.get(Channel, task.channel_id) if task.channel_id else None
        # The Agency-style dossier is the core of the prompt; personality,
        # rules and workflow actually shape the output. Fallback for legacy
        # agents without a persona keeps behavior identical.
        if agent.persona:
            system = (
                f"{agent.persona}\n\n"
                "You operate inside an AI media company that produces YouTube Shorts. "
                "Follow your Critical Rules and Workflow sections. Stay in character: your "
                "Communication Style is how you always write. "
                "Respond with a structured, actionable result for the assigned task."
            )
        else:
            system = (f"You are {agent.name}, the {agent.role} in an AI media company. {agent.description} "
                      f"Respond with a structured, actionable result for the assigned task.")
        user = f"TASK: {task.title}\n\nDETAILS:\n{task.description or '(none)'}\n\nCONTEXT:\n{context or '(none)'}"
        if channel:
            user += f"\n\nCHANNEL: {channel.name} ({channel.niche}). Audience: {channel.audience}"

        attempts = task.max_retries + 1
        last_error = None
        for attempt in range(attempts):
            run = AgentRun(agent_id=agent.id, task_id=task.id, status="running",
                           input={"title": task.title, "attempt": attempt + 1})
            self.db.add(run)
            self.db.commit()
            publish(self.db, EventType.AGENT_STARTED, {"attempt": attempt + 1},
                    org_id=task.org_id, task_id=task.id, agent_id=agent.id)

            started = time.monotonic()
            try:
                completion = provider.complete(system, user, max_tokens=2000)
                duration_ms = int((time.monotonic() - started) * 1000)

                price = MODEL_PRICES.get(completion.model, (0.0, 0.0))
                cost = round((completion.prompt_tokens * price[0] + completion.completion_tokens * price[1]), 6)

                run.status = "completed"
                run.finished_at = datetime.now(UTC)
                run.duration_ms = duration_ms
                run.output = {"result": completion.text}
                run.prompt_tokens = completion.prompt_tokens
                run.completion_tokens = completion.completion_tokens
                run.cost_usd = cost

                task.status = "completed"
                task.output = {"result": completion.text, "model": completion.model,
                               "tokens": completion.prompt_tokens + completion.completion_tokens}
                task.completed_at = datetime.now(UTC)
                task.error = None
                agent.current_task_id = None

                if cost > 0:
                    self.db.add(CostRecord(org_id=task.org_id, category="model_usage", amount_usd=cost,
                                           agent_id=agent.id, task_id=task.id, channel_id=task.channel_id,
                                           description=f"{agent.name} on '{task.title[:80]}'"))
                self.db.commit()
                publish(self.db, EventType.TASK_COMPLETED,
                        {"duration_ms": duration_ms, "cost_usd": cost},
                        org_id=task.org_id, task_id=task.id, agent_id=agent.id, commit=True)
                publish(self.db, EventType.AGENT_COMPLETED, {"duration_ms": duration_ms},
                        org_id=task.org_id, task_id=task.id, agent_id=agent.id, commit=True)
                logger.info("task completed", extra={"task_id": task.id, "agent_id": agent.id,
                                                     "status": "completed", "duration_ms": duration_ms})
                return task

            except ProviderNotConfiguredError as exc:
                run.status = "failed"
                run.error = str(exc)
                run.finished_at = datetime.now(UTC)
                self.db.commit()
                # Retrying cannot fix missing credentials - fail honestly.
                return self._fail(task, f"AI provider error: {exc}")

            except Exception as exc:  # noqa: BLE001
                duration_ms = int((time.monotonic() - started) * 1000)
                run.status = "failed"
                run.error = str(exc)[:2000]
                run.duration_ms = duration_ms
                run.finished_at = datetime.now(UTC)
                task.retry_count = attempt + 1
                self.db.commit()
                publish(self.db, EventType.AGENT_FAILED, {"attempt": attempt + 1, "error": str(exc)[:200]},
                        org_id=task.org_id, task_id=task.id, agent_id=agent.id)
                last_error = str(exc)

        return self._fail(task, f"All {attempts} attempts failed. Last error: {last_error}")

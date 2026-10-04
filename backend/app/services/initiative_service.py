"""Agent initiative: auto-assignment + self-proposed work (Section 8 + 38).

Two capabilities:
1. auto_assign: queued tasks without an agent are routed to the best-fit
   active agent (capability/department scoring) so agents work without the
   founder hand-assigning everything.
2. generate_suggestions: idle agents review their department context and
   propose the highest-value next task. The founder approves/rejects;
   approved suggestions become real Tasks assigned to the proposing agent.
   With org setting auto_approve_suggestions=true, proposals convert
   themselves immediately (full autonomy mode). Publishing/QC gates still
   apply downstream - initiative never bypasses approvals.
"""
import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agents.registry import AGENTS
from app.core.config import get_settings
from app.core.events import EventType
from app.models.agent import Agent
from app.models.initiative import AgentSuggestion
from app.models.organization import Organization
from app.models.task import Task
from app.services.event_bus import publish

logger = logging.getLogger("aihq.initiative")

STOP_WORDS = {"the", "a", "an", "for", "and", "of", "to", "in", "on", "with", "new", "our", "this"}


def _keywords(text: str) -> set[str]:
    return {w for w in text.lower().replace("/", " ").replace("-", " ").split() if len(w) > 2 and w not in STOP_WORDS}


def _pick_agent(db: Session, org_id: int, task: Task) -> Agent | None:
    """Best-fit routing: department hint wins, else capability keyword score,
    tie-broken by least queued workload."""
    agents = db.query(Agent).filter(Agent.org_id == org_id, Agent.status == "active").all()
    if not agents:
        return None
    hint = (task.input or {}).get("department")
    if hint:
        for a in agents:
            if a.department == hint:
                return a
    words = _keywords(f"{task.title} {task.description or ''}")
    registry = {r["key"]: r for r in AGENTS}

    def score(a: Agent) -> tuple:
        reg = registry.get(a.key, {})
        hay = _keywords(" ".join(reg.get("capabilities", [])) + " " + a.role + " " + (a.description or ""))
        overlap = len(words & hay)
        queued = db.query(Task).filter(Task.assigned_agent_id == a.id,
                                      Task.status.in_(["queued", "running"])).count()
        return (overlap, -queued, -a.id)

    return max(agents, key=score) if agents else None


def auto_assign_queued(db: Session, org: Organization) -> int:
    """Assign queued, agent-less tasks. Returns count assigned."""
    if (org.settings or {}).get("operations_paused"):
        return 0
    unassigned = (db.query(Task)
                  .filter(Task.org_id == org.id, Task.status == "queued",
                          Task.assigned_agent_id.is_(None)).all())
    count = 0
    for task in unassigned:
        agent = _pick_agent(db, org.id, task)
        if agent is None:
            continue
        task.assigned_agent_id = agent.id
        count += 1
        publish(db, EventType.TASK_AUTO_ASSIGNED,
                {"task": task.title, "agent": agent.name},
                org_id=org.id, task_id=task.id, agent_id=agent.id)
    if count:
        db.commit()
    return count


def _department_context(db: Session, org: Organization, agent: Agent) -> str:
    """Honest, compact snapshot of what the agent's department sees now."""
    dept_agents = db.query(Agent).filter(Agent.org_id == org.id, Agent.department == agent.department).all()
    agent_ids = [a.id for a in dept_agents]
    recent_done = (db.query(Task)
                   .filter(Task.assigned_agent_id.in_(agent_ids) if agent_ids else False,
                           Task.status == "completed")
                   .order_by(Task.id.desc()).limit(5).all())
    in_flight = (db.query(Task)
                 .filter(Task.assigned_agent_id.in_(agent_ids) if agent_ids else False,
                         Task.status.in_(["queued", "running"]))
                 .count())
    from app.models.channel import Channel
    channel_count = db.query(Channel).filter(Channel.org_id == org.id).count()
    lines = [
        f"Department: {agent.department}",
        f"Your role: {agent.role}",
        f"Tasks in progress in department: {in_flight}",
        "Recently completed tasks: "
        + ("; ".join(t.title for t in recent_done) if recent_done else "none yet"),
        f"Company channels configured: {channel_count}",
    ]
    return "\n".join(lines)


def _suggestions_today(db: Session, agent_id: int) -> int:
    since = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return (db.query(AgentSuggestion)
            .filter(AgentSuggestion.agent_id == agent_id,
                    AgentSuggestion.proposed_at >= since).count())


def _idle_agents(db: Session, org: Organization) -> list[Agent]:
    """Active agents with nothing queued/running for them AND no open proposal
    of theirs awaiting decision."""
    agents = db.query(Agent).filter(Agent.org_id == org.id, Agent.status == "active").all()
    idle = []
    for a in agents:
        busy = db.query(Task).filter(Task.assigned_agent_id == a.id,
                                     Task.status.in_(["queued", "running", "waiting"])).count()
        open_sug = (db.query(AgentSuggestion)
                    .filter(AgentSuggestion.agent_id == a.id,
                            AgentSuggestion.status == "proposed").count())
        if not busy and not open_sug:
            idle.append(a)
    return idle


def _parse_proposal(raw: str) -> dict | None:
    """Extract the JSON proposal from the model output (tolerant of wrappers)."""
    try:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1:
            return None
        data = json.loads(raw[start:end + 1])
        if not data.get("title"):
            return None
        return {
            "title": str(data["title"])[:300],
            "description": str(data.get("description", ""))[:2000],
            "rationale": str(data.get("rationale", ""))[:2000],
            "priority": data.get("priority") if data.get("priority") in
                        ("low", "medium", "high", "urgent") else "medium",
        }
    except (ValueError, TypeError):
        return None


def generate_suggestions(db: Session, org: Organization, provider=None, force: bool = False) -> int:
    """Have idle agents propose their next task. Cost-guarded by config.
    Returns number of new suggestions created."""
    settings = get_settings()
    org_settings = org.settings or {}
    if org_settings.get("operations_paused"):
        return 0
    if not force and not org_settings.get("agent_initiative", True):
        return 0

    from app.integrations.ai_providers import get_ai_provider
    provider = provider or get_ai_provider()

    candidates = _idle_agents(db, org)
    picked = []
    for a in candidates:
        if _suggestions_today(db, a.id) >= settings.INITIATIVE_MAX_PER_AGENT_PER_DAY:
            continue
        picked.append(a)
        if len(picked) >= settings.INITIATIVE_AGENTS_PER_PASS:
            break
    if not picked:
        return 0

    created = 0
    for agent in picked:
        context = _department_context(db, org, agent)
        system = (
            f"You are {agent.name}, the {agent.role} in an AI media company running "
            f"YouTube Shorts channels. You take initiative: when you have no assigned "
            f"work, you decide what the single highest-value next task for your role "
            f"would be and propose it. Propose only real, concrete work you can do "
            f"yourself as a text-producing agent (research, analysis, planning, copy, "
            f"review). Never propose actions that need spending, contracts, or "
            f"publishing. Respond ONLY with JSON: "
            f'{{"title": str, "description": str, "rationale": str, "priority": "low"|"medium"|"high"|"urgent"}}'
        )
        user = f"COMPANY CONTEXT:\n{context}\n\nPropose the one next task you would do."
        try:
            completion = provider.complete(system, user, max_tokens=500)
        except Exception as exc:  # noqa: BLE001 - provider errors must not kill the pass
            logger.warning("initiative proposal failed", extra={"agent": agent.key, "error": str(exc)[:200]})
            continue
        proposal = _parse_proposal(completion.text)
        if proposal is None:
            logger.warning("initiative proposal unparsable", extra={"agent": agent.key})
            continue
        sug = AgentSuggestion(org_id=org.id, agent_id=agent.id, created_by_agent=True,
                              status="proposed", proposed_at=datetime.now(UTC), **proposal)
        db.add(sug)
        db.commit()
        created += 1
        publish(db, EventType.SUGGESTION_CREATED,
                {"title": sug.title, "agent": agent.name, "rationale": sug.rationale[:200]},
                org_id=org.id, agent_id=agent.id)

        if org_settings.get("auto_approve_suggestions"):
            approve_suggestion(db, sug)
    return created


def approve_suggestion(db: Session, suggestion: AgentSuggestion, user_id: int | None = None) -> Task:
    """Convert an approved proposal into a real Task assigned to its agent."""
    agent = db.get(Agent, suggestion.agent_id)
    task = Task(
        org_id=suggestion.org_id,
        title=suggestion.title,
        description=suggestion.description or "",
        assigned_agent_id=suggestion.agent_id,
        priority=suggestion.priority,
        status="queued",
    )
    db.add(task)
    db.commit()
    suggestion.status = "approved"
    suggestion.decided_at = datetime.now(UTC)
    suggestion.decided_by_user_id = user_id
    suggestion.task_id = task.id
    db.commit()
    publish(db, EventType.SUGGESTION_APPROVED,
            {"title": suggestion.title, "task_id": task.id,
             "agent": agent.name if agent else "unknown"},
            org_id=suggestion.org_id, task_id=task.id, agent_id=suggestion.agent_id)
    return task


def reject_suggestion(db: Session, suggestion: AgentSuggestion, user_id: int | None = None) -> None:
    suggestion.status = "rejected"
    suggestion.decided_at = datetime.now(UTC)
    suggestion.decided_by_user_id = user_id
    db.commit()
    publish(db, EventType.SUGGESTION_REJECTED, {"title": suggestion.title},
            org_id=suggestion.org_id, agent_id=suggestion.agent_id)

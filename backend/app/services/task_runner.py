"""Background task runner (in-process poller).

Designed so the dispatch loop can be swapped for Celery/Redis later
(Section 3): anything that calls Orchestrator.execute_task(task_id)
with the same DB session semantics is a drop-in replacement.
"""
import asyncio
import logging

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.organization import Organization
from app.models.task import Task, TaskDependency
from app.services.orchestrator import Orchestrator

logger = logging.getLogger("aihq.task_runner")


def find_ready_task_ids(db: Session, limit: int = 5) -> list[int]:
    queued = db.query(Task).filter(Task.status == "queued").order_by(Task.id).limit(limit * 4).all()
    ready = []
    for task in queued:
        agent = db.get(Agent, task.assigned_agent_id) if task.assigned_agent_id else None
        if agent and agent.status != "active":
            continue
        dep_ids = [d.depends_on_id for d in db.query(TaskDependency).filter_by(task_id=task.id).all()]
        deps = db.query(Task).filter(Task.id.in_(dep_ids)).all() if dep_ids else []
        if all(d.status == "completed" for d in deps):
            ready.append(task.id)
        if len(ready) >= limit:
            break
    return ready


def _org_paused(db: Session, task: Task) -> bool:
    org = db.get(Organization, task.org_id)
    return bool((org.settings or {}).get("operations_paused")) if org else False


def run_ready_tasks() -> int:
    """Execute all currently-runnable tasks once. Returns count dispatched."""
    with SessionLocal() as db:
        ids = find_ready_task_ids(db)
    dispatched = 0
    for task_id in ids:
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task is None or task.status != "queued":
                continue
            if _org_paused(db, task):
                task.status = "blocked"
                task.error = "Operations paused (kill switch)."
                db.commit()
                continue
            task.status = "running"
            db.commit()
        with SessionLocal() as db:
            Orchestrator(db).execute_task(task_id)
        dispatched += 1
    return dispatched


def publishing_scheduled(db) -> int:
    """Scheduler (Section 40): attempt every scheduled publishing job that is due."""
    from datetime import UTC, datetime

    from app.models.organization import Organization
    from app.models.production import PublishingJob
    from app.services.publishing_service import execute_publish

    now = datetime.now(UTC)
    due = (db.query(PublishingJob)
           .filter(PublishingJob.status == "scheduled",
                   PublishingJob.scheduled_at <= now).all())
    for job in due:
        org = db.get(Organization, job.org_id)
        execute_publish(db, org, job)
    return len(due)


async def runner_loop(interval: float) -> None:
    logger.info("task runner started", extra={"status": "started"})
    from app.core.config import get_settings
    from app.services.initiative_service import auto_assign_queued, generate_suggestions
    settings = get_settings()
    initiative_every = max(float(settings.INITIATIVE_INTERVAL_SECONDS), interval)
    while True:
        # Auto-assign first: queued tasks must be routed to an agent
        # before the executor can pick them up.
        try:
            with SessionLocal() as db:
                orgs = db.query(Organization).all()
                for org in orgs:
                    auto_assign_queued(db, org)
        except Exception:  # noqa: BLE001
            logger.exception("auto-assign failed", extra={"error": "auto_assign"})
        try:
            run_ready_tasks()
        except Exception:  # noqa: BLE001
            logger.exception("task runner cycle failed", extra={"error": "runner_cycle"})
        try:
            with SessionLocal() as db:
                await asyncio.to_thread(publishing_scheduled, db)
        except Exception:  # noqa: BLE001
            logger.exception("publishing scheduler failed", extra={"error": "publishing_scheduler"})
        # Agent initiative: idle agents propose new work on the configured
        # cadence. Guarded by org settings and the operations kill switch
        # inside the service.
        if runner_loop._ticks * interval >= initiative_every or runner_loop._ticks == 0:
            try:
                with SessionLocal() as db:
                    orgs = db.query(Organization).all()
                    for org in orgs:
                        generate_suggestions(db, org)
            except Exception:  # noqa: BLE001
                logger.exception("initiative pass failed", extra={"error": "initiative"})
            runner_loop._ticks = 0
        runner_loop._ticks += 1
        await asyncio.sleep(interval)


runner_loop._ticks = 0

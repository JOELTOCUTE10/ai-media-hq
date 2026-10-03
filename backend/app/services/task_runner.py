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


async def runner_loop(interval: float) -> None:
    logger.info("task runner started", extra={"status": "started"})
    while True:
        try:
            run_ready_tasks()
        except Exception:  # noqa: BLE001
            logger.exception("task runner cycle failed", extra={"error": "runner_cycle"})
        await asyncio.sleep(interval)

"""Internal event architecture (Section 39). DB-persisted events + in-process subscribers."""
import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.models.ops import SystemEvent

logger = logging.getLogger("aihq.events")

Subscribers = list[Callable[[SystemEvent], None]]
_subscribers: Subscribers = []


def subscribe(fn: Callable[[SystemEvent], None]) -> None:
    _subscribers.append(fn)


def publish(db: Session, event_type: str, payload: dict | None = None,
            org_id: int | None = None, task_id: int | None = None,
            agent_id: int | None = None, workflow_run_id: int | None = None,
            commit: bool = False) -> SystemEvent:
    event = SystemEvent(
        org_id=org_id, event_type=event_type, payload=payload or {},
        task_id=task_id, agent_id=agent_id, workflow_run_id=workflow_run_id,
    )
    db.add(event)
    if commit:
        db.commit()
    logger.info(event_type, extra={"task_id": task_id, "agent_id": agent_id, "status": event_type})
    for fn in _subscribers:
        try:
            fn(event)
        except Exception:  # noqa: BLE001 - subscribers must never break the publisher
            logger.exception("event subscriber failed", extra={"error": event_type})
    return event

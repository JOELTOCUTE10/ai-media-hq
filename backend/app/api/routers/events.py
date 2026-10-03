"""Event feed endpoints (Section 39)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.ops import SystemEvent
from app.models.organization import User

router = APIRouter(prefix="/api/events", tags=["events"])


class EventOut(BaseModel):
    id: int
    event_type: str
    payload: dict
    task_id: int | None
    agent_id: int | None
    created_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[EventOut])
def list_events(event_type: str | None = None, limit: int = 50,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(SystemEvent).filter(SystemEvent.org_id == user.org_id)
    if event_type:
        q = q.filter(SystemEvent.event_type == event_type)
    events = q.order_by(SystemEvent.id.desc()).limit(min(limit, 200)).all()
    return [EventOut(id=e.id, event_type=e.event_type, payload=e.payload or {}, task_id=e.task_id,
                     agent_id=e.agent_id, created_at=e.created_at.isoformat()) for e in events]

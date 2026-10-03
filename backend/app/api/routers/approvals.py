"""Approval center endpoints (Sections 24-25). Publishing requires human approval
by default; the approval queue is listed from real data only."""
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.events import EventType
from app.db.session import get_db
from app.models.organization import User
from app.models.production import Approval
from app.services.event_bus import publish

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class DecisionIn(BaseModel):
    decision: str  # approved | rejected | changes_requested
    notes: str = ""


@router.get("")
def list_approvals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Approval).filter(Approval.org_id == user.org_id)
            .order_by(Approval.id.desc()).limit(100).all())
    return [{"id": a.id, "idea_id": a.idea_id, "status": a.status,
             "requested_by_agent_id": a.requested_by_agent_id,
             "notes": a.notes, "created_at": a.created_at.isoformat()} for a in rows]


@router.post("/{approval_id}/decide")
def decide(approval_id: int, data: DecisionIn, user: User = Depends(require_admin),
           db: Session = Depends(get_db)):
    approval = db.get(Approval, approval_id)
    if approval is None or approval.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found")
    if approval.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Approval already {approval.status}")
    if data.decision not in ("approved", "rejected", "changes_requested"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "decision must be approved|rejected|changes_requested")
    from datetime import datetime
    approval.status = data.decision
    approval.decided_by_user_id = user.id
    approval.decided_at = datetime.now(UTC)
    approval.notes = data.notes
    db.commit()
    event = EventType.APPROVAL_GRANTED if data.decision == "approved" else (
        EventType.APPROVAL_REJECTED if data.decision == "rejected" else EventType.APPROVAL_REQUESTED)
    publish(db, event, {"approval_id": approval.id}, org_id=user.org_id, commit=True)
    return {"id": approval.id, "status": approval.status}

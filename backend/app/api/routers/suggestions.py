"""Agent initiative endpoints: suggestions, auto-assignment, manual trigger."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.agent import Agent
from app.models.initiative import AgentSuggestion
from app.models.organization import Organization, User
from app.services.initiative_service import (
    approve_suggestion,
    generate_suggestions,
    reject_suggestion,
)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


class SuggestionOut(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    agent_department: str
    title: str
    description: str
    rationale: str
    priority: str
    status: str
    task_id: int | None
    proposed_at: str

    model_config = {"from_attributes": True}


class ApproveOut(BaseModel):
    suggestion: SuggestionOut
    task_id: int


def _out(db: Session, s: AgentSuggestion) -> SuggestionOut:
    agent = db.get(Agent, s.agent_id)
    return SuggestionOut(
        id=s.id, agent_id=s.agent_id,
        agent_name=agent.name if agent else "Unknown agent",
        agent_department=agent.department if agent else "",
        title=s.title, description=s.description or "", rationale=s.rationale or "",
        priority=s.priority, status=s.status, task_id=s.task_id,
        proposed_at=s.created_at.isoformat() if s.created_at else "",
    )


@router.get("")
def list_suggestions(status_filter: str = "", user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    q = db.query(AgentSuggestion).filter(AgentSuggestion.org_id == user.org_id)
    if status_filter:
        q = q.filter(AgentSuggestion.status == status_filter)
    rows = q.order_by(AgentSuggestion.id.desc()).limit(100).all()
    return {"suggestions": [_out(db, s) for s in rows],
            "proposed_count": db.query(AgentSuggestion)
                               .filter(AgentSuggestion.org_id == user.org_id,
                                       AgentSuggestion.status == "proposed").count()}


@router.post("/generate")
def trigger_generate(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ask idle agents for proposals right now (manual trigger)."""
    org = db.get(Organization, user.org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    if (org.settings or {}).get("operations_paused"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Operations are paused (kill switch). Resume from Settings.")
    created = generate_suggestions(db, org, force=True)
    return {"created": created}


@router.post("/{suggestion_id}/approve", response_model=ApproveOut)
def approve(suggestion_id: int, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    s = db.get(AgentSuggestion, suggestion_id)
    if s is None or s.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Suggestion not found")
    if s.status != "proposed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Suggestion already {s.status}")
    task = approve_suggestion(db, s, user_id=user.id)
    return {"suggestion": _out(db, s), "task_id": task.id}


@router.post("/{suggestion_id}/reject")
def reject(suggestion_id: int, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    s = db.get(AgentSuggestion, suggestion_id)
    if s is None or s.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Suggestion not found")
    if s.status != "proposed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Suggestion already {s.status}")
    reject_suggestion(db, s, user_id=user.id)
    return {"status": "rejected"}

"""Founder Mode endpoints (Section 7)."""
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.organization import User
from app.models.task import Goal, Task
from app.services.founder_service import create_goal, goal_progress

router = APIRouter(prefix="/api/founder", tags=["founder"])


class GoalIn(BaseModel):
    title: str
    description: str = ""
    channel_slug: str | None = None
    target_date: date_type | None = None


@router.post("/goals", status_code=201)
def create(data: GoalIn, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    goal = create_goal(db, user, data.title, data.description,
                       data.channel_slug, data.target_date)
    return {"id": goal.id, "title": goal.title, "status": goal.status,
            "progress": goal_progress(db, user.org_id, goal)}


@router.get("/goals")
def list_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Goal).filter(Goal.org_id == user.org_id)
            .order_by(Goal.id.desc()).limit(50).all())
    out = []
    for g in rows:
        out.append({"id": g.id, "title": g.title, "description": g.description,
                    "status": g.status, "target_date": str(g.target_date) if g.target_date else None,
                    "progress": goal_progress(db, user.org_id, g)})
    return out


@router.get("/goals/{goal_id}")
def get_goal(goal_id: int, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    goal = db.query(Goal).filter_by(id=goal_id, org_id=user.org_id).first()
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    tasks = db.query(Task).filter_by(goal_id=goal.id).all()
    return {"id": goal.id, "title": goal.title, "description": goal.description,
            "status": goal.status, "target_date": str(goal.target_date) if goal.target_date else None,
            "progress": goal_progress(db, user.org_id, goal),
            "tasks": [{"id": t.id, "title": t.title, "status": t.status,
                       "assigned_agent_id": t.assigned_agent_id,
                       "depends_on": t.depends_on if hasattr(t, "depends_on") else []}
                      for t in tasks]}

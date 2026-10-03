"""Command Center data endpoint (Section 5). Built from real stored data only."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.agent import Agent
from app.models.channel import Channel
from app.models.content import ContentIdea
from app.models.ops import CostRecord, Integration, SystemEvent
from app.models.organization import User
from app.models.production import Approval
from app.models.task import Task

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org_id = user.org_id

    def count(model, *filters):
        q = db.query(func.count(model.id)).filter(model.org_id == org_id)
        for f in filters:
            q = q.filter(f)
        return q.scalar() or 0

    task_counts = dict(
        db.query(Task.status, func.count(Task.id)).filter(Task.org_id == org_id)
        .group_by(Task.status).all()
    )
    integration_status = dict(
        db.query(Integration.key, Integration.status).filter(Integration.org_id == org_id).all()
    )
    recent_events = (
        db.query(SystemEvent).filter(SystemEvent.org_id == org_id)
        .order_by(SystemEvent.id.desc()).limit(10).all()
    )
    month_spend = (db.query(func.sum(CostRecord.amount_usd))
                   .filter(CostRecord.org_id == org_id, func.strftime("%Y-%m", CostRecord.occurred_at)
                           == func.strftime("%Y-%m", func.now())).scalar() or 0.0)

    recommendations = []
    if integration_status.get("ai_openai") != "configured" and integration_status.get("ai_anthropic") != "configured":
        recommendations.append("No AI provider configured - agents cannot run. Set AI_PROVIDER and an API key in .env.")
    if task_counts.get("failed", 0):
        recommendations.append(f"{task_counts['failed']} failed task(s) need attention in Tasks.")
    if task_counts.get("blocked", 0):
        recommendations.append(f"{task_counts['blocked']} blocked task(s) - check permissions or kill switch.")
    if not recommendations:
        recommendations.append("All systems operational - no critical alerts.")

    return {
        "channels": {
            "total": count(Channel),
            "active": count(Channel, Channel.is_active == True),  # noqa: E712
        },
        "agents": {
            "total": count(Agent),
            "active": count(Agent, Agent.status == "active"),
            "paused": count(Agent, Agent.status == "paused"),
        },
        "tasks": {**{s: 0 for s in ["queued", "running", "waiting", "blocked", "completed", "failed", "cancelled"]},
                  **task_counts},
        "content": {
            "in_production": count(ContentIdea, ContentIdea.status == "production"),
            "awaiting_approval": count(Approval, Approval.status == "pending"),
        },
        "integrations": integration_status,
        "costs": {"month_to_date_usd": round(month_spend, 4),
                  "budget_usd": (db.get(__import__('app.models.organization', fromlist=['Organization'])
                                        .Organization, org_id).settings or {}).get("monthly_budget_usd", 100.0)},
        "recent_events": [{"id": e.id, "type": e.event_type, "payload": e.payload,
                           "created_at": e.created_at.isoformat()} for e in recent_events],
        "recommendations": recommendations,
    }

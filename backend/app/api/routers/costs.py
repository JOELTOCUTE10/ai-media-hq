"""Cost intelligence endpoints (Section 30). Aggregations of real CostRecords only."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.channel import Channel
from app.models.ops import CostRecord
from app.models.organization import User

router = APIRouter(prefix="/api/costs", tags=["costs"])


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def total(q):
        return round(q.scalar() or 0.0, 4)

    base = db.query(func.sum(CostRecord.amount_usd)).filter(CostRecord.org_id == user.org_id)

    by_category = (db.query(CostRecord.category, func.sum(CostRecord.amount_usd))
                  .filter(CostRecord.org_id == user.org_id,
                          CostRecord.occurred_at >= month_start)
                  .group_by(CostRecord.category).all())
    by_channel = (db.query(CostRecord.channel_id, func.sum(CostRecord.amount_usd))
                  .filter(CostRecord.org_id == user.org_id,
                          CostRecord.occurred_at >= month_start)
                  .group_by(CostRecord.channel_id).all())
    by_day = (db.query(func.date(CostRecord.occurred_at), func.sum(CostRecord.amount_usd))
              .filter(CostRecord.org_id == user.org_id,
                      CostRecord.occurred_at >= month_start)
              .group_by(func.date(CostRecord.occurred_at)).all())

    from app.models.organization import Organization
    org = db.get(Organization, user.org_id)
    budget = (org.settings or {}).get("monthly_budget_usd", 0) or 0
    month = total(base.filter(CostRecord.occurred_at >= month_start))
    return {
        "today_usd": total(base.filter(CostRecord.occurred_at >= day_start)),
        "month_to_date_usd": month,
        "monthly_budget_usd": budget,
        "budget_used_pct": round(100 * month / budget, 1) if budget else None,
        "by_category": [{"category": c, "amount_usd": round(a or 0, 4)} for c, a in by_category],
        "by_channel": [{"channel": db.get(Channel, cid).name if cid and db.get(Channel, cid) else "unassigned",
                        "amount_usd": round(a or 0, 4)} for cid, a in by_channel],
        "by_day": [{"date": str(d), "amount_usd": round(a or 0, 4)} for d, a in by_day],
    }


@router.get("/records")
def records(limit: int = 100, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    rows = (db.query(CostRecord).filter(CostRecord.org_id == user.org_id)
            .order_by(CostRecord.id.desc()).limit(min(limit, 500)).all())
    return [{"id": r.id, "category": r.category, "amount_usd": r.amount_usd,
             "task_id": r.task_id, "channel_id": r.channel_id,
             "description": r.description,
             "occurred_at": r.occurred_at.isoformat()} for r in rows]

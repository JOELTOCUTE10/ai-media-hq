"""Trend Radar endpoints (Section 15). Trends computed only from real stored signals."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.organization import User
from app.models.research import Trend
from app.services.trend_service import scan

router = APIRouter(prefix="/api/trends", tags=["trends"])


class TrendOut(BaseModel):
    id: int
    topic: str
    title: str
    channel_id: int | None
    lifecycle: str
    score: float
    signals: dict
    evidence: list
    last_updated: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[TrendOut])
def list_trends(channel_id: int | None = None, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    q = db.query(Trend).filter(Trend.org_id == user.org_id)
    if channel_id:
        q = q.filter(Trend.channel_id == channel_id)
    trends = q.order_by(Trend.score.desc()).limit(100).all()
    return [TrendOut(id=t.id, topic=t.topic, title=t.title, channel_id=t.channel_id,
                     lifecycle=t.lifecycle, score=t.score, signals=t.signals or {},
                     evidence=t.evidence or [], last_updated=t.last_updated.isoformat()) for t in trends]


@router.post("/scan")
def run_scan(channel_id: int | None = None, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    trends = scan(db, user.org_id, channel_id)
    if not trends:
        return {"trends": [], "message": "No research documents found in the last 14 days. "
                "Run a research search first - trends are never fabricated."}
    return {"trends": [{"topic": t.topic, "lifecycle": t.lifecycle, "score": t.score} for t in trends]}

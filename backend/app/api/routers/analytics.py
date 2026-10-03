"""Analytics + Learning endpoints (Sections 26, 28)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.events import EventType
from app.db.session import get_db
from app.models.analytics import LearningInsight
from app.models.channel import Channel
from app.models.organization import User
from app.services.analytics_service import channel_rollup, ingest_snapshot, video_rows
from app.services.event_bus import publish
from app.services.learning_service import generate_insights

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class SnapshotIn(BaseModel):
    publishing_job_id: int
    video_title: str = ""
    views: int = 0
    watch_time_minutes: float = 0
    retention_pct: float = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    subscribers_gained: int = 0


@router.post("/snapshots", status_code=201)
def add_snapshot(data: SnapshotIn, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """Ingest a real metrics snapshot (from the YouTube API once linked, or manual entry)."""
    try:
        snap = ingest_snapshot(db, user.org_id, data.model_dump())
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    publish(db, EventType.ANALYTICS_INGESTED,
            {"snapshot_id": snap.id, "publishing_job_id": snap.publishing_job_id,
             "views": snap.views}, org_id=user.org_id, commit=True)
    return {"id": snap.id, "publishing_job_id": snap.publishing_job_id, "views": snap.views}


@router.get("/videos")
def videos(channel_slug: str = "", user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    channel_id = None
    if channel_slug:
        ch = db.query(Channel).filter_by(org_id=user.org_id, slug=channel_slug).first()
        channel_id = ch.id if ch else -1
    return video_rows(db, user.org_id, channel_id)


@router.get("/channels")
def channels(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return channel_rollup(db, user.org_id)


@router.post("/learn")
def learn(channel_slug: str = "", user: User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    """Learning Engine: structured insights from real history (Section 28)."""
    channel_id = None
    if channel_slug:
        ch = db.query(Channel).filter_by(org_id=user.org_id, slug=channel_slug).first()
        channel_id = ch.id if ch else -1
    insights = generate_insights(db, user.org_id, channel_id)
    return [{"id": i.id, "channel_id": i.channel_id, "observation": i.observation,
             "evidence": i.evidence, "sample_size": i.sample_size,
             "recommendation": i.recommendation, "status": i.status} for i in insights]


@router.get("/insights")
def insights(channel_id: int | None = None, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    q = db.query(LearningInsight).filter(LearningInsight.org_id == user.org_id)
    if channel_id:
        q = q.filter(LearningInsight.channel_id == channel_id)
    rows = q.order_by(LearningInsight.id.desc()).limit(50).all()
    return [{"id": i.id, "channel_id": i.channel_id, "observation": i.observation,
             "evidence": i.evidence, "sample_size": i.sample_size,
             "recommendation": i.recommendation, "status": i.status,
             "created_at": i.created_at.isoformat()} for i in rows]

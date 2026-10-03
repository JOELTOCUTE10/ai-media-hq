"""Analytics infrastructure (Section 26).

Composite performance is computed from measurable metrics only, with the
formula documented in code - no black-box "score" and no view-only chasing.
"""
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.analytics import AnalyticsSnapshot
from app.models.channel import Channel
from app.models.content import ContentIdea
from app.models.production import PublishingJob


def composite_score(views: int, retention_pct: float, watch_minutes: float,
                    likes: int, comments: int, shares: int, median_views: float) -> float:
    """0-100 composite: 40% retention, 30% engagement rate, 40%-weighted view factor
    is capped so a viral fluke cannot dominate quality signals.

        engagement_rate = (likes + comments + shares) / max(views, 1)
        score = 40 * (retention_pct / 100)
              + 30 * min(engagement_rate / 0.10, 1)     # 10% engagement = full marks
              + 30 * min(views / max(median_views, 1), 2) / 2
    """
    engagement = (likes + comments + shares) / max(views, 1)
    view_factor = min(views / max(median_views, 1.0), 2.0) / 2.0
    return round(40 * (retention_pct / 100.0)
                 + 30 * min(engagement / 0.10, 1.0)
                 + 30 * view_factor, 2)


def _latest_snapshots(db: Session, org_id: int, channel_id: int | None):
    q = (db.query(AnalyticsSnapshot, PublishingJob, ContentIdea)
         .join(PublishingJob, PublishingJob.id == AnalyticsSnapshot.publishing_job_id)
         .join(ContentIdea, ContentIdea.id == PublishingJob.idea_id)
         .filter(AnalyticsSnapshot.org_id == org_id))
    if channel_id:
        q = q.filter(AnalyticsSnapshot.channel_id == channel_id)
    rows = []
    seen_jobs: set[int] = set()
    for snap, job, idea in q.order_by(AnalyticsSnapshot.captured_at.desc()).all():
        if snap.publishing_job_id in seen_jobs:
            continue
        seen_jobs.add(snap.publishing_job_id)
        rows.append((snap, job, idea))
    return rows


def video_rows(db: Session, org_id: int, channel_id: int | None = None) -> list[dict]:
    rows = _latest_snapshots(db, org_id, channel_id)
    if not rows:
        return []
    median_views = sorted(s.views for s, _, _ in rows)[len(rows) // 2]
    out = []
    for snap, job, idea in rows:
        out.append({
            "publishing_job_id": job.id, "idea_id": idea.id, "title": idea.title,
            "hook": (idea.hook or "")[:120], "published_at": job.published_at.isoformat() if job.published_at else None,
            "views": snap.views, "watch_time_minutes": snap.watch_time_minutes,
            "retention_pct": snap.retention_pct, "likes": snap.likes,
            "comments": snap.comments, "shares": snap.shares,
            "subscribers_gained": snap.subscribers_gained,
            "captured_at": snap.captured_at.isoformat(),
            "composite_score": composite_score(snap.views, snap.retention_pct,
                                               snap.watch_time_minutes, snap.likes,
                                               snap.comments, snap.shares, median_views),
        })
    return sorted(out, key=lambda r: -r["composite_score"])


def channel_rollup(db: Session, org_id: int) -> list[dict]:
    rows = _latest_snapshots(db, org_id, None)
    by_channel: dict[int, list] = {}
    for snap, job, idea in rows:
        by_channel.setdefault(snap.channel_id or 0, []).append((snap, idea))
    out = []
    for cid, items in by_channel.items():
        channel = db.get(Channel, cid)
        sn = [s for s, _ in items]
        views = sum(s.views for s in sn)
        out.append({
            "channel_id": cid, "channel": channel.name if channel else "unknown",
            "videos": len(sn),
            "total_views": views,
            "avg_retention_pct": round(sum(s.retention_pct for s in sn) / len(sn), 2),
            "total_watch_minutes": round(sum(s.watch_time_minutes for s in sn), 1),
            "subscribers_gained": sum(s.subscribers_gained for s in sn),
        })
    return out


def ingest_snapshot(db: Session, org_id: int, data: dict) -> AnalyticsSnapshot:
    """Records a metrics snapshot from a real source (API ingestion or manual entry)."""
    job_id = data.get("publishing_job_id")
    if job_id is None:
        raise ValueError("publishing_job_id is required")
    job = db.query(PublishingJob).filter_by(id=job_id, org_id=org_id).first()
    if job is None:
        raise ValueError("publishing job not found")
    snap = AnalyticsSnapshot(
        org_id=org_id, publishing_job_id=job_id, channel_id=job.channel_id,
        video_title=data.get("video_title", ""),
        views=int(data.get("views", 0)), watch_time_minutes=float(data.get("watch_time_minutes", 0)),
        retention_pct=float(data.get("retention_pct", 0)), likes=int(data.get("likes", 0)),
        comments=int(data.get("comments", 0)), shares=int(data.get("shares", 0)),
        subscribers_gained=int(data.get("subscribers_gained", 0)),
        captured_at=datetime.now(UTC),
    )
    db.add(snap)
    db.flush()
    return snap

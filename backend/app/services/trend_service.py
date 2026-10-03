"""Trend Radar (Sections 14-15).

Trends are computed ONLY from stored ResearchDocuments - multiple signals,
documented inputs, and a documented score. Social documents count as
trend-discovery signals, never as factual evidence.
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.events import EventType
from app.models.research import ResearchDocument, Trend
from app.services.event_bus import publish

RECENT_DAYS = 7
SCORE_DOC_WEIGHT = 6.0
SCORE_GROWTH_WEIGHT = 20.0
SCORE_SOCIAL_WEIGHT = 1.5


def _lifecycle(recent: int, prior: int, age_days: float) -> str:
    if prior == 0 and recent > 0 and age_days <= RECENT_DAYS:
        return "emerging"
    ratio = recent / prior if prior else 2.0
    if ratio >= 1.5:
        return "growing"
    if ratio < 0.75:
        return "declining"
    return "stable"


def scan(db: Session, org_id: int, channel_id: int | None = None) -> list[Trend]:
    now = datetime.now(UTC)
    window_start = now - timedelta(days=RECENT_DAYS * 2)
    stmt = (
        db.query(
            ResearchDocument.topic,
            func.count(ResearchDocument.id),
            func.min(ResearchDocument.created_at),
        )
        .filter(
            ResearchDocument.org_id == org_id,
            ResearchDocument.topic != "",
            ResearchDocument.created_at >= window_start,
        )
    )
    if channel_id:
        stmt = stmt.filter(ResearchDocument.channel_id == channel_id)
    rows = stmt.group_by(ResearchDocument.topic).all()
    if not rows:
        return []

    cutoff = now - timedelta(days=RECENT_DAYS)
    updated: list[Trend] = []
    for topic, total, first_seen in rows:
        q = db.query(ResearchDocument).filter(
            ResearchDocument.org_id == org_id, ResearchDocument.topic == topic)
        if channel_id:
            q = q.filter(ResearchDocument.channel_id == channel_id)
        docs = q.all()
        recent_docs = [d for d in docs if d.created_at.replace(tzinfo=d.created_at.tzinfo or UTC) >= cutoff]
        prior_docs = [d for d in docs if d not in recent_docs]
        recent, prior = len(recent_docs), len(prior_docs)

        social = sum(1 for d in recent_docs if d.source_type == "social")
        ratio = (recent / prior) if prior else (2.0 if recent else 0.0)
        age_days = (now - first_seen.replace(tzinfo=first_seen.tzinfo or UTC)).total_seconds() / 86400

        # Documented score: volume + growth momentum + (damped) social signal.
        score = round(min(100.0, recent * SCORE_DOC_WEIGHT + ratio * SCORE_GROWTH_WEIGHT
                          + social * SCORE_SOCIAL_WEIGHT), 2)
        lifecycle = _lifecycle(recent, prior, age_days)
        signals = {
            "documents_recent_7d": recent,
            "documents_prior_7d": prior,
            "growth_ratio": round(ratio, 2),
            "social_signal_docs": social,
            "formula": "min(100, recent*6 + growth_ratio*20 + social_docs*1.5)",
        }
        evidence = [{"title": d.title, "url": d.url, "source_type": d.source_type} for d in recent_docs[:10]]

        trend = db.query(Trend).filter_by(org_id=org_id, channel_id=channel_id, topic=topic).first()
        if not trend:
            trend = Trend(org_id=org_id, channel_id=channel_id, topic=topic, first_detected=now)
            db.add(trend)
            if lifecycle in ("emerging", "growing"):
                publish(db, EventType.TREND_DETECTED,
                        {"topic": topic, "lifecycle": lifecycle, "score": score},
                        org_id=org_id)
        trend.title = topic.replace("_", " ").title()
        trend.lifecycle = lifecycle
        trend.score = score
        trend.signals = signals
        trend.evidence = evidence
        trend.last_updated = now
        updated.append(trend)

    db.commit()
    return updated

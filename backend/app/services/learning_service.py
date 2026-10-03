"""Learning Engine (Section 28).

Analyzes historical performance and generates structured insights with
explicit evidence, sample size and limitations. Small samples are NEVER
turned into universal rules - they are recorded as insufficient.
"""

from sqlalchemy.orm import Session

from app.core.events import EventType
from app.models.analytics import AnalyticsSnapshot, LearningInsight
from app.models.channel import Channel
from app.models.content import ContentIdea
from app.models.production import PublishingJob
from app.services.event_bus import publish

MIN_GROUP_SIZE = 5  # honest minimum sample per comparison group


def generate_insights(db: Session, org_id: int, channel_id: int | None = None) -> list[LearningInsight]:
    """Compares average retention across hook styles within each channel."""
    q = (db.query(AnalyticsSnapshot, PublishingJob, ContentIdea)
         .join(PublishingJob, PublishingJob.id == AnalyticsSnapshot.publishing_job_id)
         .join(ContentIdea, ContentIdea.id == PublishingJob.idea_id)
         .filter(AnalyticsSnapshot.org_id == org_id))
    if channel_id:
        q = q.filter(AnalyticsSnapshot.channel_id == channel_id)
    rows = q.order_by(AnalyticsSnapshot.captured_at.desc()).all()

    # latest snapshot per idea
    seen: set[int] = set()
    latest = []
    for snap, job, idea in rows:
        if idea.id in seen:
            continue
        seen.add(idea.id)
        latest.append((snap, idea))

    created: list[LearningInsight] = []
    by_channel: dict[int, list] = {}
    for snap, idea in latest:
        by_channel.setdefault(snap.channel_id or 0, []).append((snap, idea))

    for cid, items in by_channel.items():
        channel = db.get(Channel, cid)
        cname = channel.name if channel else "unknown"

        # group by hook "style" tag recorded on the idea (content rules define styles);
        # fall back to the first 3 words of the hook as a coarse grouping key.
        groups: dict[str, list[float]] = {}
        for snap, idea in items:
            key = str((idea.why_selected or {}).get("hook_style") or " ".join((idea.hook or "unknown").split()[:3]) or "unknown")
            groups.setdefault(key, []).append(snap.retention_pct)

        sufficient = {k: v for k, v in groups.items() if len(v) >= MIN_GROUP_SIZE}
        if len(sufficient) < 2:
            insight = LearningInsight(
                org_id=org_id, channel_id=cid,
                observation=f"Not enough data yet to compare hook styles on {cname} "
                            f"({len(items)} video(s), {len(groups)} group(s); need >= {MIN_GROUP_SIZE} per group and >= 2 groups).",
                evidence={"videos": len(items), "groups": {k: len(v) for k, v in groups.items()}},
                sample_size=len(items),
                recommendation="Keep publishing and ingesting analytics; the comparison will run automatically once samples exist.",
                status="insufficient_sample",
            )
            db.add(insight)
            db.flush()
            created.append(insight)
            continue

        best = max(sufficient.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
        worst = min(sufficient.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
        best_avg = sum(best[1]) / len(best[1])
        worst_avg = sum(worst[1]) / len(worst[1])
        insight = LearningInsight(
            org_id=org_id, channel_id=cid,
            observation=f"On {cname}, videos with hook style '{best[0]}' had higher average "
                        f"retention during the observed period ({best_avg:.1f}%) than '{worst[0]}' ({worst_avg:.1f}%).",
            evidence={"groups": {k: {"n": len(v), "avg_retention_pct": round(sum(v) / len(v), 2)}
                                 for k, v in sufficient.items()}},
            sample_size=sum(len(v) for v in sufficient.values()),
            recommendation=f"Consider prioritizing '{best[0]}' style hooks on {cname} in upcoming ideas, "
                          "while continuing to test alternatives (see Experiment Lab).",
            status="new",
        )
        db.add(insight)
        db.flush()
        created.append(insight)

    if created:
        publish(db, EventType.LEARNING_INSIGHT_CREATED,
                {"created": len(created), "channel_id": channel_id},
                org_id=org_id, commit=False)
    db.commit()
    return created

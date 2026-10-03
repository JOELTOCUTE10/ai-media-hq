"""Daily Executive Report (Section 32) - generated from actual stored data.
Sections with no real data say so explicitly; nothing is invented."""
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.events import EventType
from app.models.analytics import Experiment
from app.models.ops import CostRecord, Report
from app.models.organization import Organization
from app.models.production import Approval, PublishingJob
from app.models.research import Trend
from app.models.task import Task
from app.services.analytics_service import channel_rollup, video_rows
from app.services.event_bus import publish


def build_daily_report(db: Session, org: Organization, report_date: date | None = None) -> Report:
    rd = report_date or datetime.now(UTC).date()
    day_start = datetime(rd.year, rd.month, rd.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)
    org_id = org.id

    published = (db.query(PublishingJob)
                 .filter(PublishingJob.org_id == org_id, PublishingJob.status == "published",
                         PublishingJob.published_at >= day_start, PublishingJob.published_at < day_end).all())
    awaiting = (db.query(Approval).filter(Approval.org_id == org_id,
                                          Approval.status == "pending").count())
    failed_jobs = (db.query(PublishingJob)
                   .filter(PublishingJob.org_id == org_id, PublishingJob.status == "failed",
                           PublishingJob.updated_at >= day_start).all())

    videos = video_rows(db, org_id)
    top = videos[:3]
    under = sorted(videos, key=lambda v: v["composite_score"])[:3] if videos else []

    trends = (db.query(Trend).filter(Trend.org_id == org_id)
              .order_by(Trend.score.desc()).limit(5).all())
    experiments = (db.query(Experiment).filter(Experiment.org_id == org_id,
                                               Experiment.status.in_(["running", "completed"]))
                   .order_by(Experiment.id.desc()).limit(5).all())

    day_cost = (db.query(func.sum(CostRecord.amount_usd))
                .filter(CostRecord.org_id == org_id,
                        CostRecord.occurred_at >= day_start,
                        CostRecord.occurred_at < day_end).scalar() or 0.0)
    month_start = day_start.replace(day=1)
    month_cost = (db.query(func.sum(CostRecord.amount_usd))
                  .filter(CostRecord.org_id == org_id,
                          CostRecord.occurred_at >= month_start).scalar() or 0.0)
    budget = (org.settings or {}).get("monthly_budget_usd", 0) or 0

    failed_tasks = (db.query(Task)
                    .filter(Task.org_id == org_id, Task.status == "failed",
                            Task.updated_at >= day_start).all())
    queued_tasks = (db.query(Task).filter(Task.org_id == org_id,
                                          Task.status.in_(["queued", "running"])).count())

    recommendations: list[str] = []
    if awaiting:
        recommendations.append(f"{awaiting} content item(s) awaiting your approval in the Approval Center.")
    if failed_jobs:
        recommendations.append(f"{len(failed_jobs)} publishing job(s) failed today - check Publishing.")
    if failed_tasks:
        recommendations.append(f"{len(failed_tasks)} task(s) failed today - review the Tasks page.")
    if budget and month_cost >= budget * 0.8:
        recommendations.append(f"Monthly spend is ${month_cost:.2f} of ${budget:.2f} budget (>= 80%).")
    if videos:
        if top:
            recommendations.append(f"'{top[0]['title']}' is the strongest performer today "
                                   f"(composite {top[0]['composite_score']}).")
    else:
        recommendations.append("No analytics data ingested yet - publish and ingest metrics to unlock insights.")
    if trends:
        recommendations.append(f"Trend to consider: {trends[0].topic} (score {trends[0].score:.0f}, {trends[0].lifecycle}).")

    content = {
        "report_date": rd.isoformat(),
        "videos_published_today": [{"idea_id": j.idea_id, "video_id": j.video_id,
                                    "published_at": j.published_at.isoformat()} for j in published],
        "awaiting_approval": awaiting,
        "top_performers": top,
        "underperformers": under,
        "trends": [{"topic": t.topic, "lifecycle": t.lifecycle, "score": t.score,
                    "why": t.signals} for t in trends],
        "experiments": [{"name": e.name, "status": e.status, "variable": e.variable} for e in experiments],
        "costs": {"today_usd": round(day_cost, 4), "month_to_date_usd": round(month_cost, 4),
                  "monthly_budget_usd": budget},
        "system_failures": {"failed_tasks": len(failed_tasks), "failed_publishing_jobs": len(failed_jobs)},
        "work_in_progress": queued_tasks,
        "channel_rollup": channel_rollup(db, org_id),
        "recommendations": recommendations,
    }

    report = Report(org_id=org_id, report_type="daily", report_date=rd, content=content)
    db.add(report)
    db.flush()
    publish(db, EventType.REPORT_GENERATED, {"report_id": report.id, "report_date": rd.isoformat()},
            org_id=org_id, commit=False)
    db.commit()
    return report

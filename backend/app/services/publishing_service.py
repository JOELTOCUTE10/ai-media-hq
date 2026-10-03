"""Publish execution shared by the API and the scheduler (Section 40).

Runs the readiness gate, then the REAL YouTube upload. Without a connected
account or with any gate failure the job is failed with the exact reason.
"""
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.core.events import EventType
from app.models.content import ContentIdea
from app.models.organization import Organization
from app.models.production import Asset, PublishingJob
from app.services.event_bus import publish
from app.services.publishing_guard import check_publish_readiness


def execute_publish(db: Session, org: Organization, job: PublishingJob) -> PublishingJob:
    """Attempts a real publish. Returns the updated job (status tells the truth)."""
    if job.status == "published":
        return job

    ready, blockers = check_publish_readiness(db, org, job.idea_id)
    if not ready:
        job.status = "failed"
        job.error = "Readiness gate: " + "; ".join(blockers)
        db.commit()
        publish(db, EventType.PUBLISH_BLOCKED, {"job_id": job.id, "blockers": blockers},
                org_id=org.id, commit=True)
        return job

    from app.models.ops import OauthToken
    token = db.query(OauthToken).filter_by(org_id=org.id, provider="youtube").first()
    if token is None or not token.access_token:
        job.status = "failed"
        job.error = ("YouTube account not connected. Complete OAuth via "
                     "/api/publishing/youtube/connect (see docs/INTEGRATIONS.md).")
        db.commit()
        return job

    asset = (db.query(Asset).filter_by(idea_id=job.idea_id)
             .order_by(Asset.id.desc()).first())
    if asset is None or not asset.url:
        job.status = "failed"
        job.error = "No produced asset exists for this idea. Run a production job first."
        db.commit()
        return job

    meta = job.metadata_json or {}
    title = str(meta.get("title") or "")
    description = str(meta.get("description") or "")
    if not title or not description:
        job.status = "failed"
        job.error = "Publishing metadata requires title and description."
        db.commit()
        return job

    job.status = "uploading"
    db.commit()
    try:
        from app.integrations.youtube import upload_video
        media = httpx.get(asset.url, timeout=300).content
        video_id = upload_video(token.access_token, title, description,
                                meta.get("tags", []), media, meta.get("privacy", "public"))
    except Exception as exc:  # recorded, never swallowed, never faked
        job.status = "failed"
        job.error = f"{type(exc).__name__}: {exc}"
        db.commit()
        publish(db, EventType.PUBLISH_FAILED, {"job_id": job.id, "error": job.error},
                org_id=org.id, commit=True)
        return job

    job.status = "published"
    job.video_id = video_id
    job.published_at = datetime.now(UTC)
    job.error = None
    idea = db.get(ContentIdea, job.idea_id)
    if idea and idea.status not in ("published", "analyzed"):
        idea.status = "published"
    db.commit()
    publish(db, EventType.VIDEO_PUBLISHED, {"job_id": job.id, "video_id": video_id},
            org_id=org.id, commit=True)
    return job

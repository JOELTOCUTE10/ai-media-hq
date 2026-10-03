"""Publishing endpoints (Section 25): approval center integration, YouTube OAuth,
scheduling and uploads. Uploads are NEVER faked - without credentials the job
fails with setup guidance."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.events import EventType
from app.db.session import get_db
from app.models.content import ContentIdea
from app.models.ops import Integration, OauthToken
from app.models.organization import Organization, User
from app.models.production import PublishingJob
from app.services.event_bus import publish

router = APIRouter(prefix="/api/publishing", tags=["publishing"])


class PublishJobIn(BaseModel):
    idea_id: int
    platform: str = "youtube"
    scheduled_at: datetime | None = None
    metadata: dict = {}  # title, description, tags


@router.get("/youtube/status")
def youtube_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_settings()
    configured = bool(s.YOUTUBE_CLIENT_ID and s.YOUTUBE_CLIENT_SECRET)
    token = db.query(OauthToken).filter_by(org_id=user.org_id, provider="youtube").first()
    return {"oauth_app_configured": configured,
            "channel_connected": bool(token and token.refresh_token),
            "redirect_uri": s.YOUTUBE_REDIRECT_URI or "http://localhost:8000/api/publishing/youtube/callback",
            "setup_docs": "docs/INTEGRATIONS.md#youtube-publishing"}


@router.get("/youtube/connect")
def youtube_connect(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.integrations.youtube import YouTubeNotConfiguredError, consent_url

    s = get_settings()
    try:
        url = consent_url(s.YOUTUBE_REDIRECT_URI or "http://localhost:8000/api/publishing/youtube/callback",
                          state=str(user.org_id))
    except YouTubeNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    return {"consent_url": url}


@router.get("/youtube/callback")
def youtube_callback(code: str = "", state: str = "", error: str = "",
                     db: Session = Depends(get_db)):
    """OAuth callback - completes the real token exchange and stores the grant."""
    from app.integrations.youtube import YouTubeNotConfiguredError, YouTubePublishError, exchange_code

    if error or not code:
        return {"status": "error", "detail": f"Authorization failed: {error or 'no code'}"}
    org_id = int(state) if state and state.isdigit() else _default_org(db)
    s = get_settings()
    try:
        data = exchange_code(code, s.YOUTUBE_REDIRECT_URI or "http://localhost:8000/api/publishing/youtube/callback")
    except (YouTubeNotConfiguredError, YouTubePublishError) as exc:
        return {"status": "error", "detail": str(exc)}
    expires_at = datetime.now(UTC)
    from datetime import timedelta
    expires_at = expires_at + timedelta(seconds=data.get("expires_in", 3600))
    token = db.query(OauthToken).filter_by(org_id=org_id, provider="youtube").first()
    if token is None:
        token = OauthToken(org_id=org_id, provider="youtube")
        db.add(token)
    token.access_token = data.get("access_token", "")
    if data.get("refresh_token"):
        token.refresh_token = data.get("refresh_token")
    token.expires_at = expires_at
    token.scope = data.get("scope", "")
    integ = db.query(Integration).filter_by(org_id=org_id, key="youtube_publishing").first()
    if integ:
        integ.status = "configured"
    db.commit()
    publish(db, EventType.INTEGRATION_STATUS_CHANGED,
            {"integration": "youtube_publishing", "status": "configured"}, org_id=org_id, commit=True)
    return {"status": "connected", "detail": "YouTube account linked. Tokens are stored server-side and never exposed."}


def _default_org(db: Session) -> int:
    org = db.query(Organization).order_by(Organization.id).first()
    if org is None:
        raise HTTPException(404, "No organization exists")
    return org.id


@router.post("/jobs", status_code=201)
def create_publish_job(data: PublishJobIn, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    idea = db.query(ContentIdea).filter_by(id=data.idea_id, org_id=user.org_id).first()
    if idea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Idea not found")
    job = PublishingJob(org_id=user.org_id, idea_id=data.idea_id, channel_id=idea.channel_id,
                        platform=data.platform,
                        status="scheduled" if data.scheduled_at else "pending",
                        scheduled_at=data.scheduled_at, metadata_json=data.metadata)
    db.add(job)
    db.commit()
    if data.scheduled_at:
        publish(db, EventType.PUBLISHING_SCHEDULED,
                {"job_id": job.id, "scheduled_at": data.scheduled_at.isoformat()},
                org_id=user.org_id, commit=True)
    return {"id": job.id, "idea_id": job.idea_id, "status": job.status,
            "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
            "note": "Publishing still requires the readiness gate at publish time."}


@router.post("/jobs/{job_id}/publish")
def publish_now(job_id: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Runs the readiness gate, then the real YouTube upload. Nothing is faked."""
    from app.services.publishing_service import execute_publish

    job = db.query(PublishingJob).filter_by(id=job_id, org_id=user.org_id).first()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publishing job not found")
    if job.status == "published":
        raise HTTPException(status.HTTP_409_CONFLICT, "Already published")

    org = db.get(Organization, user.org_id)
    execute_publish(db, org, job)
    if job.status != "published":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            {"detail": "Publishing blocked or failed",
                             "status": job.status, "reason": job.error})
    return {"id": job.id, "status": "published", "video_id": job.video_id}


@router.get("/jobs")
def list_jobs(idea_id: int | None = None, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    q = db.query(PublishingJob).filter(PublishingJob.org_id == user.org_id)
    if idea_id:
        q = q.filter(PublishingJob.idea_id == idea_id)
    rows = q.order_by(PublishingJob.id.desc()).limit(100).all()
    return [{"id": j.id, "idea_id": j.idea_id, "platform": j.platform, "status": j.status,
             "video_id": j.video_id, "scheduled_at": j.scheduled_at.isoformat() if j.scheduled_at else None,
             "published_at": j.published_at.isoformat() if j.published_at else None,
             "error": j.error, "metadata": j.metadata_json} for j in rows]

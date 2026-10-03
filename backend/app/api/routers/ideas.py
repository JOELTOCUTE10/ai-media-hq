"""Content Idea Engine, claims, Content Passport (Sections 16, 19, 20, 37)."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.events import EventType
from app.db.session import get_db
from app.models.analytics import AnalyticsSnapshot
from app.models.channel import Channel
from app.models.content import Claim, ContentIdea, Script, ScriptVersion
from app.models.organization import User
from app.models.production import Approval, ProductionJob, PublishingJob, QualityCheck, RightsRecord
from app.services.event_bus import publish
from app.services.qc_service import latest_script_version
from app.services.strategy_room import run_strategy_room

router = APIRouter(prefix="/api/ideas", tags=["ideas"])

TRANSITIONS = {
    "research": ["candidate"],
    "candidate": ["reviewed", "rejected"],
    "reviewed": ["approved", "rejected"],
    "approved": ["production"],
    "production": ["published", "archived"],
    "published": ["analyzed"],
    "analyzed": [], "rejected": ["archived"], "archived": ["candidate"],
}


class IdeaIn(BaseModel):
    channel_slug: str
    title: str
    topic: str = ""
    hook: str = ""
    description: str = ""
    target_audience: str = ""
    source_evidence: list = []
    trend_evidence: list = []
    complexity: str = "medium"
    confidence: float = 0.0


class ClaimIn(BaseModel):
    text: str
    source: str = ""
    source_url: str = ""
    source_type: str = "secondary"
    notes: str = ""


class ClaimVerifyIn(BaseModel):
    status: str  # verified | partially_supported | disputed | unsupported | needs_review
    confidence: float = 0.0
    notes: str = ""
    reviewer_agent_key: str = "fact_verification"


def _idea_or_404(db: Session, org_id: int, idea_id: int) -> ContentIdea:
    idea = db.query(ContentIdea).filter_by(id=idea_id, org_id=org_id).first()
    if idea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Idea not found")
    return idea


@router.post("", status_code=201)
def create_idea(data: IdeaIn, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    channel = db.query(Channel).filter_by(org_id=user.org_id, slug=data.channel_slug).first()
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Channel '{data.channel_slug}' not found")
    idea = ContentIdea(org_id=user.org_id, channel_id=channel.id, title=data.title,
                       topic=data.topic, hook=data.hook, description=data.description,
                       target_audience=data.target_audience,
                       source_evidence=data.source_evidence, trend_evidence=data.trend_evidence,
                       complexity=data.complexity, confidence=data.confidence,
                       status="candidate",
                       why_selected={"source_evidence": data.source_evidence,
                                     "trend_evidence": data.trend_evidence})
    db.add(idea)
    db.commit()
    publish(db, EventType.IDEA_CREATED, {"idea_id": idea.id, "title": idea.title},
            org_id=user.org_id, commit=True)
    return idea_out(db, idea)


@router.get("")
def list_ideas(status: str = "", channel_slug: str = "", limit: int = 100,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(ContentIdea).filter(ContentIdea.org_id == user.org_id)
    if status:
        q = q.filter(ContentIdea.status == status)
    if channel_slug:
        ch = db.query(Channel).filter_by(org_id=user.org_id, slug=channel_slug).first()
        q = q.filter(ContentIdea.channel_id == (ch.id if ch else -1))
    rows = q.order_by(ContentIdea.id.desc()).limit(min(limit, 500)).all()
    return [idea_out(db, i) for i in rows]


def idea_out(db: Session, i: ContentIdea) -> dict:
    channel = db.get(Channel, i.channel_id)
    return {"id": i.id, "title": i.title, "topic": i.topic, "hook": i.hook,
            "description": i.description, "channel": channel.name if channel else "",
            "channel_slug": channel.slug if channel else "", "status": i.status,
            "complexity": i.complexity, "confidence": i.confidence,
            "why_selected": i.why_selected, "created_at": i.created_at.isoformat()}


@router.get("/{idea_id}")
def get_idea(idea_id: int, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """The Content Passport (Section 20): full auditable history of one video."""
    idea = _idea_or_404(db, user.org_id, idea_id)
    script = db.query(Script).filter_by(idea_id=idea.id).first()
    versions = ([{"version": v.version, "hook": v.hook, "body": v.body[:400], "cta": v.cta,
                  "changes": v.changes, "review_status": v.review_status,
                  "author_agent_id": v.author_agent_id}
                 for v in db.query(ScriptVersion).filter_by(script_id=script.id)
                 .order_by(ScriptVersion.version).all()] if script else [])
    claims = [{"id": c.id, "text": c.text, "status": c.status, "source_url": c.source_url,
               "source_type": c.source_type, "confidence": c.confidence, "notes": c.notes}
              for c in db.query(Claim).filter_by(idea_id=idea.id).all()]
    qcs = [{"id": q.id, "result": q.result, "reasons": q.reasons, "checks": q.checks,
            "created_at": q.created_at.isoformat()}
           for q in db.query(QualityCheck).filter_by(idea_id=idea.id)
           .order_by(QualityCheck.id.desc()).all()]
    approvals = [{"id": a.id, "status": a.status, "notes": a.notes,
                  "decided_at": a.decided_at.isoformat() if a.decided_at else None}
                 for a in db.query(Approval).filter_by(idea_id=idea.id).all()]
    jobs = [{"id": p.id, "provider": p.provider, "status": p.status, "cost_usd": p.cost_usd,
             "error": p.error} for p in db.query(ProductionJob).filter_by(idea_id=idea.id).all()]
    pub = [{"id": p.id, "platform": p.platform, "status": p.status, "video_id": p.video_id,
            "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
            "published_at": p.published_at.isoformat() if p.published_at else None}
           for p in db.query(PublishingJob).filter_by(idea_id=idea.id).all()]
    snaps = [{"views": s.views, "retention_pct": s.retention_pct,
              "captured_at": s.captured_at.isoformat()}
             for s in db.query(AnalyticsSnapshot).filter(AnalyticsSnapshot.publishing_job_id.in_(
                 [p.id for p in db.query(PublishingJob.id).filter_by(idea_id=idea.id).all()])
             ).all()] if pub else []
    return {"idea": idea_out(db, idea), "script_versions": versions, "claims": claims,
            "quality_checks": qcs, "approvals": approvals, "production_jobs": jobs,
            "publishing_jobs": pub, "analytics": snaps,
            "rights": [{"id": r.id, "status": r.status, "content_description": r.content_description}
                       for r in db.query(RightsRecord).filter_by(idea_id=idea.id).all()]}


@router.post("/{idea_id}/status")
def change_status(idea_id: int, new_status: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    idea = _idea_or_404(db, user.org_id, idea_id)
    allowed = TRANSITIONS.get(idea.status, [])
    if new_status not in allowed:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"Cannot move from '{idea.status}' to '{new_status}'. Allowed: {allowed}")
    idea.status = new_status
    db.commit()
    publish(db, EventType.IDEA_STATUS_CHANGED,
            {"idea_id": idea.id, "from": idea.status, "to": new_status},
            org_id=user.org_id, commit=True)
    return {"id": idea.id, "status": idea.status}


@router.post("/{idea_id}/strategy-room")
def strategy_room(idea_id: int, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """Structured multi-agent review (Section 17). Honest per-reviewer results."""
    idea = _idea_or_404(db, user.org_id, idea_id)
    from app.models.organization import Organization
    org = db.get(Organization, user.org_id)
    return run_strategy_room(db, org, idea)


@router.post("/{idea_id}/claims", status_code=201)
def add_claim(idea_id: int, data: ClaimIn, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    idea = _idea_or_404(db, user.org_id, idea_id)
    sv = latest_script_version(db, idea.id)
    c = Claim(org_id=user.org_id, idea_id=idea.id,
              script_version_id=sv.id if sv else None, text=data.text,
              source=data.source, source_url=data.source_url,
              source_type=data.source_type, status="needs_review",
              confidence=0.0, notes=data.notes)
    db.add(c)
    db.commit()
    return {"id": c.id, "text": c.text, "status": c.status}


@router.post("/claims/{claim_id}/verify")
def verify_claim(claim_id: int, data: ClaimVerifyIn,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Claim).filter_by(id=claim_id, org_id=user.org_id).first()
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    allowed = ("verified", "partially_supported", "disputed", "unsupported", "needs_review")
    if data.status not in allowed:
        raise HTTPException(400, f"status must be one of {allowed}")
    c.status = data.status
    c.confidence = data.confidence
    c.notes = data.notes
    db.commit()
    publish(db, EventType.CLAIM_VERIFIED if data.status == "verified" else EventType.CLAIM_FLAGGED,
            {"claim_id": c.id, "status": c.status}, org_id=user.org_id, commit=True)
    return {"id": c.id, "status": c.status, "confidence": c.confidence}


@router.post("/{idea_id}/archive")
def archive(idea_id: int, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    """Content Graveyard (Section 29): rejected/outdated ideas stay searchable."""
    idea = _idea_or_404(db, user.org_id, idea_id)
    idea.status = "archived"
    db.commit()
    return {"id": idea.id, "status": idea.status}

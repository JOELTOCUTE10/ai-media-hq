"""Script Engine endpoints (Section 18): versions, revisions, review status."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.events import EventType
from app.db.session import get_db
from app.models.content import ContentIdea, Script, ScriptVersion
from app.models.organization import User
from app.services.event_bus import publish

router = APIRouter(prefix="/api/scripts", tags=["scripts"])


class VersionIn(BaseModel):
    hook: str = ""
    body: str = ""
    transitions: str = ""
    ending: str = ""
    cta: str = ""
    pacing: dict = {}
    visual_suggestions: list = []
    narration_notes: str = ""
    on_screen_text: list = []
    changes: str = ""
    author_agent_key: str = "script"


class ReviewIn(BaseModel):
    decision: str  # approved | changes_requested
    notes: str = ""


@router.post("", status_code=201)
def create_script(idea_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    idea = db.query(ContentIdea).filter_by(id=idea_id, org_id=user.org_id).first()
    if idea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Idea not found")
    script = db.query(Script).filter_by(idea_id=idea_id).first()
    if script:
        return {"id": script.id, "idea_id": idea_id, "current_version": script.current_version}
    script = Script(org_id=user.org_id, idea_id=idea_id, current_version=0)
    db.add(script)
    db.commit()
    return {"id": script.id, "idea_id": idea_id, "current_version": 0}


@router.post("/{script_id}/versions", status_code=201)
def add_version(script_id: int, data: VersionIn,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    script = db.query(Script).filter_by(id=script_id, org_id=user.org_id).first()
    if script is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Script not found")
    from app.models.agent import Agent
    author = db.query(Agent).filter_by(org_id=user.org_id, key=data.author_agent_key).first()
    version = script.current_version + 1
    sv = ScriptVersion(script_id=script.id, version=version,
                      author_agent_id=author.id if author else None,
                      hook=data.hook, body=data.body, transitions=data.transitions,
                      ending=data.ending, cta=data.cta, pacing=data.pacing,
                      visual_suggestions=data.visual_suggestions,
                      narration_notes=data.narration_notes,
                      on_screen_text=data.on_screen_text, changes=data.changes,
                      review_status="draft", approval_status="pending")
    db.add(sv)
    script.current_version = version
    db.commit()
    publish(db, EventType.SCRIPT_READY, {"script_id": script.id, "version": version},
            org_id=user.org_id, commit=True)
    return {"script_id": script.id, "version": sv.version, "review_status": sv.review_status}


@router.get("/{script_id}/versions")
def list_versions(script_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    script = db.query(Script).filter_by(id=script_id, org_id=user.org_id).first()
    if script is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Script not found")
    rows = (db.query(ScriptVersion).filter_by(script_id=script_id)
            .order_by(ScriptVersion.version.desc()).all())
    return [{"version": v.version, "hook": v.hook, "body": v.body, "ending": v.ending,
             "cta": v.cta, "changes": v.changes, "review_status": v.review_status,
             "approval_status": v.approval_status,
             "author_agent_id": v.author_agent_id} for v in rows]


@router.get("/{script_id}/latest")
def latest_version(script_id: int, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    script = db.query(Script).filter_by(id=script_id, org_id=user.org_id).first()
    if script is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Script not found")
    v = (db.query(ScriptVersion).filter_by(script_id=script_id)
         .order_by(ScriptVersion.version.desc()).first())
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No versions yet")
    return {"version": v.version, "hook": v.hook, "body": v.body, "transitions": v.transitions,
            "ending": v.ending, "cta": v.cta, "pacing": v.pacing,
            "visual_suggestions": v.visual_suggestions, "narration_notes": v.narration_notes,
            "on_screen_text": v.on_screen_text, "changes": v.changes,
            "review_status": v.review_status, "approval_status": v.approval_status}


@router.post("/{script_id}/versions/{version}/review")
def review_version(script_id: int, version: int, data: ReviewIn,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    v = db.query(ScriptVersion).filter_by(script_id=script_id, version=version).first()
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Script version not found")
    if data.decision not in ("approved", "changes_requested"):
        raise HTTPException(400, "decision must be approved|changes_requested")
    v.review_status = data.decision
    if data.decision == "approved":
        v.approval_status = "approved"
    if data.notes:
        v.changes = (v.changes + "\n" if v.changes else "") + data.notes
    db.commit()
    return {"version": v.version, "review_status": v.review_status}

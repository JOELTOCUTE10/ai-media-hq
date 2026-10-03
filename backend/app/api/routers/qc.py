"""Quality Control endpoints (Section 23)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.content import ContentIdea
from app.models.organization import User
from app.models.production import QualityCheck
from app.services.qc_service import run_qc

router = APIRouter(prefix="/api/qc", tags=["quality"])


@router.post("/run")
def run(idea_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(ContentIdea).filter_by(id=idea_id, org_id=user.org_id).first():
        raise HTTPException(404, "Idea not found")
    qc = run_qc(db, user.org_id, idea_id)
    return {"id": qc.id, "idea_id": idea_id, "result": qc.result,
            "checks": qc.checks, "reasons": qc.reasons}


@router.get("")
def list_checks(idea_id: int | None = None, limit: int = 50,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(QualityCheck).filter(QualityCheck.org_id == user.org_id)
    if idea_id:
        q = q.filter(QualityCheck.idea_id == idea_id)
    rows = q.order_by(QualityCheck.id.desc()).limit(min(limit, 200)).all()
    return [{"id": r.id, "idea_id": r.idea_id, "result": r.result,
             "reasons": r.reasons, "checks": r.checks,
             "created_at": r.created_at.isoformat()} for r in rows]

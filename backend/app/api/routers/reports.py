"""Report endpoints (Section 32). Built from actual stored data only."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.ops import Report
from app.models.organization import Organization, User
from app.services.report_service import build_daily_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/daily")
def daily(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = db.get(Organization, user.org_id)
    report = build_daily_report(db, org)
    return {"id": report.id, "content": report.content}


@router.get("")
def list_reports(limit: int = 30, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    rows = (db.query(Report).filter(Report.org_id == user.org_id)
            .order_by(Report.id.desc()).limit(min(limit, 100)).all())
    return [{"id": r.id, "report_type": r.report_type, "report_date": str(r.report_date),
             "content": r.content} for r in rows]


@router.get("/{report_id}")
def get_report(report_id: int, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    r = db.query(Report).filter_by(id=report_id, org_id=user.org_id).first()
    if r is None:
        raise HTTPException(404, "Report not found")
    return {"id": r.id, "report_type": r.report_type, "report_date": str(r.report_date),
            "content": r.content}

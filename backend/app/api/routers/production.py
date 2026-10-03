"""Production engine endpoints (Sections 21-22): jobs, providers, assets, rights."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.events import EventType
from app.db.session import get_db
from app.models.content import ContentIdea
from app.models.organization import User
from app.models.production import Asset, ProductionJob, RightsRecord
from app.services.event_bus import publish
from app.services.qc_service import latest_script_version

router = APIRouter(prefix="/api/production", tags=["production"])

RIGHTS_STATUSES = ("user_owned", "licensed", "permission_granted", "public_domain",
                   "platform_permitted", "unknown", "blocked")


class JobIn(BaseModel):
    idea_id: int
    provider: str = "user_media"  # user_media | external
    config: dict = {}


class RightsIn(BaseModel):
    idea_id: int
    asset_id: int | None = None
    content_description: str = ""
    source_url: str = ""
    status: str
    license_ref: str = ""
    notes: str = ""


@router.post("/jobs", status_code=201)
def create_job(data: JobIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    if not db.query(ContentIdea).filter_by(id=data.idea_id, org_id=user.org_id).first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Idea not found")
    job = ProductionJob(org_id=user.org_id, idea_id=data.idea_id,
                        provider=data.provider, status="queued",
                        output={"config": data.config})
    db.add(job)
    db.commit()
    return {"id": job.id, "idea_id": job.idea_id, "provider": job.provider, "status": job.status}


@router.post("/jobs/{job_id}/run")
def run_job(job_id: int, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    """Executes the provider. Fails honestly with setup guidance when unconfigured."""
    from app.integrations.video_providers import ProviderNotConfiguredError, get_video_provider

    job = db.query(ProductionJob).filter_by(id=job_id, org_id=user.org_id).first()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Production job not found")
    if job.status not in ("queued", "failed"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Job already {job.status}")

    job.status = "running"
    db.commit()
    try:
        provider = get_video_provider(job.provider)
        sv = latest_script_version(db, job.idea_id)
        sv_data = {"hook": sv.hook, "body": sv.body, "cta": sv.cta,
                   "pacing": sv.pacing} if sv else None
        result = provider.render((job.output or {}).get("config", {}), sv_data)
        asset = Asset(org_id=user.org_id, idea_id=job.idea_id,
                      asset_type=result.asset_type, url=result.asset_url,
                      metadata_json=result.output)
        db.add(asset)
        job.status = "completed"
        job.cost_usd = result.cost_usd
        job.output = {**(job.output or {}), **result.output,
                      "asset_id": None, "result": "provider completed"}
        job.error = None
        db.flush()
        job.output["asset_id"] = asset.id
        db.commit()
        publish(db, EventType.PRODUCTION_JOB_COMPLETED,
                {"job_id": job.id, "asset_id": asset.id, "provider": job.provider},
                org_id=user.org_id, commit=True)
        return {"id": job.id, "status": job.status, "asset_id": asset.id,
                "cost_usd": job.cost_usd}
    except (ProviderNotConfiguredError, ValueError) as exc:
        job.status = "failed"
        job.error = str(exc)
        db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    except Exception as exc:  # provider runtime errors are recorded, never swallowed
        job.status = "failed"
        job.error = f"{type(exc).__name__}: {exc}"
        db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Production failed: {job.error}")


@router.get("/jobs")
def list_jobs(idea_id: int | None = None, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    q = db.query(ProductionJob).filter(ProductionJob.org_id == user.org_id)
    if idea_id:
        q = q.filter(ProductionJob.idea_id == idea_id)
    rows = q.order_by(ProductionJob.id.desc()).limit(100).all()
    return [{"id": j.id, "idea_id": j.idea_id, "provider": j.provider, "status": j.status,
             "cost_usd": j.cost_usd, "error": j.error} for j in rows]


@router.get("/assets")
def list_assets(idea_id: int | None = None, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    q = db.query(Asset).filter(Asset.org_id == user.org_id)
    if idea_id:
        q = q.filter(Asset.idea_id == idea_id)
    return [{"id": a.id, "idea_id": a.idea_id, "asset_type": a.asset_type,
             "url": a.url, "metadata": a.metadata_json} for a in q.limit(200).all()]


@router.post("/rights", status_code=201)
def set_rights(data: RightsIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    if data.status not in RIGHTS_STATUSES:
        raise HTTPException(400, f"status must be one of {RIGHTS_STATUSES}")
    record = RightsRecord(org_id=user.org_id, idea_id=data.idea_id, asset_id=data.asset_id,
                          content_description=data.content_description,
                          source_url=data.source_url, status=data.status,
                          license_ref=data.license_ref, notes=data.notes)
    db.add(record)
    db.commit()
    publish(db, EventType.RIGHTS_UPDATED,
            {"idea_id": data.idea_id, "status": data.status},
            org_id=user.org_id, commit=True)
    return {"id": record.id, "status": record.status}


@router.get("/rights")
def list_rights(idea_id: int | None = None, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    q = db.query(RightsRecord).filter(RightsRecord.org_id == user.org_id)
    if idea_id:
        q = q.filter(RightsRecord.idea_id == idea_id)
    return [{"id": r.id, "idea_id": r.idea_id, "asset_id": r.asset_id,
             "status": r.status, "source_url": r.source_url,
             "license_ref": r.license_ref, "notes": r.notes} for r in q.limit(200).all()]

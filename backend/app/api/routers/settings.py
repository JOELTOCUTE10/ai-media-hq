"""System settings + kill switches (Sections 30-31). Audit-logged."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.core.events import EventType
from app.db.session import get_db
from app.models.ops import AuditLog, Integration
from app.models.organization import Organization, User
from app.services.event_bus import publish

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsIn(BaseModel):
    operations_paused: bool | None = None
    publishing_paused: bool | None = None
    auto_publish: bool | None = None
    monthly_budget_usd: float | None = Field(default=None, ge=0)


def _org_settings(db: Session, org: Organization) -> dict:
    return org.settings or {}


@router.get("")
def get_settings_endpoint(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = db.get(Organization, user.org_id)
    settings = get_settings()
    integrations = db.query(Integration).filter(Integration.org_id == user.org_id).all()
    return {
        "organization": {"id": org.id, "name": org.name, "settings": _org_settings(db, org)},
        "system": {"ai_provider": settings.AI_PROVIDER, "ai_model": settings.AI_MODEL,
                   "task_runner_enabled": settings.TASK_RUNNER_ENABLED,
                   "monthly_budget_usd": settings.MONTHLY_BUDGET_USD},
        "integrations": [{"key": i.key, "name": i.name, "status": i.status} for i in integrations],
    }


@router.put("")
def update_settings(data: SettingsIn, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    org = db.get(Organization, user.org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    current = dict(org.settings or {})
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if "auto_publish" in updates and updates["auto_publish"] and current.get("publishing_paused", True):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Cannot enable auto_publish while publishing is paused.")
    current.update(updates)
    org.settings = current
    db.add(AuditLog(org_id=user.org_id, user_id=user.id, action="settings.update",
                    entity_type="organization", entity_id=str(org.id), details=updates))
    for key in ("operations_paused", "publishing_paused"):
        if key in updates:
            publish(db, EventType.OPERATIONS_PAUSED if (key == "operations_paused" and updates[key])
                    else EventType.OPERATIONS_RESUMED, {key: updates[key]}, org_id=user.org_id)
    db.commit()
    return {"organization": {"id": org.id, "name": org.name, "settings": current}}

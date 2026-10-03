"""Publishing gate (Sections 19, 21, 23-25).

A video can only publish when: publishing is not paused, QC passed, no
blocking claims, no blocked/unknown rights, and (unless auto-publish is
explicitly enabled) a human approved it.
"""
from sqlalchemy.orm import Session

from app.models.content import Claim, ContentIdea
from app.models.organization import Organization
from app.models.production import Approval, Asset, QualityCheck, RightsRecord

from .qc_service import BLOCKING_CLAIM_STATUSES, BLOCKING_RIGHTS_STATUSES


def check_publish_readiness(db: Session, org: Organization, idea_id: int) -> tuple[bool, list[str]]:
    """Returns (ready, blockers). Honest: every blocker names the exact reason."""
    blockers: list[str] = []
    settings = org.settings or {}

    if settings.get("publishing_paused"):
        blockers.append("Publishing is paused globally (Settings kill switch).")

    idea = db.query(ContentIdea).filter_by(id=idea_id, org_id=org.id).first()
    if idea is None:
        return False, ["Idea not found."]

    # QC must have passed on the latest run
    qc = (db.query(QualityCheck).filter_by(idea_id=idea_id)
          .order_by(QualityCheck.id.desc()).first())
    if qc is None:
        blockers.append("No QC run exists for this content. Run QC first.")
    elif qc.result != "PASS":
        blockers.append(f"Latest QC result is {qc.result}: {qc.reasons[:3]}")

    # Claims
    blocking = (db.query(Claim).filter(Claim.idea_id == idea_id,
                                       Claim.status.in_(BLOCKING_CLAIM_STATUSES)).count())
    if blocking:
        blockers.append(f"{blocking} claim(s) are disputed/unsupported.")

    # Rights: unknown rights block publishing by default (Section 21)
    bad_rights = (db.query(RightsRecord)
                  .filter(RightsRecord.idea_id == idea_id,
                          RightsRecord.status.in_(BLOCKING_RIGHTS_STATUSES)).count())
    if bad_rights:
        blockers.append(f"{bad_rights} rights record(s) are unknown/blocked - publishing blocked by default.")
    assets = db.query(Asset).filter(Asset.idea_id == idea_id).all()
    covered = {r.asset_id for r in db.query(RightsRecord)
               .filter(RightsRecord.idea_id == idea_id).all()
               if r.status not in BLOCKING_RIGHTS_STATUSES}
    idea_level_ok = any(r.asset_id is None and r.status not in BLOCKING_RIGHTS_STATUSES
                        for r in db.query(RightsRecord).filter(RightsRecord.idea_id == idea_id).all())
    uncovered = [a for a in assets if a.id not in covered and not idea_level_ok]
    if uncovered:
        blockers.append(f"{len(uncovered)} asset(s) have no usable rights record - rights unknown blocks publishing by default.")

    # Human approval (unless auto-publish explicitly enabled)
    if not settings.get("auto_publish"):
        approved = (db.query(Approval)
                   .filter_by(idea_id=idea_id, status="approved")
                   .order_by(Approval.id.desc()).first())
        if approved is None:
            blockers.append("No human approval for this content (auto-publish is off).")

    return len(blockers) == 0, blockers

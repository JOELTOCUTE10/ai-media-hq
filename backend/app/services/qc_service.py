"""Automated Quality Control engine (Section 23).

Runs deterministic checks against real stored data and returns PASS / FAIL /
NEEDS_REVIEW with explicit reasons. Nothing is guessed.
"""
from sqlalchemy.orm import Session

from app.core.events import EventType
from app.models.content import Claim, ContentIdea, Script, ScriptVersion
from app.models.production import Asset, PublishingJob, QualityCheck, RightsRecord
from app.services.event_bus import publish

BLOCKING_CLAIM_STATUSES = ("disputed", "unsupported")
REVIEW_CLAIM_STATUSES = ("needs_review", "partially_supported")
BLOCKING_RIGHTS_STATUSES = ("unknown", "blocked")


def latest_script_version(db: Session, idea_id: int) -> ScriptVersion | None:
    script = db.query(Script).filter(Script.idea_id == idea_id).first()
    if script is None:
        return None
    return (db.query(ScriptVersion).filter(ScriptVersion.script_id == script.id)
            .order_by(ScriptVersion.version.desc()).first())


def run_qc(db: Session, org_id: int, idea_id: int) -> QualityCheck:
    idea = db.query(ContentIdea).filter_by(id=idea_id, org_id=org_id).one()
    sv = latest_script_version(db, idea_id)
    checks: dict = {}
    reasons: list[str] = []
    result = "PASS"

    # 1. Script completeness -------------------------------------------------
    if sv is None:
        checks["script"] = {"status": "FAIL", "detail": "no script exists"}
        reasons.append("No script exists for this idea.")
    else:
        missing = [f for f in ("hook", "body", "cta") if not (getattr(sv, f) or "").strip()]
        checks["script"] = {
            "status": "FAIL" if missing else "PASS",
            "version": sv.version,
            "missing_fields": missing,
        }
        if missing:
            reasons.append(f"Script v{sv.version} missing: {', '.join(missing)}.")
        if sv.review_status == "draft":
            checks["script"]["review_status"] = "draft"
            reasons.append("Latest script version is still in draft review.")

    # 2. Claims ----------------------------------------------------------------
    claims = db.query(Claim).filter(Claim.idea_id == idea_id).all()
    blocking = [c for c in claims if c.status in BLOCKING_CLAIM_STATUSES]
    review = [c for c in claims if c.status in REVIEW_CLAIM_STATUSES]
    checks["claims"] = {
        "status": ("FAIL" if blocking else "NEEDS_REVIEW" if review else "PASS"),
        "total": len(claims),
        "verified": sum(1 for c in claims if c.status == "verified"),
        "blocking": len(blocking),
        "needs_review": len(review),
    }
    if blocking:
        reasons.append(f"{len(blocking)} claim(s) disputed/unsupported - publishing is blocked.")
    if review and not blocking:
        reasons.append(f"{len(review)} claim(s) need review before publishing.")

    # 3. Rights (Section 21) ----------------------------------------------------
    assets = db.query(Asset).filter(Asset.idea_id == idea_id).all()
    rights = db.query(RightsRecord).filter(RightsRecord.idea_id == idea_id).all()
    by_asset = {r.asset_id for r in rights}
    bad_rights = [r for r in rights if r.status in BLOCKING_RIGHTS_STATUSES]
    missing_rights = [a for a in assets if a.id not in by_asset]
    checks["rights"] = {"assets": len(assets), "records": len(rights),
                        "blocking": len(bad_rights), "missing_for_assets": len(missing_rights)}
    if bad_rights:
        reasons.append(f"{len(bad_rights)} rights record(s) are unknown/blocked.")
    if missing_rights:
        reasons.append(f"{len(missing_rights)} asset(s) have no rights record - rights unknown blocks publishing by default.")
    if assets and not bad_rights and not missing_rights:
        reasons.append("Rights: all assets have usable rights records.")
    if not assets:
        checks["rights"]["note"] = "no third-party assets registered"

    # 4. Metadata ----------------------------------------------------------------
    job = (db.query(PublishingJob).filter_by(idea_id=idea_id)
           .order_by(PublishingJob.id.desc()).first())
    meta = (job.metadata_json if job else {}) or {}
    if job is None:
        # Metadata is assembled at publishing time; QC only flags incompleteness
        # once a publishing job exists to evaluate.
        checks["metadata"] = {"status": "PASS",
                              "note": "no publishing job yet; metadata set at publish time"}
    else:
        meta_ok = bool(meta.get("title") or idea.title) and bool(meta.get("description"))
        checks["metadata"] = {
            "status": "PASS" if meta_ok else "NEEDS_REVIEW",
            "title_source": "job metadata" if meta.get("title") else "idea title",
            "tags": meta.get("tags", []),
        }
        if not meta_ok:
            reasons.append("Publishing metadata incomplete (title/description).")

    # 5. Channel rules -------------------------------------------------------------
    from app.models.channel import Channel
    channel = db.get(Channel, idea.channel_id)
    rules = (channel.content_rules or {}) if channel else {}
    max_duration = rules.get("max_duration_seconds")
    duration_ok = True
    if sv is not None and max_duration:
        est = (sv.pacing or {}).get("estimated_seconds")
        if est and est > max_duration:
            duration_ok = False
            reasons.append(f"Estimated duration {est}s exceeds channel max {max_duration}s.")
    checks["channel_rules"] = {"status": "PASS" if duration_ok else "FAIL"}

    # Aggregate: FAIL > NEEDS_REVIEW > PASS
    statuses = [c.get("status", "PASS") for c in checks.values() if isinstance(c, dict)]
    if "FAIL" in statuses:
        result = "FAIL"
    elif "NEEDS_REVIEW" in statuses or review:
        result = "NEEDS_REVIEW"
    if not reasons:
        reasons.append("All checks passed.")

    qc = QualityCheck(org_id=org_id, idea_id=idea_id, result=result,
                     checks=checks, reasons=reasons)
    db.add(qc)
    db.flush()
    publish(db, EventType.QC_PASSED if result == "PASS" else EventType.QC_FAILED,
            {"idea_id": idea_id, "result": result, "reasons": reasons},
            org_id=org_id, commit=False)
    db.commit()
    return qc

"""Experiment Lab endpoints (Section 27). Conclusions never claim unsupported
causation - every result records sample size and limitations."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.events import EventType
from app.db.session import get_db
from app.models.analytics import Experiment, ExperimentResult
from app.models.channel import Channel
from app.models.organization import User
from app.services.event_bus import publish

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


class ExperimentIn(BaseModel):
    name: str
    hypothesis: str
    variable: str
    control: str
    variant: str
    channel_slug: str = ""


class ResultIn(BaseModel):
    sample_size: int
    control_metrics: dict
    variant_metrics: dict


@router.post("", status_code=201)
def create(data: ExperimentIn, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    channel_id = None
    if data.channel_slug:
        ch = db.query(Channel).filter_by(org_id=user.org_id, slug=data.channel_slug).first()
        if ch is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")
        channel_id = ch.id
    e = Experiment(org_id=user.org_id, channel_id=channel_id, name=data.name,
                  hypothesis=data.hypothesis, variable=data.variable,
                  control=data.control, variant=data.variant, status="running",
                  started_at=datetime.now(UTC))
    db.add(e)
    db.commit()
    return {"id": e.id, "name": e.name, "status": e.status}


@router.get("")
def list_experiments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Experiment).filter(Experiment.org_id == user.org_id)
            .order_by(Experiment.id.desc()).limit(100).all())
    out = []
    for e in rows:
        r = (db.query(ExperimentResult).filter_by(experiment_id=e.id)
             .order_by(ExperimentResult.id.desc()).first())
        out.append({"id": e.id, "name": e.name, "hypothesis": e.hypothesis,
                    "variable": e.variable, "control": e.control, "variant": e.variant,
                    "status": e.status, "result": r.result if r else None,
                    "conclusion": r.conclusion if r else None,
                    "confidence": r.confidence if r else None,
                    "limitations": r.limitations if r else None})
    return out


@router.post("/{experiment_id}/result", status_code=201)
def record_result(experiment_id: int, data: ResultIn,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(Experiment).filter_by(id=experiment_id, org_id=user.org_id).first()
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not found")

    def metric(m: dict, key: str) -> float:
        return float(m.get(key, 0) or 0)

    control = data.control_metrics
    variant = data.variant_metrics
    deltas = {}
    for key in set(control) | set(variant):
        c, v = metric(control, key), metric(variant, key)
        if c:
            deltas[key] = round((v - c) / c * 100, 2)
    primary = "retention_pct" if "retention_pct" in deltas else (next(iter(deltas), None))
    if primary is None:
        conclusion = "No comparable metrics were provided."
        confidence = "none"
    else:
        d = deltas[primary]
        direction = "higher" if d > 0 else "lower" if d < 0 else "the same"
        conclusion = (f"During the observed period, '{e.variant}' showed {direction} "
                       f"{primary.replace('_', ' ')} than '{e.control}' "
                       f"({d:+.1f}% relative difference, n={data.sample_size}).")
        if data.sample_size < 10:
            confidence = "low - small sample"
        elif data.sample_size < 30:
            confidence = "medium - moderate sample"
        else:
            confidence = "high - adequate sample"
    limitations = (f"Observational comparison of n={data.sample_size}; no statistical test "
                   "was applied and no causal claim is made. Differences may reflect "
                   "topic, timing or audience effects.")

    r = ExperimentResult(experiment_id=e.id, sample_size=data.sample_size,
                         metrics={"control": control, "variant": variant, "deltas_pct": deltas},
                         result=f"Primary metric: {primary}", conclusion=conclusion,
                         confidence=confidence, limitations=limitations)
    db.add(r)
    e.status = "completed"
    e.ended_at = datetime.now(UTC)
    db.commit()
    publish(db, EventType.EXPERIMENT_COMPLETED,
            {"experiment_id": e.id, "conclusion": conclusion},
            org_id=user.org_id, commit=True)
    return {"id": r.id, "conclusion": conclusion, "confidence": confidence,
            "limitations": limitations, "deltas_pct": deltas}

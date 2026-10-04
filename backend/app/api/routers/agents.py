"""Agent endpoints: roster, status control, run history."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.permissions import LEVEL_PERMISSIONS
from app.api.deps import get_current_user
from app.core.events import EventType
from app.db.session import get_db
from app.models.agent import Agent, AgentRun
from app.models.organization import User
from app.services.event_bus import publish

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentOut(BaseModel):
    id: int
    key: str
    name: str
    role: str
    description: str
    persona: str = ""
    department: str
    capabilities: list
    tools: list
    permission_level: str
    permissions: list
    status: str
    current_task_id: int | None
    model_config: dict
    memory_access: list

    model_config = {"from_attributes": True}


class RunOut(BaseModel):
    id: int
    agent_id: int
    task_id: int | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    error: str | None
    cost_usd: float

    model_config = {"from_attributes": True}


def _to_out(agent: Agent) -> AgentOut:
    return AgentOut(
        id=agent.id, key=agent.key, name=agent.name, role=agent.role, description=agent.description,
                    persona=agent.persona,
        department=agent.department, capabilities=agent.capabilities, tools=agent.tools,
        permission_level=agent.permission_level,
        permissions=sorted(LEVEL_PERMISSIONS.get(agent.permission_level, set())),
        status=agent.status, current_task_id=agent.current_task_id,
        model_config=agent.model_config_json, memory_access=agent.memory_access,
    )


@router.get("", response_model=list[AgentOut])
def list_agents(department: str | None = None, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    q = db.query(Agent).filter(Agent.org_id == user.org_id)
    if department:
        q = q.filter(Agent.department == department)
    return [_to_out(a) for a in q.order_by(Agent.id).all()]


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if agent is None or agent.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    return _to_out(agent)


@router.post("/{agent_id}/pause", response_model=AgentOut)
def pause_agent(agent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if agent is None or agent.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    agent.status = "paused"
    db.commit()
    publish(db, EventType.AGENT_PAUSED, {"agent": agent.key}, org_id=user.org_id, agent_id=agent.id, commit=True)
    return _to_out(agent)


@router.post("/{agent_id}/resume", response_model=AgentOut)
def resume_agent(agent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if agent is None or agent.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    agent.status = "active"
    db.commit()
    publish(db, EventType.AGENT_RESUMED, {"agent": agent.key}, org_id=user.org_id, agent_id=agent.id, commit=True)
    return _to_out(agent)


@router.get("/{agent_id}/runs", response_model=list[RunOut])
def agent_runs(agent_id: int, limit: int = 20, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if agent is None or agent.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    return (db.query(AgentRun).filter(AgentRun.agent_id == agent_id)
            .order_by(AgentRun.id.desc()).limit(min(limit, 100)).all())

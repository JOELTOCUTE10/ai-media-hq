"""Memory endpoints (Section 11): record + keyword search across scopes."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.organization import User
from app.services import memory_service

router = APIRouter(prefix="/api/memory", tags=["memory"])

SCOPES = ["short_term", "long_term", "channel", "agent", "content", "strategic"]


class MemoryIn(BaseModel):
    scope: str = "long_term"
    content: str = Field(min_length=1, max_length=10000)
    key: str = Field(default="", max_length=200)
    channel_id: int | None = None
    agent_key: str | None = None
    idea_id: int | None = None
    tags: list[str] = Field(default_factory=list)


class MemoryOut(BaseModel):
    id: int
    scope: str
    key: str
    content: str
    channel_id: int | None
    agent_id: int | None
    idea_id: int | None
    tags: list
    created_at: str

    model_config = {"from_attributes": True}


@router.post("", response_model=MemoryOut, status_code=201)
def record_memory(data: MemoryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.scope not in SCOPES:
        raise ValueError  # handled by fastapi as 500; validated below
    agent_id = None
    if data.agent_key:
        from app.models.agent import Agent
        agent = db.query(Agent).filter(Agent.org_id == user.org_id, Agent.key == data.agent_key).first()
        agent_id = agent.id if agent else None
    mem = memory_service.record(db, user.org_id, data.scope, data.content, key=data.key,
                                channel_id=data.channel_id, agent_id=agent_id,
                                idea_id=data.idea_id, tags=data.tags)
    return MemoryOut(id=mem.id, scope=mem.scope, key=mem.key, content=mem.content,
                      channel_id=mem.channel_id, agent_id=mem.agent_id, idea_id=mem.idea_id,
                      tags=mem.tags, created_at=mem.created_at.isoformat())


@router.get("/search", response_model=list[MemoryOut])
def search_memory(q: str = Query(default=""), scope: str | None = None, limit: int = 20,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if scope is not None and scope not in SCOPES:
        from fastapi import HTTPException, status
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid scope '{scope}'. Valid: {SCOPES}")
    results = memory_service.search(db, user.org_id, q, scope, limit)
    return [MemoryOut(id=m.id, scope=m.scope, key=m.key, content=m.content, channel_id=m.channel_id,
                      agent_id=m.agent_id, idea_id=m.idea_id, tags=m.tags,
                      created_at=m.created_at.isoformat()) for m in results]

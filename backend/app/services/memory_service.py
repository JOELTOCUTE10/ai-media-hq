"""Searchable multi-scope memory (Section 11). Retrieval, never prompt-dumping."""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.channel import Channel
from app.models.knowledge import Memory
from app.models.task import Task

MAX_CONTEXT_MEMORIES = 8


def search(db: Session, org_id: int, query: str, scope: str | None = None, limit: int = 20) -> list[Memory]:
    stmt = db.query(Memory).filter(Memory.org_id == org_id)
    if scope:
        stmt = stmt.filter(Memory.scope == scope)
    if query:
        like = f"%{query}%"
        stmt = stmt.filter(or_(Memory.content.ilike(like), Memory.key.ilike(like)))
    return stmt.order_by(Memory.created_at.desc()).limit(limit).all()


def record(db: Session, org_id: int, scope: str, content: str, key: str = "",
           channel_id: int | None = None, agent_id: int | None = None,
           idea_id: int | None = None, tags: list | None = None) -> Memory:
    mem = Memory(org_id=org_id, scope=scope, content=content, key=key,
                 channel_id=channel_id, agent_id=agent_id, idea_id=idea_id, tags=tags or [])
    db.add(mem)
    db.commit()
    return mem


def build_agent_context(db: Session, task: Task, agent: Agent) -> str:
    """Compose a compact, relevant context block: recent short-term memory,
    keyword-matched long-term memory, channel memory and channel config.
    Capped - never dumps entire history (Section 11)."""
    parts: list[str] = []

    recent = (db.query(Memory)
              .filter(Memory.org_id == task.org_id, Memory.scope == "short_term")
              .order_by(Memory.created_at.desc()).limit(3).all())
    for m in recent:
        parts.append(f"[recent] {m.content[:300]}")

    keywords = [w for w in task.title.lower().split() if len(w) > 4][:5]
    if keywords:
        clauses = or_(*[Memory.content.ilike(f"%{k}%") for k in keywords])
        matched = (db.query(Memory)
                   .filter(Memory.org_id == task.org_id,
                           Memory.scope.in_(["long_term", "channel", "strategic"]),
                           clauses)
                   .order_by(Memory.created_at.desc()).limit(MAX_CONTEXT_MEMORIES - len(recent)).all())
        for m in matched:
            parts.append(f"[{m.scope}] {m.content[:300]}")

    if task.channel_id:
        channel = db.get(Channel, task.channel_id)
        if channel:
            parts.append(f"[channel] {channel.name}: niche={channel.niche}, audience={channel.audience[:200]}, "
                         f"content_rules={channel.content_rules}")

    agent_mem = (db.query(Memory)
                 .filter(Memory.org_id == task.org_id, Memory.agent_id == agent.id,
                         Memory.scope == "agent")
                 .order_by(Memory.created_at.desc()).limit(2).all())
    for m in agent_mem:
        parts.append(f"[agent-memory] {m.content[:300]}")

    return "\n".join(parts)

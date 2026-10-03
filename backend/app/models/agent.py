"""Agent organization: agents, permissions, runs, messages (Sections 8-10)."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AgentStatus, RunStatus

from .organization import TimestampMixin, utcnow


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    key: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    department: Mapped[str] = mapped_column(String(100), index=True)
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    tools: Mapped[list] = mapped_column(JSON, default=list)
    permission_level: Mapped[str] = mapped_column(String(30), default="read_only")
    status: Mapped[str] = mapped_column(String(20), default=AgentStatus.ACTIVE.value, index=True)
    current_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_config_json: Mapped[dict] = mapped_column("model_config", JSON, default=dict)
    memory_access: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)


class AgentPermission(TimestampMixin, Base):
    __tablename__ = "agent_permissions"

    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    permission: Mapped[str] = mapped_column(String(60), index=True)
    granted: Mapped[bool] = mapped_column(default=True)


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"

    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.RUNNING.value, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class AgentMessage(TimestampMixin, Base):
    __tablename__ = "agent_messages"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    sender_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    receiver_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    message_type: Mapped[str] = mapped_column(String(60), default="message")
    content: Mapped[str] = mapped_column(Text)

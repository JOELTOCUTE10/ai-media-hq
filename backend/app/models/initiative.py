"""Agent initiative: self-proposed suggestions (Section 8: proactive agents).

Agents don't just wait for assigned work. On a cadence, idle agents review
their department context and propose the highest-value next task. The founder
approves or rejects each suggestion; approved suggestions become real Tasks
assigned to the proposing agent.
"""
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

from .organization import TimestampMixin, utcnow

if TYPE_CHECKING:
    pass


class AgentSuggestion(TimestampMixin, Base):
    __tablename__ = "agent_suggestions"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    # proposed | approved | rejected
    status: Mapped[str] = mapped_column(String(20), default="proposed", index=True)
    created_by_agent: Mapped[bool] = mapped_column(Boolean, default=True)
    decided_at: Mapped["object"] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    proposed_at: Mapped["object"] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

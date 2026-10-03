"""Persistent task manager, dependencies, workflows (Sections 38-39)."""
from datetime import datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import TaskPriority, TaskStatus, WorkflowRunStatus

from .organization import TimestampMixin


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    idea_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(20), default=TaskPriority.MEDIUM.value, index=True)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.QUEUED.value, index=True)
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=2)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    workflow_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), nullable=True, index=True)


class TaskDependency(TimestampMixin, Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_id", name="uq_task_dep_unique"),)

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    depends_on_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)


class Workflow(TimestampMixin, Base):
    __tablename__ = "workflows"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    definition: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)


class WorkflowRun(TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=WorkflowRunStatus.PENDING.value, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)


class Goal(TimestampMixin, Base):
    """Founder Mode (Section 7): an objective broken down into linked tasks."""

    __tablename__ = "goals"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(400))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    target_date: Mapped[object] = mapped_column(Date, nullable=True)

"""Operations: costs, audit, events, integrations, schedules (Sections 30-40)."""
from datetime import datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CostCategory, IntegrationStatus

from .organization import TimestampMixin, utcnow


class CostRecord(TimestampMixin, Base):
    __tablename__ = "cost_records"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    category: Mapped[str] = mapped_column(String(40), default=CostCategory.MODEL_USAGE.value, index=True)
    amount_usd: Mapped[float] = mapped_column(Float, default=0.0)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(200), index=True)
    entity_type: Mapped[str] = mapped_column(String(100), default="")
    entity_id: Mapped[str] = mapped_column(String(100), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class SystemEvent(TimestampMixin, Base):
    __tablename__ = "system_events"

    org_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    agent_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    workflow_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Integration(TimestampMixin, Base):
    __tablename__ = "integrations"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    key: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default=IntegrationStatus.UNCONFIGURED.value, index=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # never secrets
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Schedule(TimestampMixin, Base):
    __tablename__ = "schedules"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    cron: Mapped[str] = mapped_column(String(100), default="")
    task_type: Mapped[str] = mapped_column(String(100), default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Report(TimestampMixin, Base):
    """Generated executive reports built from actual stored data (Section 32)."""

    __tablename__ = "reports"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    report_type: Mapped[str] = mapped_column(String(40), default="daily", index=True)
    report_date: Mapped[object] = mapped_column(Date, index=True)
    content: Mapped[dict] = mapped_column(JSON, default=dict)


class OauthToken(TimestampMixin, Base):
    """OAuth tokens for publishing platforms. Never exposed through the API."""

    __tablename__ = "oauth_tokens"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(60), index=True)
    access_token: Mapped[str] = mapped_column(Text, default="")
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str] = mapped_column(Text, default="")

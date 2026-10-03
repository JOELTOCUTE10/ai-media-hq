"""Production, rights, QC, approval, publishing (Sections 21-25)."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ApprovalStatus, ProductionStatus, PublishingStatus, QCResult, RightsStatus

from .organization import TimestampMixin


class ProductionJob(TimestampMixin, Base):
    __tablename__ = "production_jobs"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("content_ideas.id"), index=True)
    provider: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default=ProductionStatus.QUEUED.value, index=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retries: Mapped[int] = mapped_column(default=0)


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    idea_id: Mapped[int | None] = mapped_column(ForeignKey("content_ideas.id"), nullable=True, index=True)
    asset_type: Mapped[str] = mapped_column(String(60), default="video")
    url: Mapped[str] = mapped_column(String(1000), default="")
    storage_path: Mapped[str] = mapped_column(String(1000), default="")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_by_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)


class RightsRecord(TimestampMixin, Base):
    __tablename__ = "rights_records"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    idea_id: Mapped[int | None] = mapped_column(ForeignKey("content_ideas.id"), nullable=True, index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    content_description: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(40), default=RightsStatus.UNKNOWN.value, index=True)
    license_ref: Mapped[str] = mapped_column(String(500), default="")
    notes: Mapped[str] = mapped_column(Text, default="")


class QualityCheck(TimestampMixin, Base):
    __tablename__ = "quality_checks"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("content_ideas.id"), index=True)
    result: Mapped[str] = mapped_column(String(20), default=QCResult.NEEDS_REVIEW.value, index=True)
    checks: Mapped[dict] = mapped_column(JSON, default=dict)
    reasons: Mapped[list] = mapped_column(JSON, default=list)


class Approval(TimestampMixin, Base):
    __tablename__ = "approvals"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("content_ideas.id"), index=True)
    requested_by_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    decided_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=ApprovalStatus.PENDING.value, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PublishingJob(TimestampMixin, Base):
    __tablename__ = "publishing_jobs"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("content_ideas.id"), index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(40), default="youtube")
    status: Mapped[str] = mapped_column(String(20), default=PublishingStatus.PENDING.value, index=True)
    video_id: Mapped[str] = mapped_column(String(200), default="")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

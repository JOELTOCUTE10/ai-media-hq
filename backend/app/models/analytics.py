"""Analytics, experiments, learning insights (Sections 26-28)."""
from datetime import datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

from .organization import TimestampMixin


class AnalyticsSnapshot(TimestampMixin, Base):
    __tablename__ = "analytics_snapshots"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    publishing_job_id: Mapped[int | None] = mapped_column(ForeignKey("publishing_jobs.id"), nullable=True, index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    video_title: Mapped[str] = mapped_column(String(400), default="")
    views: Mapped[int] = mapped_column(Integer, default=0)
    watch_time_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    retention_pct: Mapped[float] = mapped_column(Float, default=0.0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    subscribers_gained: Mapped[int] = mapped_column(Integer, default=0)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Experiment(TimestampMixin, Base):
    __tablename__ = "experiments"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    variable: Mapped[str] = mapped_column(String(100), default="")
    control: Mapped[str] = mapped_column(Text, default="")
    variant: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExperimentResult(TimestampMixin, Base):
    __tablename__ = "experiment_results"

    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), index=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[str] = mapped_column(Text, default="")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(Text, default="")
    limitations: Mapped[str] = mapped_column(Text, default="")


class LearningInsight(TimestampMixin, Base):
    __tablename__ = "learning_insights"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    observation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    date_range_start: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    date_range_end: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    recommendation: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)

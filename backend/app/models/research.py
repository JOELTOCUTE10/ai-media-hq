"""Research engine: sources, documents, topics, trends (Sections 13-15)."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SourceType

from .organization import TimestampMixin


class ResearchSource(TimestampMixin, Base):
    __tablename__ = "research_sources"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(40), default=SourceType.SECONDARY.value)
    base_url: Mapped[str] = mapped_column(String(500), default="")
    is_active: Mapped[bool] = mapped_column(default=True)


class ResearchDocument(TimestampMixin, Base):
    __tablename__ = "research_documents"
    __table_args__ = (Index("ix_research_documents_org_topic", "org_id", "topic"),)

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("research_sources.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000), default="")
    author: Mapped[str] = mapped_column(String(300), default="")
    topic: Mapped[str] = mapped_column(String(200), default="", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_type: Mapped[str] = mapped_column(String(40), default=SourceType.UNKNOWN.value)
    source_name: Mapped[str] = mapped_column(String(200), default="")
    content_summary: Mapped[str] = mapped_column(Text, default="")
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    credibility: Mapped[dict] = mapped_column(JSON, default=dict)


class Topic(TimestampMixin, Base):
    __tablename__ = "topics"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")


class Trend(TimestampMixin, Base):
    __tablename__ = "trends"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    topic: Mapped[str] = mapped_column(String(200), index=True)
    title: Mapped[str] = mapped_column(String(400), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    lifecycle: Mapped[str] = mapped_column(String(20), default="emerging", index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    signals: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    first_detected: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

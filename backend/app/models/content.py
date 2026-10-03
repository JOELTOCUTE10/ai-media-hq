"""Content engine: ideas, claims, scripts + versions (Sections 16-20)."""
from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ClaimStatus, IdeaStatus

from .organization import TimestampMixin


class ContentIdea(TimestampMixin, Base):
    __tablename__ = "content_ideas"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    title: Mapped[str] = mapped_column(String(400))
    topic: Mapped[str] = mapped_column(String(200), default="")
    hook: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    target_audience: Mapped[str] = mapped_column(Text, default="")
    source_evidence: Mapped[list] = mapped_column(JSON, default=list)
    trend_evidence: Mapped[list] = mapped_column(JSON, default=list)
    complexity: Mapped[str] = mapped_column(String(30), default="medium")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default=IdeaStatus.RESEARCH.value, index=True)
    why_selected: Mapped[dict] = mapped_column(JSON, default=dict)


class Claim(TimestampMixin, Base):
    __tablename__ = "claims"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    idea_id: Mapped[int | None] = mapped_column(ForeignKey("content_ideas.id"), nullable=True, index=True)
    script_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(300), default="")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    source_type: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(30), default=ClaimStatus.NEEDS_REVIEW.value, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reviewer_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class Script(TimestampMixin, Base):
    __tablename__ = "scripts"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("content_ideas.id"), index=True)
    current_version: Mapped[int] = mapped_column(default=1)


class ScriptVersion(TimestampMixin, Base):
    __tablename__ = "script_versions"

    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"), index=True)
    version: Mapped[int] = mapped_column(default=1)
    author_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    hook: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    transitions: Mapped[str] = mapped_column(Text, default="")
    ending: Mapped[str] = mapped_column(Text, default="")
    cta: Mapped[str] = mapped_column(Text, default="")
    pacing: Mapped[dict] = mapped_column(JSON, default=dict)
    visual_suggestions: Mapped[list] = mapped_column(JSON, default=list)
    narration_notes: Mapped[str] = mapped_column(Text, default="")
    on_screen_text: Mapped[list] = mapped_column(JSON, default=list)
    changes: Mapped[str] = mapped_column(Text, default="")
    review_status: Mapped[str] = mapped_column(String(30), default="draft")
    approval_status: Mapped[str] = mapped_column(String(30), default="pending")

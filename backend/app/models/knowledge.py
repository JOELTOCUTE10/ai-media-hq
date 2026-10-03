"""Shared memory + knowledge base (Sections 11-12)."""
from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import MemoryScope

from .organization import TimestampMixin


class Memory(TimestampMixin, Base):
    __tablename__ = "memories"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    scope: Mapped[str] = mapped_column(String(30), default=MemoryScope.SHORT_TERM.value, index=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    idea_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSON, default=list)


class KnowledgeEntity(TimestampMixin, Base):
    __tablename__ = "knowledge_entities"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(300))
    slug: Mapped[str] = mapped_column(String(300), index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class KnowledgeRelationship(TimestampMixin, Base):
    __tablename__ = "knowledge_relationships"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    source_entity_id: Mapped[int] = mapped_column(ForeignKey("knowledge_entities.id"), index=True)
    target_entity_id: Mapped[int] = mapped_column(ForeignKey("knowledge_entities.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(100), index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)

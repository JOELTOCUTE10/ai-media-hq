"""Channel - fully configuration-driven (Section 33). No niche logic in code."""
from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

from .organization import TimestampMixin


class Channel(TimestampMixin, Base):
    __tablename__ = "channels"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    niche: Mapped[str] = mapped_column(String(200), default="")
    audience: Mapped[str] = mapped_column(Text, default="")
    brand_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    content_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    publishing_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    research_sources: Mapped[list] = mapped_column(JSON, default=list)
    style: Mapped[dict] = mapped_column(JSON, default=dict)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

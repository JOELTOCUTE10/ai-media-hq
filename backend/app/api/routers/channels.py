"""Channel CRUD - fully config-driven (Section 33)."""
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.channel import Channel
from app.models.organization import User

router = APIRouter(prefix="/api/channels", tags=["channels"])


class ChannelIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(default="", max_length=200)
    description: str = ""
    niche: str = ""
    audience: str = ""
    brand_settings: dict = Field(default_factory=dict)
    content_rules: dict = Field(default_factory=dict)
    publishing_rules: dict = Field(default_factory=dict)
    research_sources: list = Field(default_factory=list)
    style: dict = Field(default_factory=dict)
    approval_required: bool = True
    is_active: bool = True


class ChannelOut(ChannelIn):
    id: int
    org_id: int

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ChannelOut])
def list_channels(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Channel).filter(Channel.org_id == user.org_id).order_by(Channel.id).all()


@router.post("", response_model=ChannelOut, status_code=201)
def create_channel(data: ChannelIn, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    slug = data.slug or re.sub(r"[^a-z0-9]+", "-", data.name.lower()).strip("-")
    if db.query(Channel).filter(Channel.org_id == user.org_id, Channel.slug == slug).first():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Channel slug '{slug}' already exists")
    channel = Channel(org_id=user.org_id, **{**data.model_dump(), "slug": slug})
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.get("/{channel_id}", response_model=ChannelOut)
def get_channel(channel_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    channel = db.get(Channel, channel_id)
    if channel is None or channel.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")
    return channel


@router.put("/{channel_id}", response_model=ChannelOut)
def update_channel(channel_id: int, data: ChannelIn, user: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    channel = db.get(Channel, channel_id)
    if channel is None or channel.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")
    for key, value in data.model_dump(exclude={"slug"}).items():
        setattr(channel, key, value)
    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=204)
def delete_channel(channel_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    channel = db.get(Channel, channel_id)
    if channel is None or channel.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")
    db.delete(channel)
    db.commit()

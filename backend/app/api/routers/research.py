"""Research endpoints (Section 13-14). Honest 503 when providers lack credentials."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.events import EventType
from app.db.session import get_db
from app.integrations.research_providers import (
    IntegrationNotConfiguredError,
    available_research_providers,
    get_research_provider,
)
from app.models.channel import Channel
from app.models.organization import User
from app.models.research import ResearchDocument
from app.services.event_bus import publish

router = APIRouter(prefix="/api/research", tags=["research"])


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=400)
    provider: str = "tavily"
    channel_slug: str | None = None
    topic: str = Field(default="", max_length=200)
    max_results: int = Field(default=10, ge=1, le=25)


class DocumentOut(BaseModel):
    id: int
    title: str
    url: str
    topic: str
    source_name: str
    source_type: str
    author: str
    relevance: float
    content_summary: str
    retrieved_at: str

    model_config = {"from_attributes": True }


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(topic: str | None = None, limit: int = 50,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(ResearchDocument).filter(ResearchDocument.org_id == user.org_id)
    if topic:
        q = q.filter(ResearchDocument.topic == topic)
    docs = q.order_by(ResearchDocument.id.desc()).limit(min(limit, 200)).all()
    return [DocumentOut(id=d.id, title=d.title, url=d.url, topic=d.topic, source_name=d.source_name,
                        source_type=d.source_type, author=d.author, relevance=d.relevance,
                        content_summary=d.content_summary[:300],
                        retrieved_at=d.retrieved_at.isoformat()) for d in docs]


@router.get("/providers")
def providers(user: User = Depends(get_current_user)):
    return {"available": available_research_providers(),
            "message": "Providers require credentials in .env; none are simulated." if not available_research_providers() else ""}


@router.post("/search")
def search(data: SearchIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    channel_id = None
    if data.channel_slug:
        channel = db.query(Channel).filter(Channel.org_id == user.org_id,
                                           Channel.slug == data.channel_slug).first()
        if channel is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")
        channel_id = channel.id
    try:
        items = get_research_provider(data.provider).search(data.query, data.max_results)
    except IntegrationNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    stored = []
    now = datetime.now(UTC)
    for item in items:
        doc = ResearchDocument(
            org_id=user.org_id, channel_id=channel_id, title=item.title, url=item.url,
            author=item.author, topic=data.topic, retrieved_at=now,
            source_type=item.source_type, source_name=item.source_name,
            content_summary=item.summary[:4000], relevance=item.relevance,
        )
        db.add(doc)
        stored.append(doc)
    db.commit()
    publish(db, EventType.RESEARCH_COMPLETED,
            {"query": data.query, "provider": data.provider, "results": len(stored)},
            org_id=user.org_id, commit=True)
    return {"stored": len(stored), "documents": [
        {"id": d.id, "title": d.title, "url": d.url, "relevance": d.relevance} for d in stored]}

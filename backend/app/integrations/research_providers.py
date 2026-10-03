"""Research provider abstraction (Section 13). Official APIs only, no scraping.

A provider with no credentials raises IntegrationNotConfiguredError - the
API returns HTTP 503 with setup instructions instead of fake results.
"""
from dataclasses import dataclass, field

import httpx

from app.core.config import get_settings


class IntegrationNotConfiguredError(RuntimeError):
    pass


@dataclass
class ResearchItem:
    title: str
    url: str
    source_name: str = ""
    author: str = ""
    published_at: str | None = None
    summary: str = ""
    relevance: float = 0.0
    source_type: str = "secondary"
    extra: dict = field(default_factory=dict)


class ResearchProvider:
    name = "abstract"

    def search(self, query: str, max_results: int = 10) -> list[ResearchItem]:
        raise NotImplementedError


class TavilySearchProvider(ResearchProvider):
    """Web search via the Tavily API. Requires TAVILY_API_KEY."""
    name = "tavily"

    def search(self, query: str, max_results: int = 10) -> list[ResearchItem]:
        settings = get_settings()
        if not settings.TAVILY_API_KEY:
            raise IntegrationNotConfiguredError(
                "Tavily search selected but TAVILY_API_KEY is not set. Add it to .env to enable web research."
            )
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={"api_key": settings.TAVILY_API_KEY, "query": query, "max_results": max_results},
            timeout=30.0,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return [
            ResearchItem(
                title=r.get("title", ""),
                url=r.get("url", ""),
                source_name=r.get("url", "").split("/")[2] if r.get("url", "").count("/") >= 2 else "",
                summary=r.get("content", "")[:4000],
                relevance=float(r.get("score", 0.0)),
                source_type="secondary",
            )
            for r in results
        ]


class YouTubeSearchProvider(ResearchProvider):
    """YouTube Data API v3 search. Requires YOUTUBE_DATA_API_KEY."""
    name = "youtube"

    def search(self, query: str, max_results: int = 10) -> list[ResearchItem]:
        settings = get_settings()
        if not settings.YOUTUBE_DATA_API_KEY:
            raise IntegrationNotConfiguredError(
                "YouTube search selected but YOUTUBE_DATA_API_KEY is not set. Add it to .env."
            )
        resp = httpx.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"key": settings.YOUTUBE_DATA_API_KEY, "part": "snippet", "type": "video",
                    "q": query, "maxResults": min(max_results, 50)},
            timeout=30.0,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            ResearchItem(
                title=it["snippet"]["title"],
                url=f"https://www.youtube.com/watch?v={it['id'].get('videoId', '')}",
                source_name="youtube",
                author=it["snippet"].get("channelTitle", ""),
                published_at=it["snippet"].get("publishTime"),
                summary=it["snippet"].get("description", "")[:2000],
                source_type="social",
            )
            for it in items
        ]


RESEARCH_PROVIDERS = {
    TavilySearchProvider.name: TavilySearchProvider,
    YouTubeSearchProvider.name: YouTubeSearchProvider,
}


def get_research_provider(name: str) -> ResearchProvider:
    cls = RESEARCH_PROVIDERS.get(name)
    if cls is None:
        raise IntegrationNotConfiguredError(f"Unknown research provider '{name}'.")
    return cls()


def available_research_providers() -> list[str]:
    settings = get_settings()
    available = []
    if settings.TAVILY_API_KEY:
        available.append("tavily")
    if settings.YOUTUBE_DATA_API_KEY:
        available.append("youtube")
    return available

"""Research provider abstraction (Section 13). Official APIs only, no scraping.

A provider with no credentials raises IntegrationNotConfiguredError - the
API returns HTTP 503 with setup instructions instead of fake results.
"""
import re
import xml.etree.ElementTree as ET
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


class WikipediaSearchProvider(ResearchProvider):
    """Wikipedia / MediaWiki full-text search. Free, no key required."""
    name = "wikipedia"

    def search(self, query: str, max_results: int = 10) -> list[ResearchItem]:
        resp = httpx.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query,
                    "srlimit": min(max_results, 50), "format": "json"},
            timeout=30.0,
            headers={"User-Agent": "AI-Media-HQ/0.1 (https://github.com/JOELTOCUTE10/ai-media-hq)"},
        )
        resp.raise_for_status()
        results = resp.json().get("query", {}).get("search", [])
        items = []
        for r in results:
            snippet = re.sub(r"<[^>]+>", "", r.get("snippet", ""))
            items.append(ResearchItem(
                title=r.get("title", ""),
                url=f"https://en.wikipedia.org/wiki/{r['title'].replace(' ', '_')}",
                source_name="wikipedia",
                published_at=r.get("timestamp"),
                summary=snippet[:4000],
                source_type="secondary",
            ))
        return items


class HackerNewsSearchProvider(ResearchProvider):
    """Hacker News story search via the Algolia API. Free, no key required.
    Social/community signal - treated as trend discovery, not evidence."""
    name = "hackernews"

    def search(self, query: str, max_results: int = 10) -> list[ResearchItem]:
        resp = httpx.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": query, "tags": "story", "hitsPerPage": min(max_results, 50)},
            timeout=30.0,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        items = []
        for h in hits:
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID', '')}"
            items.append(ResearchItem(
                title=h.get("title", ""),
                url=url,
                source_name="hackernews",
                author=h.get("author", ""),
                published_at=h.get("created_at"),
                summary=(h.get("story_text") or "")[:4000] or h.get("title", ""),
                relevance=min(1.0, (h.get("points") or 0) / 500.0),
                source_type="social",
                extra={"points": h.get("points", 0), "num_comments": h.get("num_comments", 0)},
            ))
        return items


class ArxivSearchProvider(ResearchProvider):
    """arXiv research preprints. Free, no key required. Original research tier."""
    name = "arxiv"

    def search(self, query: str, max_results: int = 10) -> list[ResearchItem]:
        resp = httpx.get(
            "https://export.arxiv.org/api/query",
            params={"search_query": f"all:{query}", "start": 0,
                    "max_results": min(max_results, 25)},
            timeout=30.0,
        )
        resp.raise_for_status()
        items = []
        ns = {"a": "http://www.w3.org/2005/Atom"}
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as exc:
            raise RuntimeError(f"arXiv returned malformed XML: {exc}") from exc
        for entry in root.findall("a:entry", ns):
            title = (entry.findtext("a:title", "", ns) or "").strip().replace("\n", " ")
            summary = (entry.findtext("a:summary", "", ns) or "").strip()
            authors = ", ".join(a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns))
            items.append(ResearchItem(
                title=" ".join(title.split()),
                url=(entry.findtext("a:id", "", ns) or "").strip(),
                source_name="arxiv",
                author=authors[:500],
                published_at=(entry.findtext("a:published", "", ns) or "")[:10] or None,
                summary=" ".join(summary.split())[:4000],
                source_type="original_research",
            ))
        return items


class OpenAlexSearchProvider(ResearchProvider):
    """OpenAlex scholarly works catalog. Free, no key required. Original research tier."""
    name = "openalex"

    def search(self, query: str, max_results: int = 10) -> list[ResearchItem]:
        resp = httpx.get(
            "https://api.openalex.org/works",
            params={"search": query, "per_page": min(max_results, 25)},
            timeout=30.0,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        items = []
        for w in results:
            abstract = ""
            inv = w.get("abstract_inverted_index")
            if isinstance(inv, dict) and inv:
                positions = sorted(((pos, word) for word, poss in inv.items() for pos in poss))
                abstract = " ".join(word for _, word in positions)[:4000]
            doi = w.get("doi") or ""
            items.append(ResearchItem(
                title=w.get("display_name", ""),
                url=doi or w.get("id", ""),
                source_name="openalex",
                author=", ".join(a.get("author", {}).get("display_name", "")
                                 for a in (w.get("authorships") or [])[:5]),
                published_at=w.get("publication_date"),
                summary=abstract,
                relevance=w.get("relevance_score") or 0.0,
                source_type="original_research",
            ))
        return items


RESEARCH_PROVIDERS = {
    TavilySearchProvider.name: TavilySearchProvider,
    YouTubeSearchProvider.name: YouTubeSearchProvider,
    WikipediaSearchProvider.name: WikipediaSearchProvider,
    HackerNewsSearchProvider.name: HackerNewsSearchProvider,
    ArxivSearchProvider.name: ArxivSearchProvider,
    OpenAlexSearchProvider.name: OpenAlexSearchProvider,
}


def get_research_provider(name: str) -> ResearchProvider:
    cls = RESEARCH_PROVIDERS.get(name)
    if cls is None:
        raise IntegrationNotConfiguredError(f"Unknown research provider '{name}'.")
    return cls()


def available_research_providers() -> list[str]:
    """Free providers work with no credentials; key-based ones appear once configured."""
    settings = get_settings()
    available = ["wikipedia", "hackernews", "arxiv", "openalex"]
    if settings.TAVILY_API_KEY:
        available.append("tavily")
    if settings.YOUTUBE_DATA_API_KEY:
        available.append("youtube")
    return available

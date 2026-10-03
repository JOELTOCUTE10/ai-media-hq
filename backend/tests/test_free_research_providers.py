"""Free no-key research providers (Wikipedia, Hacker News, arXiv, OpenAlex).
Parsing is tested against canned real-shaped payloads; one live smoke test
against the real endpoints is marked skip-on-no-network."""
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.integrations.research_providers import (
    ArxivSearchProvider,
    HackerNewsSearchProvider,
    OpenAlexSearchProvider,
    WikipediaSearchProvider,
    available_research_providers,
)


class _Resp:
    def __init__(self, payload, text=""):
        self._payload = payload
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_free_providers_available_without_keys():
    assert available_research_providers()[:4] == ["wikipedia", "hackernews", "arxiv", "openalex"]


def test_wikipedia_parsing(monkeypatch):
    def fake_get(url, **kw):
        assert "en.wikipedia.org" in url
        return _Resp({"query": {"search": [
            {"title": "Intelligent agent", "snippet": "An <b>agent</b> is...", "timestamp": "2026-01-01T00:00:00Z"}]}})
    monkeypatch.setattr(httpx, "get", fake_get)
    items = WikipediaSearchProvider().search("agent", 5)
    assert items[0].title == "Intelligent agent"
    assert "b>" not in items[0].summary
    assert items[0].url.startswith("https://en.wikipedia.org/wiki/")
    assert items[0].source_type == "secondary"


def test_hackernews_parsing_and_social_signal(monkeypatch):
    def fake_get(url, **kw):
        return _Resp({"hits": [
            {"title": "AI agents take over", "url": "", "objectID": "42", "author": "joel",
             "created_at": "2026-09-01T00:00:00Z", "points": 800, "num_comments": 200}]})
    monkeypatch.setattr(httpx, "get", fake_get)
    items = HackerNewsSearchProvider().search("ai", 5)
    assert items[0].url == "https://news.ycombinator.com/item?id=42"
    assert items[0].source_type == "social"          # trend signal, not evidence
    assert items[0].relevance == 1.0                  # capped at 1.0


def test_arxiv_parsing(monkeypatch):
    atom = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><id>http://arxiv.org/abs/2601.00001v1</id>
    <title>Agent\n  Systems</title>
    <summary> A   study of agents. </summary>
    <published>2026-01-02T00:00:00Z</published>
    <author><name>A. Researcher</name></author></entry>
</feed>'''
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp(None, text=atom))
    items = ArxivSearchProvider().search("agents", 5)
    assert items[0].title == "Agent Systems"
    assert items[0].url.startswith("http://arxiv.org/abs/")
    assert items[0].published_at == "2026-01-02"
    assert items[0].source_type == "original_research"


def test_openalex_parsing_inverted_abstract(monkeypatch):
    def fake_get(url, **kw):
        return _Resp({"results": [{
            "display_name": "Multi-agent systems", "doi": "https://doi.org/10.1/x",
            "id": "https://openalex.org/W1", "publication_date": "2025-05-01",
            "relevance_score": 42.0, "authorships": [{"author": {"display_name": "R. Doe"}}],
            "abstract_inverted_index": {"hello": [1], "world": [0]}}]})
    monkeypatch.setattr(httpx, "get", fake_get)
    items = OpenAlexSearchProvider().search("agents", 5)
    assert items[0].summary == "world hello"         # inverted index reconstructed
    assert items[0].url == "https://doi.org/10.1/x"
    assert items[0].source_type == "original_research"


@pytest.fixture()
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_search_endpoint_with_free_provider(client, monkeypatch):
    """A no-key provider flows through the API and stores real documents."""
    token = client.post("/api/auth/register", json={
        "email": f"freeres+{uuid.uuid4().hex[:8]}@test.local", "password": "testpassword123",
        "organization_name": "Free Research Co"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp({"hits": [
        {"title": "AI agents take over", "objectID": "42", "author": "joel",
         "created_at": "2026-09-01T00:00:00Z", "points": 100, "num_comments": 10}]}))
    r = client.post("/api/research/search", headers=h,
                    json={"query": "ai agents", "provider": "hackernews", "topic": "ai-agents"})
    assert r.status_code == 200, r.text
    assert r.json()["stored"] == 1
    docs = client.get("/api/research/documents", headers=h).json()
    assert docs[0]["source_name"] == "hackernews"
    assert docs[0]["source_type"] == "social"


def test_providers_endpoint_lists_free_first(client):
    token = client.post("/api/auth/register", json={
        "email": f"prov+{uuid.uuid4().hex[:8]}@test.local", "password": "testpassword123",
        "organization_name": "Prov Co"}).json()["access_token"]
    r = client.get("/api/research/providers", headers={"Authorization": f"Bearer {token}"}).json()
    assert r["available"][:4] == ["wikipedia", "hackernews", "arxiv", "openalex"]


@pytest.mark.skip(reason="live network smoke; enable manually with: pytest -m live  (kept out of CI for determinism)")
def test_live_all_four_providers():
    for cls, q in [(WikipediaSearchProvider, "artificial intelligence"),
                  (HackerNewsSearchProvider, "AI agents"),
                  (ArxivSearchProvider, "language model agents"),
                  (OpenAlexSearchProvider, "multi-agent systems")]:
        items = cls().search(q, 3)
        assert items, f"{cls.name} returned no results"
        assert items[0].url.startswith("http")

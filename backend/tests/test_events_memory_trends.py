from datetime import UTC


def test_events_recorded(client, org):
    headers, _ = org
    task = client.post("/api/tasks", headers=headers, json={
        "title": "Eventful task", "agent_key": "web_research",
        "input": {"required_permission": "write_research"}}).json()
    client.post(f"/api/tasks/{task['id']}/run", headers=headers)
    events = client.get("/api/events", headers=headers).json()
    types = [e["event_type"] for e in events]
    assert "TASK_CREATED" in types
    assert "TASK_STARTED" in types
    assert "TASK_COMPLETED" in types


def test_memory_record_and_search(client, org):
    headers, _ = org
    client.post("/api/memory", headers=headers, json={
        "scope": "channel", "content": "AI channel performs best with tool explainers in the evening",
        "key": "ai-channel-learnings", "channel_id": 1, "tags": ["retention"]})
    client.post("/api/memory", headers=headers, json={
        "scope": "long_term", "content": "Soccer transfer rumors need two independent sources"})
    r = client.get("/api/memory/search?q=transfer", headers=headers)
    assert r.status_code == 200
    results = r.json()
    assert len(results) == 1
    assert "transfer" in results[0]["content"].lower()
    scoped = client.get("/api/memory/search?scope=channel", headers=headers).json()
    assert len(scoped) == 1


def test_trend_scan_no_data_is_honest(client, org):
    headers, _ = org
    r = client.post("/api/trends/scan", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["trends"] == []
    assert "never fabricated" in body["message"]


def test_trend_scan_from_real_documents(client, org, monkeypatch=None):
    from datetime import datetime

    from app.db.session import SessionLocal
    from app.models.channel import Channel
    from app.models.research import ResearchDocument

    headers, org_id = org
    db = SessionLocal()
    channel = db.query(Channel).filter(Channel.org_id == org_id).first()
    now = datetime.now(UTC)
    for i in range(5):
        db.add(ResearchDocument(org_id=org_id, channel_id=channel.id, topic="ai_agents",
                                title=f"AI agents doc {i}", url=f"https://example.com/{i}",
                                retrieved_at=now, source_type="secondary"))
    db.commit()
    db.close()

    r = client.post("/api/trends/scan", headers=headers)
    body = r.json()
    assert body["trends"], "expected at least one trend"
    trend = body["trends"][0]
    assert trend["topic"] == "ai_agents"
    assert trend["lifecycle"] == "emerging"

    trends = client.get("/api/trends", headers=headers).json()
    match = [t for t in trends if t["topic"] == "ai_agents"][0]
    assert match["signals"]["documents_recent_7d"] == 5
    assert match["signals"]["growth_ratio"] == 2.0
    assert len(match["evidence"]) == 5


def test_research_search_unconfigured_is_503(client, org):
    headers, _ = org
    r = client.post("/api/research/search", headers=headers,
                    json={"query": "latest AI news", "provider": "tavily"})
    assert r.status_code == 503
    assert "TAVILY_API_KEY" in r.json()["detail"]


def test_dashboard_real_data(client, org):
    headers, _ = org
    r = client.get("/api/dashboard", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["channels"]["total"] == 5
    assert body["agents"]["total"] == 33
    assert isinstance(body["recommendations"], list)
    assert body["tasks"]["queued"] >= 0


def test_settings_kill_switch_persists(client, org):
    headers, _ = org
    r = client.put("/api/settings", headers=headers, json={"publishing_paused": False})
    assert r.status_code == 200
    current = client.get("/api/settings", headers=headers).json()
    assert current["organization"]["settings"]["publishing_paused"] is False
    assert current["organization"]["settings"]["auto_publish"] is False

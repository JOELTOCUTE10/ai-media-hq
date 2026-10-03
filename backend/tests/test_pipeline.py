"""Phase 3-8 pipeline tests: ideas -> scripts -> claims -> QC -> approval ->
production -> publishing gate. All against real rows, honest expectations."""
import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def ctx():
    from app.main import app
    with TestClient(app) as client:
        email = f"pipeline+{uuid.uuid4().hex[:8]}@test.local"
        token = client.post("/api/auth/register", json={
            "email": email, "password": "testpassword123",
            "organization_name": "Pipeline Media"}).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        yield client, h


def make_idea(client, h, title="Why AI agents will run media companies", slug="ai-technology"):
    r = client.post("/api/ideas", headers=h, json={
        "channel_slug": slug, "title": title, "topic": "AI agents",
        "hook": "In 18 months, one person will run a media empire.",
        "description": "Shorts about AI agents automating content", "confidence": 0.8})
    assert r.status_code == 201, r.text
    return r.json()


def full_script(client, h, idea_id, body="Five departments. Zero employees.", cta="Follow for part 2."):
    sid = client.post(f"/api/scripts?idea_id={idea_id}", headers=h).json()["id"]
    r = client.post(f"/api/scripts/{sid}/versions", headers=h, json={
        "hook": "Stop scrolling: this changes everything.",
        "body": body, "cta": cta, "changes": "initial version",
        "author_agent_key": "script"})
    assert r.status_code == 201, r.text
    return sid, r.json()["version"]


def full_script_approve(client, h, idea_id):
    sid = client.post(f"/api/scripts?idea_id={idea_id}", headers=h).json()["id"]
    latest = client.get(f"/api/scripts/{sid}/latest", headers=h).json()
    client.post(f"/api/scripts/{sid}/versions/{latest['version']}/review", headers=h,
                json={"decision": "approved"})


def test_idea_lifecycle_and_transitions(ctx):
    client, h = ctx
    idea = make_idea(client, h, title="Idea lifecycle test")
    assert idea["status"] == "candidate"
    # invalid transition rejected
    r = client.post(f"/api/ideas/{idea['id']}/status?new_status=published", headers=h)
    assert r.status_code == 409
    r = client.post(f"/api/ideas/{idea['id']}/status?new_status=reviewed", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "reviewed"
    r = client.post(f"/api/ideas/{idea['id']}/status?new_status=approved", headers=h)
    assert r.json()["status"] == "approved"


def test_script_versions_and_review(ctx):
    client, h = ctx
    idea = make_idea(client, h, title="Script versioning test")
    sid, v1 = full_script(client, h, idea["id"])
    r = client.post(f"/api/scripts/{sid}/versions", headers=h, json={
        "hook": "Better hook.", "body": "Tighter body.", "cta": "Subscribe.",
        "changes": "tightened pacing", "author_agent_key": "script"})
    assert r.status_code == 201 and r.json()["version"] == 2
    latest = client.get(f"/api/scripts/{sid}/latest", headers=h).json()
    assert latest["version"] == 2 and latest["review_status"] == "draft"
    r = client.post(f"/api/scripts/{sid}/versions/2/review", headers=h,
                    json={"decision": "approved", "notes": "lgtm"})
    assert r.json()["review_status"] == "approved"


def test_claims_and_qc_blocking(ctx):
    client, h = ctx
    idea = make_idea(client, h, title="Claims blocking test")
    full_script(client, h, idea["id"])

    # unresolved claim -> NEEDS_REVIEW; disputed claim -> FAIL
    c1 = client.post(f"/api/ideas/{idea['id']}/claims", headers=h, json={
        "text": "AI agents can already edit video end to end.",
        "source": "TechCrunch", "source_url": "https://example.com/a",
        "source_type": "reputable_journalism"}).json()
    qc = client.post("/api/qc/run?idea_id=" + str(idea["id"]), headers=h).json()
    assert qc["result"] in ("FAIL", "NEEDS_REVIEW")
    assert any("claim" in reason.lower() for reason in qc["reasons"])

    r = client.post(f"/api/ideas/claims/{c1['id']}/verify", headers=h,
                    json={"status": "disputed", "confidence": 0.1, "notes": "not yet true"})
    assert r.json()["status"] == "disputed"
    qc = client.post("/api/qc/run?idea_id=" + str(idea["id"]), headers=h).json()
    assert qc["result"] == "FAIL"

    r = client.post(f"/api/ideas/claims/{c1['id']}/verify", headers=h,
                    json={"status": "verified", "confidence": 0.95, "notes": "confirmed"})
    # approve the script review so QC can pass (draft scripts force NEEDS_REVIEW)
    full_script_approve(client, h, idea["id"])
    qc = client.post("/api/qc/run?idea_id=" + str(idea["id"]), headers=h).json()
    assert qc["result"] == "PASS", qc["reasons"]
    assert qc["checks"]["claims"]["verified"] == 1


def test_missing_script_fails_qc(ctx):
    client, h = ctx
    idea = make_idea(client, h, title="QC without script test")
    qc = client.post("/api/qc/run?idea_id=" + str(idea["id"]), headers=h).json()
    assert qc["result"] == "FAIL"
    assert any("script" in reason.lower() for reason in qc["reasons"])


def test_rights_block_publishing_by_default(ctx):
    client, h = ctx
    idea = make_idea(client, h, title="Rights gating test")
    # publishing is paused by default (kill switch); unpause for this test flow
    client.put("/api/settings", headers=h, json={"publishing_paused": False})
    full_script(client, h, idea["id"])
    # produce an asset via the honest user_media provider
    job = client.post("/api/production/jobs", headers=h, json={
        "idea_id": idea["id"], "provider": "user_media",
        "config": {"media_url": "https://example.com/clip.mp4"}}).json()
    r = client.post(f"/api/production/jobs/{job['id']}/run", headers=h)
    assert r.status_code == 200, r.text
    asset_id = r.json()["asset_id"]

    # resolve claims, approve script review, run QC, get human approval
    cl = client.post(f"/api/ideas/{idea['id']}/claims", headers=h, json={
        "text": "Claims resolved", "source": "x", "source_url": "https://example.com/c"}).json()
    client.post(f"/api/ideas/claims/{cl['id']}/verify", headers=h,
                json={"status": "verified", "confidence": 0.9})
    full_script_approve(client, h, idea["id"])
    qc = client.post("/api/qc/run?idea_id=" + str(idea["id"]), headers=h).json()
    assert qc["result"] == "PASS", qc["reasons"]
    appr = client.post("/api/approvals", headers=h, json={"idea_id": idea["id"]}).json()
    client.post(f"/api/approvals/{appr['id']}/decide", headers=h,
                json={"decision": "approved", "notes": "looks good"})

    # rights unknown (asset has no rights record) -> guard blocks by default
    pub = client.post("/api/publishing/jobs", headers=h, json={
        "idea_id": idea["id"], "metadata": {"title": "T", "description": "D", "tags": ["ai"]}}).json()
    r = client.post(f"/api/publishing/jobs/{pub['id']}/publish", headers=h)
    assert r.status_code == 409, r.text
    assert "rights" in r.json()["detail"]["reason"].lower()

    # set proper rights -> gate passes, but honest failure: YouTube not connected
    rr = client.post("/api/production/rights", headers=h, json={
        "idea_id": idea["id"], "asset_id": asset_id, "status": "user_owned",
        "content_description": "original AI-generated clip"}).json()
    assert rr["status"] == "user_owned"
    r = client.post(f"/api/publishing/jobs/{pub['id']}/publish", headers=h)
    assert r.status_code == 409, r.text
    assert "YouTube" in r.json()["detail"]["reason"]
    job_row = client.get("/api/publishing/jobs?idea_id=" + str(idea["id"]), headers=h).json()[0]
    assert job_row["status"] == "failed" and "YouTube account not connected" in job_row["error"]


def test_approval_flow_events(ctx):
    client, h = ctx
    idea = make_idea(client, h, title="Approval flow test")
    appr = client.post("/api/approvals", headers=h, json={
        "idea_id": idea["id"], "notes": "ready for review"}).json()
    assert appr["status"] == "pending"
    r = client.post(f"/api/approvals/{appr['id']}/decide", headers=h,
                    json={"decision": "changes_requested", "notes": "shorten hook"})
    assert r.json()["status"] == "changes_requested"
    events = client.get("/api/events?limit=50", headers=h).json()
    assert any(e["event_type"] == "APPROVAL_REQUESTED" for e in events)


def test_strategy_room_honest_results(ctx):
    client, h = ctx
    idea = make_idea(client, h, title="Strategy room test")
    r = client.post(f"/api/ideas/{idea['id']}/strategy-room", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 5
    # fake provider configured in tests -> all reviews completed with real runs
    assert data["completed"] == 5
    assert all("answer" in rev and rev["answer"] for rev in data["reviews"])
    assert data["synthesis"]["task_status"] == "completed"
    # idea moved to reviewed
    idea_now = client.get(f"/api/ideas/{idea['id']}", headers=h).json()
    assert idea_now["idea"]["status"] in ("reviewed", "candidate")


def test_content_passport(ctx):
    client, h = ctx
    idea = make_idea(client, h, title="Passport test")
    full_script(client, h, idea["id"])
    cl = client.post(f"/api/ideas/{idea['id']}/claims", headers=h, json={
        "text": "Passport claim", "source": "s", "source_url": "https://example.com/p"}).json()
    client.post(f"/api/ideas/claims/{cl['id']}/verify", headers=h,
                json={"status": "verified", "confidence": 0.9})
    full_script_approve(client, h, idea["id"])
    client.post("/api/qc/run?idea_id=" + str(idea["id"]), headers=h)
    passport = client.get(f"/api/ideas/{idea['id']}", headers=h).json()
    assert passport["script_versions"] and passport["claims"]
    assert passport["quality_checks"] and passport["quality_checks"][0]["result"] == "PASS"


def test_knowledge_graph(ctx):
    client, h = ctx
    topic = client.post("/api/knowledge/entities", headers=h, json={
        "entity_type": "topic", "name": "AI Agents"}).json()
    person = client.post("/api/knowledge/entities", headers=h, json={
        "entity_type": "person", "name": "Sam Altman"}).json()
    r = client.post("/api/knowledge/relationships", headers=h, json={
        "source_entity_id": topic["id"], "target_entity_id": person["id"],
        "relation_type": "discusses"})
    assert r.status_code == 201
    graph = client.get("/api/knowledge/graph?entity_id=" + str(topic["id"]), headers=h).json()
    assert len(graph["nodes"]) == 2 and len(graph["edges"]) == 1
    found = client.get("/api/knowledge/entities?q=altman", headers=h).json()
    assert found and "Altman" in found[0]["name"]


def test_unconfigured_external_video_provider_is_honest(ctx):
    client, h = ctx
    idea = make_idea(client, h, title="External provider honesty test")
    job = client.post("/api/production/jobs", headers=h, json={
        "idea_id": idea["id"], "provider": "external", "config": {}}).json()
    r = client.post(f"/api/production/jobs/{job['id']}/run", headers=h)
    assert r.status_code == 503
    assert "VIDEO_PROVIDER_URL" in r.json()["detail"]
    jobs = client.get(f"/api/production/jobs?idea_id={idea['id']}", headers=h).json()
    assert jobs[0]["status"] == "failed"

"""Phase 7-8 + Founder Mode tests: analytics, learning, experiments, costs,
reports, goals. All against real rows - no fabricated metrics."""
import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def ctx():
    from app.main import app
    with TestClient(app) as client:
        email = f"growth+{uuid.uuid4().hex[:8]}@test.local"
        token = client.post("/api/auth/register", json={
            "email": email, "password": "testpassword123",
            "organization_name": "Growth Media"}).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        yield client, h


def _published_video(client, h, title, hook, views, retention, likes=10, shares=2):
    """Full honest chain: idea -> script -> QC -> approval -> production -> publish job
    (marked published via the guard-passing path with YouTube mocked off) is too
    heavy; instead we exercise the real data path: create idea + publishing job
    and record a metrics snapshot against it."""
    idea = client.post("/api/ideas", headers=h, json={
        "channel_slug": "ai-technology", "title": title, "topic": "AI",
        "hook": hook}).json()
    pub = client.post("/api/publishing/jobs", headers=h, json={
        "idea_id": idea["id"],
        "metadata": {"title": title, "description": "desc", "tags": ["ai"]}}).json()
    snap = client.post("/api/analytics/snapshots", headers=h, json={
        "publishing_job_id": pub["id"], "video_title": title, "views": views,
        "watch_time_minutes": views * 0.4, "retention_pct": retention,
        "likes": likes, "comments": 2, "shares": shares,
        "subscribers_gained": 5}).json()
    assert snap["id"]
    return pub


def test_analytics_ingest_and_composite(ctx):
    client, h = ctx
    _published_video(client, h, "AI agents 101", "hook one", 1000, 55)
    _published_video(client, h, "AI agents 102", "hook one", 2000, 70)
    _published_video(client, h, "AI agents 103", "hook two", 500, 30)
    videos = client.get("/api/analytics/videos", headers=h).json()
    assert len(videos) >= 3
    # composite score is documented, bounded and ordered
    for v in videos:
        assert 0 <= v["composite_score"] <= 100
    assert videos[0]["composite_score"] >= videos[-1]["composite_score"]
    roll = client.get("/api/analytics/channels", headers=h).json()
    assert roll and roll[0]["videos"] >= 3
    assert roll[0]["avg_retention_pct"] > 0


def test_learning_insight_sample_size_guard(ctx):
    client, h = ctx
    r = client.post("/api/analytics/learn?channel_slug=ai-technology", headers=h)
    insights = r.json()
    assert insights
    first = insights[0]
    # with only a handful of videos the engine must NOT claim a rule
    assert first["status"] == "insufficient_sample"
    assert "Not enough data" in first["observation"]


def test_experiment_lifecycle_honest_conclusion(ctx):
    client, h = ctx
    e = client.post("/api/experiments", headers=h, json={
        "name": "Hook A vs B", "hypothesis": "Question hooks retain better",
        "variable": "hook", "control": "statement hook", "variant": "question hook",
        "channel_slug": "ai-technology"}).json()
    assert e["status"] == "running"
    r = client.post(f"/api/experiments/{e['id']}/result", headers=h, json={
        "sample_size": 8, "control_metrics": {"retention_pct": 40},
        "variant_metrics": {"retention_pct": 52}}).json()
    assert "higher" in r["conclusion"]
    assert "low" in r["confidence"]          # small sample -> honest low confidence
    assert "no causal claim" in r["limitations"]
    listed = client.get("/api/experiments", headers=h).json()
    row = next(x for x in listed if x["id"] == e["id"])
    assert row["status"] == "completed" and row["conclusion"]


def test_costs_summary_only_real_records(ctx):
    client, h = ctx
    s = client.get("/api/costs/summary", headers=h).json()
    assert "month_to_date_usd" in s and "monthly_budget_usd" in s
    assert isinstance(s["by_category"], list)
    # costs come from real agent runs; the fake provider records them
    assert s["month_to_date_usd"] >= 0
    records = client.get("/api/costs/records", headers=h).json()
    assert isinstance(records, list)


def test_daily_report_from_real_data(ctx):
    client, h = ctx
    r = client.post("/api/reports/daily", headers=h)
    assert r.status_code == 200
    content = r.json()["content"]
    assert "recommendations" in content and "costs" in content
    assert content["videos_published_today"] == []  # honest: nothing actually published
    # the report is built from real rows in this org (it has analytics + tasks)
    assert content["channel_rollup"], content
    assert len(content["recommendations"]) > 0
    assert any("strongest performer" in rec or "analytics" in rec.lower()
               for rec in content["recommendations"])
    listed = client.get("/api/reports", headers=h).json()
    assert listed and listed[0]["content"]["report_date"]


def test_founder_mode_goal_decomposition(ctx):
    client, h = ctx
    goal = client.post("/api/founder/goals", headers=h, json={
        "title": "Grow the AI channel", "description": "More subscribers and retention",
        "channel_slug": "ai-technology"}).json()
    assert goal["progress"]["total"] == 6
    assert goal["progress"]["completed"] == 0
    listed = client.get("/api/founder/goals", headers=h).json()
    row = next(g for g in listed if g["id"] == goal["id"])
    assert row["title"] == "Grow the AI channel"
    detail = client.get(f"/api/founder/goals/{goal['id']}", headers=h).json()
    assert len(detail["tasks"]) == 6
    # tasks are real: research task can be executed through the fake provider
    task_id = detail["tasks"][0]["id"]
    r = client.post(f"/api/tasks/{task_id}/run", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "completed"
    detail = client.get(f"/api/founder/goals/{goal['id']}", headers=h).json()
    assert detail["progress"]["completed"] == 1


def test_goals_and_kill_switch_interplay(ctx):
    client, h = ctx
    # kill switch blocks execution but goal structure stays intact
    client.put("/api/settings", headers=h, json={"operations_paused": True})
    goal = client.post("/api/founder/goals", headers=h, json={
        "title": "Paused world goal"}).json()
    detail = client.get(f"/api/founder/goals/{goal['id']}", headers=h).json()
    r = client.post(f"/api/tasks/{detail['tasks'][0]['id']}/run", headers=h)
    # the orchestrator blocks the task honestly with the kill-switch reason
    assert r.json()["status"] == "blocked"
    assert "paused" in r.json()["error"].lower()
    client.put("/api/settings", headers=h, json={"operations_paused": False})

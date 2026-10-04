"""Agent initiative: auto-assignment, suggestions, approve/reject, autonomy."""
import json

import pytest

from app.db.session import SessionLocal
from app.integrations.ai_providers import Completion
from app.models.agent import Agent
from app.models.initiative import AgentSuggestion
from app.models.organization import Organization, User
from app.models.task import Task
from app.services.initiative_service import (
    approve_suggestion,
    auto_assign_queued,
    generate_suggestions,
    reject_suggestion,
)


class _JsonProvider:
    """Test double: returns a canned JSON proposal like a real agent would."""
    name = "json-fake"

    def __init__(self, proposal):
        self.proposal = proposal if isinstance(proposal, str) else json.dumps(proposal)

    def complete(self, system, user, temperature=0.4, max_tokens=2000):
        return Completion(text=self.proposal, model="fake", prompt_tokens=10,
                          completion_tokens=5)


@pytest.fixture()
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def org_row(client, db):
    """Fresh org via the API, then its DB row (agents are seeded)."""
    import uuid
    suffix = uuid.uuid4().hex[:8]
    r = client.post("/api/auth/register", json={
        "email": f"init-{suffix}@test.local", "password": "testpassword123",
        "full_name": "Init Owner", "organization_name": f"Init Media {suffix}"})
    assert r.status_code == 201, r.text
    user = db.query(User).filter_by(email=f"init-{suffix}@test.local").one()
    org = db.get(Organization, user.org_id)
    assert db.query(Agent).filter_by(org_id=org.id).count() > 0, "agents must be seeded"
    return org


def test_auto_assign_routes_unassigned_task_to_best_agent(db, org_row):
    task = Task(org_id=org_row.id,
                title="Research web sources for a trend report on AI chips",
                description="web research on AI chips", status="queued")
    db.add(task)
    db.commit()

    assigned = auto_assign_queued(db, org_row)
    assert assigned >= 1
    db.refresh(task)
    assert task.assigned_agent_id is not None
    agent = db.get(Agent, task.assigned_agent_id)
    assert agent.status == "active"


def test_auto_assign_respects_kill_switch(db, org_row):
    org_row.settings = dict(org_row.settings or {}, operations_paused=True)
    db.commit()
    task = Task(org_id=org_row.id, title="Find trends", status="queued")
    db.add(task)
    db.commit()
    assert auto_assign_queued(db, org_row) == 0
    db.refresh(task)
    assert task.assigned_agent_id is None


def test_generate_suggestions_creates_proposal(db, org_row):
    provider = _JsonProvider({
        "title": "Draft weekly channel strategy brief",
        "description": "Compare channel performance and propose focus areas",
        "rationale": "No strategy review in the last week",
        "priority": "high"})
    created = generate_suggestions(db, org_row, provider=provider, force=True)
    active = db.query(Agent).filter_by(org_id=org_row.id, status="active").count()
    # up to INITIATIVE_AGENTS_PER_PASS (default 3) idle agents propose
    assert 1 <= created <= min(3, active)
    sug = db.query(AgentSuggestion).filter_by(org_id=org_row.id).first()
    assert sug.status == "proposed"
    assert sug.created_by_agent is True
    assert sug.title == "Draft weekly channel strategy brief"
    assert sug.priority == "high"


def test_generate_suggestions_respects_opt_out(db, org_row):
    org_row.settings = dict(org_row.settings or {}, agent_initiative=False)
    db.commit()
    provider = _JsonProvider({"title": "x", "description": "", "rationale": ""})
    assert generate_suggestions(db, org_row, provider=provider) == 0


def test_generate_suggestions_blocked_when_paused(db, org_row):
    org_row.settings = dict(org_row.settings or {}, operations_paused=True)
    db.commit()
    provider = _JsonProvider({"title": "x", "description": "", "rationale": ""})
    assert generate_suggestions(db, org_row, provider=provider, force=True) == 0


def test_daily_cap_limits_proposals(db, org_row, monkeypatch):
    provider = _JsonProvider({
        "title": "Propose something", "description": "d", "rationale": "r",
        "priority": "medium"})
    from app.core.config import get_settings
    s = get_settings()
    active = db.query(Agent).filter_by(org_id=org_row.id, status="active").count()
    monkeypatch.setattr(s, "INITIATIVE_MAX_PER_AGENT_PER_DAY", 1)
    monkeypatch.setattr(s, "INITIATIVE_AGENTS_PER_PASS", active + 10)
    first = generate_suggestions(db, org_row, provider=provider, force=True)
    assert first == active  # every agent proposes exactly once
    second = generate_suggestions(db, org_row, provider=provider, force=True)
    assert second == 0  # daily cap of 1 blocks a second proposal today


def test_unparsable_proposal_is_skipped_not_crashed(db, org_row):
    provider = _JsonProvider("I refuse to use JSON")
    assert generate_suggestions(db, org_row, provider=provider, force=True) == 0


def test_approve_creates_task_assigned_to_agent(db, org_row):
    agent = db.query(Agent).filter_by(org_id=org_row.id).first()
    sug = AgentSuggestion(org_id=org_row.id, agent_id=agent.id, title="Do the thing",
                          description="details", rationale="because", priority="high",
                          status="proposed")
    db.add(sug)
    db.commit()
    task = approve_suggestion(db, sug)
    assert task.status == "queued"
    assert task.assigned_agent_id == agent.id
    assert sug.status == "approved"
    assert sug.task_id == task.id


def test_reject_marks_suggestion(db, org_row):
    agent = db.query(Agent).filter_by(org_id=org_row.id).first()
    sug = AgentSuggestion(org_id=org_row.id, agent_id=agent.id, title="Nope",
                          status="proposed")
    db.add(sug)
    db.commit()
    reject_suggestion(db, sug)
    assert sug.status == "rejected"


def test_auto_approve_setting_creates_task_immediately(db, org_row):
    org_row.settings = dict(org_row.settings or {}, auto_approve_suggestions=True)
    db.commit()
    provider = _JsonProvider({
        "title": "Autonomous work item", "description": "d", "rationale": "r",
        "priority": "medium"})
    created = generate_suggestions(db, org_row, provider=provider, force=True)
    assert created >= 1
    sugs = db.query(AgentSuggestion).filter_by(org_id=org_row.id).all()
    assert all(s.status == "approved" for s in sugs)
    assert all(s.task_id is not None for s in sugs)


def test_suggestions_api_flow(client, db, org):
    headers, org_id = org
    org_row = db.get(Organization, org_id)
    provider = _JsonProvider({
        "title": "API-created suggestion", "description": "d", "rationale": "r",
        "priority": "low"})
    generate_suggestions(db, org_row, provider=provider, force=True)

    r = client.get("/api/suggestions?status_filter=proposed", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["proposed_count"] >= 1
    sid = body["suggestions"][0]["id"]
    assert body["suggestions"][0]["agent_name"]

    r = client.post(f"/api/suggestions/{sid}/approve", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["task_id"]

    r = client.post(f"/api/suggestions/{sid}/approve", headers=headers)
    assert r.status_code == 400

    generate_suggestions(db, org_row, provider=provider, force=True)
    r = client.get("/api/suggestions?status_filter=proposed", headers=headers)
    sid2 = r.json()["suggestions"][0]["id"]
    r = client.post(f"/api/suggestions/{sid2}/reject", headers=headers)
    assert r.status_code == 200
    r = client.get("/api/suggestions?status_filter=rejected", headers=headers)
    assert any(s["id"] == sid2 for s in r.json()["suggestions"])


def test_suggestion_events_published(db, org_row):
    from app.core.events import EventType
    from app.models.ops import SystemEvent
    provider = _JsonProvider({
        "title": "Event test", "description": "d", "rationale": "r", "priority": "low"})
    before = db.query(SystemEvent).filter_by(event_type=EventType.SUGGESTION_CREATED).count()
    generate_suggestions(db, org_row, provider=provider, force=True)
    after = db.query(SystemEvent).filter_by(event_type=EventType.SUGGESTION_CREATED).count()
    assert after > before

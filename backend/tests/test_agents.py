from app.agents.permissions import LEVEL_PERMISSIONS, agent_can
from app.agents.registry import AGENTS, DEPARTMENTS


def test_registry_shape():
    assert len(AGENTS) == 33
    keys = [a["key"] for a in AGENTS]
    assert len(keys) == len(set(keys)), "agent keys must be unique"
    for a in AGENTS:
        assert a["department"] in DEPARTMENTS
        assert a["permission_level"] in LEVEL_PERMISSIONS


def test_permission_levels():
    assert agent_can("read_only", "read_research")
    assert not agent_can("read_only", "publish")
    assert agent_can("publisher", "publish")
    assert not agent_can("publisher", "create_scripts")
    assert agent_can("administrator", "modify_system")


def test_seed_agents_and_departments(client, org):
    headers, _ = org
    r = client.get("/api/agents", headers=headers)
    assert r.status_code == 200
    agents = r.json()
    assert len(agents) == 33
    by_key = {a["key"]: a for a in agents}
    assert by_key["chief_strategy"]["department"] == "executive"
    assert by_key["publishing"]["permission_level"] == "publisher"
    assert "publish" in by_key["publishing"]["permissions"]


def test_pause_resume_agent(client, org):
    headers, _ = org
    agents = client.get("/api/agents?department=intelligence", headers=headers).json()
    agent = agents[0]
    r = client.post(f"/api/agents/{agent['id']}/pause", headers=headers)
    assert r.json()["status"] == "paused"
    r = client.post(f"/api/agents/{agent['id']}/resume", headers=headers)
    assert r.json()["status"] == "active"

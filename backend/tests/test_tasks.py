def _create_task(client, headers, **overrides):
    payload = {"title": "Find five strong AI Shorts ideas for this week",
               "description": "Command Center request",
               "agent_key": "idea", "channel_slug": "ai-technology",
               "priority": "high", "input": {"required_permission": "create_ideas"}}
    payload.update(overrides)
    return client.post("/api/tasks", headers=headers, json=payload)


def test_create_and_run_task(client, org):
    headers, _ = org
    r = _create_task(client, headers)
    assert r.status_code == 201, r.text
    task = r.json()
    assert task["status"] == "queued"
    assert task["assigned_agent_id"] is not None

    run = client.post(f"/api/tasks/{task['id']}/run", headers=headers)
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["status"] == "completed", body
    assert "[fake-provider]" in body["output"]["result"]


def test_permission_block(client, org):
    headers, _ = org
    r = _create_task(client, headers, agent_key="analytics",
                     input={"required_permission": "create_ideas"})
    task = r.json()
    run = client.post(f"/api/tasks/{task['id']}/run", headers=headers)
    assert run.json()["status"] == "blocked"
    assert "lacks permission" in run.json()["error"]


def test_paused_agent_blocked(client, org):
    headers, _ = org
    task = _create_task(client, headers).json()
    agent_id = task["assigned_agent_id"]
    client.post(f"/api/agents/{agent_id}/pause", headers=headers)
    run = client.post(f"/api/tasks/{task['id']}/run", headers=headers)
    assert run.json()["status"] == "blocked"
    client.post(f"/api/agents/{agent_id}/resume", headers=headers)


def test_kill_switch_blocks_execution(client, org):
    headers, _ = org
    task = _create_task(client, headers).json()
    put = client.put("/api/settings", headers=headers, json={"operations_paused": True})
    assert put.status_code == 200
    run = client.post(f"/api/tasks/{task['id']}/run", headers=headers)
    assert run.json()["status"] == "blocked"
    assert "kill switch" in run.json()["error"]
    client.put("/api/settings", headers=headers, json={"operations_paused": False})


def test_dependencies(client, org):
    headers, _ = org
    first = _create_task(client, headers, title="Research trends").json()
    second = _create_task(client, headers, title="Summarize findings",
                          agent_key="chief_strategy",
                          input={"required_permission": "review_content"},
                          depends_on=[first["id"]]).json()
    run = client.post(f"/api/tasks/{second['id']}/run", headers=headers)
    assert run.json()["status"] == "waiting"

    client.post(f"/api/tasks/{first['id']}/run", headers=headers)
    run2 = client.post(f"/api/tasks/{second['id']}/run", headers=headers)
    assert run2.json()["status"] == "completed", run2.json()


def test_task_cancel(client, org):
    headers, _ = org
    task = _create_task(client, headers, title="To be cancelled").json()
    r = client.post(f"/api/tasks/{task['id']}/cancel", headers=headers)
    assert r.json()["status"] == "cancelled"
    dup = client.post(f"/api/tasks/{task['id']}/cancel", headers=headers)
    assert dup.status_code == 409


def test_agent_run_recorded(client, org):
    headers, _ = org
    task = _create_task(client, headers).json()
    client.post(f"/api/tasks/{task['id']}/run", headers=headers)
    runs = client.get(f"/api/agents/{task['assigned_agent_id']}/runs", headers=headers).json()
    assert runs and runs[0]["status"] == "completed"
    assert runs[0]["cost_usd"] == 0.0  # fake provider is free

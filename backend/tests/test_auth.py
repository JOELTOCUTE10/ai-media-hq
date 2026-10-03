def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_login_me(client, org):
    headers, org_id = org
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["org_id"] == org_id
    assert r.json()["role"] == "owner"


def test_register_duplicate_email(client, org):
    import uuid
    email = f"dupe-{uuid.uuid4().hex[:6]}@test.local"
    first = client.post("/api/auth/register", json={"email": email, "password": "testpassword123"})
    assert first.status_code == 201
    duplicate = client.post("/api/auth/register", json={"email": email, "password": "testpassword123"})
    assert duplicate.status_code == 409


def test_login_wrong_password(client, org):
    import uuid
    email = f"login-{uuid.uuid4().hex[:6]}@test.local"
    client.post("/api/auth/register", json={"email": email, "password": "testpassword123"})
    r = client.post("/api/auth/login", json={"email": email, "password": "wrongpassword"})
    assert r.status_code == 401


def test_unauthenticated_blocked(client):
    assert client.get("/api/channels").status_code == 401

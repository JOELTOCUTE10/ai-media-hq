"""Test configuration: isolated SQLite DB, FakeProvider, disabled runner."""
import os
import uuid

os.environ["AI_PROVIDER"] = "fake"
os.environ["DATABASE_URL"] = "sqlite:///./test_ai_media_hq.db"
os.environ["TASK_RUNNER_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-bytes-long!!"

if os.path.exists("./test_ai_media_hq.db"):
    os.remove("./test_ai_media_hq.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def org(client):
    """Register a fresh organization + owner, return (headers, org_id)."""
    suffix = uuid.uuid4().hex[:8]
    r = client.post("/api/auth/register", json={
        "email": f"owner-{suffix}@test.local", "password": "testpassword123",
        "full_name": "Test Owner", "organization_name": f"Test Media {suffix}"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/auth/me", headers=headers)
    return headers, me.json()["org_id"]

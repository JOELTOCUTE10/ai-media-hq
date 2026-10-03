def test_seed_channels(client, org):
    headers, _ = org
    r = client.get("/api/channels", headers=headers)
    assert r.status_code == 200
    channels = r.json()
    slugs = {c["slug"] for c in channels}
    assert {"ai-technology", "soccer", "business-money", "transformative-clips", "interesting-facts"} <= slugs


def test_create_channel_and_duplicate_slug(client, org):
    headers, _ = org
    r = client.post("/api/channels", headers=headers, json={
        "name": "Gaming", "niche": "gaming", "audience": "gamers"})
    assert r.status_code == 201
    assert r.json()["slug"] == "gaming"
    dup = client.post("/api/channels", headers=headers, json={"name": "Gaming"})
    assert dup.status_code == 409


def test_channel_is_config_driven(client, org):
    headers, _ = org
    r = client.post("/api/channels", headers=headers, json={
        "name": "Science", "content_rules": {"every_claim_needs_source": True},
        "publishing_rules": {"cadence_per_week": 3}, "style": {"length_seconds": [30, 45]}})
    assert r.status_code == 201
    assert r.json()["content_rules"]["every_claim_needs_source"] is True
    assert r.json()["publishing_rules"]["cadence_per_week"] == 3

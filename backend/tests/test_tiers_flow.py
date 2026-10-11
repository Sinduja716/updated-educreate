"""Different purposes get different tiers, every plan and finished page shows an estimate, the user can override."""


def make(client, button, prompt, overrides=None):
    body = {"material_type": button, "prompt": prompt}
    if overrides:
        body["overrides"] = overrides
    return client.post("/api/v1/plans", json=body).json()


def test_purpose_sets_tier_and_reason(client):
    colouring = make(client, "colouring", "cat")
    poster = make(client, "poster", "water cycle")
    assert colouring["tier"] == "draft" and poster["tier"] == "high"
    assert colouring["steps"] < poster["steps"]
    assert colouring["tier_reason"] and poster["tier_reason"]
    assert colouring["estimate"]["neurons"] < poster["estimate"]["neurons"]
    assert colouring["estimate"]["saving_percent"] > 0 and poster["estimate"]["saving_percent"] == 0


def test_manual_tier_override(client):
    plan = make(client, "colouring", "cat", {"tier": "high"})
    assert plan["tier"] == "high"
    assert plan["resolved"]["tier"]["source"] == "user"


def test_auto_never_stays_auto(client):
    plan = make(client, "auto", "a quick icon for my app")
    assert plan["material_type"] == "thumbnail"
    assert plan["tier"] == "draft"
    assert make(client, "auto", "something unclear")["material_type"] != "auto"


def test_estimate_after_generation(client):
    plan = make(client, "thumbnail", "red apple")
    client.post(f"/api/v1/plans/{plan['plan_id']}/generate")
    job = client.get(f"/api/v1/plans/{plan['plan_id']}/status").json()["jobs"][0]
    assert job["status"] == "completed"
    assert job["estimate"]["measured"] is True
    assert job["estimate"]["saving_percent"] > 0
    m = client.get(f"/api/v1/plans/{plan['plan_id']}/metrics").json()
    assert m["saving_percent"] > 0 and m["tier_counts"] == {"draft": 1}

"""Sessions, preferences, saved images and global numbers used by the web app."""



def _make(c, prompt, material="flashcards", count=2):
    plan = c.post("/api/v1/plans", json={"material_type": material, "prompt": prompt, "overrides": {"count": count}}).json()
    c.post(f"/api/v1/plans/{plan['plan_id']}/generate")
    return c.get(f"/api/v1/plans/{plan['plan_id']}/status").json()


def test_sessions_roundtrip(client):
    c = client
    c.delete("/api/v1/sessions")
    assert c.get("/api/v1/sessions").json() == []
    c.put("/api/v1/sessions/s1", json={"id": "s1", "title": "A", "timestamp": "2026-01-01T00:00:00", "images": []})
    c.put("/api/v1/sessions/s2", json={"id": "s2", "title": "B", "timestamp": "2026-02-01T00:00:00", "images": []})
    assert [s["id"] for s in c.get("/api/v1/sessions").json()] == ["s2", "s1"]
    assert c.patch("/api/v1/sessions/s1", json={"title": "Z"}).json()["title"] == "Z"
    assert c.patch("/api/v1/sessions/nope", json={"title": "Z"}).status_code == 404
    c.delete("/api/v1/sessions/s2")
    assert [s["id"] for s in c.get("/api/v1/sessions").json()] == ["s1"]
    c.delete("/api/v1/sessions")
    assert c.get("/api/v1/sessions").json() == []


def test_preferences_merge(client):
    c = client
    base = c.get("/api/v1/preferences").json()
    assert base["theme"] == "System"
    out = c.put("/api/v1/preferences", json={"theme": "Dark"}).json()
    assert out["theme"] == "Dark" and out["density"] == base["density"]
    assert c.get("/api/v1/preferences").json()["theme"] == "Dark"


def test_saved_images_and_global_metrics(client):
    c = client
    c.delete("/api/v1/saved-images")
    assert c.get("/api/v1/metrics/global").json()["totalRequested"] == 0
    _make(c, "animals cat and dog", "flashcards", 2)
    saved = c.get("/api/v1/saved-images").json()
    assert len(saved) == 2 and saved[0]["category"] == "Flashcards"
    assert c.get(saved[0]["url"]).status_code == 200
    g = c.get("/api/v1/metrics/global").json()
    assert g["totalRequested"] == 2 and g["totalGenerated"] + g["totalReused"] == 2
    c.delete(f"/api/v1/saved-images/{saved[0]['id']}")
    assert len(c.get("/api/v1/saved-images").json()) == 1
    c.delete("/api/v1/saved-images")
    assert c.get("/api/v1/saved-images").json() == []


def test_search_saved_images_and_upgrade(client):
    c = client
    c.delete("/api/v1/saved-images")
    plan = c.post("/api/v1/plans", json={"material_type": "flashcards", "prompt": "animals cat and dog", "overrides": {"count": 2, "tier": "draft"}}).json()
    c.post(f"/api/v1/plans/{plan['plan_id']}/generate")
    assert len(c.get("/api/v1/saved-images", params={"q": "cat"}).json()) == 2
    assert c.get("/api/v1/saved-images", params={"q": "zebra"}).json() == []
    job = c.get(f"/api/v1/plans/{plan['plan_id']}/status").json()["jobs"][0]
    assert c.post(f"/api/v1/jobs/{job['job_id']}/upgrade", json={"tier": "draft"}).status_code == 409
    assert c.post(f"/api/v1/jobs/{job['job_id']}/upgrade", json={"tier": "ultra"}).status_code == 400
    assert c.post(f"/api/v1/jobs/{job['job_id']}/upgrade", json={"tier": "high"}).status_code == 202
    after = c.get(f"/api/v1/jobs/{job['job_id']}").json()
    assert after["tier"] == "high" and after["steps"] == 8 and after["status"] == "completed"


def test_upgrade_still_works_after_restart(client):
    from app.store import store
    c = client
    plan = c.post("/api/v1/plans", json={"material_type": "flashcards", "prompt": "animals cat", "overrides": {"count": 1, "tier": "draft"}}).json()
    c.post(f"/api/v1/plans/{plan['plan_id']}/generate")
    job_id = plan["jobs"][0]["job_id"]
    store.clear()   # same as restarting the backend: memory is empty, the database still has the plan
    assert c.get(f"/api/v1/plans/{plan['plan_id']}/status").json()["completed"] == 1
    store.clear()
    assert c.post(f"/api/v1/jobs/{job_id}/upgrade", json={"tier": "high"}).status_code == 202
    assert c.get(f"/api/v1/jobs/{job_id}").json()["tier"] == "high"


def test_old_plan_rebuilt_from_history(client):
    from app.pipeline import app_state
    from app.store import store
    c = client
    plan = c.post("/api/v1/plans", json={"material_type": "flashcards", "prompt": "animals cat", "overrides": {"count": 2, "tier": "draft"}}).json()
    c.post(f"/api/v1/plans/{plan['plan_id']}/generate")
    app_state.delete("plans", plan["plan_id"])      # a plan made before plans were saved
    store.clear()
    status = c.get(f"/api/v1/plans/{plan['plan_id']}/status").json()
    assert status["total"] == 2 and status["completed"] == 2
    job_id = plan["jobs"][0]["job_id"]
    store.clear()
    assert c.post(f"/api/v1/jobs/{job_id}/upgrade", json={"tier": "high"}).status_code == 202

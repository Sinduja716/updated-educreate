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

"""End-to-end check with the mock provider. Every track must keep this passing."""


def test_full_flow(client):
    r = client.post("/api/v1/plans", json={"material_type": "flashcards", "prompt": "farm animals"})
    assert r.status_code == 200
    plan = r.json()
    assert len(plan["jobs"]) >= 1
    assert [j["sequence"] for j in plan["jobs"]] == list(range(1, len(plan["jobs"]) + 1))

    assert client.post(f"/api/v1/plans/{plan['plan_id']}/generate").status_code == 202
    st = client.get(f"/api/v1/plans/{plan['plan_id']}/status").json()
    assert st["complete"] is True
    assert st["completed"] == st["total"]

    ex = client.post(f"/api/v1/plans/{plan['plan_id']}/export")
    assert ex.status_code == 200
    pdf = client.get(ex.json()["download_url"])
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")

    m = client.get(f"/api/v1/plans/{plan['plan_id']}/metrics")
    assert m.status_code == 200
    assert m.json()["saving_percent"] is not None


def test_export_blocked_until_complete(client):
    plan = client.post("/api/v1/plans", json={"material_type": "poster", "prompt": "water cycle"}).json()
    assert client.post(f"/api/v1/plans/{plan['plan_id']}/export").status_code == 409


def test_unknown_plan_404(client):
    assert client.get("/api/v1/plans/nope/status").status_code == 404

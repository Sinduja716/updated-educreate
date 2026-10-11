def test_method_endpoint_explains_the_estimate(client):
    r = client.get("/api/v1/estimate/method")
    assert r.status_code == 200
    m = r.json()
    assert m["formulas"] and m["caveats"] and m["unit"]
    assert [t["steps"] for t in m["tiers"]] == [2, 4, 8]
    assert m["maximum_setting"]["steps"] == 8


def test_every_job_and_plan_carries_cost_time_and_saving(client):
    plan = client.post("/api/v1/plans", json={"material_type": "colouring", "prompt": "farm animals"}).json()
    e = plan["estimate"]
    for key in ("neurons", "cost_usd", "seconds", "saving_percent", "time_saving_percent", "method"):
        assert e[key] is not None
    client.post(f"/api/v1/plans/{plan['plan_id']}/generate")
    st = client.get(f"/api/v1/plans/{plan['plan_id']}/status").json()
    assert all(j["estimate"]["seconds"] is not None and j["estimate"]["saving_percent"] is not None for j in st["jobs"])

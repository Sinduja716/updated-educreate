"""Smoke test of everything merged: planner (gg), pipeline + estimate (Sinduja), API contract the UI (Mona) uses.
Free: uses the mock image provider. Run from the repo root:  python smoke_test.py
"""
import sys
import time

sys.path.insert(0, "backend")
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402

settings.image_provider = "mock"
from app.main import app  # noqa: E402

c = TestClient(app)
fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(name)


r = c.get("/api/v1/health")
check("health", r.status_code == 200)

# 1. Planner (gg)
cases = [("colouring", "farm animals A to Z", 26, "draft"),
         ("flashcards", "numbers 1 to 5", None, "standard"),
         ("poster", "a farm scene with animals", None, "high")]
for mtype, prompt, pages, tier in cases:
    r = c.post("/api/v1/plans", json={"material_type": mtype, "prompt": prompt})
    p = r.json() if r.status_code == 200 else {}
    keys = [j["item_key"] for j in p.get("jobs", [])][:3]
    check(f"planner {mtype}: '{prompt}'",
          r.status_code == 200 and p.get("tier") == tier and (pages is None or len(p["jobs"]) == pages),
          f"tier={p.get('tier')} pages={len(p.get('jobs', []))} keys={keys}")

# 2. Estimate on the plan (Sinduja) - cost, saving, time, method
r = c.post("/api/v1/plans", json={"material_type": "colouring", "prompt": "farm animals A to Z"})
plan = r.json()
e = plan["estimate"]
check("estimate has neurons+cost+saving", all(k in e for k in ("neurons", "cost_usd", "saving_percent")),
      f"{e['neurons']} neurons, ${e['cost_usd']}, saved {e['saving_percent']}%")
check("estimate has time fields", all(k in e for k in ("seconds", "max_seconds", "time_saving_percent", "method")))
check("draft costs less than max", e["neurons"] < e["max_neurons"])

m = c.get("/api/v1/estimate/method")
check("method endpoint (How is this calculated?)", m.status_code == 200 and "formulas" in m.json(),
      str(list(m.json().keys())) if m.status_code == 200 else str(m.status_code))

# 3. Generate (mock), poll until done (Sinduja pipeline)
plan["jobs"] = plan["jobs"]
pid = plan["plan_id"]
g = c.post(f"/api/v1/plans/{pid}/generate")
check("generate accepted", g.status_code in (200, 202), str(g.status_code))
t0 = time.time()
jobs = []
while time.time() - t0 < 60:
    jobs = c.get(f"/api/v1/plans/{pid}").json()["jobs"]
    if all(j["status"] in ("completed", "failed") for j in jobs):
        break
    time.sleep(0.5)
done = [j for j in jobs if j["status"] == "completed"]
check("all pages completed", len(done) == len(jobs) and len(jobs) == 26, f"{len(done)}/{len(jobs)}")
check("every completed job has an estimate", all(j.get("estimate") for j in done))
a = c.get(f"/api/v1/jobs/{done[0]['job_id']}/asset") if done else None
check("asset downloadable", a is not None and a.status_code == 200 and len(a.content) > 100)

# 4. Metrics: totals + saving split (gg) + time (contract)
mt = c.get(f"/api/v1/plans/{pid}/metrics").json()
check("metrics totals", mt.get("neurons_used") is not None and mt.get("baseline_neurons"),
      f"used={mt.get('neurons_used')} baseline={mt.get('baseline_neurons')} saved={mt.get('saving_percent')}%")
check("metrics has saving split note", any("lower tiers" in n for n in mt.get("notes", [])))
check("metrics has time saving", mt.get("time_saving_percent") is not None, str(mt.get("time_saving_percent")))

print()
print("ALL GOOD" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)

"""App entry. OWNER: integrator. Each track only edits its own router/module, never this file."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_config, routes_estimate, routes_history, routes_jobs, routes_metrics, routes_plans, routes_upload

app = FastAPI(title="EduCreate AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(routes_plans.router)
app.include_router(routes_jobs.router)
app.include_router(routes_metrics.router)
app.include_router(routes_estimate.router)
app.include_router(routes_config.router)
app.include_router(routes_history.router)
app.include_router(routes_upload.router)

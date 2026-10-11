"""FROZEN DATA CONTRACT. OWNER: integrator only.

Every track imports these models. Changing a field here breaks the other two tracks, so
nobody except the integrator edits this file. tests/test_contract_snapshot.py fails if it changes.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class MaterialType(str, Enum):
    """The PURPOSE of the image. `auto` means the system decides; a Plan never keeps `auto`."""

    colouring = "colouring"
    worksheet = "worksheet"
    flashcards = "flashcards"
    poster = "poster"
    thumbnail = "thumbnail"
    auto = "auto"


Tier = Literal["draft", "standard", "high"]


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


PageFormat = Literal["A4_PORTRAIT", "A3_PORTRAIT", "CARD_3X5", "SQUARE_SMALL"]


class Overrides(BaseModel):
    """Values the teacher edited on the summary card."""

    count: int | None = Field(default=None, ge=1, le=30)
    age_band: str | None = None
    language: str | None = None
    tier: Tier | None = None  # manual quality tier; None = let the system choose
    colour_mode: Literal["outline", "colour"] | None = None  # black-and-white outline or colour; None = let the system choose


class GenerationRequest(BaseModel):
    material_type: MaterialType
    prompt: str = Field(min_length=1, max_length=500)
    overrides: Overrides | None = None


class ResolvedField(BaseModel):
    """One value on the summary card and where it came from."""

    value: str | int
    source: Literal["user", "planner", "default"]


class ResourceEstimate(BaseModel):
    """Compute estimate for ONE image, next to what maximum quality would have cost.
    Built only by app/estimate.py so every track shows identical numbers."""

    tier: Tier
    steps: int
    neurons: float
    cost_usd: float
    energy_wh: float | None = None  # only when an energy assumption is configured
    max_steps: int
    max_neurons: float
    max_cost_usd: float
    max_energy_wh: float | None = None
    saving_percent: float  # compute saved versus maximum quality, 0-100
    measured: bool  # True when `neurons` came from a real provider reading
    placeholder: bool  # True while the neuron table is not yet measured
    # Second cost measure (constraint: show compute time, energy or an equivalent, plus the saving vs maximum).
    seconds: float | None = None  # estimated generation time for this image (measured table or actual reading)
    max_seconds: float | None = None
    time_saving_percent: float | None = None  # time saved versus maximum quality, 0-100
    method: str = ""  # one-line "how this was calculated"; full text at GET /api/v1/estimate/method
    notes: list[str] = Field(default_factory=list)


class Job(BaseModel):
    job_id: str
    plan_id: str
    sequence: int
    item_key: str
    prompt: str
    status: JobStatus = JobStatus.pending
    attempts: int = 0
    steps: int = 4
    tier: Tier = "standard"
    estimate: ResourceEstimate | None = None
    asset_uri: str | None = None
    error_code: str | None = None
    cache_hit: bool = False
    provider: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    neurons: float | None = None


class Plan(BaseModel):
    plan_id: str
    material_type: MaterialType
    original_prompt: str
    page_format: PageFormat
    profile: str
    steps: int
    tier: Tier
    tier_reason: str
    estimate: ResourceEstimate
    resolved: dict[str, ResolvedField]
    warnings: list[str] = Field(default_factory=list)
    jobs: list[Job]


class StatusResponse(BaseModel):
    plan_id: str
    total: int
    completed: int
    failed: int
    pending: int
    processing: int
    complete: bool
    jobs: list[Job]


class GenerateResponse(BaseModel):
    plan_id: str
    accepted: bool


class ExportResponse(BaseModel):
    plan_id: str
    download_url: str


class MetricsResponse(BaseModel):
    plan_id: str
    image_calls: int
    cache_hits: int
    neurons_used: float | None = None
    estimated_cost_usd: float | None = None
    baseline_neurons: float | None = None
    baseline_cost_usd: float | None = None
    saving_percent: float | None = None
    seconds_used: float | None = None
    baseline_seconds: float | None = None
    time_saving_percent: float | None = None
    energy_wh_used: float | None = None
    baseline_energy_wh: float | None = None
    energy_saved_wh: float | None = None
    tier_counts: dict[str, int] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    code: str
    message: str


class ConfigResponse(BaseModel):
    """What the app is running with. The UI shows a banner when something is missing or simulated."""

    image_provider: str
    provider_configured: bool
    demo_mode: bool  # true when the mock provider is on: pictures and numbers are not real
    database_connected: bool
    online_search: bool
    planner: str


class HistoryItem(BaseModel):
    """One finished image the user received (generated, reused, uploaded or found online)."""

    creation_id: str
    plan_id: str | None = None
    job_id: str | None = None
    material_type: str
    prompt: str
    item_key: str
    colour_mode: str | None = None
    age_band: str | None = None
    tier: str | None = None
    neurons: float | None = None
    seconds: float | None = None
    cost_usd: float | None = None
    provider: str | None = None  # cloudflare_flux, mock, library, upload, online
    cache_hit: bool = False
    created_at: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem] = Field(default_factory=list)


class UploadOutlineRequest(BaseModel):
    filename: str
    image_base64: str
    mode: Literal["outline", "grayscale"] = "outline"
    threshold: int | None = Field(default=None, ge=0, le=255)


class UploadOutlineResponse(BaseModel):
    creation_id: str
    material_type: str = "colouring"
    provider: str = "upload"
    neurons: float = 0.0
    seconds: float | None = None
    cost_usd: float = 0.0
    asset_uri: str


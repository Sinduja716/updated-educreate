// Real API layer. Every call goes to the FastAPI backend through the Vite proxy (/api -> 127.0.0.1:8000).
// Nothing in this file is mocked or hard coded: pictures, numbers and history all come from the backend.
import type {
  AgeGroup, ColourMode, CreationSession, GlobalMetrics, ImageResult, OutputCategory,
  SessionMetrics, Tier, UserPreferences,
} from '../types';

const API = '/api/v1';

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { const j = await res.json(); detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j); } catch { /* keep statusText */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------- mappings between the screen's words and the backend's words ----------
const MATERIAL_OF: Record<OutputCategory, string> = {
  Images: 'thumbnail', Flashcards: 'flashcards', Worksheets: 'worksheet', Posters: 'poster',
};
const AUTO = 'auto'; // no category chosen: the planner works it out from the words
const CATEGORY_OF: Record<string, OutputCategory> = {
  colouring: 'Images', thumbnail: 'Images', flashcards: 'Flashcards', worksheet: 'Worksheets', poster: 'Posters',
};
const BACKEND_AGE: Record<AgeGroup, string> = { '3-5': '3-5', '6-8': '6-8', '9-11': '9-12', '12-14': '9-12', '15-18': 'adult' };
const UI_AGE: Record<string, AgeGroup> = { '3-5': '3-5', '6-8': '6-8', '9-12': '9-11', adult: '15-18' };

export const categoryOf = (material: string): OutputCategory => CATEGORY_OF[material] ?? 'Images';

// ---------- plan (the proposal shown before generating) ----------
export interface PlanOptions {
  category?: OutputCategory;
  material?: string; // exact material found by the planner, used when no category was chosen
  ageGroup?: AgeGroup;
  quantity?: number;
  tier?: Tier;
  colourMode?: ColourMode;
}

export interface Field { value: string | number; source: 'user' | 'planner' | 'default' }
export interface PlanView {
  planId: string;
  tier: Tier;
  steps: number;
  tierReason: string;
  resolved: Record<string, Field>;
  warnings: string[];
  estimate: {
    neurons: number; costUsd: number; seconds: number | null;
    maxNeurons: number; maxCostUsd: number; maxSeconds: number | null;
    savingPercent: number | null; placeholder: boolean; notes: string[];
  };
  perImageNeurons: number;
  count: number;
  totalNeurons: number;
  totalCostUsd: number;
  maxTotalNeurons: number;
  ageGroup?: AgeGroup;
  colourMode: ColourMode;
  material: string;
  category: OutputCategory;
  tierSource: string;
  reusable: number;
}

function toPlanView(p: any): PlanView {
  const e = p.estimate;
  const count = Number(p.resolved?.count?.value ?? p.jobs.length);
  const age = p.resolved?.age_band?.value as string | undefined;
  return {
    planId: p.plan_id,
    tier: p.tier,
    steps: p.steps,
    tierReason: p.tier_reason,
    resolved: p.resolved,
    warnings: p.warnings ?? [],
    estimate: {
      neurons: e.neurons, costUsd: e.cost_usd, seconds: e.seconds ?? null,
      maxNeurons: e.max_neurons, maxCostUsd: e.max_cost_usd, maxSeconds: e.max_seconds ?? null,
      savingPercent: e.saving_percent ?? null, placeholder: !!e.placeholder, notes: e.notes ?? [],
    },
    perImageNeurons: e.neurons,
    count,
    totalNeurons: round(e.neurons * count, 3),
    totalCostUsd: round(e.cost_usd * count, 6),
    maxTotalNeurons: round(e.max_neurons * count, 3),
    ageGroup: age ? UI_AGE[age] : undefined,
    colourMode: (p.resolved?.colour_mode?.value ?? 'colour') as ColourMode,
    material: p.material_type,
    category: categoryOf(p.material_type),
    tierSource: p.resolved?.tier?.source ?? 'planner',
    reusable: 0,
  };
}

const round = (n: number, d: number) => Math.round(n * 10 ** d) / 10 ** d;

function overridesOf(o: PlanOptions) {
  const ov: Record<string, unknown> = {};
  if (o.quantity) ov.count = o.quantity;
  if (o.ageGroup) ov.age_band = BACKEND_AGE[o.ageGroup];
  if (o.tier) ov.tier = o.tier;
  if (o.colourMode) ov.colour_mode = o.colourMode;
  return ov;
}

// ---------- number formatting for the screens ----------
export const fmtNeurons = (n: number) => `${round(n, 1)} neurons`;
export const fmtUsd = (n: number) => `$${n < 0.01 ? n.toFixed(4) : n.toFixed(2)}`;

// ---------- status mapping ----------
function toImage(job: any): ImageResult {
  const base = { id: job.job_id, isRetrieved: !!job.cache_hit, tier: job.tier as Tier, neurons: job.cache_hit ? 0 : (job.neurons ?? undefined) };
  if (job.status === 'completed') return { ...base, status: 'Completed', url: `${API}/history/${job.job_id}/asset` };
  if (job.status === 'failed') {
    const why: Record<string, string> = {
      budget: 'The free daily compute budget is used up.', filtered: 'The safety filter rejected this picture.',
      timeout: 'The image service timed out.', server_error: 'The image service had an error.',
      bad_image: 'The image could not be read.',
    };
    return { ...base, status: 'Failed', errorMessage: why[job.error_code] ?? 'Failed to generate image. Please try again.' };
  }
  if (job.status === 'processing') return { ...base, status: 'Generating' };
  return { ...base, status: 'Ready' };
}

async function metricsOf(planId: string, tier: Tier): Promise<SessionMetrics> {
  const m = await call<any>(`/plans/${planId}/metrics`);
  const total = m.image_calls + m.cache_hits;
  const savedNeurons = Math.max(0, (m.baseline_neurons ?? 0) - (m.neurons_used ?? 0));
  const savedUsd = Math.max(0, (m.baseline_cost_usd ?? 0) - (m.estimated_cost_usd ?? 0));
  return {
    requested: total,
    reused: m.cache_hits,
    generated: m.image_calls,
    resourceUsage: fmtNeurons(m.neurons_used ?? 0),
    estimatedCost: fmtUsd(m.estimated_cost_usd ?? 0),
    savings: `${fmtNeurons(savedNeurons)} (${fmtUsd(savedUsd)})`,
    neuronsUsed: m.neurons_used ?? 0,
    baselineNeurons: m.baseline_neurons ?? 0,
    savingPercent: m.saving_percent ?? null,
    secondsUsed: m.seconds_used ?? null,
    timeSavingPercent: m.time_saving_percent ?? null,
    tier,
  };
}

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

async function pollUntilDone(planId: string, onProgress: (images: ImageResult[]) => void): Promise<ImageResult[]> {
  for (;;) {
    const s = await call<any>(`/plans/${planId}/status`);
    const images = s.jobs.map(toImage);
    onProgress(images);
    if (s.pending === 0 && s.processing === 0) return images;
    await sleep(700);
  }
}

export const apiService = {
  // ----- planning -----
  // 'Images' sends no fixed material: the words decide (colouring book, plain picture, ...).
  async plan(prompt: string, o: PlanOptions): Promise<PlanView> {
    const p = await call<any>('/plans', {
      method: 'POST',
      body: JSON.stringify({ material_type: o.material ?? (o.category && o.category !== 'Images' ? MATERIAL_OF[o.category] : AUTO), prompt, overrides: overridesOf(o) }),
    });
    const view = toPlanView(p);
    // How many pictures are already in the library? They cost 0 neurons.
    try {
      const r = await call<{ reusable: number }>(`/plans/${view.planId}/reuse`);
      view.reusable = r.reusable;
      const paid = Math.max(0, view.count - r.reusable);
      view.totalNeurons = round(view.perImageNeurons * paid, 3);
      view.totalCostUsd = round(p.estimate.cost_usd * paid, 6);
    } catch { /* the preview still works without it */ }
    return view;
  },

  async config() {
    return call<{ image_provider: string; demo_mode: boolean; database_connected: boolean; planner: string; provider_configured: boolean }>('/config');
  },

  async estimateMethod() {
    return call<Record<string, unknown>>('/estimate/method');
  },

  // ----- generating -----
  /** Creates the plan, runs it on the backend and reports every status change. Retries failed pictures of an existing plan. */
  async processImages(session: CreationSession, onProgress: (images: ImageResult[]) => void, onPlan?: (p: { planId: string; tier: Tier; colourMode: ColourMode; category: OutputCategory; ageGroup?: AgeGroup; quantity: number; material: string }) => void): Promise<{ metrics: SessionMetrics; planId: string; tier: Tier; colourMode: ColourMode }> {
    let planId = session.planId;
    let tier = session.tier;
    let colourMode = session.colourMode;
    if (planId && session.images.some(i => i.status === 'Failed')) {
      for (const img of session.images.filter(i => i.status === 'Failed')) {
        await call(`/jobs/${img.id}/retry`, { method: 'POST' }).catch(() => undefined);
      }
    } else {
      const plan = await this.plan(session.prompt, {
        category: session.category, material: session.material, ageGroup: session.ageGroup, quantity: session.quantity,
        tier: session.tier, colourMode: session.colourMode,
      });
      planId = plan.planId; tier = plan.tier; colourMode = plan.colourMode;
      onPlan?.({ planId, tier: plan.tier, colourMode: plan.colourMode, category: plan.category, ageGroup: plan.ageGroup, quantity: plan.count, material: plan.material });
      onProgress(Array.from({ length: plan.count }, (_, i) => ({ id: `${planId}-${i}`, status: 'Ready' as const, isRetrieved: false })));
      await call(`/plans/${planId}/generate`, { method: 'POST' });
    }
    await pollUntilDone(planId!, onProgress);
    return { metrics: await metricsOf(planId!, tier ?? 'standard'), planId: planId!, tier: tier ?? 'standard', colourMode: colourMode ?? 'colour' };
  },

  // ----- files -----
  async exportPdf(planId: string): Promise<string> {
    const r = await call<{ download_url: string }>(`/plans/${planId}/export`, { method: 'POST' });
    return r.download_url;
  },
  imagesZipUrl: (planId: string) => `${API}/plans/${planId}/images.zip`,

  // ----- sessions -----
  getSessions: () => call<CreationSession[]>('/sessions'),
  saveSession: (s: CreationSession) => call<CreationSession>(`/sessions/${s.id}`, { method: 'PUT', body: JSON.stringify(s) }).then(() => undefined),
  deleteSession: (id: string) => call<void>(`/sessions/${id}`, { method: 'DELETE' }),
  renameSession: (id: string, title: string) => call<CreationSession>(`/sessions/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) }).then(() => undefined),
  clearAllSessions: () => call<void>('/sessions', { method: 'DELETE' }),

  // ----- preferences -----
  getPreferences: () => call<UserPreferences>('/preferences'),
  savePreferences: (p: Partial<UserPreferences>) => call<UserPreferences>('/preferences', { method: 'PUT', body: JSON.stringify(p) }).then(() => undefined),

  // ----- saved images and numbers -----
  getSavedImages: (q?: string) => call<{ id: string; url: string; title: string; category: string; date: string }[]>('/saved-images' + (q && q.trim() ? `?q=${encodeURIComponent(q.trim())}` : '')),

  // ----- upgrade on demand: make one finished picture again at a higher quality -----
  async upgradeImage(session: CreationSession, imageId: string, tier: Tier, onProgress: (images: ImageResult[]) => void): Promise<SessionMetrics> {
    await call(`/jobs/${imageId}/upgrade`, { method: 'POST', body: JSON.stringify({ tier }) });
    await sleep(500);
    const images = await pollUntilDone(session.planId!, onProgress);
    const bust = Date.now();
    onProgress(images.map(i => (i.url ? { ...i, url: `${i.url}?v=${bust}` } : i)));
    return metricsOf(session.planId!, session.tier ?? 'standard');
  },
  clearSavedImages: () => call<void>('/saved-images', { method: 'DELETE' }),

  async getGlobalMetrics(): Promise<GlobalMetrics> {
    const g = await call<any>('/metrics/global');
    return {
      totalRequested: g.totalRequested,
      totalGenerated: g.totalGenerated,
      totalReused: g.totalReused,
      totalResourceUsage: fmtNeurons(g.neuronsUsed),
      totalCost: fmtUsd(g.costUsd),
      totalResourceSaved: fmtNeurons(g.neuronsSaved),
      totalCostSaved: fmtUsd(g.costSavedUsd),
      savingsPercentage: `${g.savingsPercent}%`,
    };
  },
};

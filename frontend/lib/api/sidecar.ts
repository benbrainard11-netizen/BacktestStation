/**
 * Typed client for the research_sidecar HTTP API.
 *
 * Browser requests go through the Next rewrite at `/api/sidecar/*` —
 * configured in `next.config.mjs`. Server-side calls hit the same path
 * because the rewrite is honored by the framework.
 *
 * Schemas mirror `research_sidecar/app/http_api/schemas.py`. Keep these
 * in sync manually until/unless the sidecar's OpenAPI gets stitched
 * into the BacktestStation `openapi-typescript` build.
 */

const SIDECAR_BASE = "/api/sidecar";

// ---------------------------------------------------------------------------
// Types — mirror Pydantic schemas one-to-one.
// ---------------------------------------------------------------------------

export interface IdeaSource {
  source_name: string | null;
  source_type: string | null;
  url: string | null;
  title: string | null;
  published_at: string | null;
}

export interface BacktestResultRecord {
  run_id: number;
  profit_factor: number | null;
  expectancy_r: number | null;
  trade_count: number | null;
  win_rate: number | null;
  run_at: string;
  note: string | null;
}

export interface IdeaRead {
  id: number;
  raw_document_id: number;

  title: string | null;
  summary: string | null;
  archetype: string | null;
  asset_class: string | null;
  timeframe: string | null;
  entry_concept: string | null;
  exit_concept: string | null;
  stop_concept: string | null;
  filters: string[];
  indicators: string[];
  required_data: string[];
  notes: string | null;

  final_score: number;
  recommendation_label: string;
  extracted_confidence: number;
  clarity_score: number;
  testability_score: number;
  relevance_score: number;
  novelty_score: number;

  source: IdeaSource | null;
  backtest_results: BacktestResultRecord[];
  skipped_at: string | null;
  created_at: string;
}

export interface IdeaListResponse {
  ideas: IdeaRead[];
  count: number;
}

export interface BacktestResultPayload {
  run_id: number;
  profit_factor?: number | null;
  expectancy_r?: number | null;
  trade_count?: number | null;
  win_rate?: number | null;
  run_at?: string | null;
  note?: string | null;
}

export interface SkipPayload {
  reason?: string | null;
}

export interface SidecarHealth {
  status: "ok" | "degraded";
  service_name: string;
  db_reachable: boolean;
  promising_idea_count: number | null;
  review_idea_count: number | null;
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export class SidecarError extends Error {
  readonly status: number;
  readonly detail: string | null;
  constructor(status: number, detail: string | null) {
    super(detail ?? `Sidecar request failed: ${status}`);
    this.name = "SidecarError";
    this.status = status;
    this.detail = detail;
  }
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${SIDECAR_BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
    },
  });
  if (!r.ok) {
    let detail: string | null = null;
    try {
      const body = (await r.json()) as { detail?: string };
      detail = body.detail ?? null;
    } catch {
      /* ignore */
    }
    throw new SidecarError(r.status, detail);
  }
  return (await r.json()) as T;
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

export interface ListIdeasOptions {
  /** Comma-separated label filter, e.g. "promising,review". Empty = all. */
  label?: string;
  /** Minimum final_score, 0..1. */
  minScore?: number;
  /** Cap on result count. Defaults server-side to 50, max 500. */
  limit?: number;
  signal?: AbortSignal;
}

export function listIdeas(opts: ListIdeasOptions = {}): Promise<IdeaListResponse> {
  const params = new URLSearchParams();
  if (opts.label) params.set("label", opts.label);
  if (opts.minScore != null) params.set("min_score", String(opts.minScore));
  if (opts.limit != null) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return getJson<IdeaListResponse>(`/ideas${qs ? `?${qs}` : ""}`, {
    signal: opts.signal,
  });
}

export function getIdea(ideaId: number, signal?: AbortSignal): Promise<IdeaRead> {
  return getJson<IdeaRead>(`/ideas/${ideaId}`, { signal });
}

export function postBacktestResult(
  ideaId: number,
  payload: BacktestResultPayload,
): Promise<IdeaRead> {
  return getJson<IdeaRead>(`/ideas/${ideaId}/result`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function skipIdea(
  ideaId: number,
  payload: SkipPayload = {},
): Promise<IdeaRead> {
  return getJson<IdeaRead>(`/ideas/${ideaId}/skip`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSidecarHealth(signal?: AbortSignal): Promise<SidecarHealth> {
  return getJson<SidecarHealth>("/health", { signal });
}

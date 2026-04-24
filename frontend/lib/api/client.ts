/**
 * Server-side fetch helper.
 *
 * The Next rewrite in `next.config.mjs` proxies `/api/*` for browser requests,
 * but server components run in Node and need an absolute URL. This helper
 * resolves a relative backend path against the configured base URL and throws
 * on non-2xx responses so `error.tsx` can handle them.
 */
const DEFAULT_BACKEND_URL = "http://localhost:8000";

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL?.trim() || DEFAULT_BACKEND_URL;
}

/**
 * Shape of the FastAPI error body when `HTTPException(status_code=..., detail="...")`
 * is raised. FastAPI doesn't model this in OpenAPI (the schema only describes
 * successful responses + its own `HTTPValidationError` for 422 Pydantic errors),
 * so it stays hand-declared here alongside `ApiError` which consumes it.
 */
export interface BackendErrorBody {
  detail?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | null;

  constructor(status: number, detail: string | null, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const url = `${apiBaseUrl()}${path}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    const detail = await extractDetail(response);
    throw new ApiError(
      response.status,
      detail,
      detail ?? `${response.status} ${response.statusText || "Request failed"}`,
    );
  }
  return (await response.json()) as T;
}

async function extractDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" && body.detail.length > 0
      ? body.detail
      : null;
  } catch {
    return null;
  }
}

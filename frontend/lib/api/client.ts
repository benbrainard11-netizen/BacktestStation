export type JsonObject = Record<string, unknown>;

export type ProbeResult = {
  ok: boolean;
  status: number;
  data: unknown;
  error: string | null;
  fetchedAt: number;
};

export async function fetchJson(path: string): Promise<ProbeResult> {
  try {
    const response = await fetch(path, { cache: "no-store" });
    const text = await response.text();
    let data: unknown = null;
    if (text) {
      try {
        data = JSON.parse(text) as unknown;
      } catch {
        data = text;
      }
    }
    return {
      ok: response.ok,
      status: response.status,
      data,
      error: response.ok ? null : extractError(data) ?? response.statusText,
      fetchedAt: Date.now(),
    };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: err instanceof Error ? err.message : "Network error",
      fetchedAt: Date.now(),
    };
  }
}

export function asObject(value: unknown): JsonObject {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonObject)
    : {};
}

export function readPath(value: unknown, path: string): unknown {
  let current: unknown = value;
  for (const part of path.split(".")) {
    if (!current || typeof current !== "object" || Array.isArray(current)) {
      return undefined;
    }
    current = (current as JsonObject)[part];
  }
  return current;
}

export function asString(value: unknown, fallback = "-"): string {
  if (typeof value === "string" && value.length > 0) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value === "boolean") return value ? "yes" : "no";
  return fallback;
}

export function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function extractError(data: unknown): string | null {
  const obj = asObject(data);
  const detail = obj.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return "Validation error";
  const message = obj.message;
  return typeof message === "string" ? message : null;
}

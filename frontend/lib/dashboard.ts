"use client";

export type LoadState<T> =
  | { kind: "loading" }
  | { kind: "error"; message: string; data?: T }
  | { kind: "data"; data: T; fetchedAt: number; refreshing: boolean };

export type ChipTone = "default" | "accent" | "pos" | "neg" | "warn";
export type DotTone = "pos" | "neg" | "warn" | "info" | "muted";

export async function apiFetch<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText || "Request failed"}`);
  }
  return (await response.json()) as T;
}

export async function apiPost<T>(url: string): Promise<T> {
  const response = await fetch(url, { method: "POST", cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText || "Request failed"}`);
  }
  return (await response.json()) as T;
}

export function formatCount(value: number | null | undefined): string {
  if (value == null) return "-";
  return value.toLocaleString("en-US");
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.toISOString().slice(0, 10)} ${date.toISOString().slice(11, 16)}`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().slice(0, 10);
}

export function prettyLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value.replaceAll("_", " ");
}

export function shortHash(value: string | null | undefined, size = 10): string {
  if (!value) return "-";
  return value.length <= size ? value : value.slice(0, size);
}

export function jsonPreview(value: unknown): string {
  if (value == null) return "-";
  return JSON.stringify(value, null, 2);
}

export function statusTone(status: string): ChipTone {
  if (
    [
      "active",
      "completed",
      "paper_ready",
      "pass_paper",
      "micro_live",
      "scale_candidate",
      "validated",
    ].includes(status)
  ) {
    return "pos";
  }
  if (["running", "draft", "queued", "needs_more_validation"].includes(status)) {
    return "warn";
  }
  if (["failed", "killed", "rejected", "abandoned"].includes(status)) {
    return "neg";
  }
  if (["pre_validation", "pre_test", "final"].includes(status)) {
    return "accent";
  }
  return "default";
}

export function dotTone(status: string): DotTone {
  const tone = statusTone(status);
  if (tone === "pos") return "pos";
  if (tone === "neg") return "neg";
  if (tone === "warn") return "warn";
  if (tone === "accent") return "info";
  return "muted";
}

import type { FindingsFilters } from "./types";

export const REFRESH_MS = 5 * 60 * 1000;

export function formatBytes(bytes: number | null | undefined): string {
  const b = bytes ?? 0;
  if (b <= 0) return "-";
  if (b < 1e6) return `${(b / 1e3).toFixed(1)} KB`;
  if (b < 1e9) return `${(b / 1e6).toFixed(1)} MB`;
  return `${(b / 1e9).toFixed(2)} GB`;
}

export function formatCount(value: number | null | undefined): string {
  if (value == null) return "-";
  return value.toLocaleString();
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatDay(value: string | null | undefined): string {
  if (!value) return "-";
  return value.length >= 10 ? value.slice(0, 10) : value;
}

export function durationFromSeconds(seconds: number | null | undefined): string {
  if (seconds == null) return "-";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h`;
  return `${Math.round(hours / 24)}d`;
}

export function findingsUrl(filters: FindingsFilters): string {
  const params = new URLSearchParams();
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.schema) params.set("schema", filters.schema);
  if (filters.symbol) params.set("symbol", filters.symbol);
  if (filters.date) params.set("date", filters.date);
  const qs = params.toString();
  return `/api/dashboard/data-health/findings${qs ? `?${qs}` : ""}`;
}

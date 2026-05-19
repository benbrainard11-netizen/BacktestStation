"use client";

import { Card, Chip, StatusDot } from "@/components/atoms";
import { cn } from "@/lib/utils";
import { dotTone, prettyLabel, statusTone } from "@/lib/dashboard";

export function RefreshButton({
  state,
  onRefresh,
}: {
  state: "loading" | "error" | "data";
  onRefresh: () => void;
}) {
  return (
    <button
      type="button"
      onClick={() => void onRefresh()}
      disabled={state === "loading"}
      className={cn(
        "inline-flex items-center gap-2 rounded border border-line bg-bg-2",
        "px-3 py-1.5 font-mono text-[11px] text-ink-1 transition",
        "hover:border-line-2 hover:bg-bg-3 disabled:cursor-not-allowed",
        "disabled:opacity-50",
      )}
    >
      {state === "loading" ? (
        <span className="live-pulse inline-block h-2 w-2 rounded-full bg-accent" />
      ) : null}
      Refresh
    </button>
  );
}

export function StateCard({ text }: { text: string }) {
  return (
    <Card className="mt-6 px-4 py-6 text-[12px] text-ink-3">
      {text}
    </Card>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <StatusDot tone={dotTone(status)} />
      <Chip tone={statusTone(status)}>{prettyLabel(status)}</Chip>
    </span>
  );
}

export function EmptyCopy({
  text,
  compact = false,
}: {
  text: string;
  compact?: boolean;
}) {
  return (
    <div
      className={cn(
        "text-[12px] text-ink-3",
        compact ? "py-2" : "px-4 py-8",
      )}
    >
      {text}
    </div>
  );
}

export function JsonBlock({ value }: { value: string }) {
  return (
    <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap border-t border-line bg-bg-0 px-4 py-3 font-mono text-[11px] leading-5 text-ink-2">
      {value}
    </pre>
  );
}

export function KeyValue({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="border-b border-line px-4 py-3 last:border-0">
      <div className="table-head mb-1">{label}</div>
      <div className="text-[13px] text-ink-1">{value}</div>
    </div>
  );
}

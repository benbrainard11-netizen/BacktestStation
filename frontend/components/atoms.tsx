"use client";

import { cn } from "@/lib/utils";

/**
 * Base atoms — Card, Stat, Chip, Tag, StatusDot — kept tiny and dumb so every
 * page composes the same way. Use only the design tokens (CSS vars), no
 * inline hex.
 */

export function Card({
  className,
  ...rest
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...rest}
      className={cn(
        "border border-line bg-bg-1 rounded-lg",
        className,
      )}
    />
  );
}

export function CardHead({
  title,
  eyebrow,
  right,
  className,
}: {
  title: string;
  eyebrow?: string;
  right?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 border-b border-line px-4 py-3",
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow && <div className="card-eyebrow mb-0.5">{eyebrow}</div>}
        <div className="card-title truncate">{title}</div>
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}

export function Stat({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  tone?: "default" | "pos" | "neg" | "warn" | "accent";
}) {
  const valueColor =
    tone === "pos"
      ? "text-pos"
      : tone === "neg"
        ? "text-neg"
        : tone === "warn"
          ? "text-warn"
          : tone === "accent"
            ? "text-accent"
            : "text-ink-0";
  return (
    <div className="flex flex-col gap-1.5 px-4 py-3">
      <span className="stat-label">{label}</span>
      <span className={cn("stat-value font-mono", valueColor)}>{value}</span>
      {sub != null && <span className="text-[11px] text-ink-3">{sub}</span>}
    </div>
  );
}

export function Chip({
  children,
  tone = "default",
  className,
}: {
  children: React.ReactNode;
  tone?: "default" | "accent" | "pos" | "neg" | "warn";
  className?: string;
}) {
  const styles: Record<string, string> = {
    default: "bg-bg-2 border-line text-ink-2",
    accent: "bg-accent-soft text-accent border-accent-line",
    pos: "bg-pos-soft text-pos border-pos/30",
    neg: "bg-neg-soft text-neg border-neg/30",
    warn: "border-warn/30 text-warn bg-warn/10",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded border px-2 py-0.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.06em]",
        styles[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function StatusDot({
  tone = "pos",
  pulsing = false,
  size = 8,
}: {
  tone?: "pos" | "neg" | "warn" | "info" | "muted";
  pulsing?: boolean;
  size?: number;
}) {
  const color = {
    pos: "var(--pos)",
    neg: "var(--neg)",
    warn: "var(--warn)",
    info: "var(--info)",
    muted: "var(--ink-4)",
  }[tone];
  return (
    <span
      aria-hidden
      className={cn("inline-block rounded-full", pulsing && "live-pulse")}
      style={{
        width: size,
        height: size,
        background: color,
        boxShadow: tone === "muted" ? undefined : `0 0 6px ${color}`,
      }}
    />
  );
}

export function PageHeader({
  eyebrow,
  title,
  sub,
  right,
}: {
  eyebrow?: string;
  title: string;
  sub?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-6 px-6 pb-6 pt-8">
      <div className="min-w-0">
        {eyebrow && <div className="page-eyebrow">{eyebrow}</div>}
        <h1 className="page-title">{title}</h1>
        {sub && <p className="page-sub">{sub}</p>}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}

export function PageStub({
  title,
  blurb,
  eyebrow = "scaffolded",
}: {
  title: string;
  blurb: string;
  eyebrow?: string;
}) {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <PageHeader eyebrow={`${title.toUpperCase()} · ${eyebrow}`} title={title} sub={blurb} />
      <Card className="mt-6 px-6 py-12 text-center">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-4">
          empty state
        </div>
        <div className="mt-2 text-sm text-ink-2">
          This page is wired to the backend but has no UI yet.
        </div>
      </Card>
    </div>
  );
}

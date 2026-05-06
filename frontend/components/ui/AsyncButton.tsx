"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

type Phase =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "error"; message: string };

/**
 * AsyncButton — wraps the idle → running → error state machine.
 *
 * `onClick` returns a Promise. While in flight: button shows "..." and is
 * disabled. On rejection: an inline error message renders next to the
 * button (text-neg). Clicking the button again clears the error and retries.
 */
export function AsyncButton({
  onClick,
  children,
  className,
  variant = "primary",
  disabled = false,
  type = "button",
}: {
  onClick: () => Promise<void>;
  children: React.ReactNode;
  className?: string;
  variant?: "primary" | "ghost" | "danger";
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  async function handle() {
    if (phase.kind === "running" || disabled) return;
    setPhase({ kind: "running" });
    try {
      await onClick();
      setPhase({ kind: "idle" });
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Failed",
      });
    }
  }

  const variantClass = {
    primary: "border-accent bg-accent text-bg-0 hover:bg-accent/90",
    ghost: "border-line text-ink-1 hover:border-line-3 bg-bg-2",
    danger: "border-neg/40 text-neg hover:bg-neg/10",
  }[variant];

  return (
    <div className="flex items-center gap-2">
      <button
        type={type}
        onClick={handle}
        disabled={disabled || phase.kind === "running"}
        className={cn(
          "rounded border px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] transition-colors disabled:cursor-not-allowed disabled:opacity-50",
          variantClass,
          className,
        )}
      >
        {phase.kind === "running" ? "…" : children}
      </button>
      {phase.kind === "error" && (
        <span className="text-[11px] text-neg">{phase.message}</span>
      )}
    </div>
  );
}

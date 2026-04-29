"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import { cn } from "@/lib/utils";

interface ShipToLiveButtonProps {
  strategyId: number;
  status: string;
}

type Phase =
  | { kind: "idle" }
  | { kind: "confirming" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

/**
 * Status-flip primary action for the strategy detail header. v1 just
 * sets `Strategy.status`. Code-deployment to ben-247 stays a manual
 * step for now (Phase 2 will wire it up).
 *
 * - status !== "live" → button label "Ship to live", target = "live"
 * - status === "live" → button label "Mark retired", target = "retired"
 *
 * Archive flow remains separate (ArchiveStrategyButton next to this).
 */
export default function ShipToLiveButton({
  strategyId,
  status,
}: ShipToLiveButtonProps) {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  // Hide entirely when the strategy is archived; retired strategies are
  // still on the page but only the "back to idea" path makes sense and
  // that's handled by ArchiveStrategyButton.
  if (status === "archived") return null;

  const targetStatus = status === "live" ? "retired" : "live";
  const idleLabel = status === "live" ? "Mark retired" : "Ship to live";
  const confirmCopy =
    status === "live"
      ? "Retire this strategy? It will stop appearing in the live dashboard cards."
      : "Ship this strategy to live? Marks the strategy as live so the dashboard surfaces it. Code-deployment to ben-247 is still a manual step.";

  async function submit() {
    setPhase({ kind: "saving" });
    try {
      const response = await fetch(`/api/strategies/${strategyId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: targetStatus }),
      });
      if (!response.ok) {
        setPhase({ kind: "error", message: await describe(response) });
        return;
      }
      setPhase({ kind: "idle" });
      router.refresh();
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  if (phase.kind === "confirming") {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] text-text-dim">{confirmCopy}</span>
        <button
          type="button"
          onClick={submit}
          className={cn(
            "border px-2.5 py-1 tabular-nums text-[10px]",
            status === "live"
              ? "border-warn/30 bg-warn/10 text-warn hover:bg-warn/20"
              : "border-pos/30 bg-pos/10 text-pos hover:bg-pos/20",
          )}
        >
          {status === "live" ? "yes, retire" : "yes, ship"}
        </button>
        <button
          type="button"
          onClick={() => setPhase({ kind: "idle" })}
          className="border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
        >
          cancel
        </button>
      </div>
    );
  }

  return (
    <span className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => setPhase({ kind: "confirming" })}
        disabled={phase.kind === "saving"}
        className={cn(
          "rounded-md border px-3 py-1.5 text-[13px] leading-none transition-colors",
          status === "live"
            ? "border-warn/30 bg-warn/10 text-warn hover:bg-warn/20"
            : "border-pos/30 bg-pos/10 text-pos hover:bg-pos/20",
          phase.kind === "saving" && "opacity-50",
        )}
      >
        {phase.kind === "saving"
          ? status === "live"
            ? "retiring…"
            : "shipping…"
          : idleLabel}
      </button>
      {phase.kind === "error" ? (
        <span className="tabular-nums text-[11px] text-neg">
          {phase.message}
        </span>
      ) : null}
    </span>
  );
}

async function describe(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    /* fall through */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}

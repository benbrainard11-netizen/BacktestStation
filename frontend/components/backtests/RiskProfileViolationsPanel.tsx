"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import type { components } from "@/lib/api/generated";

type RiskProfile = components["schemas"]["RiskProfileRead"];
type RiskEvaluation = components["schemas"]["RiskEvaluationRead"];

interface RiskProfileViolationsPanelProps {
  runId: number;
}

type ProfileEvaluation = {
  profile: RiskProfile;
  evaluation: RiskEvaluation | null;
  error: string | null;
};

type FetchState =
  | { kind: "loading" }
  | { kind: "no_profiles" }
  | { kind: "error"; message: string }
  | { kind: "data"; rows: ProfileEvaluation[] };

export default function RiskProfileViolationsPanel({
  runId,
}: RiskProfileViolationsPanelProps) {
  const [state, setState] = useState<FetchState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = await loadAll(runId);
      if (!cancelled) setState(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (state.kind === "loading") {
    return (
      <div className="flex items-center gap-3 text-zinc-400">
        <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} aria-hidden />
        <span className="font-mono text-xs uppercase tracking-widest">
          Evaluating risk profiles…
        </span>
      </div>
    );
  }

  if (state.kind === "no_profiles") {
    return (
      <div className="flex flex-col gap-2">
        <p className="font-mono text-xs text-zinc-500">
          No risk profiles defined yet.
        </p>
        <Link
          href="/risk-profiles"
          className="font-mono text-[11px] uppercase tracking-widest text-zinc-300 underline-offset-2 hover:underline"
        >
          Create one →
        </Link>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-rose-300">
          <AlertTriangle className="h-4 w-4" strokeWidth={1.5} aria-hidden />
          <span>Failed to load risk profiles</span>
        </div>
        <p className="font-mono text-xs text-zinc-200">{state.message}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {state.rows.map((row) => (
        <ProfileRow key={row.profile.id} row={row} />
      ))}
    </div>
  );
}

function ProfileRow({ row }: { row: ProfileEvaluation }) {
  const [expanded, setExpanded] = useState(false);
  const { profile, evaluation, error } = row;

  if (error) {
    return (
      <div className="border border-rose-900 bg-rose-950/20 px-3 py-2.5">
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono text-xs text-zinc-200">{profile.name}</span>
          <span className="font-mono text-[11px] uppercase tracking-widest text-rose-300">
            evaluation failed
          </span>
        </div>
        <p className="mt-1 font-mono text-[11px] text-rose-300">{error}</p>
      </div>
    );
  }

  if (!evaluation) return null;

  const violationCount = evaluation.violations.length;
  const clean = violationCount === 0;
  const tone = clean ? "border-emerald-900/60" : "border-amber-900/60";

  return (
    <div className={`border ${tone} bg-zinc-950/40 px-3 py-2.5`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          {clean ? (
            <CheckCircle2
              className="h-4 w-4 shrink-0 text-emerald-400"
              strokeWidth={1.5}
              aria-hidden
            />
          ) : (
            <AlertTriangle
              className="h-4 w-4 shrink-0 text-amber-300"
              strokeWidth={1.5}
              aria-hidden
            />
          )}
          <Link
            href={`/risk-profiles/${profile.id}`}
            className="truncate font-mono text-xs text-zinc-100 hover:underline"
          >
            {profile.name}
          </Link>
          {profile.status !== "active" ? (
            <span className="border border-zinc-800 bg-zinc-950 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-zinc-500">
              {profile.status}
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`font-mono text-[11px] uppercase tracking-widest ${
              clean ? "text-emerald-300" : "text-amber-300"
            }`}
          >
            {clean
              ? "no violations"
              : `${violationCount} violation${violationCount === 1 ? "" : "s"}`}
          </span>
          <span className="font-mono text-[10px] text-zinc-500">
            {evaluation.total_trades_evaluated} trades
          </span>
          {!clean ? (
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              className="border border-zinc-800 bg-zinc-900 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-zinc-300 hover:bg-zinc-800"
            >
              {expanded ? "hide" : "show"}
            </button>
          ) : null}
        </div>
      </div>

      {expanded && !clean ? (
        <ul className="mt-2 flex flex-col gap-1.5 border-t border-zinc-800/60 pt-2">
          {evaluation.violations.map((v, i) => (
            <li
              key={`${v.at_trade_id}-${v.kind}-${i}`}
              className="grid grid-cols-[auto_auto_1fr] gap-x-3 font-mono text-[11px]"
            >
              <span className="text-zinc-500">#{v.at_trade_index + 1}</span>
              <span className="text-amber-300 uppercase tracking-widest">
                {v.kind}
              </span>
              <span className="text-zinc-200 break-words">{v.message}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

async function loadAll(runId: number): Promise<FetchState> {
  let profiles: RiskProfile[];
  try {
    const res = await fetch("/api/risk-profiles", { cache: "no-store" });
    if (!res.ok) {
      return {
        kind: "error",
        message: `${res.status} ${res.statusText || "Risk profile list failed"}`,
      };
    }
    profiles = (await res.json()) as RiskProfile[];
  } catch (err) {
    return {
      kind: "error",
      message: err instanceof Error ? err.message : "Network error",
    };
  }

  if (profiles.length === 0) return { kind: "no_profiles" };

  const rows: ProfileEvaluation[] = await Promise.all(
    profiles.map(async (profile) => {
      try {
        const url = `/api/risk-profiles/${profile.id}/evaluate?run_id=${runId}`;
        const res = await fetch(url, { method: "POST", cache: "no-store" });
        if (!res.ok) {
          return {
            profile,
            evaluation: null,
            error: `${res.status} ${res.statusText || "evaluation failed"}`,
          };
        }
        const evaluation = (await res.json()) as RiskEvaluation;
        return { profile, evaluation, error: null };
      } catch (err) {
        return {
          profile,
          evaluation: null,
          error: err instanceof Error ? err.message : "Network error",
        };
      }
    }),
  );

  return { kind: "data", rows };
}

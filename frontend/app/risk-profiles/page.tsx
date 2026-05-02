"use client";

import { useState, useCallback } from "react";

import { Card, CardHead, Chip, PageHeader, Stat } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate } from "@/lib/format";
import { usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

type RiskProfile = components["schemas"]["RiskProfileRead"];
type RiskEvaluation = components["schemas"]["RiskEvaluationRead"];
type BackendErrorBody = { detail?: string };

const POLL_INTERVAL = 30_000;

const INPUT_CLS =
  "w-full rounded border border-line bg-bg-2 px-2 py-1.5 font-mono text-[12px] text-ink-0 placeholder:text-ink-4 focus:border-accent focus:outline-none";

function statusTone(s: string): "pos" | "default" {
  return s === "active" ? "pos" : "default";
}

function fmtCap(v: number | null, unit = "R"): string {
  return v != null ? `${v}${unit}` : "—";
}

async function extractError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as BackendErrorBody;
    if (typeof body.detail === "string" && body.detail) return body.detail;
  } catch {
    /* fall through */
  }
  return `${res.status} ${res.statusText || "Request failed"}`;
}

/* ============================================================
   Page root
   ============================================================ */

export default function RiskProfilesPage() {
  const poll = usePoll<RiskProfile[]>("/api/risk-profiles", POLL_INTERVAL);
  const statusesPoll = usePoll<{ statuses: string[] }>(
    "/api/risk-profiles/statuses",
    POLL_INTERVAL,
  );

  const [_tick, setTick] = useState(0);
  const refresh = useCallback(() => setTick((n) => n + 1), []);

  const profiles = poll.kind === "data" ? poll.data : [];
  const statuses =
    statusesPoll.kind === "data" ? statusesPoll.data.statuses : ["active", "archived"];

  const totalCount = profiles.length;
  // Build per-status counts from the enum vocabulary
  const countByStatus = Object.fromEntries(
    statuses.map((s) => [s, profiles.filter((p) => p.status === s).length]),
  );

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={
          poll.kind === "loading"
            ? "RISK PROFILES · LOADING"
            : poll.kind === "error"
              ? "RISK PROFILES · ERROR"
              : `RISK PROFILES · ${totalCount} TOTAL`
        }
        title="Risk Profiles"
        sub="Named R-multiple cap sets. Apply retroactively to any backtest run to surface violations. Also prefills the Run-a-Backtest form."
        right={<NewProfileDialog onCreated={refresh} statuses={statuses} />}
      />

      {/* Stat tiles: total + per-status */}
      <div className="mt-2 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat
            label="Total profiles"
            value={poll.kind === "loading" ? "…" : String(totalCount)}
            sub="across all statuses"
          />
        </Card>
        {statuses.slice(0, 3).map((s) => (
          <Card key={s}>
            <Stat
              label={s}
              value={poll.kind === "loading" ? "…" : String(countByStatus[s] ?? 0)}
              sub={`status: ${s}`}
              tone={statusTone(s)}
            />
          </Card>
        ))}
      </div>

      {/* Body */}
      <div className="mt-6">
        {poll.kind === "loading" && (
          <Card>
            <div className="px-6 py-8 text-sm text-ink-3">Loading risk profiles…</div>
          </Card>
        )}
        {poll.kind === "error" && (
          <Card className="border-neg/30 bg-neg-soft">
            <div className="px-6 py-6">
              <div className="card-eyebrow text-neg">failed to load risk profiles</div>
              <div className="mt-1 text-sm text-ink-1">{poll.message}</div>
              <div className="mt-2 text-xs text-ink-3">Retrying every 30s.</div>
            </div>
          </Card>
        )}
        {poll.kind === "data" && profiles.length === 0 && (
          <Card>
            <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
              <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-ink-4">
                empty state
              </div>
              <div className="text-sm text-ink-2">
                No risk profiles yet. Create the first one with the button above.
              </div>
            </div>
          </Card>
        )}
        {poll.kind === "data" && profiles.length > 0 && (
          <ProfileTable profiles={profiles} statuses={statuses} onMutated={refresh} />
        )}
      </div>
    </div>
  );
}

/* ============================================================
   Risk profile table
   ============================================================ */

function ProfileTable({
  profiles,
  statuses,
  onMutated,
}: {
  profiles: RiskProfile[];
  statuses: string[];
  onMutated: () => void;
}) {
  return (
    <Card>
      <CardHead
        eyebrow="profiles"
        title="All risk profiles"
        right={
          <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
            {profiles.length} total
          </span>
        }
      />
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[12.5px]">
          <thead>
            <tr className="border-b border-line text-left">
              {[
                { label: "Name" },
                { label: "Status" },
                { label: "Daily loss cap", align: "text-right" },
                { label: "Max DD cap", align: "text-right" },
                { label: "Max consec losses", align: "text-right" },
                { label: "Max position size", align: "text-right" },
                { label: "Allowed hours" },
                { label: "Updated", align: "text-right" },
                { label: "", align: "text-right" },
              ].map((h) => (
                <th
                  key={h.label || "_actions"}
                  className={cn(
                    "px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-4",
                    h.align,
                  )}
                >
                  {h.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {profiles.map((p, i) => (
              <ProfileRow
                key={p.id}
                profile={p}
                isLast={i === profiles.length - 1}
                statuses={statuses}
                onMutated={onMutated}
              />
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/* ============================================================
   Profile row — with inline evaluate action
   ============================================================ */

function ProfileRow({
  profile,
  isLast,
  statuses,
  onMutated,
}: {
  profile: RiskProfile;
  isLast: boolean;
  statuses: string[];
  onMutated: () => void;
}) {
  const [evalOpen, setEvalOpen] = useState(false);

  const updatedAt =
    profile.updated_at != null
      ? fmtDate(String(profile.updated_at))
      : fmtDate(String(profile.created_at));

  return (
    <>
      <tr
        className={cn("hover:bg-bg-2", !isLast && !evalOpen && "border-b border-line")}
      >
        {/* Name */}
        <td className="px-4 py-2.5 font-medium text-ink-0">{profile.name}</td>
        {/* Status */}
        <td className="px-4 py-2.5">
          <Chip tone={statusTone(profile.status)}>{profile.status}</Chip>
        </td>
        {/* Daily loss */}
        <td className="px-4 py-2.5 text-right font-mono text-ink-2">
          {fmtCap(profile.max_daily_loss_r)}
        </td>
        {/* Max DD */}
        <td className="px-4 py-2.5 text-right font-mono text-ink-2">
          {fmtCap(profile.max_drawdown_r)}
        </td>
        {/* Consecutive losses */}
        <td className="px-4 py-2.5 text-right font-mono text-ink-2">
          {profile.max_consecutive_losses != null
            ? String(profile.max_consecutive_losses)
            : "—"}
        </td>
        {/* Position size */}
        <td className="px-4 py-2.5 text-right font-mono text-ink-2">
          {profile.max_position_size != null
            ? String(profile.max_position_size)
            : "—"}
        </td>
        {/* Allowed hours */}
        <td className="px-4 py-2.5">
          {profile.allowed_hours != null && profile.allowed_hours.length > 0 ? (
            <div className="flex flex-wrap gap-0.5">
              {profile.allowed_hours.map((h) => (
                <span
                  key={h}
                  className="inline-flex h-4 w-5 items-center justify-center rounded bg-accent-soft font-mono text-[9px] text-accent"
                >
                  {h}
                </span>
              ))}
            </div>
          ) : (
            <span className="font-mono text-[10.5px] text-ink-4">any</span>
          )}
        </td>
        {/* Updated */}
        <td className="px-4 py-2.5 text-right font-mono text-[11px] text-ink-3">
          {updatedAt}
        </td>
        {/* Actions */}
        <td className="px-4 py-2.5 text-right">
          <span className="flex items-center justify-end gap-3">
            <button
              type="button"
              className={cn(
                "font-mono text-[10.5px] hover:text-accent",
                evalOpen ? "text-accent" : "text-ink-3",
              )}
              onClick={() => setEvalOpen((v) => !v)}
            >
              {evalOpen ? "cancel" : "evaluate"}
            </button>
            <ProfileActions
              profile={profile}
              statuses={statuses}
              onMutated={onMutated}
            />
          </span>
        </td>
      </tr>

      {/* Evaluate panel */}
      {evalOpen && (
        <tr className={cn("bg-bg-2", !isLast && "border-b border-line")}>
          <td colSpan={9} className="px-6 py-4">
            <EvaluatePanel
              profileId={profile.id}
              profileName={profile.name}
              onClose={() => setEvalOpen(false)}
            />
          </td>
        </tr>
      )}
    </>
  );
}

/* ============================================================
   Per-profile actions — archive/unarchive, delete
   ============================================================ */

type ProfileActionPhase =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

function ProfileActions({
  profile,
  statuses,
  onMutated,
}: {
  profile: RiskProfile;
  statuses: string[];
  onMutated: () => void;
}) {
  const [phase, setPhase] = useState<ProfileActionPhase>({ kind: "idle" });

  async function patchStatus(nextStatus: string) {
    setPhase({ kind: "saving" });
    try {
      const res = await fetch(`/api/risk-profiles/${profile.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      if (!res.ok) {
        setPhase({ kind: "error", message: await extractError(res) });
        return;
      }
      setPhase({ kind: "idle" });
      onMutated();
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  async function doDelete() {
    if (
      !window.confirm(
        `Delete profile "${profile.name}"? This cannot be undone. Trade data is unaffected.`,
      )
    ) {
      return;
    }
    setPhase({ kind: "saving" });
    try {
      const res = await fetch(`/api/risk-profiles/${profile.id}`, {
        method: "DELETE",
      });
      if (!res.ok && res.status !== 204) {
        setPhase({ kind: "error", message: await extractError(res) });
        return;
      }
      setPhase({ kind: "idle" });
      onMutated();
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  if (phase.kind === "saving") {
    return <span className="font-mono text-[10.5px] text-ink-3">saving…</span>;
  }
  if (phase.kind === "error") {
    return (
      <span className="flex items-center gap-2">
        <span className="font-mono text-[10.5px] text-neg">{phase.message}</span>
        <button
          type="button"
          className="font-mono text-[10.5px] text-ink-3 underline"
          onClick={() => setPhase({ kind: "idle" })}
        >
          ok
        </button>
      </span>
    );
  }

  const isArchived = profile.status === "archived";
  const nextStatus = isArchived ? "active" : "archived";

  return (
    <span className="flex items-center gap-3">
      <button
        type="button"
        className="font-mono text-[10.5px] text-ink-3 hover:text-ink-1"
        onClick={() => patchStatus(nextStatus)}
      >
        {isArchived ? "unarchive" : "archive"}
      </button>
      <button
        type="button"
        className="font-mono text-[10.5px] text-neg/70 hover:text-neg"
        onClick={doDelete}
      >
        delete
      </button>
    </span>
  );
}

/* ============================================================
   Evaluate panel — POST /risk-profiles/{id}/evaluate?run_id=N
   Shows violations inline after the row
   ============================================================ */

type EvalPhase =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "result"; data: RiskEvaluation }
  | { kind: "error"; message: string };

function EvaluatePanel({
  profileId,
  profileName,
  onClose,
}: {
  profileId: number;
  profileName: string;
  onClose: () => void;
}) {
  const [runIdVal, setRunIdVal] = useState("");
  const [evalPhase, setEvalPhase] = useState<EvalPhase>({ kind: "idle" });

  async function evaluate() {
    const runId = parseInt(runIdVal, 10);
    if (!Number.isFinite(runId) || runId <= 0) return;
    setEvalPhase({ kind: "loading" });
    try {
      const res = await fetch(
        `/api/risk-profiles/${profileId}/evaluate?run_id=${runId}`,
        { method: "POST" },
      );
      if (!res.ok) {
        setEvalPhase({ kind: "error", message: await extractError(res) });
        return;
      }
      const data = (await res.json()) as RiskEvaluation;
      setEvalPhase({ kind: "result", data });
    } catch (e) {
      setEvalPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
          Evaluate "{profileName}" against backtest run
        </span>
        <span className="flex items-center gap-2">
          <input
            type="number"
            min={1}
            placeholder="run id"
            value={runIdVal}
            onChange={(e) => setRunIdVal(e.target.value)}
            className="w-24 rounded border border-line bg-bg-3 px-2 py-0.5 font-mono text-[11px] text-ink-0 placeholder:text-ink-4 focus:border-accent focus:outline-none"
            onKeyDown={(e) => {
              if (e.key === "Enter") void evaluate();
            }}
          />
          <button
            type="button"
            disabled={evalPhase.kind === "loading" || !runIdVal.trim()}
            className="rounded border border-accent/40 bg-accent-soft px-3 py-0.5 font-mono text-[10.5px] text-accent disabled:opacity-40"
            onClick={() => void evaluate()}
          >
            {evalPhase.kind === "loading" ? "evaluating…" : "run"}
          </button>
          <button
            type="button"
            className="font-mono text-[10.5px] text-ink-3 hover:text-ink-1"
            onClick={onClose}
          >
            cancel
          </button>
        </span>
      </div>

      {evalPhase.kind === "error" && (
        <div className="rounded border border-neg/30 bg-neg-soft px-3 py-2 font-mono text-[11px] text-neg">
          {evalPhase.message}
        </div>
      )}

      {evalPhase.kind === "result" && (
        <EvalResult result={evalPhase.data} />
      )}
    </div>
  );
}

function EvalResult({ result }: { result: RiskEvaluation }) {
  const { total_trades_evaluated, violations } = result;
  const clean = violations.length === 0;

  return (
    <div className="flex flex-col gap-3 rounded border border-line bg-bg-1 p-4">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
          Evaluation result · run #{result.run_id} · {total_trades_evaluated} trades
        </span>
        {clean ? (
          <Chip tone="pos">no violations</Chip>
        ) : (
          <Chip tone="neg">{violations.length} violation{violations.length === 1 ? "" : "s"}</Chip>
        )}
      </div>

      {clean && (
        <p className="text-[13px] text-ink-2">
          All {total_trades_evaluated} trades passed every cap in this profile.
        </p>
      )}

      {!clean && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[11.5px]">
            <thead>
              <tr className="border-b border-line text-left">
                {["Kind", "Trade index", "Trade id", "Message"].map((h) => (
                  <th
                    key={h}
                    className="pb-1.5 pr-6 font-mono text-[9.5px] font-semibold uppercase tracking-[0.08em] text-ink-4"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {violations.map((v, i) => (
                <tr
                  key={i}
                  className={cn("hover:bg-bg-2", i < violations.length - 1 && "border-b border-line/50")}
                >
                  <td className="py-1.5 pr-6">
                    <Chip tone="neg">{v.kind.replace(/_/g, " ")}</Chip>
                  </td>
                  <td className="py-1.5 pr-6 font-mono text-ink-2">
                    #{v.at_trade_index}
                  </td>
                  <td className="py-1.5 pr-6 font-mono text-ink-3">
                    {v.at_trade_id}
                  </td>
                  <td className="py-1.5 text-ink-1">{v.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ============================================================
   New profile modal dialog (full form matching RiskProfileCreate)
   ============================================================ */

type NewProfilePhase =
  | { kind: "closed" }
  | { kind: "open" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

function NewProfileDialog({
  onCreated,
  statuses,
}: {
  onCreated: () => void;
  statuses: string[];
}) {
  const [phase, setPhase] = useState<NewProfilePhase>({ kind: "closed" });
  const [name, setName] = useState("");
  const [status, setStatus] = useState("active");
  const [maxDailyLossR, setMaxDailyLossR] = useState("");
  const [maxDrawdownR, setMaxDrawdownR] = useState("");
  const [maxConsecLosses, setMaxConsecLosses] = useState("");
  const [maxPositionSize, setMaxPositionSize] = useState("");
  const [allowedHoursRaw, setAllowedHoursRaw] = useState("");
  const [notes, setNotes] = useState("");
  const [strategyParamsJson, setStrategyParamsJson] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);

  function open() {
    setName("");
    setStatus("active");
    setMaxDailyLossR("");
    setMaxDrawdownR("");
    setMaxConsecLosses("");
    setMaxPositionSize("");
    setAllowedHoursRaw("");
    setNotes("");
    setStrategyParamsJson("");
    setJsonError(null);
    setPhase({ kind: "open" });
  }

  function close() {
    setPhase({ kind: "closed" });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    // Validate strategy params JSON if provided
    let strategyParams: Record<string, unknown> | null = null;
    if (strategyParamsJson.trim()) {
      try {
        const parsed = JSON.parse(strategyParamsJson) as unknown;
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          setJsonError("Must be a JSON object, e.g. {}");
          return;
        }
        strategyParams = parsed as Record<string, unknown>;
        setJsonError(null);
      } catch {
        setJsonError("Invalid JSON — check syntax");
        return;
      }
    }

    // Parse allowed hours
    const allowedHours = allowedHoursRaw
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
      .map((s) => parseInt(s, 10))
      .filter((n) => Number.isFinite(n) && n >= 0 && n <= 23);

    const body = {
      name: name.trim(),
      status,
      max_daily_loss_r: emptyOrFloat(maxDailyLossR),
      max_drawdown_r: emptyOrFloat(maxDrawdownR),
      max_consecutive_losses: emptyOrInt(maxConsecLosses),
      max_position_size: emptyOrInt(maxPositionSize),
      allowed_hours: allowedHours.length > 0 ? allowedHours : null,
      notes: notes.trim() || null,
      strategy_params: strategyParams,
    };

    setPhase({ kind: "saving" });
    try {
      const res = await fetch("/api/risk-profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        setPhase({ kind: "error", message: await extractError(res) });
        return;
      }
      setPhase({ kind: "closed" });
      onCreated();
    } catch (e2) {
      setPhase({
        kind: "error",
        message: e2 instanceof Error ? e2.message : "Network error",
      });
    }
  }

  if (phase.kind === "closed") {
    return (
      <button
        type="button"
        onClick={open}
        className="rounded border border-pos/40 bg-pos/10 px-3 py-1.5 font-mono text-[11px] font-semibold text-pos hover:bg-pos/20"
      >
        + New profile
      </button>
    );
  }

  const saving = phase.kind === "saving";

  return (
    /* Backdrop */
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-bg-0/80 backdrop-blur-sm">
      <form
        onSubmit={(e) => void submit(e)}
        className="my-10 w-full max-w-lg rounded-lg border border-line bg-bg-1 p-6 shadow-2xl"
      >
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-[15px] font-semibold text-ink-0">New risk profile</h2>
          <button
            type="button"
            onClick={close}
            className="text-xl leading-none text-ink-3 hover:text-ink-0"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="flex flex-col gap-4">
          {/* Name + Status */}
          <div className="grid grid-cols-[2fr_1fr] gap-3">
            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
                Name *
              </span>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Conservative"
                required
                className={INPUT_CLS}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
                Status
              </span>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className={INPUT_CLS}
              >
                {statuses.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {/* Cap fields */}
          <div>
            <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
              R-multiple caps (blank = no cap)
            </div>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1">
                <span className="font-mono text-[10px] text-ink-4">Max daily loss R</span>
                <input
                  type="number"
                  step="any"
                  value={maxDailyLossR}
                  onChange={(e) => setMaxDailyLossR(e.target.value)}
                  placeholder="e.g. 3"
                  className={INPUT_CLS}
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="font-mono text-[10px] text-ink-4">Max drawdown R</span>
                <input
                  type="number"
                  step="any"
                  value={maxDrawdownR}
                  onChange={(e) => setMaxDrawdownR(e.target.value)}
                  placeholder="e.g. 6"
                  className={INPUT_CLS}
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="font-mono text-[10px] text-ink-4">Max consecutive losses</span>
                <input
                  type="number"
                  step="1"
                  value={maxConsecLosses}
                  onChange={(e) => setMaxConsecLosses(e.target.value)}
                  placeholder="e.g. 4"
                  className={INPUT_CLS}
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="font-mono text-[10px] text-ink-4">Max position size (contracts)</span>
                <input
                  type="number"
                  step="1"
                  value={maxPositionSize}
                  onChange={(e) => setMaxPositionSize(e.target.value)}
                  placeholder="e.g. 2"
                  className={INPUT_CLS}
                />
              </label>
            </div>
          </div>

          {/* Allowed hours */}
          <label className="flex flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
              Allowed UTC hours (comma-separated, blank = any)
            </span>
            <input
              type="text"
              value={allowedHoursRaw}
              onChange={(e) => setAllowedHoursRaw(e.target.value)}
              placeholder="13, 14, 15, 16, 17"
              className={INPUT_CLS}
            />
          </label>

          {/* Notes */}
          <label className="flex flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
              Notes (optional)
            </span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className={cn(INPUT_CLS, "resize-y")}
              placeholder="Any notes about this profile…"
            />
          </label>

          {/* Strategy params JSON */}
          <label className="flex flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
              Strategy params (JSON, optional)
            </span>
            <span className="font-mono text-[10px] text-ink-4">
              Prefills the Run-a-Backtest form. Must be a JSON object.
            </span>
            <textarea
              value={strategyParamsJson}
              onChange={(e) => setStrategyParamsJson(e.target.value)}
              rows={4}
              spellCheck={false}
              placeholder={'{\n  "max_risk_dollars": 300,\n  "target_r": 3.0\n}'}
              className={cn(INPUT_CLS, "resize-y font-mono text-[11px]")}
            />
            {jsonError && (
              <span className="font-mono text-[10px] text-neg">{jsonError}</span>
            )}
          </label>

          {phase.kind === "error" && (
            <div className="rounded border border-neg/30 bg-neg-soft px-3 py-2 font-mono text-[11px] text-neg">
              {phase.message}
            </div>
          )}

          <div className="flex items-center gap-3 pt-1">
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="rounded border border-pos/40 bg-pos/10 px-4 py-1.5 font-mono text-[11px] font-semibold text-pos disabled:opacity-40"
            >
              {saving ? "creating…" : "Create profile"}
            </button>
            <button
              type="button"
              onClick={close}
              disabled={saving}
              className="font-mono text-[11px] text-ink-3 hover:text-ink-1 disabled:opacity-40"
            >
              Cancel
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

/* ============================================================
   Utilities
   ============================================================ */

function emptyOrFloat(v: string): number | null {
  if (!v.trim()) return null;
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

function emptyOrInt(v: string): number | null {
  const n = emptyOrFloat(v);
  return n === null ? null : Math.round(n);
}

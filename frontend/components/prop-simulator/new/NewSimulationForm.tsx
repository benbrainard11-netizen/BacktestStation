"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type Profile = components["schemas"]["FirmRuleProfileRead"];
type SimulationRunRequest = components["schemas"]["SimulationRunRequest"];
type SimulationRunDetail = components["schemas"]["SimulationRunDetail"];

interface NewSimulationFormProps {
  runs: BacktestRun[];
  profiles: Profile[];
}

type SamplingMode = SimulationRunRequest["sampling_mode"];
type RiskMode = SimulationRunRequest["risk_mode"];
type PhaseMode = SimulationRunRequest["phase_mode"];

const SAMPLING_OPTIONS: { value: SamplingMode; label: string; hint: string }[] =
  [
    {
      value: "trade_bootstrap",
      label: "Trade bootstrap",
      hint: "Resample individual trades. Fastest, biased away from realistic intraday clustering.",
    },
    {
      value: "day_bootstrap",
      label: "Day bootstrap",
      hint: "Resample whole days. Preserves intraday correlation. Recommended.",
    },
    {
      value: "regime_bootstrap",
      label: "Regime bootstrap",
      hint: "Resample within volatility regimes. Most realistic, slowest.",
    },
  ];

const RISK_OPTIONS: { value: RiskMode; label: string; hint: string }[] = [
  {
    value: "fixed_dollar",
    label: "Fixed dollar",
    hint: "Same $ at risk per trade.",
  },
  {
    value: "fixed_contracts",
    label: "Fixed contracts",
    hint: "Same contract count per trade.",
  },
  {
    value: "percent_balance",
    label: "% of balance",
    hint: "Risk a fixed % of current balance per trade.",
  },
  {
    value: "risk_sweep",
    label: "Risk sweep",
    hint: "Run the same simulation across multiple risk levels.",
  },
];

const PHASE_OPTIONS: { value: PhaseMode; label: string }[] = [
  { value: "eval_only", label: "Eval only" },
  { value: "funded_only", label: "Funded only" },
  { value: "eval_to_payout", label: "Eval → payout" },
];

export default function NewSimulationForm({
  runs,
  profiles,
}: NewSimulationFormProps) {
  const router = useRouter();

  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [selectedRuns, setSelectedRuns] = useState<number[]>([]);
  const [profileId, setProfileId] = useState<string>(
    profiles[0]?.profile_id ?? "",
  );
  const [samplingMode, setSamplingMode] =
    useState<SamplingMode>("day_bootstrap");
  const [useReplacement, setUseReplacement] = useState(true);
  const [simulationCount, setSimulationCount] = useState(500);
  const [randomSeed, setRandomSeed] = useState(42);
  const [riskMode, setRiskMode] = useState<RiskMode>("fixed_dollar");
  const [riskPerTrade, setRiskPerTrade] = useState(200);
  const [riskSweepValues, setRiskSweepValues] = useState("100, 200, 300, 400");
  const [accountSize, setAccountSize] = useState(50_000);
  const [startingBalance, setStartingBalance] = useState(50_000);
  const [feesEnabled, setFeesEnabled] = useState(true);
  const [copyTradeAccounts, setCopyTradeAccounts] = useState(1);
  const [payoutRulesEnabled, setPayoutRulesEnabled] = useState(true);
  const [phaseMode, setPhaseMode] = useState<PhaseMode>("eval_only");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [dailyLossStop, setDailyLossStop] = useState<number | "">("");
  const [dailyProfitStop, setDailyProfitStop] = useState<number | "">("");
  const [dailyTradeLimit, setDailyTradeLimit] = useState<number | "">("");
  const [maxLossesPerDay, setMaxLossesPerDay] = useState<number | "">("");
  const [maxTradesPerSequence, setMaxTradesPerSequence] = useState<
    number | ""
  >("");
  const [maxDaysPerSequence, setMaxDaysPerSequence] = useState<number | "">("");
  const [reduceRiskAfterLoss, setReduceRiskAfterLoss] = useState(false);
  const [walkawayAfterWinner, setWalkawayAfterWinner] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedProfile = useMemo(
    () => profiles.find((p) => p.profile_id === profileId) ?? null,
    [profiles, profileId],
  );

  const formIsValid =
    name.trim().length > 0 &&
    selectedRuns.length > 0 &&
    profileId !== "" &&
    accountSize > 0 &&
    startingBalance > 0 &&
    simulationCount >= 1 &&
    simulationCount <= 10_000;

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!formIsValid) return;
    setSubmitting(true);
    setError(null);

    const payload: SimulationRunRequest = {
      name: name.trim(),
      notes: notes.trim(),
      selected_backtest_ids: selectedRuns,
      firm_profile_id: profileId,
      sampling_mode: samplingMode,
      use_replacement: useReplacement,
      simulation_count: simulationCount,
      random_seed: randomSeed,
      risk_mode: riskMode,
      risk_per_trade: riskMode === "risk_sweep" ? null : riskPerTrade,
      risk_sweep_values:
        riskMode === "risk_sweep" ? parseSweep(riskSweepValues) : null,
      account_size: accountSize,
      starting_balance: startingBalance,
      fees_enabled: feesEnabled,
      copy_trade_accounts: copyTradeAccounts,
      payout_rules_enabled: payoutRulesEnabled,
      phase_mode: phaseMode,
      daily_loss_stop: dailyLossStop === "" ? null : dailyLossStop,
      daily_profit_stop: dailyProfitStop === "" ? null : dailyProfitStop,
      daily_trade_limit: dailyTradeLimit === "" ? null : dailyTradeLimit,
      max_losses_per_day: maxLossesPerDay === "" ? null : maxLossesPerDay,
      max_trades_per_sequence:
        maxTradesPerSequence === "" ? null : maxTradesPerSequence,
      max_days_per_sequence:
        maxDaysPerSequence === "" ? null : maxDaysPerSequence,
      reduce_risk_after_loss: reduceRiskAfterLoss,
      walkaway_after_winner: walkawayAfterWinner,
    };

    try {
      const r = await fetch("/api/prop-firm/simulations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!r.ok) {
        const detail = await r
          .json()
          .then((b: { detail?: string }) => b.detail)
          .catch(() => null);
        setError(detail ?? `${r.status} ${r.statusText || "Request failed"}`);
        setSubmitting(false);
        return;
      }
      const created = (await r.json()) as SimulationRunDetail;
      router.push(`/prop-simulator/runs/${created.config.simulation_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      {/* Identity */}
      <Panel title="Identity">
        <div className="grid grid-cols-1 gap-3">
          <Field label="Name" required>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="ORB fade · Topstep 50K · day bootstrap"
              className={inputCls}
              autoFocus
            />
          </Field>
          <Field label="Notes">
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Optional context — what's being tested or compared."
              className={cn(inputCls, "resize-y")}
            />
          </Field>
        </div>
      </Panel>

      {/* Backtests */}
      <Panel
        title="Backtests"
        meta={`${selectedRuns.length} selected · ${runs.length} available`}
      >
        <ul className="m-0 flex max-h-[280px] list-none flex-col gap-1 overflow-y-auto p-0">
          {runs.map((r) => {
            const on = selectedRuns.includes(r.id);
            return (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() =>
                    setSelectedRuns((prev) =>
                      on
                        ? prev.filter((x) => x !== r.id)
                        : [...prev, r.id],
                    )
                  }
                  className={cn(
                    "flex w-full items-start gap-2 rounded-md border px-2.5 py-2 text-left transition-colors",
                    on
                      ? "border-accent/40 bg-accent/[0.06]"
                      : "border-border bg-surface-alt hover:border-border-strong",
                  )}
                >
                  <span
                    className={cn(
                      "mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border",
                      on
                        ? "border-accent bg-accent text-bg"
                        : "border-border-strong bg-surface",
                    )}
                  >
                    {on ? <span className="text-[10px]">✓</span> : null}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="m-0 truncate text-[13px] text-text">
                      {r.name ?? `BT-${r.id}`}
                    </p>
                    <p className="m-0 text-xs text-text-mute">
                      {r.symbol} · {r.timeframe ?? "—"} ·{" "}
                      {shortDate(r.start_ts)} → {shortDate(r.end_ts)}
                    </p>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      </Panel>

      {/* Firm + sampling */}
      <div className="grid grid-cols-2 gap-4">
        <Panel title="Firm rule profile">
          <Field label="Profile" required>
            <select
              value={profileId}
              onChange={(e) => setProfileId(e.target.value)}
              className={inputCls}
            >
              {profiles.map((p) => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.firm_name} · {p.account_name}
                </option>
              ))}
            </select>
          </Field>
          {selectedProfile ? (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-text-dim">
              <Pill tone={profileTone(selectedProfile.verification_status)}>
                {selectedProfile.verification_status}
              </Pill>
              <span>
                ${selectedProfile.account_size.toLocaleString()} acct ·{" "}
                profit target ${selectedProfile.profit_target.toLocaleString()}
              </span>
            </div>
          ) : null}
        </Panel>
        <Panel title="Sampling">
          <div className="flex flex-col gap-2">
            {SAMPLING_OPTIONS.map((opt) => (
              <RadioRow
                key={opt.value}
                label={opt.label}
                hint={opt.hint}
                checked={samplingMode === opt.value}
                onChange={() => setSamplingMode(opt.value)}
              />
            ))}
            <CheckboxRow
              label="Sample with replacement"
              checked={useReplacement}
              onChange={setUseReplacement}
            />
          </div>
        </Panel>
      </div>

      {/* Sequences + risk */}
      <div className="grid grid-cols-2 gap-4">
        <Panel title="Sequences">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Simulations" required>
              <input
                type="number"
                min={1}
                max={10_000}
                value={simulationCount}
                onChange={(e) =>
                  setSimulationCount(parseIntOr(e.target.value, 500))
                }
                className={inputCls}
              />
            </Field>
            <Field label="Random seed">
              <input
                type="number"
                value={randomSeed}
                onChange={(e) =>
                  setRandomSeed(parseIntOr(e.target.value, 42))
                }
                className={inputCls}
              />
            </Field>
          </div>
        </Panel>
        <Panel title="Risk model">
          <div className="flex flex-col gap-2">
            {RISK_OPTIONS.map((opt) => (
              <RadioRow
                key={opt.value}
                label={opt.label}
                hint={opt.hint}
                checked={riskMode === opt.value}
                onChange={() => setRiskMode(opt.value)}
              />
            ))}
            {riskMode === "risk_sweep" ? (
              <Field label="Sweep values (comma-separated)">
                <input
                  type="text"
                  value={riskSweepValues}
                  onChange={(e) => setRiskSweepValues(e.target.value)}
                  placeholder="100, 200, 300, 400"
                  className={inputCls}
                />
              </Field>
            ) : (
              <Field label="Risk per trade">
                <input
                  type="number"
                  min={0}
                  value={riskPerTrade}
                  onChange={(e) =>
                    setRiskPerTrade(parseIntOr(e.target.value, 200))
                  }
                  className={inputCls}
                />
              </Field>
            )}
          </div>
        </Panel>
      </div>

      {/* Account */}
      <Panel title="Account">
        <div className="grid grid-cols-3 gap-3">
          <Field label="Starting balance" required>
            <input
              type="number"
              min={1}
              value={startingBalance}
              onChange={(e) =>
                setStartingBalance(parseIntOr(e.target.value, 50_000))
              }
              className={inputCls}
            />
          </Field>
          <Field label="Account size" required>
            <input
              type="number"
              min={1}
              value={accountSize}
              onChange={(e) =>
                setAccountSize(parseIntOr(e.target.value, 50_000))
              }
              className={inputCls}
            />
          </Field>
          <Field label="Phase">
            <select
              value={phaseMode}
              onChange={(e) => setPhaseMode(e.target.value as PhaseMode)}
              className={inputCls}
            >
              {PHASE_OPTIONS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Copy-trade accounts">
            <input
              type="number"
              min={1}
              value={copyTradeAccounts}
              onChange={(e) =>
                setCopyTradeAccounts(parseIntOr(e.target.value, 1))
              }
              className={inputCls}
            />
          </Field>
          <CheckboxRow
            label="Apply commissions + slippage"
            checked={feesEnabled}
            onChange={setFeesEnabled}
          />
          <CheckboxRow
            label="Apply payout rules"
            checked={payoutRulesEnabled}
            onChange={setPayoutRulesEnabled}
          />
        </div>
      </Panel>

      {/* Advanced toggle */}
      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          className="text-xs text-accent hover:underline"
        >
          {showAdvanced ? "− Hide" : "+ Show"} advanced caps & rules
        </button>
      </div>

      {showAdvanced ? (
        <Panel title="Advanced caps & rules">
          <div className="grid grid-cols-3 gap-3">
            <Field label="Daily loss stop ($)">
              <NumOrEmpty value={dailyLossStop} onChange={setDailyLossStop} />
            </Field>
            <Field label="Daily profit stop ($)">
              <NumOrEmpty
                value={dailyProfitStop}
                onChange={setDailyProfitStop}
              />
            </Field>
            <Field label="Daily trade limit">
              <NumOrEmpty
                value={dailyTradeLimit}
                onChange={setDailyTradeLimit}
              />
            </Field>
            <Field label="Max losses per day">
              <NumOrEmpty
                value={maxLossesPerDay}
                onChange={setMaxLossesPerDay}
              />
            </Field>
            <Field label="Max trades per sequence">
              <NumOrEmpty
                value={maxTradesPerSequence}
                onChange={setMaxTradesPerSequence}
              />
            </Field>
            <Field label="Max days per sequence">
              <NumOrEmpty
                value={maxDaysPerSequence}
                onChange={setMaxDaysPerSequence}
              />
            </Field>
            <CheckboxRow
              label="Reduce risk after a loss"
              checked={reduceRiskAfterLoss}
              onChange={setReduceRiskAfterLoss}
            />
            <CheckboxRow
              label="Walk away after a winner"
              checked={walkawayAfterWinner}
              onChange={setWalkawayAfterWinner}
            />
          </div>
        </Panel>
      ) : null}

      {/* Submit */}
      <div className="flex items-center justify-between gap-4 rounded-lg border border-border bg-surface px-[18px] py-3">
        <div className="text-xs text-text-mute">
          {error ? <span className="text-neg">{error}</span> : "Posts to /api/prop-firm/simulations · runs synchronously"}
        </div>
        <Btn
          type="submit"
          variant="primary"
          disabled={!formIsValid || submitting}
        >
          {submitting ? "Running…" : "Run simulation"}
        </Btn>
      </div>
    </form>
  );
}

const inputCls =
  "rounded-md border border-border bg-surface-alt px-2.5 py-1.5 text-[13px] text-text outline-none placeholder:text-text-mute focus:border-border-strong";

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-text-mute">
      <span>
        {label}
        {required ? <span className="ml-1 text-neg">*</span> : null}
      </span>
      {children}
    </label>
  );
}

function RadioRow({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onChange}
      className={cn(
        "flex w-full items-start gap-2 rounded-md border px-2.5 py-2 text-left transition-colors",
        checked
          ? "border-accent/40 bg-accent/[0.06]"
          : "border-border bg-surface-alt hover:border-border-strong",
      )}
    >
      <span
        className={cn(
          "mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border",
          checked
            ? "border-accent bg-accent text-bg"
            : "border-border-strong bg-surface",
        )}
      >
        {checked ? <span className="h-1.5 w-1.5 rounded-full bg-bg" /> : null}
      </span>
      <div className="min-w-0 flex-1">
        <p className="m-0 text-[13px] text-text">{label}</p>
        {hint ? (
          <p className="m-0 mt-0.5 text-xs text-text-mute">{hint}</p>
        ) : null}
      </div>
    </button>
  );
}

function CheckboxRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 rounded-md px-1 py-1 text-[13px] text-text-dim hover:text-text">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-3.5 w-3.5 rounded border-border-strong"
      />
      {label}
    </label>
  );
}

function NumOrEmpty({
  value,
  onChange,
}: {
  value: number | "";
  onChange: (next: number | "") => void;
}) {
  return (
    <input
      type="number"
      value={value}
      onChange={(e) => {
        const raw = e.target.value;
        if (raw === "") {
          onChange("");
          return;
        }
        const n = Number(raw);
        if (Number.isFinite(n)) onChange(n);
      }}
      placeholder="—"
      className={inputCls}
    />
  );
}

function profileTone(
  status: string,
): "pos" | "neg" | "warn" | "accent" | "neutral" {
  switch (status) {
    case "verified":
      return "pos";
    case "unverified":
      return "warn";
    case "demo":
      return "neutral";
    default:
      return "neutral";
  }
}

function parseIntOr(raw: string, fallback: number): number {
  const n = Number(raw);
  return Number.isFinite(n) ? Math.round(n) : fallback;
}

function parseSweep(raw: string): number[] {
  return raw
    .split(",")
    .map((s) => Number(s.trim()))
    .filter((n) => Number.isFinite(n) && n > 0);
}

function shortDate(iso: string | null): string {
  if (iso === null) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}

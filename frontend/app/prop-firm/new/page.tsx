"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Card, CardHead, PageHeader } from "@/components/atoms";
import { AsyncButton } from "@/components/ui/AsyncButton";
import { RunPicker } from "@/components/ui/RunPicker";
import { usePoll } from "@/lib/poll";

type FirmProfile = {
  profile_id: string;
  firm_name: string;
  account_name: string;
  account_size: number;
};

type SamplingMode = "trade_bootstrap" | "day_bootstrap" | "regime_bootstrap";
type RiskMode =
  | "fixed_dollar"
  | "fixed_contracts"
  | "percent_balance"
  | "risk_sweep";

const SAMPLING_MODES: { id: SamplingMode; label: string; help: string }[] = [
  {
    id: "trade_bootstrap",
    label: "Trade bootstrap",
    help: "Resample individual trades with replacement. Fastest; assumes trades are i.i.d.",
  },
  {
    id: "day_bootstrap",
    label: "Day bootstrap",
    help: "Resample whole trading days. Preserves intraday autocorrelation.",
  },
  {
    id: "regime_bootstrap",
    label: "Regime bootstrap",
    help: "Stratify by regime tag, then resample within each. Best when trade behavior is regime-dependent.",
  },
];

const RISK_MODES: { id: RiskMode; label: string }[] = [
  { id: "fixed_dollar", label: "Fixed $ per trade" },
  { id: "fixed_contracts", label: "Fixed contracts" },
  { id: "percent_balance", label: "% of balance" },
  { id: "risk_sweep", label: "Risk sweep (multiple levels)" },
];

export default function NewPropFirmSimulationPage() {
  const router = useRouter();
  const firms = usePoll<FirmProfile[]>(
    "/api/prop-firm/profiles?include_archived=false",
    5 * 60_000,
  );

  const [name, setName] = useState("");
  const [firmId, setFirmId] = useState<string>("");
  const [picks, setPicks] = useState<number[]>([]);
  const [samplingMode, setSamplingMode] =
    useState<SamplingMode>("trade_bootstrap");
  const [riskMode, setRiskMode] = useState<RiskMode>("fixed_dollar");
  const [simulationCount, setSimulationCount] = useState(1000);
  const [accountSize, setAccountSize] = useState(50000);
  const [startingBalance, setStartingBalance] = useState(50000);
  const [riskPerTrade, setRiskPerTrade] = useState(500);

  const allFirms = firms.kind === "data" ? firms.data : [];

  // Default first firm and reflect its account size into the inputs
  useEffect(() => {
    if (firmId === "" && allFirms.length > 0) {
      setFirmId(allFirms[0].profile_id);
      setAccountSize(allFirms[0].account_size);
      setStartingBalance(allFirms[0].account_size);
    }
  }, [allFirms, firmId]);

  const canSubmit = name.trim().length > 0 && firmId !== "" && picks.length > 0;

  async function submit() {
    if (!canSubmit)
      throw new Error("Pick a name, firm, and at least one backtest.");
    const payload = {
      name: name.trim(),
      firm_profile_id: firmId,
      selected_backtest_ids: picks,
      sampling_mode: samplingMode,
      risk_mode: riskMode,
      simulation_count: simulationCount,
      account_size: accountSize,
      starting_balance: startingBalance,
      risk_per_trade: riskPerTrade,
    };
    const r = await fetch("/api/prop-firm/simulations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      let msg = `${r.status} ${r.statusText}`;
      try {
        const j = (await r.json()) as { detail?: string };
        if (j.detail) msg = j.detail;
      } catch {
        /* ignore */
      }
      throw new Error(msg);
    }
    const created = (await r.json()) as { id: number };
    router.push(`/prop-firm/runs/${created.id}`);
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <PageHeader
        eyebrow="NEW · PROP FIRM SIMULATION"
        title="New simulation"
        sub="Configure a Monte Carlo prop-firm simulation against selected backtests. Synchronous — takes seconds to ~1 minute, then redirects to the run detail."
      />

      <Card className="mt-2">
        <CardHead title="Configuration" />
        <div className="grid gap-5 px-5 py-5">
          <Field label="Name" hint="A short label for the run.">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              placeholder="e.g. fractal_amd_q1_topstepX"
              className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
            />
          </Field>

          <Field
            label="Firm rule profile"
            hint={
              firms.kind === "loading"
                ? "loading firms…"
                : firms.kind === "error"
                  ? `firms unavailable: ${firms.message}`
                  : `${allFirms.length} active`
            }
          >
            <select
              value={firmId}
              onChange={(e) => {
                const id = e.target.value;
                setFirmId(id);
                const f = allFirms.find((x) => x.profile_id === id);
                if (f) {
                  setAccountSize(f.account_size);
                  setStartingBalance(f.account_size);
                }
              }}
              className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
            >
              <option value="">— select —</option>
              {allFirms.map((f) => (
                <option key={f.profile_id} value={f.profile_id}>
                  {f.firm_name} · {f.account_name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Backtests in pool" hint={`${picks.length} selected`}>
            <RunPicker
              multi
              value={picks}
              onChange={(ids) => setPicks(ids as number[])}
              max={20}
              placeholder="Add backtests…"
            />
          </Field>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Field label="Sampling mode">
              <select
                value={samplingMode}
                onChange={(e) =>
                  setSamplingMode(e.target.value as SamplingMode)
                }
                className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
              >
                {SAMPLING_MODES.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
              <span className="text-[10.5px] text-ink-3">
                {SAMPLING_MODES.find((m) => m.id === samplingMode)?.help}
              </span>
            </Field>
            <Field label="Risk mode">
              <select
                value={riskMode}
                onChange={(e) => setRiskMode(e.target.value as RiskMode)}
                className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
              >
                {RISK_MODES.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Field label="Account size ($)">
              <input
                type="number"
                min={1}
                value={accountSize}
                onChange={(e) =>
                  setAccountSize(parseInt(e.target.value, 10) || 0)
                }
                className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
              />
            </Field>
            <Field label="Starting balance ($)">
              <input
                type="number"
                min={0}
                value={startingBalance}
                onChange={(e) =>
                  setStartingBalance(parseInt(e.target.value, 10) || 0)
                }
                className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
              />
            </Field>
            <Field label="Risk per trade ($)">
              <input
                type="number"
                min={1}
                value={riskPerTrade}
                onChange={(e) =>
                  setRiskPerTrade(parseInt(e.target.value, 10) || 0)
                }
                className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
              />
            </Field>
          </div>

          <Field label="Number of simulation paths">
            <input
              type="number"
              min={1}
              max={100000}
              step={500}
              value={simulationCount}
              onChange={(e) =>
                setSimulationCount(parseInt(e.target.value, 10) || 1)
              }
              className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
            />
          </Field>

          <div className="flex items-center justify-end gap-2 border-t border-line pt-4">
            <button
              type="button"
              className="btn"
              onClick={() => router.push("/prop-firm")}
            >
              Cancel
            </button>
            <AsyncButton
              onClick={submit}
              variant="primary"
              disabled={!canSubmit}
            >
              Run simulation
            </AsyncButton>
          </div>
        </div>
      </Card>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="grid gap-1.5">
      <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      {children}
      {hint && <span className="text-[10.5px] text-ink-3">{hint}</span>}
    </label>
  );
}

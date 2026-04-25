import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import NewSimulationWorkflow from "@/components/prop-simulator/new/NewSimulationWorkflow";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import type {
  FirmRuleProfile,
  PoolBacktestSummary,
} from "@/lib/prop-simulator/types";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type Preset = components["schemas"]["PropFirmPresetRead"];

export const dynamic = "force-dynamic";

export default async function NewSimulationPage() {
  // Fetch real backtests + firm presets so the wizard's pickers show
  // real data the backend can resolve. Wizard falls back to its mocks
  // when these are empty.
  const [runs, presets] = await Promise.all([
    apiGet<BacktestRun[]>("/api/backtests").catch(() => [] as BacktestRun[]),
    apiGet<Preset[]>("/api/prop-firm/presets").catch(() => [] as Preset[]),
  ]);
  const firms: FirmRuleProfile[] = presets.map((p) => ({
    profile_id: p.key,
    firm_name: p.name.split("-")[0].trim() || p.name,
    account_name: p.name,
    account_size: p.starting_balance,
    phase_type: "evaluation",
    profit_target: p.profit_target,
    max_drawdown: p.max_drawdown,
    daily_loss_limit: p.daily_loss_limit,
    trailing_drawdown_enabled: p.trailing_drawdown,
    trailing_drawdown_type: p.trailing_drawdown ? "intraday" : "none",
    trailing_drawdown_stop_level: null,
    minimum_trading_days: null,
    maximum_trading_days: null,
    max_contracts: p.max_trades_per_day,
    scaling_plan_enabled: false,
    scaling_plan_rules: [],
    consistency_rule_enabled: p.consistency_pct !== null,
    consistency_rule_type:
      p.consistency_pct !== null ? "best_day_pct_of_total" : "none",
    consistency_rule_value: p.consistency_pct,
    news_trading_allowed: true,
    overnight_holding_allowed: false,
    weekend_holding_allowed: false,
    copy_trading_allowed: true,
    payout_min_days: null,
    payout_min_profit: null,
    payout_cap: null,
    payout_split: 0.9,
    first_payout_rules: null,
    recurring_payout_rules: null,
    eval_fee: 0,
    activation_fee: 0,
    reset_fee: 0,
    monthly_fee: 0,
    refund_rules: null,
    rule_source_url: null,
    rule_last_verified_at: null,
    verification_status: "demo",
    notes: p.notes,
    version: 1,
    active: true,
  }));
  const pool: PoolBacktestSummary[] = runs.map((run) => ({
    backtest_id: run.id,
    strategy_id: run.strategy_version_id,
    strategy_name: run.name ?? `Backtest ${run.id}`,
    strategy_version: "",
    symbol: run.symbol,
    market: "futures",
    timeframe: run.timeframe ?? "1m",
    start_date: run.start_ts ? run.start_ts.slice(0, 10) : "",
    end_date: run.end_ts ? run.end_ts.slice(0, 10) : "",
    data_source: run.import_source ?? run.source ?? "",
    commission_model: "default",
    slippage_model: "default",
    initial_balance: 25_000,
    confidence_score: 50,
    trade_count: 0,
    day_count: 0,
  }));

  return (
    <div className="pb-10">
      <div className="px-6 pt-4">
        <Link
          href="/prop-simulator"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← Simulator
        </Link>
      </div>
      <PageHeader
        title="New simulation"
        description="Assemble a Monte Carlo prop-firm simulation from imported backtests, firm rules, sampling mode, risk model, and personal rules."
        meta={pool.length > 0 ? "live data" : "no real backtests yet"}
      />
      <div className="px-6">
        <NewSimulationWorkflow pool={pool} firms={firms} />
      </div>
    </div>
  );
}

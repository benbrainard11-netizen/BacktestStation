// ============================================================================
// Hand-authored types (legacy). Mirror the FastAPI Pydantic shapes by
// convention — no generator enforces agreement.
//
// Prefer the auto-generated shapes in `./generated.ts` for NEW code:
//
//   import type { components } from "@/lib/api/generated";
//   type Note = components["schemas"]["NoteRead"];
//
// Migrate existing consumers of this file to generated types over time, one
// call site at a time, so the legacy file can eventually be deleted. Do not
// add new interfaces here — edit a Pydantic schema and run
// `scripts/generate-types.sh` instead.
// ============================================================================

export interface ImportBacktestResponse {
  backtest_id: number;
  strategy_id: number;
  strategy_version_id: number;
  trades_imported: number;
  equity_points_imported: number;
  metrics_imported: boolean;
  config_imported: boolean;
}

export interface BacktestRun {
  id: number;
  strategy_version_id: number;
  name: string | null;
  symbol: string;
  timeframe: string | null;
  session_label: string | null;
  start_ts: string | null;
  end_ts: string | null;
  import_source: string | null;
  status: string;
  created_at: string;
}

export interface StrategyVersion {
  id: number;
  strategy_id: number;
  version: string;
  entry_md: string | null;
  exit_md: string | null;
  risk_md: string | null;
  git_commit_sha: string | null;
  created_at: string;
}

export interface Strategy {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  status: string;
  tags: string[] | null;
  created_at: string;
  versions: StrategyVersion[];
}

export interface RunMetrics {
  id: number;
  backtest_run_id: number;
  net_pnl: number | null;
  net_r: number | null;
  win_rate: number | null;
  profit_factor: number | null;
  max_drawdown: number | null;
  avg_r: number | null;
  avg_win: number | null;
  avg_loss: number | null;
  trade_count: number | null;
  longest_losing_streak: number | null;
  best_trade: number | null;
  worst_trade: number | null;
}

export interface Trade {
  id: number;
  backtest_run_id: number;
  entry_ts: string;
  exit_ts: string | null;
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number | null;
  stop_price: number | null;
  target_price: number | null;
  size: number;
  pnl: number | null;
  r_multiple: number | null;
  exit_reason: string | null;
  tags: string[] | null;
}

export interface EquityPoint {
  id: number;
  backtest_run_id: number;
  ts: string;
  equity: number;
  drawdown: number | null;
}

export interface Note {
  id: number;
  backtest_run_id: number | null;
  trade_id: number | null;
  body: string;
  created_at: string;
}

export interface NoteCreate {
  body: string;
  backtest_run_id?: number | null;
  trade_id?: number | null;
}

export interface BackendErrorBody {
  detail?: string;
}

export interface LiveMonitorStatus {
  source_path: string;
  source_exists: boolean;
  strategy_status: string;
  last_heartbeat: string | null;
  current_symbol: string | null;
  current_session: string | null;
  today_pnl: number | null;
  today_r: number | null;
  trades_today: number | null;
  last_signal: Record<string, unknown> | string | null;
  last_error: string | null;
  raw: Record<string, unknown> | null;
}

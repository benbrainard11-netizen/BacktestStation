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

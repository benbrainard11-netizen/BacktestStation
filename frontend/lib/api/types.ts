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

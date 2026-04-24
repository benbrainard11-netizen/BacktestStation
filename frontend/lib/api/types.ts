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

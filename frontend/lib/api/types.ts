export interface ImportBacktestResponse {
  backtest_id: number;
  strategy_id: number;
  strategy_version_id: number;
  trades_imported: number;
  equity_points_imported: number;
  metrics_imported: boolean;
  config_imported: boolean;
}

export interface BackendErrorBody {
  detail?: string;
}

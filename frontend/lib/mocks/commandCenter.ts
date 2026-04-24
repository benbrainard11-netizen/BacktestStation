// =============================================================================
// MOCK DATA for the Command Center page.
//
// These constants are layout-only placeholders so the UI can be designed and
// reviewed before real API endpoints exist. Replace every export in this file
// with real data fetched from the backend once Phase 1 importer + endpoints
// land. Nothing in app/components should reach outside this file for sample
// values — if you find yourself inlining a number, add it here instead so the
// mock surface stays explicit.
// =============================================================================

export type Tone = "positive" | "negative" | "neutral";

export interface MockKpi {
  key: string;
  label: string;
  value: string;
  valueTone: Tone;
  delta: string;
  deltaTone: Tone;
}

export const MOCK_KPIS: MockKpi[] = [
  { key: "net_pnl",      label: "Net PnL",              value: "$24,310.50", valueTone: "positive", delta: "+2.43% vs prev 30d", deltaTone: "positive" },
  { key: "net_r",        label: "Net R",                value: "+132.47",    valueTone: "positive", delta: "+11.28 vs prev 30d", deltaTone: "positive" },
  { key: "win_rate",     label: "Win Rate",             value: "53.21%",     valueTone: "positive", delta: "+2.14% vs prev 30d", deltaTone: "positive" },
  { key: "profit_factor",label: "Profit Factor",        value: "1.78",       valueTone: "neutral",  delta: "+0.18 vs prev 30d",  deltaTone: "positive" },
  { key: "max_dd",       label: "Max Drawdown",         value: "-8.37%",     valueTone: "negative", delta: "-1.21% vs prev 30d", deltaTone: "negative" },
  { key: "trade_count",  label: "Trade Count",          value: "1,248",      valueTone: "neutral",  delta: "+156 vs prev 30d",   deltaTone: "positive" },
  { key: "avg_r",        label: "Avg R",                value: "+0.106",     valueTone: "positive", delta: "+0.009 vs prev 30d", deltaTone: "positive" },
  { key: "loss_streak",  label: "Longest Losing Streak",value: "7",          valueTone: "neutral",  delta: "-2 vs prev 30d",     deltaTone: "positive" },
];

export interface MockPhase {
  key: string;
  label: string;
  status: "complete" | "active" | "pending";
  detail: string;
}

export const MOCK_PHASES: MockPhase[] = [
  { key: "0", label: "Phase 0", status: "complete", detail: "Environment Ready" },
  { key: "1", label: "Phase 1", status: "active", detail: "Data Import & Parsing" },
  { key: "2", label: "Phase 2", status: "pending", detail: "Backtest & Validate" },
  { key: "3", label: "Phase 3", status: "pending", detail: "Analyze & Deploy" },
];

export interface MockBacktestRow {
  run: string;
  strategy: string;
  symbol: string;
  trades: number;
  netR: number;
  pf: number;
  maxDd: number;
  importedAt: string;
  status: "Complete" | "Running" | "Failed";
}

export const MOCK_BACKTESTS: MockBacktestRow[] = [
  { run: "BT-2025-05-19-07", strategy: "ORB Fade v2.1",        symbol: "ES",  trades: 186, netR:  18.24, pf: 1.92, maxDd:  -6.21, importedAt: "14:12:03", status: "Complete" },
  { run: "BT-2025-05-19-06", strategy: "Opening Drive v1.3",   symbol: "NQ",  trades: 214, netR:  24.57, pf: 1.88, maxDd:  -5.83, importedAt: "13:47:19", status: "Complete" },
  { run: "BT-2025-05-19-05", strategy: "Micro Pullback v1.0",  symbol: "MES", trades: 312, netR:  15.31, pf: 1.56, maxDd:  -7.14, importedAt: "12:58:44", status: "Complete" },
  { run: "BT-2025-05-19-04", strategy: "VWAP Mean Rev v2.2",   symbol: "MNQ", trades: 167, netR:  -3.21, pf: 0.76, maxDd: -11.92, importedAt: "12:21:11", status: "Complete" },
  { run: "BT-2025-05-19-03", strategy: "Range Expansion v1.4", symbol: "ES",  trades: 198, netR:   9.87, pf: 1.41, maxDd:  -4.32, importedAt: "11:35:02", status: "Complete" },
  { run: "BT-2025-05-19-02", strategy: "Opening Drive v1.2",   symbol: "YM",  trades: 143, netR:   6.42, pf: 1.27, maxDd:  -5.07, importedAt: "10:48:37", status: "Complete" },
  { run: "BT-2025-05-19-01", strategy: "ORB Fade v2.0",        symbol: "NQ",  trades: 175, netR:  12.03, pf: 1.63, maxDd:  -6.66, importedAt: "09:56:18", status: "Complete" },
];

export const MOCK_BACKTESTS_TOTAL = 128;

export interface MockSystemStatusRow {
  key: string;
  label: string;
  value: string;
  tone?: "positive" | "muted";
}

export const MOCK_SYSTEM_STATUS: MockSystemStatusRow[] = [
  { key: "latest_import", label: "Latest Import", value: "May 19, 2025 14:12:03" },
  { key: "latest_signal", label: "Latest Signal", value: "May 19, 2025 14:37:58" },
  { key: "live_monitor", label: "Live Monitor", value: "Running", tone: "positive" },
  { key: "imported_files", label: "Imported Files (Today)", value: "29" },
  { key: "rows_imported", label: "Rows Imported (Today)", value: "1,482,931" },
  { key: "data_quality", label: "Data Quality", value: "99.68%", tone: "positive" },
  { key: "disk_usage", label: "Disk Usage", value: "452 GB / 1.00 TB" },
  { key: "uptime", label: "Uptime", value: "2d 14h 38m" },
];

export const MOCK_DISK_PERCENT = 45.2;

export interface MockActivityRow {
  time: string;
  kind: "signal" | "import" | "backtest";
  text: string;
  meta?: string;
}

export const MOCK_ACTIVITY: MockActivityRow[] = [
  { time: "14:37:58", kind: "signal",   text: "New signal generated", meta: "ORB Fade v2.1 (ES)" },
  { time: "14:12:03", kind: "import",   text: "Import completed",     meta: "1,248,921 rows" },
  { time: "13:47:19", kind: "backtest", text: "Backtest completed",   meta: "Opening Drive v1.3 (NQ)" },
  { time: "12:58:44", kind: "import",   text: "Import completed",     meta: "1,153,442 rows" },
  { time: "12:21:11", kind: "backtest", text: "Backtest completed",   meta: "VWAP Mean Rev v2.2 (MNQ)" },
];

export const MOCK_EQUITY = {
  currentUSD: 1_024_310.5,
  currentUSDLabel: "$1,024,310.50",
  netR: 132.47,
  netRLabel: "+132.47",
  windowLabel: "30D",
  windowDeltaLabel: "+2.43%",
  // Normalized points for a 30-day chart. Values roughly 900K → 1.025M USD.
  // Hand-authored so the curve looks like a realistic equity drift with
  // drawdowns and recoveries.
  series: [
    900_210, 905_430, 914_820, 911_300, 920_110, 927_880, 932_440, 928_700,
    939_120, 946_880, 951_020, 947_330, 956_110, 964_580, 970_340, 962_110,
    971_880, 984_310, 990_120, 983_540, 994_780, 1_001_220, 1_008_330, 999_870,
    1_005_410, 1_013_220, 1_019_110, 1_015_380, 1_021_440, 1_024_310.5,
  ],
  xLabels: ["Apr 20", "Apr 27", "May 4", "May 11", "May 18"],
};

export const MOCK_SYSTEM_SPARKLINES = {
  cpu: { value: "14%", series: [12, 14, 11, 15, 18, 13, 10, 12, 14, 16, 17, 14] },
  mem: { value: "38%", series: [36, 37, 38, 39, 38, 37, 39, 40, 38, 37, 38, 38] },
  disk: { value: "22%", series: [21, 22, 22, 23, 22, 22, 21, 22, 23, 22, 22, 22] },
  buildDate: "2025.05.19",
  version: "0.1.0",
};

export const MOCK_TOP_BAR = {
  apiLabel: "API",
  apiValue: "ONLINE",
  dbLabel: "DB",
  dbValue: "READY",
};

export interface MockQuickTile {
  href: string;
  label: string;
  iconKey:
    | "import"
    | "strategies"
    | "backtests"
    | "replay"
    | "monitor"
    | "journal";
}

export const MOCK_QUICK_TILES: MockQuickTile[] = [
  { href: "/import",      label: "Import Results",  iconKey: "import" },
  { href: "/strategies",  label: "Strategy Library", iconKey: "strategies" },
  { href: "/backtests",   label: "Backtest Runs",   iconKey: "backtests" },
  { href: "/replay",      label: "Replay Engine",   iconKey: "replay" },
  { href: "/monitor",     label: "Live Monitor",    iconKey: "monitor" },
  { href: "/journal",     label: "Journal",         iconKey: "journal" },
];

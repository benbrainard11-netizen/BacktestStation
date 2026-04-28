import Panel from "@/components/Panel";
import type {
 FirmRuleProfile,
 PoolBacktestSummary,
 SimulationRunConfig,
} from "@/lib/prop-simulator/types";
import { samplingModeLabel } from "@/lib/prop-simulator/format";

interface RunSummaryPanelProps {
 config: SimulationRunConfig;
 firm: FirmRuleProfile;
 pool: PoolBacktestSummary[];
}

function Row({ label, value }: { label: string; value: string }) {
 return (
 <div className="flex items-center justify-between border-b border-border py-1.5 last:border-b-0">
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <span className="tabular-nums text-xs tabular-nums text-text">
 {value}
 </span>
 </div>
 );
}

export default function RunSummaryPanel({
 config,
 firm,
 pool,
}: RunSummaryPanelProps) {
 const totalTrades = pool.reduce((sum, bt) => sum + bt.trade_count, 0);
 const totalDays = pool.reduce((sum, bt) => sum + bt.day_count, 0);
 const risk =
 config.risk_mode === "risk_sweep"
 ? `sweep · ${(config.risk_sweep_values ?? []).join(", ")}`
 : config.risk_per_trade !== null
 ? `$${config.risk_per_trade} / trade`
 : "—";

 return (
 <Panel title="Run summary" meta={config.simulation_id}>
 <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
 <div>
 <p className="mb-2 tabular-nums text-[10px] text-text-mute">
 Inputs
 </p>
 <Row label="Firm" value={`${firm.firm_name} · ${firm.account_name}`} />
 <Row
 label="Account"
 value={`$${firm.account_size.toLocaleString()}`}
 />
 <Row label="Phase mode" value={config.phase_mode} />
 <Row
 label="Backtests"
 value={`${pool.length} · ${totalTrades.toLocaleString()} trades · ${totalDays} days`}
 />
 <Row
 label="Pool strategies"
 value={
 pool.map((bt) => bt.strategy_name)
 .filter((v, i, a) => a.indexOf(v) === i)
 .join(", ") || "—"
 }
 />
 </div>
 <div>
 <p className="mb-2 tabular-nums text-[10px] text-text-mute">
 Simulation
 </p>
 <Row
 label="Sampling"
 value={samplingModeLabel(config.sampling_mode)}
 />
 <Row
 label="Sequences"
 value={config.simulation_count.toLocaleString()}
 />
 <Row
 label="Replacement"
 value={config.use_replacement ? "with" : "without"}
 />
 <Row label="Random seed" value={String(config.random_seed)} />
 <Row label="Risk" value={risk} />
 <Row
 label="Fees enabled"
 value={config.fees_enabled ? "on" : "off"}
 />
 </div>
 </div>
 </Panel>
 );
}

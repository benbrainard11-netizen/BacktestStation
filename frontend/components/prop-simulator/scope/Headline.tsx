// Tearsheet headline — asymmetric 5/7 split. Left column carries the
// run identity + supporting facts; right column carries the dominant
// verdict number set massive.

import { cn } from "@/lib/utils";
import type {
 ConfidenceInterval,
 FirmRuleProfile,
 SimulationRunConfig,
 SimulatorConfidenceScore,
} from "@/lib/prop-simulator/types";
import {
 confidenceLabelText,
 formatCurrencySigned,
 samplingModeLabel,
} from "@/lib/prop-simulator/format";

interface HeadlineProps {
 config: SimulationRunConfig;
 firm: FirmRuleProfile;
 evAfterFees: ConfidenceInterval;
 passRate: ConfidenceInterval;
 confidence: SimulatorConfidenceScore;
}

function StatRule({
 label,
 value,
 tone,
}: {
 label: string;
 value: string;
 tone?: "positive" | "negative" | "neutral";
}) {
 const toneClass =
 tone === "positive"
 ? "text-pos"
 : tone === "negative"
 ? "text-neg"
 : "text-text";
 return (
 <div className="flex items-baseline justify-between gap-3 border-b border-border py-2">
 <span className="text-[10px] tracking-[0.32em] text-text-mute">
 {label}
 </span>
 <span className={cn("font-light tabular-nums", toneClass)}>{value}</span>
 </div>
 );
}

export default function Headline({
 config,
 firm,
 evAfterFees,
 passRate,
 confidence,
}: HeadlineProps) {
 const tone =
 evAfterFees.value > 0
 ? "positive"
 : evAfterFees.value < 0
 ? "negative"
 : "neutral";
 const toneClass =
 tone === "positive"
 ? "text-pos"
 : tone === "negative"
 ? "text-neg"
 : "text-text";

 return (
 <section className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-12">
 <div className="flex flex-col gap-6 lg:col-span-5">
 <div className="flex flex-col gap-1.5">
 <span className="text-[10px] tracking-[0.5em] text-text-mute">
 Run dossier
 </span>
 <h1 className="text-3xl font-light leading-tight tracking-tight text-text sm:text-4xl">
 {firm.firm_name}
 <span className="text-text-mute"> · </span>
 <span className="font-extralight">
 ${(firm.account_size / 1000).toFixed(0)}K
 </span>
 </h1>
 <p className="font-light text-text-dim">
 {samplingModeLabel(config.sampling_mode)}
 <span className="text-text-mute"> · </span>
 {config.risk_per_trade !== null
 ? `$${config.risk_per_trade}/trade`
 : "risk sweep"}
 <span className="text-text-mute"> · </span>
 {config.simulation_count.toLocaleString()} sequences
 </p>
 </div>

 <div className="flex flex-col">
 <StatRule
 label="Pass probability"
 value={`${(passRate.value * 100).toFixed(1)}%`}
 />
 <StatRule
 label="95% CI · pass"
 value={`${(passRate.low * 100).toFixed(1)} – ${(passRate.high * 100).toFixed(1)}%`}
 />
 <StatRule
 label="Confidence"
 value={`${confidence.overall} · ${confidenceLabelText(confidence.label)}`}
 />
 <StatRule label="Phase mode" value={config.phase_mode.replace(/_/g, " ")} />
 <StatRule label="Random seed" value={String(config.random_seed)} />
 </div>
 </div>

 <div className="relative flex flex-col justify-end lg:col-span-7">
 <span className="absolute -top-4 left-0 text-[10px] tracking-[0.5em] text-text-mute">
 Verdict · expected value after fees
 </span>
 <p
 className={cn(
 "font-extralight tabular-nums leading-[0.85] tracking-[-0.04em]",
 toneClass,
 )}
 style={{ fontSize: "clamp(5rem, 13vw, 11rem)" }}
 >
 {formatCurrencySigned(evAfterFees.value)}
 </p>
 <p className="mt-4 flex flex-wrap items-baseline gap-x-4 gap-y-1 font-light text-text-dim">
 <span className="text-[10px] tracking-[0.32em] text-text-mute">
 95% CI
 </span>
 <span className="tabular-nums">
 {formatCurrencySigned(evAfterFees.low)}
 </span>
 <span className="text-text-mute">—</span>
 <span className="tabular-nums">
 {formatCurrencySigned(evAfterFees.high)}
 </span>
 </p>
 </div>
 </section>
 );
}

import ConfidenceScorePanel from "@/components/prop-simulator/shared/ConfidenceScorePanel";
import type { BacktestConfidenceScore } from "@/lib/prop-simulator/types";

interface BacktestConfidencePanelProps {
  confidence: BacktestConfidenceScore;
}

function subscoreRows(confidence: BacktestConfidenceScore) {
  const s = confidence.subscores;
  return [
    { label: "Sample size", score: s.sample_size },
    { label: "Data quality", score: s.data_quality },
    { label: "Execution realism", score: s.execution_realism },
    { label: "Regime coverage", score: s.regime_coverage },
    { label: "Out-of-sample", score: s.out_of_sample },
    { label: "Cost sensitivity", score: s.cost_sensitivity },
  ];
}

const RISK_LABEL: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

export default function BacktestConfidencePanel({
  confidence,
}: BacktestConfidencePanelProps) {
  return (
    <div className="flex flex-col gap-4">
      <ConfidenceScorePanel
        overall={confidence.overall}
        label={confidence.label}
        subscoreRows={subscoreRows(confidence)}
        weaknesses={confidence.weaknesses}
      />
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div className="flex items-center justify-between border border-zinc-800 bg-zinc-950 px-3 py-2">
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Overfit risk
          </span>
          <span className="font-mono text-xs text-zinc-200">
            {RISK_LABEL[confidence.overfit_risk] ?? confidence.overfit_risk}
          </span>
        </div>
        <div className="flex items-center justify-between border border-zinc-800 bg-zinc-950 px-3 py-2">
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Cost sensitivity
          </span>
          <span className="font-mono text-xs text-zinc-200">
            {RISK_LABEL[confidence.cost_sensitivity] ?? confidence.cost_sensitivity}
          </span>
        </div>
      </div>
    </div>
  );
}

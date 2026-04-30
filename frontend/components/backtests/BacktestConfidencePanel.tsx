import { cn } from "@/lib/utils";
import type { components } from "@/lib/api/generated";

type AutopsyReport = components["schemas"]["AutopsyReportRead"];
type DataQualityReport = components["schemas"]["DataQualityReportRead"];

interface BacktestConfidencePanelProps {
  autopsy: AutopsyReport | null;
  dataQuality: DataQualityReport | null;
  tradeCount: number;
}

const REC_LABEL: Record<string, string> = {
  not_ready: "not ready",
  forward_test_only: "forward test only",
  small_size: "small size ok",
  validated: "validated",
};

const REC_TONE: Record<string, "pos" | "neg" | "warn" | "neutral"> = {
  not_ready: "neg",
  forward_test_only: "warn",
  small_size: "neutral",
  validated: "pos",
};

/**
 * Slim "is this backtest trustworthy" headline. Real values only — pulls
 * edge confidence from /api/backtests/{id}/autopsy and reliability from
 * /data-quality. Sample-size threshold is computed from trade count.
 *
 * The deeper bullet-point breakdown (strengths/weaknesses/conditions) lives
 * in the AutopsyPanel below this card.
 */
export default function BacktestConfidencePanel({
  autopsy,
  dataQuality,
  tradeCount,
}: BacktestConfidencePanelProps) {
  const edge = autopsy?.edge_confidence ?? null;
  const verdict = autopsy?.overall_verdict ?? null;
  const rec = autopsy?.go_live_recommendation ?? null;
  const reliability = dataQuality?.reliability_score ?? null;
  const sample = sampleAdequacy(tradeCount);
  const recTone = rec ? REC_TONE[rec] ?? "neutral" : "neutral";
  const recText = rec ? REC_LABEL[rec] ?? rec : "—";

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-[auto_1fr] items-center gap-6">
        <div className="text-center">
          <p className="m-0 text-xs text-text-mute">edge confidence</p>
          <p
            className={cn(
              "m-0 mt-1 text-[40px] tabular-nums leading-none",
              edge === null
                ? "text-text-mute"
                : edge >= 70
                  ? "text-pos"
                  : edge >= 50
                    ? "text-warn"
                    : "text-neg",
            )}
          >
            {edge ?? "—"}
            <span className="text-base text-text-mute">/100</span>
          </p>
        </div>
        <div className="flex flex-col gap-1">
          <span
            className={cn(
              "inline-flex w-fit items-center rounded border px-2 py-[2px] text-xs",
              recTone === "pos" && "border-pos/30 bg-pos/10 text-pos",
              recTone === "neg" && "border-neg/30 bg-neg/10 text-neg",
              recTone === "warn" && "border-warn/30 bg-warn/10 text-warn",
              recTone === "neutral" && "border-border bg-surface-alt text-text-dim",
            )}
          >
            {recText}
          </span>
          <p className="m-0 text-[13px] leading-relaxed text-text-dim">
            {verdict ?? "Autopsy not generated for this run."}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 border-t border-border pt-3">
        <SubStat
          label="Sample size"
          value={`${tradeCount} trades`}
          tone={sample.tone}
          hint={sample.hint}
        />
        <SubStat
          label="Data quality"
          value={
            reliability === null ? "—" : `${reliability}/100`
          }
          tone={
            reliability === null
              ? "neutral"
              : reliability >= 80
                ? "pos"
                : reliability >= 60
                  ? "warn"
                  : "neg"
          }
          hint={reliability === null ? "no report" : "from /data-quality"}
        />
        <SubStat
          label="Out-of-sample"
          value="—"
          tone="neutral"
          hint="not yet wired"
        />
      </div>
    </div>
  );
}

function SubStat({
  label,
  value,
  tone,
  hint,
}: {
  label: string;
  value: string;
  tone: "pos" | "neg" | "warn" | "neutral";
  hint: string;
}) {
  return (
    <div className="rounded-md border border-border bg-surface-alt px-3 py-2">
      <p className="m-0 text-xs text-text-mute">{label}</p>
      <p
        className={cn(
          "m-0 mt-1 text-[14px] tabular-nums leading-none",
          tone === "pos" && "text-pos",
          tone === "neg" && "text-neg",
          tone === "warn" && "text-warn",
          tone === "neutral" && "text-text",
        )}
      >
        {value}
      </p>
      <p className="m-0 mt-1 text-xs text-text-mute">{hint}</p>
    </div>
  );
}

function sampleAdequacy(n: number): {
  tone: "pos" | "neg" | "warn" | "neutral";
  hint: string;
} {
  if (n === 0) return { tone: "neg", hint: "no trades" };
  if (n < 30) return { tone: "neg", hint: "small (<30)" };
  if (n < 100) return { tone: "warn", hint: "thin (30–100)" };
  if (n < 300) return { tone: "neutral", hint: "ok (100–300)" };
  return { tone: "pos", hint: "good (300+)" };
}

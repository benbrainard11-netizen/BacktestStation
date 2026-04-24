import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Report = components["schemas"]["AutopsyReportRead"];
type Slice = components["schemas"]["AutopsyConditionSlice"];

interface AutopsyPanelProps {
  report: Report | null;
  loadError: string | null;
}

const RECOMMENDATION_LABEL: Record<string, string> = {
  not_ready: "NOT READY",
  forward_test_only: "FORWARD TEST ONLY",
  small_size: "SMALL SIZE OK",
  validated: "VALIDATED",
};

const RECOMMENDATION_STYLE: Record<string, string> = {
  not_ready: "border-rose-900 bg-rose-950/40 text-rose-300",
  forward_test_only: "border-amber-900 bg-amber-950/30 text-amber-200",
  small_size: "border-sky-900 bg-sky-950/40 text-sky-200",
  validated: "border-emerald-900 bg-emerald-950/40 text-emerald-300",
};

export default function AutopsyPanel({ report, loadError }: AutopsyPanelProps) {
  if (loadError !== null) {
    return (
      <div className="border border-rose-900 bg-rose-950/40 p-3 font-mono text-xs text-zinc-200">
        <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
          Autopsy unavailable
        </p>
        <p className="mt-1">{loadError}</p>
      </div>
    );
  }
  if (report === null) {
    return (
      <p className="font-mono text-xs text-zinc-500">Autopsy not generated.</p>
    );
  }

  const recStyle =
    RECOMMENDATION_STYLE[report.go_live_recommendation] ??
    RECOMMENDATION_STYLE.not_ready;
  const recLabel =
    RECOMMENDATION_LABEL[report.go_live_recommendation] ??
    report.go_live_recommendation;

  return (
    <div className="flex flex-col gap-4">
      <div className={cn("border p-3", recStyle)}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest">
              {recLabel}
            </p>
            <p className="mt-1 font-mono text-xs text-zinc-100">
              {report.overall_verdict}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
              Edge confidence
            </p>
            <p className="font-mono text-3xl leading-none text-zinc-100">
              {report.edge_confidence}
              <span className="text-zinc-500">/100</span>
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <BulletList
          title="Strengths"
          color="text-emerald-300"
          items={report.strengths}
          fallback="None identified by the current rules."
        />
        <BulletList
          title="Weaknesses"
          color="text-rose-300"
          items={report.weaknesses}
          fallback="None identified."
        />
        <BulletList
          title="Overfitting warnings"
          color="text-amber-300"
          items={report.overfitting_warnings}
          fallback="No overfitting flags triggered."
        />
        <BulletList
          title="Risk notes"
          color="text-sky-300"
          items={report.risk_notes}
          fallback="Nothing flagged beyond the drawdown stats."
        />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <ConditionList
          title="Best conditions"
          color="text-emerald-300"
          slices={report.best_conditions}
        />
        <ConditionList
          title="Worst conditions"
          color="text-rose-300"
          slices={report.worst_conditions}
        />
      </div>

      <div className="border border-zinc-800 bg-zinc-950 p-3">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Suggested next test
        </p>
        <p className="mt-1 text-sm text-zinc-200">{report.suggested_next_test}</p>
      </div>
    </div>
  );
}

function BulletList({
  title,
  color,
  items,
  fallback,
}: {
  title: string;
  color: string;
  items: string[];
  fallback: string;
}) {
  return (
    <div className="border border-zinc-800 bg-zinc-950 p-3">
      <p className={cn("font-mono text-[10px] uppercase tracking-widest", color)}>
        {title}
      </p>
      {items.length === 0 ? (
        <p className="mt-2 font-mono text-xs text-zinc-500">{fallback}</p>
      ) : (
        <ul className="mt-2 flex flex-col gap-1 font-mono text-xs text-zinc-300">
          {items.map((item, i) => (
            <li key={i}>· {item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ConditionList({
  title,
  color,
  slices,
}: {
  title: string;
  color: string;
  slices: Slice[];
}) {
  return (
    <div className="border border-zinc-800 bg-zinc-950 p-3">
      <p className={cn("font-mono text-[10px] uppercase tracking-widest", color)}>
        {title}
      </p>
      {slices.length === 0 ? (
        <p className="mt-2 font-mono text-xs text-zinc-500">
          Not enough trades per group (min 5) to slice.
        </p>
      ) : (
        <ul className="mt-2 flex flex-col gap-1 font-mono text-[11px] text-zinc-300">
          {slices.map((slice, i) => (
            <li key={i} className="flex items-center justify-between gap-3">
              <span className="text-zinc-400">{slice.label}</span>
              <span className="shrink-0">
                <span
                  className={
                    slice.net_r > 0
                      ? "text-emerald-400"
                      : slice.net_r < 0
                        ? "text-rose-400"
                        : "text-zinc-400"
                  }
                >
                  {slice.net_r > 0 ? "+" : ""}
                  {slice.net_r.toFixed(1)}R
                </span>
                <span className="ml-2 text-zinc-600">{slice.trades} trades</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

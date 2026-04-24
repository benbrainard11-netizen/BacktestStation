import { ChevronDown } from "lucide-react";

import { MOCK_EQUITY } from "@/lib/mocks/commandCenter";

const CHART_WIDTH = 600;
const CHART_HEIGHT = 180;
const PADDING_X = 40;
const PADDING_TOP = 8;
const PADDING_BOTTOM = 24;

function buildPath(values: number[]): { line: string; ticks: number[] } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const innerW = CHART_WIDTH - PADDING_X * 2;
  const innerH = CHART_HEIGHT - PADDING_TOP - PADDING_BOTTOM;
  const stepX = innerW / (values.length - 1 || 1);

  const line = values
    .map((v, i) => {
      const x = PADDING_X + i * stepX;
      const y = PADDING_TOP + innerH - ((v - min) / range) * innerH;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");

  // 4 horizontal gridline values, evenly spaced between min and max.
  const ticks = [0, 1, 2, 3].map((i) => min + (range * i) / 3);

  return { line, ticks };
}

function formatTick(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `${Math.round(v / 1_000)}K`;
  return v.toFixed(0);
}

export default function EquitySnapshotPanel() {
  const { line, ticks } = buildPath(MOCK_EQUITY.series);
  const innerH = CHART_HEIGHT - PADDING_TOP - PADDING_BOTTOM;

  return (
    <section className="flex flex-col border border-zinc-800 bg-zinc-950">
      <header className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
        <h3 className="font-mono text-[11px] uppercase tracking-widest text-zinc-300">
          Equity Snapshot (All Strategies)
        </h3>
        <button
          type="button"
          className="inline-flex h-7 items-center gap-1 rounded-sm border border-zinc-800 bg-zinc-900/60 px-2 font-mono text-[10px] uppercase tracking-widest text-zinc-300 transition-colors hover:border-zinc-700 hover:text-zinc-100"
        >
          {MOCK_EQUITY.windowLabel}
          <ChevronDown className="h-3 w-3" strokeWidth={1.5} aria-hidden="true" />
        </button>
      </header>

      <div className="flex items-start gap-10 px-4 py-4">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Equity
          </p>
          <p className="mt-1 font-mono text-2xl text-zinc-100">
            {MOCK_EQUITY.currentUSDLabel}
          </p>
          <p className="mt-1 font-mono text-[11px] text-emerald-400">
            {MOCK_EQUITY.windowDeltaLabel}
          </p>
        </div>
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Net R
          </p>
          <p className="mt-1 font-mono text-2xl text-emerald-400">
            {MOCK_EQUITY.netRLabel}
          </p>
        </div>
      </div>

      <div className="px-2 pb-4">
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          className="h-44 w-full"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          {/* Horizontal gridlines */}
          {ticks.map((tick, i) => {
            const y = PADDING_TOP + innerH - (i / 3) * innerH;
            return (
              <g key={i}>
                <line
                  x1={PADDING_X}
                  x2={CHART_WIDTH - PADDING_X}
                  y1={y}
                  y2={y}
                  stroke="rgb(39 39 42)"
                  strokeDasharray="2 4"
                  strokeWidth={1}
                />
                <text
                  x={PADDING_X - 6}
                  y={y + 3}
                  textAnchor="end"
                  fontSize={9}
                  fill="rgb(113 113 122)"
                  fontFamily="ui-monospace, monospace"
                >
                  {formatTick(tick)}
                </text>
              </g>
            );
          })}

          {/* X-axis labels */}
          {MOCK_EQUITY.xLabels.map((label, i) => {
            const frac = i / (MOCK_EQUITY.xLabels.length - 1);
            const x = PADDING_X + frac * (CHART_WIDTH - PADDING_X * 2);
            return (
              <text
                key={label}
                x={x}
                y={CHART_HEIGHT - 6}
                textAnchor="middle"
                fontSize={9}
                fill="rgb(113 113 122)"
                fontFamily="ui-monospace, monospace"
              >
                {label}
              </text>
            );
          })}

          {/* Line */}
          <path
            d={line}
            fill="none"
            stroke="rgb(228 228 231)"
            strokeWidth={1.2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </section>
  );
}

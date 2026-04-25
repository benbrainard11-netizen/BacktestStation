// SVG heartbeat trace — a flat baseline with one ECG-style spike that
// scrolls left to right via CSS transform. Pure CSS animation, no JS
// timers. Behind prefers-reduced-motion, the trace becomes static.

import { cn } from "@/lib/utils";

type PulseTone = "live" | "off" | "idle" | "warn";

interface HeartbeatPulseProps {
  tone: PulseTone;
  width?: number;
  height?: number;
  className?: string;
}

const TONE_STROKE: Record<PulseTone, string> = {
  live: "stroke-emerald-400",
  off: "stroke-rose-400",
  idle: "stroke-zinc-500",
  warn: "stroke-amber-400",
};

const TONE_GLOW: Record<PulseTone, string> = {
  live: "drop-shadow-[0_0_6px_rgba(52,211,153,0.45)]",
  off: "drop-shadow-[0_0_6px_rgba(244,63,94,0.45)]",
  idle: "",
  warn: "drop-shadow-[0_0_6px_rgba(251,191,36,0.45)]",
};

// One full ECG segment shape, repeated three times across the path so the
// CSS scroll can loop seamlessly.
function buildTracePath(segmentWidth: number, height: number): string {
  const baseline = height / 2;
  const segment = (offset: number): string => {
    const x = (n: number) => offset + n;
    return [
      `M ${x(0)},${baseline}`,
      // long flat run
      `L ${x(segmentWidth * 0.5)},${baseline}`,
      // tiny p-wave
      `L ${x(segmentWidth * 0.55)},${baseline - 4}`,
      `L ${x(segmentWidth * 0.6)},${baseline}`,
      // QRS spike
      `L ${x(segmentWidth * 0.62)},${baseline - 2}`,
      `L ${x(segmentWidth * 0.64)},${baseline + 16}`,
      `L ${x(segmentWidth * 0.66)},${baseline - 22}`,
      `L ${x(segmentWidth * 0.68)},${baseline + 4}`,
      `L ${x(segmentWidth * 0.7)},${baseline}`,
      // T-wave
      `L ${x(segmentWidth * 0.78)},${baseline - 6}`,
      `L ${x(segmentWidth * 0.85)},${baseline}`,
      // tail
      `L ${x(segmentWidth)},${baseline}`,
    ].join(" ");
  };
  return [segment(0), segment(segmentWidth), segment(segmentWidth * 2)].join(
    " ",
  );
}

export default function HeartbeatPulse({
  tone,
  width = 280,
  height = 56,
  className,
}: HeartbeatPulseProps) {
  // Static trace for non-live tones — no scroll.
  const isAnimated = tone === "live" || tone === "warn";
  const segmentWidth = width;
  const path = buildTracePath(segmentWidth, height);

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md border border-zinc-800/80 bg-zinc-950/60 shadow-edge-top",
        className,
      )}
      style={{ width, height }}
    >
      {/* faint grid behind the trace */}
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-50"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px)",
          backgroundSize: "14px 14px",
        }}
      />
      <svg
        viewBox={`0 0 ${segmentWidth * 3} ${height}`}
        width={segmentWidth * 3}
        height={height}
        className={cn(
          "absolute left-0 top-0 h-full",
          isAnimated ? "ecg-scroll" : "",
        )}
        style={{ width: segmentWidth * 3 }}
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path
          d={path}
          fill="none"
          strokeWidth="1.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={cn(TONE_STROKE[tone], TONE_GLOW[tone])}
        />
      </svg>
      <div className="absolute inset-0 bg-gradient-to-r from-zinc-950 via-transparent to-zinc-950" />
    </div>
  );
}

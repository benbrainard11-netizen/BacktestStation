"use client";

import { useEffect, useId, useRef, useState } from "react";

/**
 * ECG-style heartbeat trace. Renders a wide SVG path and CSS-translates it left
 * forever; the same shape is repeated 3x so the spike enters/exits cleanly.
 * Pulses only when `pulse` is true; flatlines otherwise.
 */
export function Heartbeat({
  pulse,
  color = "var(--accent)",
  height = 32,
}: {
  pulse: boolean;
  color?: string;
  height?: number;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [w, setW] = useState(360);
  const id = useId();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const seg = w; // one segment width = full visible width
  const totalW = seg * 3;
  const mid = height / 2;
  const spike = (offsetX: number) => {
    const o = offsetX;
    const peak = mid - height * 0.42;
    const trough = mid + height * 0.18;
    return [
      `M${o},${mid}`,
      `L${o + seg * 0.32},${mid}`,
      `L${o + seg * 0.36},${mid - height * 0.05}`,
      `L${o + seg * 0.4},${peak}`,
      `L${o + seg * 0.44},${trough}`,
      `L${o + seg * 0.48},${mid}`,
      `L${o + seg},${mid}`,
    ].join(" ");
  };
  const flat = (offsetX: number) => `M${offsetX},${mid} L${offsetX + seg},${mid}`;
  const d = pulse
    ? [spike(0), spike(seg), spike(seg * 2)].join(" ")
    : [flat(0), flat(seg), flat(seg * 2)].join(" ");

  return (
    <div ref={ref} className="relative h-full w-full overflow-hidden" style={{ height }}>
      <svg
        width={totalW}
        height={height}
        viewBox={`0 0 ${totalW} ${height}`}
        className={pulse ? "ecg-scroll absolute left-0 top-0" : "absolute left-0 top-0"}
        style={{ width: totalW }}
        aria-labelledby={id}
      >
        <title id={id}>{pulse ? "Live heartbeat" : "Flatline — bot not running"}</title>
        <path
          d={d}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          style={pulse ? { filter: `drop-shadow(0 0 4px ${color})` } : undefined}
        />
      </svg>
      <style jsx>{`
        @keyframes ecg-scroll {
          from {
            transform: translateX(0);
          }
          to {
            transform: translateX(-33.333%);
          }
        }
        :global(.ecg-scroll) {
          animation: ecg-scroll 4s linear infinite;
          will-change: transform;
        }
      `}</style>
    </div>
  );
}

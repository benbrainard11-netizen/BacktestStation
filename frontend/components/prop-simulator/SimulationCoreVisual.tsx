// Pure-SVG research instrument visual for the /prop-simulator hero.
//
// Three concentric rings (one solid, two dashed) read as Monte Carlo
// boundaries; a scatter of dim dots reads as the sample field; an
// emerald core pulses to imply convergence. No external 3D libraries.

const FIELD_DOTS: { x: number; y: number; r: number; op: number }[] = [
  { x: 84, y: 70, r: 1.1, op: 0.32 },
  { x: 112, y: 56, r: 1.3, op: 0.42 },
  { x: 144, y: 50, r: 0.9, op: 0.28 },
  { x: 178, y: 64, r: 1.2, op: 0.38 },
  { x: 198, y: 96, r: 1.0, op: 0.3 },
  { x: 214, y: 132, r: 1.1, op: 0.34 },
  { x: 220, y: 168, r: 1.3, op: 0.36 },
  { x: 200, y: 198, r: 1.0, op: 0.28 },
  { x: 174, y: 218, r: 1.2, op: 0.32 },
  { x: 138, y: 226, r: 1.0, op: 0.3 },
  { x: 102, y: 220, r: 1.1, op: 0.34 },
  { x: 76, y: 198, r: 1.0, op: 0.3 },
  { x: 60, y: 168, r: 1.2, op: 0.36 },
  { x: 56, y: 132, r: 0.9, op: 0.28 },
  { x: 70, y: 100, r: 1.0, op: 0.3 },
  { x: 124, y: 86, r: 1.4, op: 0.5 },
  { x: 162, y: 84, r: 1.2, op: 0.45 },
  { x: 188, y: 122, r: 1.3, op: 0.48 },
  { x: 184, y: 162, r: 1.1, op: 0.4 },
  { x: 162, y: 192, r: 1.2, op: 0.44 },
  { x: 122, y: 198, r: 1.3, op: 0.46 },
  { x: 92, y: 158, r: 1.1, op: 0.4 },
  { x: 96, y: 122, r: 1.4, op: 0.5 },
  { x: 154, y: 108, r: 1.2, op: 0.55 },
  { x: 170, y: 144, r: 1.0, op: 0.42 },
  { x: 116, y: 158, r: 1.1, op: 0.46 },
];

const TICK_ANGLES = [10, 38, 72, 116, 148, 202, 238, 290, 326];
const OUTER_MARKS = [0, 90, 180, 270];

export default function SimulationCoreVisual() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[260px]">
      <div className="core-tilt absolute inset-0">
      <svg viewBox="0 0 280 280" className="absolute inset-0 h-full w-full">
        <defs>
          <radialGradient id="core-grad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.05)" />
            <stop offset="60%" stopColor="rgba(255,255,255,0.012)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
        </defs>

        <circle cx="140" cy="140" r="135" fill="url(#core-grad)" />

        {/* Slowly rotating outer boundary ring — clockwise */}
        <g className="orbit-slow">
          <circle
            cx="140"
            cy="140"
            r="128"
            fill="none"
            stroke="rgb(63 63 70 / 0.45)"
            strokeWidth="1"
            strokeDasharray="2 6"
          />
          {OUTER_MARKS.map((deg) => (
            <line
              key={deg}
              x1="140"
              y1="6"
              x2="140"
              y2="14"
              stroke="rgb(113 113 122 / 0.7)"
              strokeWidth="1"
              transform={`rotate(${deg} 140 140)`}
            />
          ))}
        </g>

        {/* Mid ring — counter-rotating */}
        <g className="orbit-medium">
          <circle
            cx="140"
            cy="140"
            r="100"
            fill="none"
            stroke="rgb(82 82 91 / 0.35)"
            strokeWidth="0.85"
            strokeDasharray="3 5"
          />
        </g>

        {/* Static inner ring */}
        <circle
          cx="140"
          cy="140"
          r="68"
          fill="none"
          stroke="rgb(82 82 91 / 0.4)"
          strokeWidth="0.85"
          strokeDasharray="4 5"
        />
        <circle
          cx="140"
          cy="140"
          r="34"
          fill="none"
          stroke="rgb(63 63 70 / 0.55)"
          strokeWidth="1"
        />

        {/* Sample field — slow ambient opacity pulse */}
        <g className="ambient-pulse">
          {FIELD_DOTS.map((d, i) => (
            <circle
              key={i}
              cx={d.x}
              cy={d.y}
              r={d.r}
              fill="rgb(212 212 216)"
              fillOpacity={d.op}
            />
          ))}
        </g>

        {/* Tick marks just inside the inner ring */}
        {TICK_ANGLES.map((angle) => (
          <line
            key={angle}
            x1="140"
            y1="106"
            x2="140"
            y2="115"
            stroke="rgb(82 82 91 / 0.55)"
            strokeWidth="0.8"
            transform={`rotate(${angle} 140 140)`}
          />
        ))}

        {/* Core — emerald node with expanding halo (SVG SMIL animation) */}
        <circle
          cx="140"
          cy="140"
          r="3"
          fill="none"
          stroke="rgb(52 211 153 / 0.7)"
          strokeWidth="0.6"
        >
          <animate
            attributeName="r"
            values="3;16;3"
            dur="4s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="stroke-opacity"
            values="0.7;0;0.7"
            dur="4s"
            repeatCount="indefinite"
          />
        </circle>
        <circle
          cx="140"
          cy="140"
          r="9"
          fill="none"
          stroke="rgb(52 211 153 / 0.32)"
          strokeWidth="0.85"
        />
        <circle cx="140" cy="140" r="3" fill="rgb(52 211 153 / 0.95)" />
      </svg>
      </div>
    </div>
  );
}

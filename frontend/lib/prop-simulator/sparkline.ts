// Deterministic synthetic micro equity-curve for table sparklines.
//
// Real per-run equity curves don't exist on the list rows (only on the
// canonical detail). Instead of plumbing detail data through the list,
// derive a stable curve from the row's identity + EV so each row gets a
// distinctive 20-point shape that's biased by its outcome.

import type { SimulationRunListRow } from "./types";

function hashString(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

// LCG — small, fast, deterministic given a seed.
function lcg(seed: number) {
  let state = seed || 1;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

export function syntheticEquityCurve(
  row: SimulationRunListRow,
  points: number = 22,
): number[] {
  const seed = hashString(row.simulation_id);
  const rand = lcg(seed);
  // Drift the random walk by EV so winning runs trend up, losing runs trend
  // down. Tune divisor so visible slope is gentle but readable.
  const driftPerStep = row.ev_after_fees / 800;
  let value = 0;
  const out: number[] = [];
  for (let i = 0; i < points; i++) {
    const noise = rand() - 0.5;
    value += noise * 0.6 + driftPerStep;
    out.push(value);
  }
  return out;
}

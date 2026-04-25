"use client";

import { usePathname } from "next/navigation";

import ConnectionStatus from "@/components/ConnectionStatus";
import LocalClock from "@/components/LocalClock";
import WindowControls from "@/components/WindowControls";

type Segment = { text: string; tone: "muted" | "accent" | "body" };

const PROP_FIRM_LABELS: { prefix: string; label: string; matchExact?: boolean }[] = [
  { prefix: "/prop-simulator/firms", label: "Firm Rules" },
  { prefix: "/prop-simulator/runs", label: "Simulation Runs", matchExact: true },
  { prefix: "/prop-simulator/compare", label: "Compare" },
  { prefix: "/prop-simulator/new", label: "New Simulation" },
  { prefix: "/prop-simulator", label: "Simulator", matchExact: true },
];

function resolvePropFirmLabel(pathname: string): string | null {
  // Detail page gets its own label so it's distinct from the list.
  if (
    pathname.startsWith("/prop-simulator/runs/") &&
    pathname !== "/prop-simulator/runs"
  ) {
    return "Simulation Detail";
  }
  for (const entry of PROP_FIRM_LABELS) {
    if (entry.matchExact) {
      if (pathname === entry.prefix) return entry.label;
    } else if (
      pathname === entry.prefix ||
      pathname.startsWith(`${entry.prefix}/`)
    ) {
      return entry.label;
    }
  }
  return null;
}

function segmentsFor(pathname: string): Segment[] {
  const propFirm = resolvePropFirmLabel(pathname);
  if (propFirm !== null) {
    return [
      { text: "Prop Firm", tone: "muted" },
      { text: propFirm, tone: "body" },
    ];
  }
  return [
    { text: "Local Research Terminal", tone: "muted" },
    { text: "Phase 1", tone: "accent" },
    { text: "Command Center", tone: "body" },
  ];
}

const TONE_CLASS: Record<Segment["tone"], string> = {
  muted: "text-zinc-500",
  accent: "text-emerald-400",
  body: "text-zinc-300",
};

export default function TopBar() {
  const pathname = usePathname();
  const segments = segmentsFor(pathname);

  return (
    <header
      data-tauri-drag-region=""
      className="flex h-12 shrink-0 select-none items-center border-b border-zinc-800 bg-zinc-950"
    >
      <div
        data-tauri-drag-region=""
        className="flex h-full flex-1 items-center gap-2 pl-6 pr-4 font-mono text-[11px] uppercase tracking-widest"
      >
        {segments.map((segment, i) => (
          <span key={`${segment.text}-${i}`} className="flex items-center gap-2">
            {i > 0 ? (
              <span data-tauri-drag-region="" className="text-zinc-700">
                ·
              </span>
            ) : null}
            <span
              data-tauri-drag-region=""
              className={TONE_CLASS[segment.tone]}
            >
              {segment.text}
            </span>
          </span>
        ))}
      </div>
      <div data-tauri-drag-region="" className="flex items-center gap-2 pr-2">
        <LocalClock />
        <ConnectionStatus />
      </div>
      <WindowControls />
    </header>
  );
}

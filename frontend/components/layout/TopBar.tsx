"use client";

import { usePathname } from "next/navigation";

import ConnectionStatus from "@/components/ConnectionStatus";
import CurrentStrategySwitcher from "@/components/CurrentStrategySwitcher";
import LocalClock from "@/components/LocalClock";
import WindowControls from "@/components/WindowControls";

type Segment = { text: string; tone: "muted" | "accent" | "body" };

const PROP_FIRM_LABELS: { prefix: string; label: string; matchExact?: boolean }[] = [
  { prefix: "/prop-simulator/firms", label: "Firm rules" },
  { prefix: "/prop-simulator/runs", label: "Simulation runs", matchExact: true },
  { prefix: "/prop-simulator/compare", label: "Compare" },
  { prefix: "/prop-simulator/new", label: "New simulation" },
  { prefix: "/prop-simulator", label: "Simulator", matchExact: true },
];

function resolvePropFirmLabel(pathname: string): string | null {
  if (
    pathname.startsWith("/prop-simulator/runs/") &&
    pathname !== "/prop-simulator/runs"
  ) {
    return "Simulation detail";
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
      { text: "prop firm", tone: "muted" },
      { text: propFirm, tone: "body" },
    ];
  }
  if (pathname === "/" || pathname === "") {
    return [{ text: "command center", tone: "body" }];
  }
  if (pathname.startsWith("/backtests")) {
    return [{ text: "backtests", tone: "body" }];
  }
  if (pathname.startsWith("/monitor")) {
    return [{ text: "monitor", tone: "body" }];
  }
  if (pathname.startsWith("/journal")) {
    return [{ text: "journal", tone: "body" }];
  }
  return [{ text: "research terminal", tone: "muted" }];
}

const TONE_CLASS: Record<Segment["tone"], string> = {
  muted: "text-text-mute",
  accent: "text-accent",
  body: "text-text-dim",
};

export default function TopBar() {
  const pathname = usePathname();
  const segments = segmentsFor(pathname);

  return (
    <header
      data-tauri-drag-region=""
      className="flex h-12 shrink-0 select-none items-center border-b border-border bg-surface"
    >
      <div
        data-tauri-drag-region=""
        className="flex h-full flex-1 items-center gap-2 pl-8 pr-4 text-xs"
      >
        {segments.map((segment, i) => (
          <span key={`${segment.text}-${i}`} className="flex items-center gap-2">
            {i > 0 ? (
              <span data-tauri-drag-region="" className="text-text-mute">
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
        <CurrentStrategySwitcher />
        <LocalClock />
        <ConnectionStatus />
      </div>
      <WindowControls />
    </header>
  );
}

import ConnectionStatus from "@/components/ConnectionStatus";
import LocalClock from "@/components/LocalClock";
import StatusPill from "@/components/StatusPill";
import WindowControls from "@/components/WindowControls";
import { MOCK_TOP_BAR } from "@/lib/mocks/commandCenter";

interface TopBarProps {
  pageLabel?: string;
}

export default function TopBar({ pageLabel = "Command Center" }: TopBarProps) {
  // The whole bar is a drag region. Interactive elements (buttons) escape
  // drag automatically; the pills are static and are fine to double as drag
  // handles.
  return (
    <header
      data-tauri-drag-region=""
      className="flex h-12 shrink-0 select-none items-center border-b border-zinc-800 bg-zinc-950"
    >
      <div
        data-tauri-drag-region=""
        className="flex h-full flex-1 items-center gap-2 pl-6 pr-4 font-mono text-[11px] uppercase tracking-widest"
      >
        <span data-tauri-drag-region="" className="text-zinc-500">
          Local Research Terminal
        </span>
        <span data-tauri-drag-region="" className="text-zinc-700">·</span>
        <span data-tauri-drag-region="" className="text-emerald-400">Phase 1</span>
        <span data-tauri-drag-region="" className="text-zinc-700">·</span>
        <span data-tauri-drag-region="" className="text-zinc-300">{pageLabel}</span>
      </div>
      <div
        data-tauri-drag-region=""
        className="flex items-center gap-2 pr-2"
      >
        <LocalClock />
        <ConnectionStatus />
        <StatusPill
          label={MOCK_TOP_BAR.dbLabel}
          value={MOCK_TOP_BAR.dbValue}
          dot="live"
        />
      </div>
      <WindowControls />
    </header>
  );
}

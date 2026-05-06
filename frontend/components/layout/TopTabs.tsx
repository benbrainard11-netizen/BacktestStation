"use client";

import { Minus, Square, X } from "lucide-react";
import { useEffect, useState } from "react";

import type { components } from "@/lib/api/generated";
import { fmtPnl, tone } from "@/lib/format";
import { usePoll } from "@/lib/poll";

type LiveStatus = components["schemas"]["LiveMonitorStatus"];

/**
 * Top header strip — brand · live meta strip (bot status / symbol / P&L) ·
 * Tauri window controls. Cleaned up 2026-05-05: dropped the macOS-style ⌘
 * command-palette icon, the unwired Bell button, and the redundant Settings
 * link (Settings is in the SubNav already). Whole row is the Tauri drag
 * region; interactive children opt out via [data-no-drag].
 */
export function TopTabs() {
  const live = usePoll<LiveStatus>("/api/monitor/live", 10_000);
  const [isTauri, setIsTauri] = useState(false);

  useEffect(() => {
    setIsTauri(typeof window !== "undefined" && "__TAURI_INTERNALS__" in window);
  }, []);

  async function winAction(action: "minimize" | "maximize" | "close") {
    if (!isTauri) return;
    try {
      const mod = (await import("@tauri-apps/api/window")) as {
        getCurrentWindow?: () => {
          minimize: () => Promise<void>;
          toggleMaximize: () => Promise<void>;
          close: () => Promise<void>;
        };
      };
      const w = mod.getCurrentWindow?.();
      if (!w) return;
      if (action === "minimize") await w.minimize();
      else if (action === "maximize") await w.toggleMaximize();
      else await w.close();
    } catch {
      /* noop in browser */
    }
  }

  const liveOk = live.kind === "data" && live.data.source_exists;
  const status = liveOk ? live.data.strategy_status.toUpperCase() : "—";
  const symbol = liveOk ? live.data.current_symbol ?? "—" : "—";
  const pnl = liveOk ? live.data.today_pnl : null;
  const pnlTone = tone(pnl);

  return (
    <div data-tauri-drag-region className="top-tabs">
      <div data-no-drag className="brand-mini">
        <div className="brand-mark">B</div>
        <div className="brand-name">BacktestStation</div>
      </div>

      <div className="spacer" />

      <div data-no-drag className="top-meta">
        <span>
          <span
            className="live-pulse"
            style={{
              background: liveOk ? "var(--pos)" : "var(--ink-4)",
              boxShadow: liveOk
                ? "0 0 0 3px var(--pos-soft)"
                : "0 0 0 3px rgba(69,76,86,0.18)",
            }}
          />
          bot <strong>{status}</strong>
        </span>
        {symbol !== "—" && <span>{symbol}</span>}
        <span>
          P&L{" "}
          <strong
            style={{
              color:
                pnlTone === "pos"
                  ? "var(--pos)"
                  : pnlTone === "neg"
                    ? "var(--neg)"
                    : "var(--ink-0)",
            }}
          >
            {fmtPnl(pnl)}
          </strong>
        </span>
      </div>

      {isTauri && (
        <div data-no-drag className="flex h-full items-center pl-2">
          <button
            type="button"
            className="icon-btn"
            aria-label="Minimize"
            onClick={() => winAction("minimize")}
          >
            <Minus size={12} />
          </button>
          <button
            type="button"
            className="icon-btn"
            aria-label="Maximize"
            onClick={() => winAction("maximize")}
          >
            <Square size={10} />
          </button>
          <button
            type="button"
            className="icon-btn danger"
            aria-label="Close"
            onClick={() => winAction("close")}
          >
            <X size={12} />
          </button>
        </div>
      )}
    </div>
  );
}

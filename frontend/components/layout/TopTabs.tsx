"use client";

import { Bell, Command, Minus, Settings as SettingsIcon, Square, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import type { components } from "@/lib/api/generated";
import { fmtPnl, tone } from "@/lib/format";
import { usePoll } from "@/lib/poll";

type LiveStatus = components["schemas"]["LiveMonitorStatus"];

/**
 * Top header strip — brand · live meta strip (status / symbol / P&L) · cmd /
 * bell / settings icon-buttons · Tauri window controls. Profile-tabs strip
 * removed in the 2026-05-05 simplification — primary nav lives in SubNav now.
 *
 * Whole row is the Tauri drag region; interactive children opt out via [data-no-drag].
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
        <div className="brand-version">v0.3</div>
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
        <span>{symbol === "—" ? null : <>{symbol}</>}</span>
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

      <button
        data-no-drag
        type="button"
        className="icon-btn"
        aria-label="Command palette"
        onClick={() => window.dispatchEvent(new CustomEvent("open-cmd"))}
      >
        <Command size={16} />
      </button>
      <button data-no-drag type="button" className="icon-btn" aria-label="Notifications">
        <Bell size={16} />
      </button>
      <Link data-no-drag href="/settings" className="icon-btn" aria-label="Settings">
        <SettingsIcon size={16} />
      </Link>

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

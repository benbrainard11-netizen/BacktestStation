"use client";

import { Minus, Square, X } from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

type WindowAction = "minimize" | "toggleMaximize" | "close";

async function callWindow(action: WindowAction) {
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
    return;
  }
  const { getCurrentWindow } = await import("@tauri-apps/api/window");
  const w = getCurrentWindow();
  if (action === "minimize") await w.minimize();
  if (action === "toggleMaximize") await w.toggleMaximize();
  if (action === "close") await w.close();
}

export default function WindowControls() {
  const [inTauri, setInTauri] = useState(false);

  useEffect(() => {
    setInTauri(typeof window !== "undefined" && "__TAURI_INTERNALS__" in window);
  }, []);

  if (!inTauri) return null;

  return (
    <div className="flex h-full items-stretch">
      <ControlButton ariaLabel="Minimize" onClick={() => callWindow("minimize")}>
        <Minus className="h-3.5 w-3.5" strokeWidth={1.5} />
      </ControlButton>
      <ControlButton
        ariaLabel="Maximize"
        onClick={() => callWindow("toggleMaximize")}
      >
        <Square className="h-3 w-3" strokeWidth={1.5} />
      </ControlButton>
      <ControlButton
        ariaLabel="Close"
        onClick={() => callWindow("close")}
        danger
      >
        <X className="h-4 w-4" strokeWidth={1.5} />
      </ControlButton>
    </div>
  );
}

function ControlButton({
  children,
  onClick,
  ariaLabel,
  danger,
}: {
  children: React.ReactNode;
  onClick: () => void;
  ariaLabel: string;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      className={cn(
        "flex h-full w-11 items-center justify-center text-zinc-500 transition-colors",
        danger
          ? "hover:bg-rose-500/80 hover:text-white"
          : "hover:bg-zinc-800 hover:text-zinc-100",
      )}
    >
      {children}
    </button>
  );
}

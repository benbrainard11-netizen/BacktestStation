"use client";

import { useCallback, useEffect, useState } from "react";
import { Keyboard } from "lucide-react";

import { cn } from "@/lib/utils";

interface Shortcut {
  keys: string[];
  description: string;
}

interface ShortcutGroup {
  title: string;
  shortcuts: Shortcut[];
}

const GROUPS: ShortcutGroup[] = [
  {
    title: "Global",
    shortcuts: [
      { keys: ["⌘", "K"], description: "Open command palette" },
      { keys: ["?"], description: "Show this keyboard reference" },
      { keys: ["Esc"], description: "Close any open overlay" },
    ],
  },
  {
    title: "Command palette",
    shortcuts: [
      { keys: ["↑", "↓"], description: "Navigate results" },
      { keys: ["⏎"], description: "Open selected" },
      { keys: ["Esc"], description: "Close palette" },
    ],
  },
  {
    title: "Charts",
    shortcuts: [
      { keys: ["mouse"], description: "Hover equity overlay for crosshair" },
      { keys: ["mouse"], description: "Hover histogram bars for bucket counts" },
      { keys: ["click"], description: "Switch metric tabs · risk-sweep ticks" },
    ],
  },
  {
    title: "Risk slider",
    shortcuts: [
      { keys: ["←", "→"], description: "Step slider one risk level (when focused)" },
      { keys: ["Tab"], description: "Focus the slider thumb" },
      { keys: ["click"], description: "Jump to a tick label below the slider" },
    ],
  },
];

export default function KeyboardHelp() {
  const [open, setOpen] = useState(false);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // `?` is shift+/ on US keyboards. Skip when typing in inputs/textareas
      // so we don't intercept legitimate punctuation.
      const target = e.target as HTMLElement | null;
      const isEditable =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable === true;

      if (e.key === "?" && !isEditable) {
        e.preventDefault();
        setOpen((prev) => !prev);
      } else if (e.key === "Escape" && open) {
        e.preventDefault();
        close();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-zinc-950/70 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="panel-enter mt-24 w-full max-w-xl overflow-hidden rounded-md border border-zinc-700 bg-zinc-950 shadow-hero">
        <div className="flex items-center justify-between gap-2 border-b border-zinc-800 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <Keyboard
              className="h-3.5 w-3.5 shrink-0 text-zinc-500"
              strokeWidth={1.75}
              aria-hidden="true"
            />
            <span className="font-mono text-[11px] uppercase tracking-[0.32em] text-zinc-300">
              Keyboard reference
            </span>
          </div>
          <kbd className="flex h-5 items-center rounded-sm border border-zinc-700 bg-zinc-900 px-1.5 font-mono text-[9px] uppercase tracking-widest text-zinc-400">
            esc
          </kbd>
        </div>

        <div className="max-h-[70vh] overflow-y-auto">
          {GROUPS.map((group) => (
            <section
              key={group.title}
              className="border-b border-zinc-900 px-4 py-3 last:border-b-0"
            >
              <h3 className="mb-2 font-mono text-[10px] uppercase tracking-[0.32em] text-zinc-500">
                {group.title}
              </h3>
              <dl className="flex flex-col gap-1.5">
                {group.shortcuts.map((sc) => (
                  <div
                    key={sc.description}
                    className="flex items-baseline justify-between gap-3"
                  >
                    <dt className="text-xs text-zinc-300">{sc.description}</dt>
                    <dd className="flex shrink-0 items-center gap-1">
                      {sc.keys.map((k, i) => (
                        <kbd
                          key={`${k}-${i}`}
                          className={cn(
                            "flex h-5 min-w-[1.25rem] items-center justify-center rounded-sm border border-zinc-700 bg-zinc-900 px-1.5 font-mono text-[10px] tabular-nums",
                            k === "mouse" || k === "click"
                              ? "italic text-zinc-500"
                              : "text-zinc-200",
                          )}
                        >
                          {k}
                        </kbd>
                      ))}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-zinc-800 px-4 py-2 font-mono text-[9px] uppercase tracking-widest text-zinc-600">
          <span>
            <kbd className="rounded-sm border border-zinc-700 bg-zinc-900 px-1 text-zinc-400">
              ?
            </kbd>{" "}
            toggle
          </span>
          <span>
            <kbd className="rounded-sm border border-zinc-700 bg-zinc-900 px-1 text-zinc-400">
              esc
            </kbd>{" "}
            close
          </span>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Compass,
  CornerDownLeft,
  Plus,
  Search,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/navigation";

type CommandKind = "nav" | "action";

interface CommandItem {
  id: string;
  label: string;
  hint: string;
  kind: CommandKind;
  href: string;
}

const ACTION_ITEMS: CommandItem[] = [
  {
    id: "act-new-sim",
    label: "New simulation",
    hint: "Start a fresh Monte Carlo run",
    kind: "action",
    href: "/prop-simulator/new",
  },
  {
    id: "act-open-runs",
    label: "Open simulation runs",
    hint: "Saved Monte Carlo runs list",
    kind: "action",
    href: "/prop-simulator/runs",
  },
  {
    id: "act-compare",
    label: "Compare setups",
    hint: "Side-by-side firm/risk comparison",
    kind: "action",
    href: "/prop-simulator/compare",
  },
  {
    id: "act-firm-rules",
    label: "Edit firm rules",
    hint: "Demo firm profile editor",
    kind: "action",
    href: "/prop-simulator/firms",
  },
  {
    id: "act-featured-run",
    label: "Open featured run",
    hint: "sim-001 · Topstep 50K · $100 risk",
    kind: "action",
    href: "/prop-simulator/runs/sim-001",
  },
];

function buildItems(): CommandItem[] {
  const navItems: CommandItem[] = NAV_ITEMS.map((n) => ({
    id: `nav-${n.href}`,
    label: n.label,
    hint: `Go to ${n.href}`,
    kind: "nav",
    href: n.href,
  }));
  return [...navItems, ...ACTION_ITEMS];
}

function fuzzyMatch(query: string, target: string): boolean {
  if (!query) return true;
  const q = query.toLowerCase();
  const t = target.toLowerCase();
  let qi = 0;
  for (let i = 0; i < t.length && qi < q.length; i++) {
    if (t[i] === q[qi]) qi++;
  }
  return qi === q.length;
}

export default function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const items = useMemo(() => buildItems(), []);
  const filtered = useMemo(() => {
    if (!query.trim()) return items;
    return items.filter(
      (i) => fuzzyMatch(query, i.label) || fuzzyMatch(query, i.hint),
    );
  }, [items, query]);

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setActiveIndex(0);
  }, []);

  const runCommand = useCallback(
    (item: CommandItem) => {
      router.push(item.href);
      close();
    },
    [router, close],
  );

  // Global keyboard shortcuts: Cmd+K / Ctrl+K to open, Escape to close.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const isOpenShortcut =
        (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k";
      if (isOpenShortcut) {
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

  // Focus the search input on open + reset selection on filter change.
  useEffect(() => {
    if (open) {
      // Defer one frame so the input is mounted.
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  // Arrow / Enter navigation handled on the input; scroll the active row
  // into view if it goes off-screen.
  function onInputKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(filtered.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = filtered[activeIndex];
      if (item) runCommand(item);
    }
  }

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const child = list.children[activeIndex] as HTMLElement | undefined;
    child?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, filtered.length]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-zinc-950/70 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="panel-enter mt-32 w-full max-w-lg overflow-hidden rounded-md border border-zinc-700 bg-zinc-950 shadow-hero">
        <div className="flex items-center gap-2 border-b border-zinc-800 px-3 py-2.5">
          <Search
            className="h-3.5 w-3.5 shrink-0 text-zinc-500"
            strokeWidth={1.75}
            aria-hidden="true"
          />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onInputKey}
            placeholder="Search routes, simulations, actions…"
            className="flex-1 bg-transparent text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
            aria-label="Command palette search"
          />
          <kbd className="hidden h-5 items-center rounded-sm border border-zinc-700 bg-zinc-900 px-1.5 font-mono text-[9px] uppercase tracking-widest text-zinc-400 sm:flex">
            esc
          </kbd>
        </div>

        <ul
          ref={listRef}
          className="max-h-[360px] overflow-y-auto py-1"
          role="listbox"
        >
          {filtered.length === 0 ? (
            <li className="px-3 py-6 text-center font-mono text-[11px] uppercase tracking-widest text-zinc-600">
              No matches
            </li>
          ) : (
            filtered.map((item, i) => {
              const isActive = i === activeIndex;
              const Icon = item.kind === "action" ? Plus : Compass;
              return (
                <li
                  key={item.id}
                  role="option"
                  aria-selected={isActive}
                  onMouseEnter={() => setActiveIndex(i)}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    runCommand(item);
                  }}
                  className={cn(
                    "flex cursor-pointer items-center gap-3 px-3 py-2 transition-colors",
                    isActive
                      ? "bg-zinc-900 text-zinc-100"
                      : "text-zinc-300 hover:bg-zinc-900/50",
                  )}
                >
                  <Icon
                    className={cn(
                      "h-3.5 w-3.5 shrink-0",
                      isActive ? "text-emerald-400" : "text-zinc-500",
                    )}
                    strokeWidth={1.75}
                    aria-hidden="true"
                  />
                  <div className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate text-sm">{item.label}</span>
                    <span className="truncate font-mono text-[10px] uppercase tracking-widest text-zinc-500">
                      {item.hint}
                    </span>
                  </div>
                  {isActive ? (
                    <CornerDownLeft
                      className="h-3 w-3 text-zinc-500"
                      strokeWidth={1.75}
                      aria-hidden="true"
                    />
                  ) : (
                    <ArrowRight
                      className="h-3 w-3 text-zinc-700"
                      strokeWidth={1.75}
                      aria-hidden="true"
                    />
                  )}
                </li>
              );
            })
          )}
        </ul>

        <div className="flex items-center justify-between gap-3 border-t border-zinc-800 px-3 py-1.5 font-mono text-[9px] uppercase tracking-widest text-zinc-600">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="rounded-sm border border-zinc-700 bg-zinc-900 px-1 text-zinc-400">
                ↑
              </kbd>
              <kbd className="ml-1 rounded-sm border border-zinc-700 bg-zinc-900 px-1 text-zinc-400">
                ↓
              </kbd>{" "}
              navigate
            </span>
            <span>
              <kbd className="rounded-sm border border-zinc-700 bg-zinc-900 px-1 text-zinc-400">
                ⏎
              </kbd>{" "}
              open
            </span>
            <span>
              <kbd className="rounded-sm border border-zinc-700 bg-zinc-900 px-1 text-zinc-400">
                esc
              </kbd>{" "}
              close
            </span>
          </div>
          <span className="text-zinc-600">
            {filtered.length} / {items.length}
          </span>
        </div>
      </div>
    </div>
  );
}

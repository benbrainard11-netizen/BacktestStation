"use client";

import { Settings as SettingsIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import {
  NAV_GROUPS,
  NAV_ITEMS,
  TOP_TAB_HREFS,
  type NavItem,
} from "@/lib/navigation";
import { cn } from "@/lib/utils";

const ADMIN_ITEMS: NavItem[] = NAV_ITEMS.filter(
  (item) => !TOP_TAB_HREFS.has(item.href),
);

/**
 * Compact admin overflow menu. Cog icon in the top bar; click opens a
 * dropdown grouping the old sidebar items (Backtests, Monitor, Replay,
 * Data Health, Settings, Prop Simulator, etc.). Click-outside closes.
 *
 * This is the "admin tooling" landing place for the new strategies-
 * first IA — Dashboard + Strategies stay the primary flow up top, and
 * everything else lives here behind a single icon.
 */
export default function AdminMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex h-7 w-7 items-center justify-center rounded-md text-text-mute transition-colors hover:bg-surface-alt hover:text-text",
          open && "bg-surface-alt text-text",
        )}
        aria-label="Admin menu"
        aria-expanded={open}
      >
        <SettingsIcon className="h-4 w-4" strokeWidth={1.5} />
      </button>
      {open ? (
        <div
          className="absolute right-0 top-full z-50 mt-1 w-60 overflow-hidden rounded-md border border-border bg-surface shadow-lg"
          role="menu"
        >
          {NAV_GROUPS.map((group) => {
            const items = ADMIN_ITEMS.filter((i) => i.group === group.key);
            if (items.length === 0) return null;
            return (
              <div
                key={group.key}
                className="border-b border-border last:border-b-0"
              >
                <p className="px-3 pb-1 pt-2 text-[10px] uppercase tracking-wider text-text-mute">
                  {group.label}
                </p>
                <ul className="m-0 list-none p-0 pb-1">
                  {items.map((item) => {
                    const Icon = item.icon;
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          onClick={() => setOpen(false)}
                          className="flex items-center gap-2 px-3 py-1.5 text-[13px] text-text-dim transition-colors hover:bg-surface-alt hover:text-text"
                        >
                          <Icon
                            className="h-3.5 w-3.5 shrink-0 text-text-mute"
                            strokeWidth={1.5}
                            aria-hidden="true"
                          />
                          <span>{item.label}</span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

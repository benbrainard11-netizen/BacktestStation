"use client";

import { LogOut, SunMedium } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { NAV_GROUPS, NAV_ITEMS, type NavItem } from "@/lib/navigation";

// App version. Hardcoded, matches backend/pyproject.toml + frontend/package.json.
// Build-time injection (git SHA + commit date) lands with Phase 3+ tooling.
const APP_VERSION = "0.1.0";

function pickActiveHref(pathname: string, items: NavItem[]): string | null {
  if (pathname === "/") return "/";
  let best: { href: string; length: number } | null = null;
  for (const item of items) {
    if (item.href === "/") continue;
    if (pathname !== item.href && !pathname.startsWith(`${item.href}/`)) continue;
    if (best === null || item.href.length > best.length) {
      best = { href: item.href, length: item.href.length };
    }
  }
  return best?.href ?? null;
}

function NavRow({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={cn(
        "group relative flex items-center gap-3 rounded-md px-3 py-2 text-[13px]",
        "transition-colors duration-150 ease-out",
        active
          ? "bg-surface-alt text-text"
          : "text-text-dim hover:bg-surface-alt hover:text-text",
      )}
    >
      {active ? (
        <span
          aria-hidden="true"
          className="absolute inset-y-1.5 left-0 w-[2px] rounded-full bg-accent/80"
        />
      ) : null}
      <Icon
        className={cn(
          "h-4 w-4 shrink-0 transition-colors duration-150",
          active
            ? "text-accent"
            : "text-text-mute group-hover:text-text-dim",
        )}
        strokeWidth={1.5}
        aria-hidden="true"
      />
      <span>{item.label}</span>
    </Link>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const activeHref = pickActiveHref(pathname, NAV_ITEMS);

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface">
      <div className="border-b border-border px-4 py-4">
        <h1 className="text-[15px] font-medium tracking-[-0.01em] text-text">
          backtest&nbsp;station
        </h1>
        <p className="mt-0.5 text-xs text-text-mute">v{APP_VERSION}</p>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {NAV_GROUPS.map((group) => {
          const items = NAV_ITEMS.filter((i) => i.group === group.key);
          if (items.length === 0) return null;
          return (
            <div key={group.key} className="mb-5 last:mb-0">
              <p className="px-3 pb-2 text-xs text-text-mute">
                {group.label}
              </p>
              <ul className="space-y-px">
                {items.map((item) => (
                  <li key={item.href}>
                    <NavRow item={item} active={item.href === activeHref} />
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </nav>

      <div className="flex items-center justify-between border-t border-border px-4 py-3 text-xs text-text-mute">
        <div className="flex items-center gap-2">
          <span>local build</span>
          <span className="text-text-dim">v{APP_VERSION}</span>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-border px-4 py-2">
        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-md text-text-mute transition-colors hover:bg-surface-alt hover:text-text"
          aria-label="Toggle theme (not implemented)"
        >
          <SunMedium className="h-4 w-4" strokeWidth={1.5} />
        </button>
        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-md text-text-mute transition-colors hover:bg-surface-alt hover:text-text"
          aria-label="Sign out (not implemented)"
        >
          <LogOut className="h-4 w-4" strokeWidth={1.5} />
        </button>
      </div>
    </aside>
  );
}

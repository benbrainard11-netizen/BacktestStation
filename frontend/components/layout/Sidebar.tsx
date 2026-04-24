"use client";

import { LogOut, SunMedium } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { NAV_GROUPS, NAV_ITEMS, type NavItem } from "@/lib/navigation";

// App build info. Hardcoded until a build-time injection is wired (Phase 3+).
const APP_VERSION = "0.1.0";
const APP_BUILD_DATE = "2026-04-24";

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavRow({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors",
        active
          ? "bg-zinc-900 text-zinc-100"
          : "text-zinc-400 hover:bg-zinc-900/60 hover:text-zinc-100",
      )}
    >
      <Icon
        className={cn(
          "h-4 w-4 shrink-0",
          active ? "text-emerald-400" : "text-zinc-500",
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

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="border-b border-zinc-800 px-4 py-4">
        <h1 className="font-mono text-base tracking-[0.25em] text-zinc-100">
          BACKTESTSTATION
        </h1>
        <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          v{APP_VERSION}
        </p>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {NAV_GROUPS.map((group) => {
          const items = NAV_ITEMS.filter((i) => i.group === group.key);
          if (items.length === 0) return null;
          return (
            <div key={group.key} className="mb-5 last:mb-0">
              <p className="px-3 pb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
                {group.label}
              </p>
              <ul className="space-y-px">
                {items.map((item) => (
                  <li key={item.href}>
                    <NavRow item={item} active={isActive(pathname, item.href)} />
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </nav>

      <div className="flex items-center justify-between border-t border-zinc-800 px-4 py-3 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-zinc-600">Version</span>
            <span className="text-zinc-300">v{APP_VERSION}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-zinc-600">Build</span>
            <span className="text-zinc-300">{APP_BUILD_DATE}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-zinc-800 px-4 py-2">
        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-sm text-zinc-500 transition-colors hover:bg-zinc-900 hover:text-zinc-100"
          aria-label="Toggle theme (not implemented)"
        >
          <SunMedium className="h-4 w-4" strokeWidth={1.5} />
        </button>
        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-sm text-zinc-500 transition-colors hover:bg-zinc-900 hover:text-zinc-100"
          aria-label="Sign out (not implemented)"
        >
          <LogOut className="h-4 w-4" strokeWidth={1.5} />
        </button>
      </div>
    </aside>
  );
}

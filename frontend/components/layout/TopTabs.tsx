"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import AdminMenu from "@/components/layout/AdminMenu";
import { TOP_TAB_ITEMS } from "@/lib/navigation";
import { cn } from "@/lib/utils";

/**
 * Direction A horizontal top-tab nav. Two tabs in v1 (Dashboard,
 * Strategies). Logo on the left, admin gear on the right reveals the
 * old sidebar items (Backtests / Monitor / Replay / Data Health /
 * Prop Simulator / Settings).
 *
 * Active state is derived from `usePathname()` — the Strategies tab
 * stays active for any `/strategies/*` deep link.
 */
export default function TopTabs() {
  const pathname = usePathname();
  return (
    <nav
      className="flex h-11 shrink-0 items-center gap-1 border-b border-border bg-surface px-4"
      aria-label="Primary"
    >
      <Link
        href="/"
        className="mr-4 text-[13px] font-medium tracking-[-0.01em] text-text"
      >
        backtest&nbsp;station
      </Link>
      {TOP_TAB_ITEMS.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "relative flex items-center px-4 py-2 text-[13px] tracking-[-0.005em] transition-colors",
              active
                ? "text-text"
                : "text-text-mute hover:text-text-dim",
            )}
          >
            {item.label}
            {active ? (
              <span
                aria-hidden="true"
                className="absolute inset-x-3 bottom-[-1px] h-[2px] rounded-t-sm bg-accent"
              />
            ) : null}
          </Link>
        );
      })}
      <div className="ml-auto flex items-center gap-2 pr-1">
        <AdminMenu />
      </div>
    </nav>
  );
}

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

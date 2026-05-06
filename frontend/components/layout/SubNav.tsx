"use client";

import { Search } from "lucide-react";
import Link from "next/link";

import { Icon } from "@/components/Icon";
import { NAV_ITEMS, isActive } from "@/lib/navigation";

/**
 * Single horizontal nav row — Inbox · Backtests · Replay · Catalog · Library
 * · Settings — with a search/cmd-palette pill on the right. Replaces the old
 * profile-tabs + sub-nav split. Designed to match the chrome in the design
 * tokens (no card chrome, just the row).
 */
export function SubNav({ pathname }: { pathname: string }) {
  return (
    <nav className="subnav subnav-flat" aria-label="Primary navigation">
      <div className="subnav-items">
        {NAV_ITEMS.map((it) => {
          const active = isActive(it, pathname);
          return (
            <Link
              key={it.id}
              href={it.href}
              aria-current={active ? "page" : undefined}
              className="subnav-item"
            >
              <span className="subnav-icon">
                <Icon name={it.icon} size={14} />
              </span>
              <span>{it.label}</span>
            </Link>
          );
        })}
      </div>

      <div className="spacer" />

      <button
        type="button"
        className="search-pill"
        onClick={() => window.dispatchEvent(new CustomEvent("open-cmd"))}
      >
        <Search size={13} />
        <span>Search</span>
        <span className="kbd-mini">Ctrl K</span>
      </button>
    </nav>
  );
}

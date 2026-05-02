"use client";

import { Search } from "lucide-react";
import Link from "next/link";

import { Icon } from "@/components/Icon";
import { PROFILES, profileForPath } from "@/lib/navigation";

/**
 * Horizontal sub-nav row under the top tabs. Shows the groups + items for the
 * currently active profile, separated by vertical dividers. Search pill on the
 * far right opens the command palette.
 */
export function SubNav({ pathname }: { pathname: string }) {
  const profile = PROFILES.find((p) => p.id === profileForPath(pathname));
  if (!profile) return null;

  return (
    <nav className="subnav" aria-label="Section navigation">
      {profile.groups.map((g) => (
        <div key={g.title} className="subnav-group">
          <div className="subnav-group-title">{g.title}</div>
          <div className="subnav-items">
            {g.items.map((it) => {
              const isActive = pathname === it.href || pathname.startsWith(it.href + "/");
              return (
                <Link
                  key={it.id}
                  href={it.href}
                  aria-current={isActive ? "page" : undefined}
                  className="subnav-item"
                >
                  <span className="subnav-icon">
                    <Icon name={it.icon} size={14} />
                  </span>
                  <span>{it.label}</span>
                  {it.live && <span className="subnav-live">LIVE</span>}
                </Link>
              );
            })}
          </div>
        </div>
      ))}

      <div className="spacer" />

      <button
        type="button"
        className="search-pill"
        onClick={() => window.dispatchEvent(new CustomEvent("open-cmd"))}
      >
        <Search size={13} />
        <span>Search · jump · run</span>
        <span className="kbd-mini">⌘K</span>
      </button>
    </nav>
  );
}

/**
 * App navigation source of truth — pruned per Ben's 2026-05-01 triage:
 * default to CUT, port only what's on the strategy-cards-first critical path.
 *
 * Top-level: 3 profiles (Dashboard / Research / Strategies) shown as tabs.
 * Each profile has groups; each group has items; each item is a sub-nav row
 * that maps to a Next.js route.
 */

export type IconName =
  | "home"
  | "pulse"
  | "clipboard"
  | "database"
  | "cog"
  | "download"
  | "flask"
  | "beaker"
  | "bolt"
  | "film"
  | "shield"
  | "layers"
  | "compare"
  | "settings"
  | "search";

export type NavItem = {
  id: string;
  label: string;
  icon: IconName;
  href: string;
  live?: boolean;
};

export type NavGroup = {
  title: string;
  items: NavItem[];
};

export type Profile = {
  id: "dashboard" | "research" | "strategies";
  label: string;
  kbd: "1" | "2" | "3";
  groups: NavGroup[];
};

export const PROFILES: Profile[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    kbd: "1",
    groups: [
      {
        title: "Live",
        items: [
          { id: "overview", label: "Overview", icon: "home", href: "/" },
          { id: "monitor", label: "Monitor", icon: "pulse", href: "/monitor", live: true },
          { id: "notes", label: "Notes", icon: "clipboard", href: "/notes" },
        ],
      },
      {
        title: "System",
        items: [
          { id: "datahealth", label: "Data Health", icon: "database", href: "/data-health" },
          { id: "settings", label: "Settings", icon: "cog", href: "/settings" },
        ],
      },
    ],
  },
  {
    id: "research",
    label: "Research",
    kbd: "2",
    groups: [
      {
        title: "Research",
        items: [
          { id: "import", label: "Import", icon: "download", href: "/import" },
          { id: "experiments", label: "Experiments", icon: "flask", href: "/experiments" },
        ],
      },
      {
        title: "Test",
        items: [
          { id: "backtests", label: "Backtests", icon: "bolt", href: "/backtests" },
          { id: "replay", label: "Replay", icon: "film", href: "/replay" },
        ],
      },
    ],
  },
  {
    id: "strategies",
    label: "Strategies",
    kbd: "3",
    groups: [
      {
        title: "Build",
        items: [
          {
            id: "strategies_list",
            label: "Strategy Catalog",
            icon: "layers",
            href: "/strategies",
          },
          { id: "risk", label: "Risk Profiles", icon: "shield", href: "/risk-profiles" },
        ],
      },
    ],
  },
];

export const ALL_NAV_ITEMS = PROFILES.flatMap((p) =>
  p.groups.flatMap((g) =>
    g.items.map((it) => ({
      ...it,
      profile: p.id,
      profileLabel: p.label,
      group: g.title,
    })),
  ),
);

/** Resolve which profile owns a given pathname (longest-prefix match). */
export function profileForPath(pathname: string): Profile["id"] {
  let best: { profile: Profile["id"]; len: number } = { profile: "dashboard", len: 0 };
  for (const p of PROFILES) {
    for (const g of p.groups) {
      for (const it of g.items) {
        const matches = pathname === it.href || pathname.startsWith(it.href + "/");
        if (matches && it.href.length > best.len) {
          best = { profile: p.id, len: it.href.length };
        }
      }
    }
  }
  return best.profile;
}

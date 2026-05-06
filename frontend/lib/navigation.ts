/**
 * App navigation source of truth — flat, single-row, six items.
 *
 * The earlier 3-profile (Dashboard / Research / Strategies) tab system is
 * gone. We collapsed it down to one horizontal nav per the simplification
 * plan (SIMPLIFY_PLAN.md, decided 2026-05-05). Folded routes:
 *   - Overview / Monitor / Notes / Data Health / Import / Experiments  → DELETED
 *   - Risk Profiles                                                    → tab inside Catalog
 *   - Data Health / Live Bot / Admin                                   → tabs inside Settings
 */

export type IconName =
  | "inbox"
  | "bolt"
  | "film"
  | "layers"
  | "library"
  | "settings";

export type NavItem = {
  id: string;
  label: string;
  icon: IconName;
  href: string;
};

export const NAV_ITEMS: NavItem[] = [
  { id: "inbox",     label: "Inbox",     icon: "inbox",    href: "/inbox" },
  { id: "backtests", label: "Backtests", icon: "bolt",     href: "/backtests" },
  { id: "replay",    label: "Replay",    icon: "film",     href: "/replay" },
  { id: "catalog",   label: "Catalog",   icon: "layers",   href: "/strategies" },
  { id: "library",   label: "Library",   icon: "library",  href: "/library" },
  { id: "settings",  label: "Settings",  icon: "settings", href: "/settings" },
];

/** Returns true if the given pathname is "inside" the nav item's route. */
export function isActive(item: NavItem, pathname: string): boolean {
  return pathname === item.href || pathname.startsWith(item.href + "/");
}

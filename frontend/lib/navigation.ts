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
  | "wand"
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
  { id: "builder",   label: "Builder",   icon: "wand",     href: "/strategies/builder" },
  { id: "library",   label: "Library",   icon: "library",  href: "/library" },
  { id: "settings",  label: "Settings",  icon: "settings", href: "/settings" },
];

/** Resolve the single active nav item for a pathname.
 *
 * Uses longest-prefix-match so that when multiple items would match
 * (e.g. Catalog `/strategies` and Builder `/strategies/builder` both
 * "match" `/strategies/builder`), only the most specific one wins. The
 * earlier per-item `isActive` would light up both tabs at once.
 *
 * Returns the matching NavItem or null if no item is in the path.
 */
export function findActiveNavItem(pathname: string): NavItem | null {
  let best: NavItem | null = null;
  let bestLen = -1;
  for (const item of NAV_ITEMS) {
    const matches =
      pathname === item.href || pathname.startsWith(item.href + "/");
    if (matches && item.href.length > bestLen) {
      best = item;
      bestLen = item.href.length;
    }
  }
  return best;
}

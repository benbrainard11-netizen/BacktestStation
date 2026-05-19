/**
 * App navigation source of truth.
 *
 * Dashboard Q5 brings Data Health back as an operator-console route while the
 * rest of the app keeps the current horizontal chrome.
 */

export type IconName =
  | "inbox"
  | "health"
  | "trials"
  | "candidates"
  | "bolt"
  | "film"
  | "layers"
  | "wand"
  | "library"
  | "research"
  | "settings";

export type NavItem = {
  id: string;
  label: string;
  icon: IconName;
  href: string;
};

export const NAV_ITEMS: NavItem[] = [
  { id: "data-health", label: "Data Health", icon: "health", href: "/data-health" },
  { id: "trials", label: "Trials", icon: "trials", href: "/trials" },
  {
    id: "candidates",
    label: "Candidates",
    icon: "candidates",
    href: "/candidates",
  },
  { id: "inbox", label: "Inbox", icon: "inbox", href: "/inbox" },
  { id: "backtests", label: "Backtests", icon: "bolt", href: "/backtests" },
  { id: "replay", label: "Replay", icon: "film", href: "/replay" },
  { id: "catalog", label: "Catalog", icon: "layers", href: "/strategies" },
  {
    id: "builder",
    label: "Builder",
    icon: "wand",
    href: "/strategies/builder",
  },
  { id: "library", label: "Library", icon: "library", href: "/library" },
  { id: "research", label: "Research", icon: "research", href: "/research/events" },
  { id: "settings", label: "Settings", icon: "settings", href: "/settings" },
];

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

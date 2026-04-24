import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BarChart3,
  BookOpen,
  Database,
  Download,
  LayoutDashboard,
  Notebook,
  Settings as SettingsIcon,
} from "lucide-react";

export type NavGroup = "research" | "live" | "system";

export interface NavItem {
  href: string;
  label: string;
  group: NavGroup;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Command Center", group: "research", icon: LayoutDashboard },
  { href: "/import", label: "Import", group: "research", icon: Download },
  { href: "/strategies", label: "Strategies", group: "research", icon: BookOpen },
  { href: "/backtests", label: "Backtests", group: "research", icon: BarChart3 },

  { href: "/monitor", label: "Monitor", group: "live", icon: Activity },
  { href: "/journal", label: "Journal", group: "live", icon: Notebook },

  { href: "/data-health", label: "Data Health", group: "system", icon: Database },
  { href: "/settings", label: "Settings", group: "system", icon: SettingsIcon },
];

export const NAV_GROUPS: { key: NavGroup; label: string }[] = [
  { key: "research", label: "Research" },
  { key: "live", label: "Live" },
  { key: "system", label: "System" },
];

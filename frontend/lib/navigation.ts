import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BarChart3,
  BookOpen,
  Building2,
  Database,
  Dices,
  Download,
  GitCompareArrows,
  History,
  LayoutDashboard,
  Notebook,
  Settings as SettingsIcon,
} from "lucide-react";

export type NavGroup = "research" | "prop_firm" | "live" | "system";

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

  { href: "/prop-simulator", label: "Simulator", group: "prop_firm", icon: Dices },
  { href: "/prop-simulator/firms", label: "Firm Rules", group: "prop_firm", icon: Building2 },
  { href: "/prop-simulator/runs", label: "Simulation Runs", group: "prop_firm", icon: History },
  { href: "/prop-simulator/compare", label: "Compare", group: "prop_firm", icon: GitCompareArrows },

  { href: "/monitor", label: "Monitor", group: "live", icon: Activity },
  { href: "/journal", label: "Journal", group: "live", icon: Notebook },

  { href: "/data-health", label: "Data Health", group: "system", icon: Database },
  { href: "/settings", label: "Settings", group: "system", icon: SettingsIcon },
];

export const NAV_GROUPS: { key: NavGroup; label: string }[] = [
  { key: "research", label: "Research" },
  { key: "prop_firm", label: "Prop Firm" },
  { key: "live", label: "Live" },
  { key: "system", label: "System" },
];

import {
  Activity,
  BarChart3,
  Film,
  FileText,
  Home,
  Inbox,
  Layers,
  Library,
  Search,
  Settings as Cog,
  Wand2,
  Zap,
} from "lucide-react";

import type { IconName } from "@/lib/navigation";

const MAP: Record<IconName, typeof Inbox> = {
  home: Home,
  inbox: Inbox,
  bolt: Zap,
  film: Film,
  layers: Layers,
  wand: Wand2,
  library: Library,
  settings: Cog,
  activity: Activity,
};

export function Icon({
  name,
  size = 14,
  className,
  strokeWidth = 1.75,
}: {
  name: IconName;
  size?: number;
  className?: string;
  strokeWidth?: number;
}) {
  const Cmp = MAP[name] ?? Inbox;
  return <Cmp size={size} className={className} strokeWidth={strokeWidth} />;
}

// Re-export a few of the most-used icons for direct use without the indirection.
export { BarChart3, FileText, Search };

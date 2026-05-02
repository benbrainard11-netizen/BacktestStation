import {
  Activity,
  BarChart3,
  Beaker,
  Clipboard,
  Database,
  Download,
  FileText,
  Film,
  FlaskConical,
  GitCompare,
  Home,
  Layers,
  Search,
  Settings as Cog,
  Shield,
  Zap,
} from "lucide-react";

import type { IconName } from "@/lib/navigation";

const MAP: Record<IconName, typeof Home> = {
  home: Home,
  pulse: Activity,
  clipboard: Clipboard,
  database: Database,
  cog: Cog,
  download: Download,
  flask: FlaskConical,
  beaker: Beaker,
  bolt: Zap,
  film: Film,
  shield: Shield,
  layers: Layers,
  compare: GitCompare,
  settings: Cog,
  search: Search,
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
  const Cmp = MAP[name] ?? Home;
  return <Cmp size={size} className={className} strokeWidth={strokeWidth} />;
}

// Re-export a few of the most-used icons for direct use without the indirection.
export { BarChart3, FileText };

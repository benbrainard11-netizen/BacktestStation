import {
  Activity,
  BarChart3,
  BookOpen,
  Download,
  Notebook,
  PlayCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";

import { MOCK_QUICK_TILES } from "@/lib/mocks/commandCenter";

const ICONS: Record<string, LucideIcon> = {
  import: Download,
  strategies: BookOpen,
  backtests: BarChart3,
  replay: PlayCircle,
  monitor: Activity,
  journal: Notebook,
};

export default function QuickAccessGrid() {
  return (
    <section className="flex flex-col border border-zinc-800 bg-zinc-950">
      <header className="border-b border-zinc-800 px-4 py-3">
        <h3 className="font-mono text-[11px] uppercase tracking-widest text-zinc-300">
          Quick Access
        </h3>
      </header>
      <div className="grid grid-cols-3 gap-px bg-zinc-800">
        {MOCK_QUICK_TILES.map((tile) => {
          const Icon = ICONS[tile.iconKey];
          return (
            <Link
              key={tile.href}
              href={tile.href}
              className="group flex aspect-square flex-col items-center justify-center gap-3 bg-zinc-950 px-3 py-4 text-zinc-400 transition-colors hover:bg-zinc-900 hover:text-zinc-100"
            >
              <Icon
                className="h-6 w-6 text-zinc-400 transition-colors group-hover:text-emerald-400"
                strokeWidth={1.5}
                aria-hidden="true"
              />
              <span className="text-center text-xs leading-tight">
                {tile.label}
              </span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

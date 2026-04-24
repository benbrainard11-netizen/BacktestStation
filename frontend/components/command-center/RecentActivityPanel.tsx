import {
  BarChart3,
  Check,
  ChevronRight,
  Download,
  Signal,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";

import { MOCK_ACTIVITY, type MockActivityRow } from "@/lib/mocks/commandCenter";

const ICONS: Record<MockActivityRow["kind"], LucideIcon> = {
  signal: Signal,
  import: Download,
  backtest: BarChart3,
};

export default function RecentActivityPanel() {
  return (
    <section className="flex flex-col border border-zinc-800 bg-zinc-950">
      <header className="border-b border-zinc-800 px-4 py-3">
        <h3 className="font-mono text-[11px] uppercase tracking-widest text-zinc-300">
          Recent Activity
        </h3>
      </header>
      <ul className="flex-1 divide-y divide-zinc-800/60">
        {MOCK_ACTIVITY.map((item, i) => {
          const Icon = ICONS[item.kind];
          return (
            <li key={i} className="flex items-center gap-3 px-4 py-3">
              <Icon className="h-3.5 w-3.5 shrink-0 text-zinc-500" strokeWidth={1.5} aria-hidden="true" />
              <span className="shrink-0 font-mono text-[11px] text-zinc-500">
                {item.time}
              </span>
              <span className="flex-1 truncate text-xs text-zinc-300">
                {item.text}
                {item.meta ? (
                  <span className="ml-1 text-zinc-500">· {item.meta}</span>
                ) : null}
              </span>
              {item.kind !== "signal" ? (
                <Check className="h-3 w-3 shrink-0 text-emerald-400" strokeWidth={2} aria-hidden="true" />
              ) : null}
            </li>
          );
        })}
      </ul>
      <footer className="border-t border-zinc-800 px-4 py-3">
        <Link
          href="/monitor"
          className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 transition-colors hover:text-zinc-100"
        >
          View all activity
          <ChevronRight className="h-3 w-3" strokeWidth={1.5} aria-hidden="true" />
        </Link>
      </footer>
    </section>
  );
}

import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];

export const dynamic = "force-dynamic";

const COLUMNS = [
  "Strategy",
  "Slug",
  "Status",
  "Versions",
  "Tags",
  "Created",
  "",
] as const;

export default async function StrategiesPage() {
  const strategies = await apiGet<Strategy[]>("/api/strategies");

  return (
    <div>
      <PageHeader
        title="Strategies"
        description="Every strategy seen across imported runs, with its versions"
      />
      <div className="px-6 pb-10">
        {strategies.length === 0 ? (
          <EmptyStrategies />
        ) : (
          <StrategiesTable strategies={strategies} />
        )}
      </div>
    </div>
  );
}

function EmptyStrategies() {
  return (
    <div className="border border-dashed border-zinc-800 bg-zinc-950 px-6 py-10">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        No strategies yet
      </p>
      <p className="mt-2 text-sm text-zinc-300">
        Strategies are inferred from imported runs. Import a bundle to register one.
      </p>
      <Link
        href="/import"
        className="mt-3 inline-block border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
      >
        Go to Import →
      </Link>
    </div>
  );
}

function StrategiesTable({ strategies }: { strategies: Strategy[] }) {
  return (
    <div className="overflow-x-auto border border-zinc-800">
      <table className="w-full min-w-[800px]">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/40">
            {COLUMNS.map((col, i) => (
              <th
                key={`${col}-${i}`}
                className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-zinc-500"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {strategies.map((strategy) => (
            <tr
              key={strategy.id}
              className="border-b border-zinc-900 font-mono text-xs text-zinc-300 last:border-b-0 hover:bg-zinc-900/30"
            >
              <td className="px-3 py-2 text-zinc-100">{strategy.name}</td>
              <td className="px-3 py-2 text-zinc-500">{strategy.slug}</td>
              <td className="px-3 py-2 text-zinc-400">{strategy.status}</td>
              <td className="px-3 py-2 text-zinc-400">
                {strategy.versions.length}
              </td>
              <td className="px-3 py-2 text-zinc-500">
                {strategy.tags && strategy.tags.length > 0
                  ? strategy.tags.join(", ")
                  : "—"}
              </td>
              <td className="px-3 py-2 text-zinc-500">
                {formatDate(strategy.created_at)}
              </td>
              <td className="px-3 py-2">
                <Link
                  href={`/strategies/${strategy.id}`}
                  className="border border-zinc-800 bg-zinc-900 px-2 py-1 text-[10px] uppercase tracking-widest text-zinc-200 hover:bg-zinc-800"
                >
                  Open →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().slice(0, 10);
}

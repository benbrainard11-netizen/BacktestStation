"use client";

import Link from "next/link";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import { ago, usePoll } from "@/lib/poll";

type Sim = {
  id: number;
  name: string;
  firm_profile_id: string;
  starting_balance: number;
  account_size: number;
  simulation_count: number;
  pass_rate: number | null;
  ev_after_fees: number | null;
  created_at: string;
};

function pct(v: number | null): string {
  if (v == null) return "—";
  const n = Math.abs(v) <= 1 ? v * 100 : v;
  return `${n.toFixed(1)}%`;
}

function money(v: number | null): string {
  if (v == null) return "—";
  return v.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

export default function PropFirmRunsPage() {
  const sims = usePoll<Sim[]>("/api/prop-firm/simulations", 60_000);

  const all = sims.kind === "data" ? sims.data : [];

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={
          sims.kind === "data"
            ? `SIMULATIONS · ${all.length} TOTAL`
            : "SIMULATIONS"
        }
        title="Simulation Runs"
        sub="All Monte Carlo prop-firm simulation runs. Sorted newest first."
        right={
          <Link href="/prop-firm/new" className="btn btn-primary">
            + New simulation
          </Link>
        }
      />

      <div className="mt-2">
        {sims.kind === "loading" && (
          <Card className="px-6 py-12 text-center text-[12px] text-ink-3">
            Loading…
          </Card>
        )}
        {sims.kind === "error" && (
          <Card className="border-neg/30 px-6 py-12 text-center text-[12px] text-neg">
            {sims.message}
          </Card>
        )}
        {sims.kind === "data" && all.length === 0 && (
          <Card>
            <EmptyState
              title="no simulations"
              blurb="No prop-firm simulations have been run yet."
              action={
                <Link href="/prop-firm/new" className="btn btn-primary">
                  + New simulation
                </Link>
              }
            />
          </Card>
        )}
        {sims.kind === "data" && all.length > 0 && (
          <Card>
            <CardHead title="All runs" />
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b border-line text-left">
                    {[
                      "Name",
                      "Firm",
                      "Paths",
                      "Pass rate",
                      "EV after fees",
                      "Account",
                      "Created",
                    ].map((h) => (
                      <th
                        key={h}
                        className="px-3 py-2 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {all.map((s) => {
                    const passTone =
                      s.pass_rate != null
                        ? s.pass_rate >= 0.5
                          ? "pos"
                          : "neg"
                        : "default";
                    return (
                      <tr
                        key={s.id}
                        className="border-b border-line last:border-b-0 hover:bg-bg-2"
                      >
                        <td className="px-3 py-2 font-mono font-semibold text-ink-0">
                          <Link
                            href={`/prop-firm/runs/${s.id}`}
                            className="hover:text-accent"
                          >
                            {s.name}
                          </Link>
                        </td>
                        <td className="px-3 py-2 text-ink-1">
                          {s.firm_profile_id}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-ink-2">
                          {s.simulation_count.toLocaleString()}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <Chip tone={passTone}>{pct(s.pass_rate)}</Chip>
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-ink-1">
                          {money(s.ev_after_fees)}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-ink-2">
                          {money(s.account_size)}
                        </td>
                        <td className="px-3 py-2 font-mono text-[10.5px] text-ink-3">
                          {ago(s.created_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

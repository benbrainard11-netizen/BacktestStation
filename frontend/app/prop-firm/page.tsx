"use client";

import Link from "next/link";

import { Card, CardHead, Chip, PageHeader, Stat } from "@/components/atoms";
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

export default function PropFirmDashboardPage() {
  const sims = usePoll<Sim[]>("/api/prop-firm/simulations", 60_000);

  const all = sims.kind === "data" ? sims.data : [];
  const featured = all[0]; // newest first
  const passed = all.filter(
    (s) => s.pass_rate != null && s.pass_rate >= 0.5,
  ).length;
  const positive = all.filter((s) => (s.ev_after_fees ?? 0) > 0).length;

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={
          sims.kind === "data"
            ? `PROP FIRM · ${all.length} SIMULATIONS`
            : "PROP FIRM"
        }
        title="Prop Firm Simulator"
        sub="Monte Carlo prop-firm pass/fail simulations against your backtest pools. MVP scope — fan envelopes, scope tearsheet, and per-firm editor coming in v2."
        right={
          <div className="flex items-center gap-2">
            <Link href="/prop-firm/firms" className="btn">
              Firms
            </Link>
            <Link href="/prop-firm/runs" className="btn">
              All Runs
            </Link>
            <Link href="/prop-firm/new" className="btn btn-primary">
              + New simulation
            </Link>
          </div>
        }
      />

      <div className="mt-2">
        <Chip tone="warn">
          [V2] fan envelope · scope tearsheet · firm editor — deferred
        </Chip>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-4">
        <div className="bg-bg-1">
          <Stat label="Total simulations" value={all.length} />
        </div>
        <div className="bg-bg-1">
          <Stat
            label="Passed"
            value={passed}
            sub={all.length > 0 ? pct(passed / all.length) : "—"}
            tone="pos"
          />
        </div>
        <div className="bg-bg-1">
          <Stat
            label="Positive EV"
            value={positive}
            sub={all.length > 0 ? pct(positive / all.length) : "—"}
            tone="accent"
          />
        </div>
        <div className="bg-bg-1">
          <Stat
            label="Last run"
            value={featured ? ago(featured.created_at) : "—"}
            sub={featured ? featured.name : "no runs yet"}
          />
        </div>
      </div>

      {featured ? (
        <Card className="mt-4">
          <CardHead
            eyebrow="featured · most recent"
            title={featured.name}
            right={
              <Link href={`/prop-firm/runs/${featured.id}`} className="btn">
                Open detail →
              </Link>
            }
          />
          <div className="grid grid-cols-2 gap-px overflow-hidden border-t border-line bg-line sm:grid-cols-4">
            <div className="bg-bg-1">
              <Stat
                label="Pass rate"
                value={pct(featured.pass_rate)}
                tone={
                  featured.pass_rate != null && featured.pass_rate >= 0.5
                    ? "pos"
                    : "neg"
                }
              />
            </div>
            <div className="bg-bg-1">
              <Stat
                label="EV after fees"
                value={money(featured.ev_after_fees)}
                tone={(featured.ev_after_fees ?? 0) > 0 ? "pos" : "neg"}
              />
            </div>
            <div className="bg-bg-1">
              <Stat
                label="Account"
                value={money(featured.account_size)}
                sub={featured.firm_profile_id}
              />
            </div>
            <div className="bg-bg-1">
              <Stat
                label="Paths"
                value={featured.simulation_count.toLocaleString()}
              />
            </div>
          </div>
        </Card>
      ) : (
        <Card className="mt-4">
          <EmptyState
            title="no simulations yet"
            blurb="Run your first prop-firm Monte Carlo simulation to see the dashboard populate."
            action={
              <Link href="/prop-firm/new" className="btn btn-primary">
                + New simulation
              </Link>
            }
          />
        </Card>
      )}
    </div>
  );
}

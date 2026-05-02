"use client";

import Link from "next/link";

import { Card, CardHead, Chip, PageHeader, Stat, StatusDot } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtPnl, fmtR, tone } from "@/lib/format";
import { ago, usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

type LiveStatus = components["schemas"]["LiveMonitorStatus"];
type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];

// TPT (TradersPost) prop-firm rule defaults — single account assumption per
// Ben's 2026-05-01 triage. Swap for a /api/prop-firm/profiles read once Ben
// runs more than one firm.
const TPT_RULES = {
  dailyLossUSD: 1500,
  trailingDrawdownUSD: 2000,
  startingBalanceUSD: 50_000,
};

export default function OverviewPage() {
  const live = usePoll<LiveStatus>("/api/monitor/live", 10_000);
  const strategies = usePoll<Strategy[]>("/api/strategies", 60_000);
  const backtests = usePoll<BacktestRun[]>("/api/backtests", 60_000);

  const liveOk = live.kind === "data" && live.data.source_exists;
  const todayPnl = liveOk ? live.data.today_pnl : null;
  const todayR = liveOk ? live.data.today_r : null;
  const tradesToday = liveOk ? live.data.trades_today : null;
  const stratList = strategies.kind === "data" ? strategies.data : [];
  const liveStrats = stratList.filter(
    (s) => s.status === "live" || s.status === "forward_test",
  );
  const runList = backtests.kind === "data" ? backtests.data : [];
  const lastRun = runList[0];

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        eyebrow={liveOk ? "OVERVIEW · LIVE" : "OVERVIEW"}
        title="Welcome back."
        sub="Today at a glance. Realized P&L, prop-firm compliance, recent activity."
        right={
          <Chip tone={liveOk ? "pos" : live.kind === "error" ? "neg" : "default"}>
            <StatusDot
              tone={liveOk ? "pos" : live.kind === "error" ? "neg" : "muted"}
              pulsing={liveOk}
              size={6}
            />
            {liveOk ? "backend ok" : live.kind === "error" ? "backend down" : "checking"}
          </Chip>
        }
      />

      <div className="mt-2 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat
            label="Today P&L"
            value={fmtPnl(todayPnl)}
            sub={tradesToday != null ? `${tradesToday} trades` : "no live data"}
            tone={tone(todayPnl)}
          />
        </Card>
        <Card>
          <Stat
            label="Today R"
            value={fmtR(todayR)}
            sub={liveOk ? live.data.current_session ?? "—" : "no live data"}
            tone={tone(todayR)}
          />
        </Card>
        <Card>
          <Stat
            label="Active strategies"
            value={String(liveStrats.length)}
            sub={`${stratList.length} total`}
          />
        </Card>
        <Card>
          <Stat
            label="Last backtest"
            value={lastRun ? `BT-${lastRun.id}` : "—"}
            sub={lastRun ? ago(lastRun.created_at) : "no runs yet"}
          />
        </Card>
      </div>

      {/* TPT compliance + Quick actions */}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <TptComplianceCard todayPnl={todayPnl} />
        <Card>
          <CardHead eyebrow="quick actions" title="Get going" />
          <div className="grid gap-2 px-4 py-4">
            <ActionRow href="/strategies" label="Open strategy catalog" />
            <ActionRow href="/backtests" label="Inspect a backtest run" />
            <ActionRow href="/monitor" label="Watch live monitor" />
            <ActionRow href="/settings" label="Customize the look" />
          </div>
        </Card>
      </div>
    </div>
  );
}

/**
 * TPT compliance — single-account assumption (one TradersPost relay).
 * Daily loss against TPT_RULES, drawdown placeholder until Ben wires firm rules.
 */
function TptComplianceCard({ todayPnl }: { todayPnl: number | null }) {
  // Daily-loss usage: how much of the $1,500 floor we've consumed today.
  const dailyLossUsed = todayPnl != null && todayPnl < 0 ? Math.abs(todayPnl) : 0;
  const dailyLossPct = Math.min(100, (dailyLossUsed / TPT_RULES.dailyLossUSD) * 100);
  const status: "compliant" | "at-risk" | "breached" =
    dailyLossPct >= 100
      ? "breached"
      : dailyLossPct >= 80
        ? "at-risk"
        : "compliant";
  const statusTone =
    status === "breached" ? "neg" : status === "at-risk" ? "warn" : "pos";

  // Trailing drawdown — placeholder. Real value needs /api/prop-firm wired.
  const trailingDDPct = 0;

  return (
    <Card>
      <CardHead
        eyebrow="prop firm"
        title="TPT compliance · today"
        right={
          <Chip tone={statusTone}>
            <StatusDot tone={statusTone} pulsing={status === "compliant"} />
            {status}
          </Chip>
        }
      />
      <div className="grid gap-4 px-4 py-4">
        <Meter
          label="Daily loss"
          used={dailyLossUsed}
          cap={TPT_RULES.dailyLossUSD}
          pct={dailyLossPct}
          format={(n) => `$${n.toFixed(0)}`}
          tone={statusTone}
        />
        <Meter
          label="Trailing drawdown"
          used={0}
          cap={TPT_RULES.trailingDrawdownUSD}
          pct={trailingDDPct}
          format={(n) => `$${n.toFixed(0)}`}
          tone="default"
          note="awaiting /api/prop-firm/profiles wiring"
        />
        <div className="flex items-baseline justify-between border-t border-line pt-3">
          <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
            ruleset
          </span>
          <span className="font-mono text-[11px] text-ink-2">
            TPT default · ${TPT_RULES.startingBalanceUSD.toLocaleString()} starting
          </span>
        </div>
      </div>
    </Card>
  );
}

function Meter({
  label,
  used,
  cap,
  pct,
  format,
  tone,
  note,
}: {
  label: string;
  used: number;
  cap: number;
  pct: number;
  format: (n: number) => string;
  tone: "pos" | "neg" | "warn" | "default";
  note?: string;
}) {
  const barColor =
    tone === "neg"
      ? "var(--neg)"
      : tone === "warn"
        ? "var(--warn)"
        : tone === "pos"
          ? "var(--pos)"
          : "var(--ink-3)";
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
          {label}
        </span>
        <span className="font-mono text-[12px] text-ink-1">
          {format(used)} / {format(cap)}
        </span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-bg-3">
        <div
          className="h-full rounded-full transition-[width] duration-300"
          style={{
            width: `${Math.max(2, pct)}%`,
            background: barColor,
            boxShadow: pct > 50 ? `0 0 6px ${barColor}` : undefined,
          }}
        />
      </div>
      {note && (
        <div className="mt-1 font-mono text-[10.5px] text-ink-4">{note}</div>
      )}
    </div>
  );
}

function ActionRow({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className={cn(
        "group flex items-center justify-between rounded border border-line bg-bg-2 px-3 py-2.5 text-sm text-ink-1 transition-colors",
        "hover:border-accent-line hover:bg-accent-soft hover:text-accent",
      )}
    >
      <span>{label}</span>
      <span className="font-mono text-[11px] text-ink-4 group-hover:text-accent">→</span>
    </Link>
  );
}

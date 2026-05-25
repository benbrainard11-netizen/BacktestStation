"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  asArray,
  asNumber,
  asObject,
  asString,
  fetchJson,
  readPath,
  type ProbeResult,
} from "@/lib/api/client";
import {
  formatAgo,
  formatBytes,
  formatDateTime,
  formatFixed,
  formatNumber,
} from "@/lib/format";

type ProbeKey =
  | "ops"
  | "api"
  | "r2Status"
  | "r2Freshness"
  | "coverage"
  | "live"
  | "ingester"
  | "r2Upload"
  | "liveTrades";

type Probe = {
  key: ProbeKey;
  label: string;
  path: string;
  critical: boolean;
};

const PROBES: Probe[] = [
  { key: "ops", label: "Ops Snapshot", path: "/api/ops/status", critical: true },
  { key: "api", label: "BacktestStation API", path: "/api/health", critical: true },
  {
    key: "r2Status",
    label: "R2 Inventory",
    path: "/api/dashboard/data-health/r2-status",
    critical: true,
  },
  {
    key: "r2Freshness",
    label: "R2 MBO Freshness",
    path: "/api/dashboard/data-health/r2-freshness",
    critical: true,
  },
  {
    key: "coverage",
    label: "Local Coverage",
    path: "/api/dashboard/data-health/local-coverage",
    critical: false,
  },
  { key: "live", label: "Live Bot", path: "/api/monitor/live", critical: false },
  {
    key: "ingester",
    label: "Live Ingester",
    path: "/api/monitor/ingester",
    critical: false,
  },
  {
    key: "r2Upload",
    label: "R2 Upload Log",
    path: "/api/monitor/r2-upload",
    critical: false,
  },
  {
    key: "liveTrades",
    label: "Live Trades Import",
    path: "/api/monitor/live-trades",
    critical: false,
  },
];

type ProbeMap = Partial<Record<ProbeKey, ProbeResult>>;

export function OpsMonitor() {
  const [probes, setProbes] = useState<ProbeMap>({});
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    const entries = await Promise.all(
      PROBES.map(async (probe) => [probe.key, await fetchJson(probe.path)] as const),
    );
    setProbes(Object.fromEntries(entries) as ProbeMap);
    setLastRefresh(Date.now());
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 60_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const alerts = useMemo(() => buildAlerts(probes), [probes]);
  const systemTone = alerts.some((a) => a.tone === "bad")
    ? "bad"
    : alerts.some((a) => a.tone === "warn")
      ? "warn"
      : "good";

  return (
    <main className="monitor-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">BacktestStation control room</p>
          <h1>Ops Monitor</h1>
          <p className="hero-copy">
            One screen for data freshness, R2 sync, local jobs, live feed health,
            and what still needs wiring.
          </p>
        </div>
        <div className="hero-actions">
          <div className={`system-light ${systemTone}`}>
            <span />
            {systemTone === "good"
              ? "stack clean"
              : systemTone === "warn"
                ? "needs attention"
                : "action needed"}
          </div>
          <button className="refresh-button" disabled={loading} onClick={() => void refresh()}>
            {loading ? "refreshing" : "refresh"}
          </button>
          <div className="refresh-meta">
            {lastRefresh ? `updated ${new Date(lastRefresh).toLocaleTimeString()}` : "not loaded"}
          </div>
        </div>
      </section>

      <section className="grid top-grid">
        <StatusCard
          title="API"
          probe={probes.api}
          goodText="online"
          badText="offline"
          lines={[
            ["endpoint", "/api/health"],
            ["status", probes.api?.ok ? "reachable" : probes.api?.error ?? "loading"],
          ]}
        />
        <R2FreshnessCard probe={probes.r2Freshness} />
        <R2InventoryCard probe={probes.r2Status} />
        <IngesterCard probe={probes.ingester} />
      </section>

      <section className="grid detail-grid">
        <CoverageCard probe={probes.coverage} />
        <LiveBotCard probe={probes.live} />
        <R2UploadCard probe={probes.r2Upload} />
        <LiveTradesCard probe={probes.liveTrades} />
      </section>

      <section className="grid bottom-grid">
        <OpsSnapshotCard probe={probes.ops} />
        <AlertsCard alerts={alerts} />
      </section>
    </main>
  );
}

function OpsSnapshotCard({ probe }: { probe?: ProbeResult }) {
  const data = probe?.data;
  const checks = asArray(readPath(data, "checks"));
  const counts: Record<string, number> = {};
  for (const raw of checks) {
    const status = asString(readPath(raw, "status"), "unknown");
    counts[status] = (counts[status] ?? 0) + 1;
  }
  const overall = asString(readPath(data, "overall_status"), probe?.ok ? "ok" : "loading");
  const tone: Tone =
    overall === "ok" ? "good" : overall === "fail" ? "bad" : overall === "warn" ? "warn" : "idle";
  return (
    <article className="card span-2">
      <CardHeader title="Unified Ops Snapshot" tone={tone} label={overall} />
      <div className="metric-row ops-counts">
        <Metric label="ok" value={formatNumber(counts.ok ?? 0)} />
        <Metric label="warn/fail" value={formatNumber((counts.warn ?? 0) + (counts.fail ?? 0))} />
        <Metric label="not wired" value={formatNumber(counts.not_wired ?? 0)} />
      </div>
      <div className="table ops-table">
        <div className="table-head grid-4">
          <span>check</span>
          <span>status</span>
          <span>updated</span>
          <span>message</span>
        </div>
        {checks.slice(0, 10).map((raw, idx) => {
          const item = asObject(raw);
          const status = asString(item.status, "unknown");
          return (
            <div className="table-row grid-4" key={`${asString(item.id)}-${idx}`}>
              <span>{asString(item.label)}</span>
              <span className={`pill ${status}`}>{status}</span>
              <span>{formatAgo(item.updated_at)}</span>
              <span>{asString(item.message)}</span>
            </div>
          );
        })}
        {checks.length === 0 ? <Empty text="Unified ops endpoint has not responded yet." /> : null}
      </div>
      <p className="small-muted">
        Warehouse: <strong>{asString(readPath(data, "warehouse_root"))}</strong>
      </p>
    </article>
  );
}

function StatusCard({
  title,
  probe,
  goodText,
  badText,
  lines,
}: {
  title: string;
  probe?: ProbeResult;
  goodText: string;
  badText: string;
  lines: [string, string][];
}) {
  const tone = probe?.ok ? "good" : probe ? "bad" : "idle";
  return (
    <article className={`card status-card ${tone}`}>
      <CardHeader title={title} tone={tone} label={tone === "good" ? goodText : badText} />
      <div className="line-list">
        {lines.map(([k, v]) => (
          <div key={k}>
            <span>{k}</span>
            <strong>{v}</strong>
          </div>
        ))}
      </div>
    </article>
  );
}

function R2FreshnessCard({ probe }: { probe?: ProbeResult }) {
  const data = probe?.data;
  const inventory = readPath(data, "inventory");
  const bucket = readPath(data, "bucket_objects");
  const local = readPath(data, "local");
  const ok = probe?.ok && readPath(data, "status") === "ok";
  const tone = ok ? "good" : probe?.ok ? "warn" : probe ? "bad" : "idle";
  return (
    <article className={`card status-card ${tone}`}>
      <CardHeader title="MBO in R2" tone={tone} label={asString(readPath(data, "status"), "loading")} />
      <div className="metric-row">
        <Metric label="R2 objects" value={formatNumber(readPath(bucket, "partition_count"))} />
        <Metric label="R2 GB" value={formatFixed(readPath(bucket, "total_gb"), 2)} />
        <Metric label="latest" value={asString(readPath(bucket, "latest_date"))} />
      </div>
      <div className="line-list compact">
        <div>
          <span>local objects</span>
          <strong>{formatNumber(readPath(local, "partition_count"))}</strong>
        </div>
        <div>
          <span>inventory objects</span>
          <strong>{formatNumber(readPath(inventory, "partition_count"))}</strong>
        </div>
        <div>
          <span>inventory matches bucket</span>
          <strong>{asString(readPath(data, "inventory_matches_bucket"))}</strong>
        </div>
        <div>
          <span>local matches inventory</span>
          <strong>{asString(readPath(data, "local_matches_inventory"))}</strong>
        </div>
      </div>
    </article>
  );
}

function R2InventoryCard({ probe }: { probe?: ProbeResult }) {
  const data = probe?.data;
  const reachable = readPath(data, "reachable") === true;
  const tone = reachable ? "good" : probe?.ok ? "warn" : probe ? "bad" : "idle";
  return (
    <article className={`card status-card ${tone}`}>
      <CardHeader title="R2 Inventory" tone={tone} label={reachable ? "reachable" : "check"} />
      <div className="metric-row">
        <Metric label="objects" value={formatNumber(readPath(data, "object_count"))} />
        <Metric label="total" value={formatBytes(readPath(data, "total_bytes"))} />
        <Metric label="age" value={formatAgeSeconds(readPath(data, "age_seconds"))} />
      </div>
      <p className="small-muted">
        Bucket: <strong>{asString(readPath(data, "bucket"))}</strong>
      </p>
    </article>
  );
}

function IngesterCard({ probe }: { probe?: ProbeResult }) {
  const data = probe?.data;
  const ticks = asNumber(readPath(data, "ticks_last_60s")) ?? 0;
  const running = probe?.ok && readPath(data, "status") === "running";
  const tone = running && ticks > 0 ? "good" : running ? "warn" : probe ? "bad" : "idle";
  return (
    <article className={`card status-card ${tone}`}>
      <CardHeader
        title="Live Feed"
        tone={tone}
        label={running ? (ticks > 0 ? "receiving" : "quiet") : "offline"}
      />
      <div className="metric-row">
        <Metric label="ticks 60s" value={formatNumber(ticks)} />
        <Metric label="received" value={formatNumber(readPath(data, "ticks_received"))} />
        <Metric label="schema" value={asString(readPath(data, "schema"))} />
      </div>
      <div className="line-list compact">
        <div>
          <span>last tick</span>
          <strong>{formatAgo(readPath(data, "last_tick_ts"))}</strong>
        </div>
        <div>
          <span>file</span>
          <strong>{shortPath(asString(readPath(data, "current_file")))}</strong>
        </div>
      </div>
    </article>
  );
}

function CoverageCard({ probe }: { probe?: ProbeResult }) {
  const rows = asArray(readPath(probe?.data, "items"));
  const topRows = rows.slice(0, 7);
  return (
    <article className="card span-2">
      <CardHeader title="Local Warehouse Coverage" tone={probe?.ok ? "good" : "warn"} label={`${rows.length} datasets`} />
      <div className="table">
        <div className="table-head grid-5">
          <span>dataset</span>
          <span>status</span>
          <span>parts</span>
          <span>latest</span>
          <span>size</span>
        </div>
        {topRows.map((row, idx) => {
          const obj = asObject(row);
          return (
            <div className="table-row grid-5" key={`${asString(obj.name)}-${idx}`}>
              <span>{asString(obj.name)}</span>
              <span className={`pill ${asString(obj.status)}`}>{asString(obj.status)}</span>
              <span>{formatNumber(obj.partition_count)}</span>
              <span>{asString(obj.latest_date)}</span>
              <span>{formatBytes(obj.total_bytes)}</span>
            </div>
          );
        })}
        {topRows.length === 0 ? <Empty text="No local coverage response yet." /> : null}
      </div>
    </article>
  );
}

function LiveBotCard({ probe }: { probe?: ProbeResult }) {
  const data = probe?.data;
  const sourceExists = readPath(data, "source_exists") === true;
  const tone = sourceExists ? "good" : probe?.ok ? "warn" : probe ? "bad" : "idle";
  return (
    <article className="card">
      <CardHeader title="Tradebot State" tone={tone} label={sourceExists ? "heartbeat" : "empty"} />
      <div className="line-list">
        <div>
          <span>strategy</span>
          <strong>{asString(readPath(data, "strategy_status"))}</strong>
        </div>
        <div>
          <span>symbol</span>
          <strong>{asString(readPath(data, "current_symbol"))}</strong>
        </div>
        <div>
          <span>PnL today</span>
          <strong>{formatFixed(readPath(data, "today_pnl"), 2)}</strong>
        </div>
        <div>
          <span>last heartbeat</span>
          <strong>{formatAgo(readPath(data, "last_heartbeat"))}</strong>
        </div>
      </div>
    </article>
  );
}

function R2UploadCard({ probe }: { probe?: ProbeResult }) {
  const last = readPath(probe?.data, "last_run");
  const errors = asArray(readPath(last, "errors")).length;
  const refused = asNumber(readPath(last, "refused")) ?? 0;
  const tone = !probe?.ok ? "bad" : errors || refused ? "warn" : "good";
  return (
    <article className="card">
      <CardHeader title="R2 Upload" tone={tone} label={tone === "good" ? "clean" : "check"} />
      <div className="metric-row">
        <Metric label="uploaded" value={formatNumber(readPath(last, "uploaded"))} />
        <Metric label="skipped" value={formatNumber(readPath(last, "skipped_existing"))} />
        <Metric label="refused" value={formatNumber(refused)} />
      </div>
      <p className="small-muted">Last run: {formatDateTime(readPath(last, "ts"))}</p>
    </article>
  );
}

function LiveTradesCard({ probe }: { probe?: ProbeResult }) {
  const data = probe?.data;
  const status = asString(readPath(data, "import_log_last_status"), "unknown");
  const tone = status === "ok" || status === "no_jsonl" ? "good" : status === "running" ? "warn" : "idle";
  return (
    <article className="card">
      <CardHeader title="Live Trades Import" tone={tone} label={status} />
      <div className="line-list">
        <div>
          <span>latest run</span>
          <strong>{asString(readPath(data, "last_run_name"))}</strong>
        </div>
        <div>
          <span>trades</span>
          <strong>{formatNumber(readPath(data, "trade_count"))}</strong>
        </div>
        <div>
          <span>inbox jsonl</span>
          <strong>{asString(readPath(data, "inbox_jsonl_exists"))}</strong>
        </div>
      </div>
    </article>
  );
}

function AlertsCard({ alerts }: { alerts: Alert[] }) {
  return (
    <article className="card span-2 alerts-card">
      <CardHeader title="Alerts" tone={alerts.length ? "warn" : "good"} label={`${alerts.length} active`} />
      {alerts.length ? (
        <div className="alerts">
          {alerts.map((alert) => (
            <div className={`alert ${alert.tone}`} key={alert.text}>
              <span>{alert.tone}</span>
              <strong>{alert.text}</strong>
            </div>
          ))}
        </div>
      ) : (
        <Empty text="No obvious stack alerts from the current endpoints." />
      )}
    </article>
  );
}

function NotWiredCard() {
  return (
    <article className="card roadmap-card">
      <CardHeader title="Not Wired Yet" tone="warn" label="next build" />
      <div className="roadmap-list">
        <div>
          <strong>InsyncApp bridge</strong>
          <span>BacktestStation needs a direct heartbeat from InsyncAPP_247.</span>
        </div>
        <div>
          <strong>Rithmic market data</strong>
          <span>Execution exists. Market data is still a probe/stub task.</span>
        </div>
        <div>
          <strong>MBO feature sync</strong>
          <span>Raw MBO is in R2. Processed orderflow matrices need R2 publishing.</span>
        </div>
      </div>
    </article>
  );
}

function CardHeader({
  title,
  tone,
  label,
}: {
  title: string;
  tone: Tone;
  label: string;
}) {
  return (
    <div className="card-header">
      <h2>{title}</h2>
      <span className={`chip ${tone}`}>{label}</span>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}

type Tone = "good" | "warn" | "bad" | "idle";
type Alert = { tone: Exclude<Tone, "idle">; text: string };

function buildAlerts(probes: ProbeMap): Alert[] {
  const out: Alert[] = [];
  for (const probe of PROBES) {
    const result = probes[probe.key];
    if (!result) continue;
    if (!result.ok && probe.critical) {
      out.push({ tone: "bad", text: `${probe.label} failed: ${result.error ?? result.status}` });
    } else if (!result.ok) {
      out.push({ tone: "warn", text: `${probe.label} unavailable: ${result.error ?? result.status}` });
    }
  }

  const fresh = probes.r2Freshness?.data;
  if (readPath(fresh, "inventory_matches_bucket") === false) {
    out.push({ tone: "bad", text: "R2 inventory does not match bucket objects." });
  }
  if (readPath(fresh, "local_matches_inventory") === false) {
    out.push({ tone: "warn", text: "This PC is missing some MBO objects that already exist in R2." });
  }

  const ticks = asNumber(readPath(probes.ingester?.data, "ticks_last_60s"));
  const ingesterOk = probes.ingester?.ok && readPath(probes.ingester.data, "status") === "running";
  if (ingesterOk && ticks === 0) {
    out.push({ tone: "warn", text: "Live ingester is running but no ticks arrived in the last 60 seconds." });
  }

  const lastUpload = readPath(probes.r2Upload?.data, "last_run");
  if ((asNumber(readPath(lastUpload, "refused")) ?? 0) > 0) {
    out.push({ tone: "warn", text: "Last R2 upload refused one or more partitions." });
  }
  if (asArray(readPath(lastUpload, "errors")).length > 0) {
    out.push({ tone: "bad", text: "Last R2 upload logged errors." });
  }

  for (const raw of asArray(readPath(probes.ops?.data, "checks"))) {
    const status = asString(readPath(raw, "status"), "unknown");
    const label = asString(readPath(raw, "label"), "Ops check");
    const message = asString(readPath(raw, "message"), "");
    if (status === "fail") out.push({ tone: "bad", text: `${label}: ${message}` });
    if (status === "warn") out.push({ tone: "warn", text: `${label}: ${message}` });
  }

  return out;
}

function formatAgeSeconds(value: unknown): string {
  const n = asNumber(value);
  if (n === null) return "-";
  if (n < 60) return `${n}s`;
  if (n < 3600) return `${Math.round(n / 60)}m`;
  if (n < 86_400) return `${Math.round(n / 3600)}h`;
  return `${Math.round(n / 86_400)}d`;
}

function shortPath(value: string): string {
  if (!value || value === "-") return "-";
  const parts = value.split(/[\\/]/);
  return parts.slice(-3).join("/");
}

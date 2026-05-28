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
import { formatAgo, formatBytes, formatDateTime, formatNumber } from "@/lib/format";

type ProbeKey =
  | "api"
  | "ingester"
  | "r2Upload"
  | "datasets"
  | "coverage"
  | "r2Status"
  | "r2Freshness"
  | "live"
  | "liveTrades"
  | "storedEvents";

type Probe = {
  key: ProbeKey;
  label: string;
  path: string;
  critical: boolean;
};

type ProbeMap = Partial<Record<ProbeKey, ProbeResult>>;
type JsonRow = Record<string, unknown>;
type Tone = "good" | "warn" | "bad" | "idle";

const PROBES: Probe[] = [
  { key: "api", label: "API", path: "/api/health", critical: true },
  { key: "ingester", label: "Raw live feed", path: "/api/monitor/ingester", critical: true },
  { key: "r2Upload", label: "R2 upload job", path: "/api/monitor/r2-upload", critical: true },
  { key: "datasets", label: "Dataset registry", path: "/api/datasets?limit=500", critical: false },
  { key: "coverage", label: "Local coverage scan", path: "/api/datasets/coverage", critical: false },
  { key: "r2Status", label: "R2 inventory", path: "/api/dashboard/data-health/r2-status", critical: false },
  { key: "r2Freshness", label: "R2 freshness", path: "/api/dashboard/data-health/r2-freshness", critical: false },
  { key: "live", label: "Live bot state", path: "/api/monitor/live", critical: false },
  { key: "liveTrades", label: "Live trades import", path: "/api/monitor/live-trades", critical: false },
  { key: "storedEvents", label: "Stored event sample", path: "/api/research/events?limit=100", critical: false },
];

export function DataWarehouseMonitor() {
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

  const ingester = probes.ingester?.data;
  const upload = probes.r2Upload?.data;
  const uploadLast = readPath(upload, "last_run");
  const datasets = useMemo(() => rowsFrom(probes.datasets?.data), [probes.datasets]);
  const coverageRows = useMemo(() => rowsFrom(readPath(probes.coverage?.data, "rows")), [probes.coverage]);
  const storedEvents = useMemo(() => rowsFrom(probes.storedEvents?.data), [probes.storedEvents]);
  const r2Freshness = probes.r2Freshness?.data;
  const r2Status = probes.r2Status?.data;
  const dataRows = coverageRows.length > 0 ? coverageRows : datasets;

  const ticksLast60 = asNumber(readPath(ingester, "ticks_last_60s")) ?? 0;
  const feedRunning = probes.ingester?.ok && readPath(ingester, "status") === "running";
  const feedTone: Tone = feedRunning && ticksLast60 > 0 ? "good" : feedRunning ? "warn" : probes.ingester ? "bad" : "idle";
  const uploadErrors = asArray(readPath(uploadLast, "errors")).length;
  const refused = asNumber(readPath(uploadLast, "refused")) ?? 0;
  const uploadTone: Tone = !probes.r2Upload ? "idle" : probes.r2Upload.ok && uploadErrors === 0 && refused === 0 ? "good" : "warn";
  const r2ObjectCount =
    asNumber(readPath(r2Freshness, "bucket_objects.partition_count")) ??
    asNumber(readPath(r2Status, "object_count")) ??
    asNumber(readPath(uploadLast, "inventory_partitions"));
  const r2Bytes =
    asNumber(readPath(r2Freshness, "bucket_objects.total_bytes")) ??
    asNumber(readPath(r2Status, "total_bytes"));
  const liveBotExists = readPath(probes.live?.data, "source_exists") === true;
  const systemTone = feedTone === "good" && uploadTone === "good" ? "good" : feedTone === "bad" ? "bad" : "warn";

  const checks = useMemo(() => buildChecks(probes), [probes]);
  const storedFamilyCounts = useMemo(
    () => topCounts(storedEvents, (row) => asString(row.feature_name, "unknown"), 8),
    [storedEvents],
  );

  return (
    <main className="monitor-shell database-shell">
      <section className="hero-panel database-hero">
        <div>
          <p className="eyebrow">Data warehouse</p>
          <h1>Data Monitor</h1>
          <p className="hero-copy">
            One place to see whether raw market data is flowing, local files are being written,
            R2 uploads are clean, and stored database data is visible.
          </p>
        </div>
        <div className="hero-actions">
          <div className={`system-light ${systemTone}`}>
            <span />
            {systemTone === "good" ? "data flowing" : systemTone === "bad" ? "feed problem" : "check data"}
          </div>
          <button className="refresh-button" disabled={loading} onClick={() => void refresh()}>
            {loading ? "refreshing" : "refresh data"}
          </button>
          <div className="refresh-meta">
            {lastRefresh ? `updated ${new Date(lastRefresh).toLocaleTimeString()}` : "not loaded"}
          </div>
        </div>
      </section>

      <section className="db-metric-grid">
        <BigMetric label="raw feed" value={feedRunning ? "running" : "offline"} sublabel={asString(readPath(ingester, "schema"))} tone={feedTone} />
        <BigMetric label="ticks last 60s" value={formatNumber(ticksLast60)} sublabel={formatAgo(readPath(ingester, "last_tick_ts"))} tone={feedTone} />
        <BigMetric label="current raw file" value={fileName(asString(readPath(ingester, "current_file")))} sublabel={asString(readPath(ingester, "current_date"))} tone={feedTone} />
        <BigMetric label="R2 last upload" value={formatNumber(readPath(uploadLast, "uploaded"))} sublabel={formatDateTime(readPath(uploadLast, "ts"))} tone={uploadTone} />
        <BigMetric label="R2 inventory parts" value={formatNumber(r2ObjectCount)} sublabel={formatBytes(r2Bytes)} tone={uploadTone} />
        <BigMetric label="stored datasets" value={formatNumber(dataRows.length)} sublabel={coverageRows.length ? "coverage rows" : "registry rows"} tone={dataRows.length ? "good" : "warn"} />
      </section>

      <section className="db-browser-grid">
        <RawFeedCard probe={probes.ingester} />
        <R2UploadCard probe={probes.r2Upload} />
        <DataChecklistCard checks={checks} />
      </section>

      <section className="db-browser-grid">
        <StoredDataCard rows={dataRows} coverageProbe={probes.coverage} datasetsProbe={probes.datasets} />
        <CloudWarehouseCard status={probes.r2Status} freshness={probes.r2Freshness} upload={probes.r2Upload} />
      </section>

      <section className="db-browser-grid">
        <LocalRuntimeCard live={probes.live} liveTrades={probes.liveTrades} liveBotExists={liveBotExists} />
        <StoredDatabaseSampleCard events={storedEvents} counts={storedFamilyCounts} />
        <PathsCard ingester={probes.ingester} upload={probes.r2Upload} liveTrades={probes.liveTrades} />
      </section>
    </main>
  );
}

function RawFeedCard({ probe }: { probe?: ProbeResult }) {
  const data = probe?.data;
  const ticks = asNumber(readPath(data, "ticks_last_60s")) ?? 0;
  const running = probe?.ok && readPath(data, "status") === "running";
  const tone: Tone = running && ticks > 0 ? "good" : running ? "warn" : probe ? "bad" : "idle";
  return (
    <article className="card db-panel db-panel-wide">
      <CardHeader title="Raw Feed Right Now" tone={tone} label={running ? (ticks > 0 ? "receiving" : "quiet") : "offline"} />
      <div className="metric-row">
        <Metric label="ticks 60s" value={formatNumber(ticks)} />
        <Metric label="total ticks" value={formatNumber(readPath(data, "ticks_received"))} />
        <Metric label="reconnects" value={formatNumber(readPath(data, "reconnect_count"))} />
      </div>
      <div className="warehouse-line-grid">
        <Line label="dataset" value={asString(readPath(data, "dataset"))} />
        <Line label="schema" value={asString(readPath(data, "schema"))} />
        <Line label="symbols" value={asArray(readPath(data, "symbols")).map((item) => asString(item)).join(", ") || "-"} />
        <Line label="last tick" value={formatAgo(readPath(data, "last_tick_ts"))} />
        <Line label="started" value={formatDateTime(readPath(data, "started_at"))} />
        <Line label="current file" value={asString(readPath(data, "current_file"))} wide />
      </div>
      {asString(readPath(data, "last_error"), "") ? (
        <p className="db-warning">Last feed error: {asString(readPath(data, "last_error"))}</p>
      ) : null}
    </article>
  );
}

function R2UploadCard({ probe }: { probe?: ProbeResult }) {
  const data = probe?.data;
  const last = readPath(data, "last_run");
  const errors = asArray(readPath(last, "errors"));
  const refused = asNumber(readPath(last, "refused")) ?? 0;
  const tone: Tone = !probe ? "idle" : probe.ok && errors.length === 0 && refused === 0 ? "good" : "warn";
  const recent = rowsFrom(readPath(data, "recent_runs"));
  return (
    <article className="card db-panel">
      <CardHeader title="R2 Upload Job" tone={tone} label={tone === "good" ? "clean" : "check"} />
      <div className="metric-row">
        <Metric label="uploaded" value={formatNumber(readPath(last, "uploaded"))} />
        <Metric label="skipped" value={formatNumber(readPath(last, "skipped_existing"))} />
        <Metric label="refused" value={formatNumber(refused)} />
      </div>
      <div className="line-list compact">
        <Line label="last run" value={formatDateTime(readPath(last, "ts"))} />
        <Line label="validated" value={formatNumber(readPath(last, "validated"))} />
        <Line label="inventory parts" value={formatNumber(readPath(last, "inventory_partitions"))} />
      </div>
      <div className="db-mini-table">
        {recent.slice(0, 5).map((row, idx) => (
          <div key={`${asString(row.ts)}-${idx}`}>
            <span>{formatDateTime(row.ts)}</span>
            <strong>{formatNumber(row.uploaded)} up / {formatNumber(row.skipped_existing)} skip</strong>
          </div>
        ))}
      </div>
    </article>
  );
}

function DataChecklistCard({ checks }: { checks: DataCheck[] }) {
  return (
    <article className="card db-panel">
      <CardHeader title="Data Health Checklist" tone={checks.some((check) => check.tone === "bad") ? "bad" : checks.some((check) => check.tone === "warn") ? "warn" : "good"} label={`${checks.length} checks`} />
      <div className="warehouse-checks">
        {checks.map((check) => (
          <div className={`warehouse-check ${check.tone}`} key={check.label}>
            <span>{check.label}</span>
            <strong>{check.value}</strong>
            <small>{check.detail}</small>
          </div>
        ))}
      </div>
    </article>
  );
}

function StoredDataCard({
  rows,
  coverageProbe,
  datasetsProbe,
}: {
  rows: JsonRow[];
  coverageProbe?: ProbeResult;
  datasetsProbe?: ProbeResult;
}) {
  const tone: Tone = rows.length ? "good" : coverageProbe?.ok || datasetsProbe?.ok ? "warn" : "bad";
  return (
    <article className="card db-panel db-panel-wide">
      <CardHeader title="Stored Data Coverage" tone={tone} label={`${rows.length} rows`} />
      <div className="db-coverage-table">
        <div className="db-coverage-head">
          <span>dataset</span>
          <span>schema</span>
          <span>status</span>
          <span>parts</span>
          <span>latest</span>
          <span>size</span>
        </div>
        {rows.slice(0, 14).map((row, idx) => (
          <div className="db-coverage-row" key={`${asString(row.name, asString(row.dataset_code))}-${idx}`}>
            <span>{asString(row.name, asString(row.dataset_code))}</span>
            <span>{asString(row.schema, asString(row.data_schema))}</span>
            <span className={`pill ${asString(row.status)}`}>{asString(row.status, "seen")}</span>
            <span>{formatNumber(row.partition_count)}</span>
            <span>{asString(row.latest_date, asString(row.end_date))}</span>
            <span>{formatBytes(row.total_bytes)}</span>
          </div>
        ))}
        {rows.length === 0 ? (
          <Empty text="No dataset registry or coverage rows are populated yet. The raw feed can still be running; this means the warehouse scan/index needs wiring or a refresh." />
        ) : null}
      </div>
    </article>
  );
}

function CloudWarehouseCard({
  status,
  freshness,
  upload,
}: {
  status?: ProbeResult;
  freshness?: ProbeResult;
  upload?: ProbeResult;
}) {
  const fresh = freshness?.data;
  const inv = status?.data;
  const lastUpload = readPath(upload?.data, "last_run");
  const bucketObjects = readPath(fresh, "bucket_objects");
  const tone: Tone = status?.ok || freshness?.ok || upload?.ok ? "good" : "warn";
  return (
    <article className="card db-panel">
      <CardHeader title="Cloud Stored Data" tone={tone} label={tone === "good" ? "visible" : "not wired"} />
      <div className="metric-row">
        <Metric label="objects" value={formatNumber(readPath(bucketObjects, "partition_count") ?? readPath(inv, "object_count") ?? readPath(lastUpload, "inventory_partitions"))} />
        <Metric label="size" value={formatBytes(readPath(bucketObjects, "total_bytes") ?? readPath(inv, "total_bytes"))} />
        <Metric label="latest" value={asString(readPath(bucketObjects, "latest_date"))} />
      </div>
      <div className="line-list compact">
        <Line label="bucket" value={asString(readPath(fresh, "bucket"), asString(readPath(inv, "bucket")))} />
        <Line label="R2 freshness endpoint" value={freshness?.ok ? "online" : freshness ? `missing (${freshness.status})` : "loading"} />
        <Line label="R2 inventory endpoint" value={status?.ok ? "online" : status ? `missing (${status.status})` : "loading"} />
        <Line label="upload log" value={upload?.ok ? "online" : "missing"} />
      </div>
    </article>
  );
}

function LocalRuntimeCard({
  live,
  liveTrades,
  liveBotExists,
}: {
  live?: ProbeResult;
  liveTrades?: ProbeResult;
  liveBotExists: boolean;
}) {
  const tradeStatus = asString(readPath(liveTrades?.data, "import_log_last_status"), "unknown");
  return (
    <article className="card db-panel">
      <CardHeader title="Local Runtime Data" tone={liveBotExists ? "good" : "warn"} label={liveBotExists ? "heartbeat" : "no bot file"} />
      <div className="line-list">
        <Line label="live status file" value={liveBotExists ? "present" : "missing"} />
        <Line label="strategy" value={asString(readPath(live?.data, "strategy_status"))} />
        <Line label="last heartbeat" value={formatAgo(readPath(live?.data, "last_heartbeat"))} />
        <Line label="trade import" value={tradeStatus} />
        <Line label="trade count" value={formatNumber(readPath(liveTrades?.data, "trade_count"))} />
      </div>
    </article>
  );
}

function StoredDatabaseSampleCard({
  events,
  counts,
}: {
  events: JsonRow[];
  counts: { label: string; count: number; pct: number }[];
}) {
  const latest = latestTimestamp(events, "bar_end_utc");
  return (
    <article className="card db-panel">
      <CardHeader title="Stored DB Sample" tone={events.length ? "good" : "warn"} label={`${events.length} rows loaded`} />
      <p className="small-muted">
        This is only a light stored-data sanity check, not a research browser.
      </p>
      <div className="line-list compact">
        <Line label="latest stored event" value={formatDateTime(latest)} />
        <Line label="families in sample" value={formatNumber(counts.length)} />
      </div>
      <div className="db-bars warehouse-small-bars">
        {counts.slice(0, 5).map((row) => (
          <div className="db-bar-row" key={row.label}>
            <div>
              <span>{row.label}</span>
              <strong>{formatNumber(row.count)}</strong>
            </div>
            <div className="db-bar-track">
              <span style={{ width: `${Math.max(4, row.pct * 100)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

function PathsCard({
  ingester,
  upload,
  liveTrades,
}: {
  ingester?: ProbeResult;
  upload?: ProbeResult;
  liveTrades?: ProbeResult;
}) {
  return (
    <article className="card db-panel">
      <CardHeader title="Important Paths" tone="good" label="local" />
      <div className="warehouse-paths">
        <PathLine label="raw file" value={asString(readPath(ingester?.data, "current_file"))} />
        <PathLine label="R2 upload log" value={asString(readPath(upload?.data, "log_path"))} />
        <PathLine label="trade inbox" value={asString(readPath(liveTrades?.data, "inbox_dir"))} />
        <PathLine label="trade import log" value={asString(readPath(liveTrades?.data, "import_log_path"))} />
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

function BigMetric({
  label,
  value,
  sublabel,
  tone,
}: {
  label: string;
  value: string;
  sublabel: string;
  tone: Tone;
}) {
  return (
    <article className={`db-big-metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{sublabel}</small>
    </article>
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

function Line({
  label,
  value,
  wide = false,
}: {
  label: string;
  value: string;
  wide?: boolean;
}) {
  return (
    <div className={wide ? "wide" : undefined}>
      <span>{label}</span>
      <strong>{value || "-"}</strong>
    </div>
  );
}

function PathLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong title={value}>{value}</strong>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}

type DataCheck = {
  label: string;
  value: string;
  detail: string;
  tone: Tone;
};

function buildChecks(probes: ProbeMap): DataCheck[] {
  const out: DataCheck[] = [];
  const ingester = probes.ingester?.data;
  const ticks = asNumber(readPath(ingester, "ticks_last_60s")) ?? 0;
  const feedRunning = probes.ingester?.ok && readPath(ingester, "status") === "running";
  out.push({
    label: "raw feed",
    value: feedRunning ? (ticks > 0 ? "receiving" : "quiet") : "offline",
    detail: `${formatNumber(ticks)} ticks in 60s`,
    tone: feedRunning && ticks > 0 ? "good" : feedRunning ? "warn" : "bad",
  });

  const uploadLast = readPath(probes.r2Upload?.data, "last_run");
  const uploadErrors = asArray(readPath(uploadLast, "errors")).length;
  const refused = asNumber(readPath(uploadLast, "refused")) ?? 0;
  out.push({
    label: "R2 upload",
    value: probes.r2Upload?.ok && uploadErrors === 0 && refused === 0 ? "clean" : "check",
    detail: `last run ${formatDateTime(readPath(uploadLast, "ts"))}`,
    tone: probes.r2Upload?.ok && uploadErrors === 0 && refused === 0 ? "good" : "warn",
  });

  const coverageRows = rowsFrom(readPath(probes.coverage?.data, "rows"));
  out.push({
    label: "coverage scan",
    value: coverageRows.length ? `${coverageRows.length} rows` : "empty",
    detail: probes.coverage?.ok ? "endpoint online" : `endpoint ${probes.coverage?.status ?? "loading"}`,
    tone: coverageRows.length ? "good" : "warn",
  });

  const datasetRows = rowsFrom(probes.datasets?.data);
  out.push({
    label: "dataset registry",
    value: datasetRows.length ? `${datasetRows.length} rows` : "empty",
    detail: probes.datasets?.ok ? "endpoint online" : `endpoint ${probes.datasets?.status ?? "loading"}`,
    tone: datasetRows.length ? "good" : "warn",
  });

  out.push({
    label: "R2 inventory endpoint",
    value: probes.r2Status?.ok ? "online" : "not wired",
    detail: probes.r2Status?.ok ? "freshness visible" : `status ${probes.r2Status?.status ?? "loading"}`,
    tone: probes.r2Status?.ok ? "good" : "warn",
  });

  out.push({
    label: "live bot file",
    value: readPath(probes.live?.data, "source_exists") === true ? "present" : "missing",
    detail: asString(readPath(probes.live?.data, "source_path")),
    tone: readPath(probes.live?.data, "source_exists") === true ? "good" : "warn",
  });

  out.push({
    label: "trade import",
    value: asString(readPath(probes.liveTrades?.data, "import_log_last_status"), "unknown"),
    detail: asString(readPath(probes.liveTrades?.data, "inbox_dir")),
    tone: probes.liveTrades?.ok ? "good" : "warn",
  });

  return out;
}

function rowsFrom(value: unknown): JsonRow[] {
  return asArray(value).map(asObject).filter((row) => Object.keys(row).length > 0);
}

function topCounts(rows: JsonRow[], getKey: (row: JsonRow) => string, limit: number) {
  const counts = new Map<string, number>();
  for (const row of rows) {
    const key = getKey(row) || "unknown";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  const max = Math.max(...counts.values(), 1);
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([label, count]) => ({ label, count, pct: count / max }));
}

function latestTimestamp(rows: JsonRow[], key: string): string {
  let chosen = 0;
  let chosenRaw = "";
  for (const row of rows) {
    const raw = asString(row[key], "");
    const ts = raw ? new Date(raw).getTime() : Number.NaN;
    if (Number.isNaN(ts)) continue;
    if (ts > chosen) {
      chosen = ts;
      chosenRaw = raw;
    }
  }
  return chosenRaw;
}

function fileName(value: string): string {
  if (!value || value === "-") return "-";
  const parts = value.split(/[\\/]/);
  return parts[parts.length - 1] || value;
}

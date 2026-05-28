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
import { formatBytes, formatDateTime, formatFixed, formatNumber } from "@/lib/format";

type ProbeKey =
  | "features"
  | "events"
  | "datasets"
  | "coverage"
  | "r2Status"
  | "r2Freshness"
  | "hypotheses"
  | "trialGroups"
  | "locks"
  | "candidates"
  | "validation";

type Probe = {
  key: ProbeKey;
  label: string;
  path: string;
};

type ProbeMap = Partial<Record<ProbeKey, ProbeResult>>;
type JsonRow = Record<string, unknown>;
type CountRow = { label: string; count: number; pct: number };

const PROBES: Probe[] = [
  { key: "features", label: "Feature primitives", path: "/api/features" },
  { key: "events", label: "Research events", path: "/api/research/events?limit=500" },
  { key: "datasets", label: "Dataset registry", path: "/api/datasets?limit=500" },
  { key: "coverage", label: "Dataset coverage", path: "/api/datasets/coverage" },
  { key: "r2Status", label: "R2 inventory", path: "/api/dashboard/data-health/r2-status" },
  { key: "r2Freshness", label: "R2 MBO freshness", path: "/api/dashboard/data-health/r2-freshness" },
  { key: "hypotheses", label: "Hypotheses", path: "/api/dashboard/trials/hypotheses" },
  { key: "trialGroups", label: "Trial groups", path: "/api/dashboard/trials/groups" },
  { key: "locks", label: "Trial locks", path: "/api/dashboard/trials/locks/recent" },
  { key: "candidates", label: "Model candidates", path: "/api/dashboard/candidates/list" },
  { key: "validation", label: "Latest validation", path: "/api/dashboard/data-health/latest-validation" },
];

export function DatabaseBrowser() {
  const [probes, setProbes] = useState<ProbeMap>({});
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<number | null>(null);
  const [featureFilter, setFeatureFilter] = useState("all");
  const [symbolFilter, setSymbolFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [selectedEventKey, setSelectedEventKey] = useState<string | null>(null);

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
  }, [refresh]);

  const features = useMemo(() => rowsFrom(probes.features?.data), [probes.features]);
  const events = useMemo(() => rowsFrom(probes.events?.data), [probes.events]);
  const datasets = useMemo(() => rowsFrom(probes.datasets?.data), [probes.datasets]);
  const coverageRows = useMemo(() => rowsFrom(readPath(probes.coverage?.data, "rows")), [probes.coverage]);

  const featureOptions = useMemo(
    () => uniqueSorted(events.map((row) => asString(row.feature_name, ""))),
    [events],
  );
  const symbolOptions = useMemo(
    () => uniqueSorted(events.map((row) => asString(row.primary_symbol, ""))),
    [events],
  );
  const typeOptions = useMemo(
    () => uniqueSorted(events.map((row) => asString(row.event_type, ""))),
    [events],
  );

  const filteredEvents = useMemo(
    () =>
      events.filter((row) => {
        const matchesFeature = featureFilter === "all" || asString(row.feature_name) === featureFilter;
        const matchesSymbol = symbolFilter === "all" || asString(row.primary_symbol) === symbolFilter;
        const matchesType = typeFilter === "all" || asString(row.event_type) === typeFilter;
        return matchesFeature && matchesSymbol && matchesType;
      }),
    [events, featureFilter, symbolFilter, typeFilter],
  );

  useEffect(() => {
    if (!selectedEventKey && filteredEvents.length > 0) {
      setSelectedEventKey(eventKey(filteredEvents[0]));
    }
  }, [filteredEvents, selectedEventKey]);

  const selectedEvent = useMemo(() => {
    if (filteredEvents.length === 0) return null;
    return filteredEvents.find((row) => eventKey(row) === selectedEventKey) ?? filteredEvents[0];
  }, [filteredEvents, selectedEventKey]);

  const featureCounts = useMemo(
    () => topCounts(events, (row) => asString(row.feature_name, "unknown"), 10),
    [events],
  );
  const symbolCounts = useMemo(
    () => topCounts(events, (row) => asString(row.primary_symbol, "unknown"), 10),
    [events],
  );
  const eventTypeCounts = useMemo(
    () => topCounts(events, (row) => asString(row.event_type, "unknown"), 10),
    [events],
  );
  const roleCounts = useMemo(
    () => {
      const counts = new Map<string, number>();
      for (const feature of features) {
        for (const role of asArray(feature.roles)) {
          const key = asString(role, "");
          if (key) counts.set(key, (counts.get(key) ?? 0) + 1);
        }
      }
      const total = features.length || 1;
      return [...counts.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .map(([label, count]) => ({ label, count, pct: count / total }));
    },
    [features],
  );

  const latestEventTs = latestTimestamp(events, "bar_end_utc");
  const earliestEventTs = earliestTimestamp(events, "bar_end_utc");
  const r2Freshness = probes.r2Freshness?.data;
  const r2Status = probes.r2Status?.data;
  const r2Objects =
    asNumber(readPath(r2Freshness, "bucket_objects.partition_count")) ??
    asNumber(readPath(r2Status, "object_count"));
  const r2Bytes =
    asNumber(readPath(r2Freshness, "bucket_objects.total_bytes")) ??
    asNumber(readPath(r2Status, "total_bytes"));
  const datasetRows = coverageRows.length > 0 ? coverageRows : datasets;
  const candidates = rowsFrom(readPath(probes.candidates?.data, "candidates"));
  const locks = rowsFrom(readPath(probes.locks?.data, "locks"));
  const hypotheses = rowsFrom(readPath(probes.hypotheses?.data, "hypotheses"));
  const groups = rowsFrom(readPath(probes.trialGroups?.data, "groups"));
  const availableProbeCount = PROBES.filter((probe) => probes[probe.key]?.ok).length;
  const healthTone = availableProbeCount >= 5 ? "good" : availableProbeCount >= 2 ? "warn" : "bad";

  return (
    <main className="monitor-shell database-shell">
      <section className="hero-panel database-hero">
        <div>
          <p className="eyebrow">Research database</p>
          <h1>Data Map</h1>
          <p className="hero-copy">
            Browse what BacktestStation can currently see: detector events, feature primitives,
            local/cloud coverage, trial locks, and candidate model metadata.
          </p>
        </div>
        <div className="hero-actions">
          <div className={`system-light ${healthTone}`}>
            <span />
            {availableProbeCount}/{PROBES.length} endpoints
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
        <BigMetric
          label="research events"
          sublabel="loaded slice"
          value={formatNumber(events.length)}
        />
        <BigMetric
          label="event families"
          sublabel="from loaded events"
          value={formatNumber(featureOptions.length)}
        />
        <BigMetric
          label="symbols"
          sublabel="from loaded events"
          value={formatNumber(symbolOptions.length)}
        />
        <BigMetric
          label="feature primitives"
          sublabel="strategy builder"
          value={formatNumber(features.length)}
        />
        <BigMetric
          label="R2 MBO objects"
          sublabel={asString(readPath(r2Freshness, "bucket"), asString(readPath(r2Status, "bucket")))}
          value={formatNumber(r2Objects)}
        />
        <BigMetric
          label="R2 MBO size"
          sublabel="bucket/inventory view"
          value={formatBytes(r2Bytes)}
        />
      </section>

      <section className="db-browser-grid">
        <article className="card db-panel db-panel-wide">
          <CardHeader title="Research Events" tone={probes.events?.ok ? "good" : "warn"} label={`${filteredEvents.length} shown`} />
          <div className="db-filter-bar">
            <FilterSelect label="family" value={featureFilter} options={featureOptions} onChange={setFeatureFilter} />
            <FilterSelect label="symbol" value={symbolFilter} options={symbolOptions} onChange={setSymbolFilter} />
            <FilterSelect label="type" value={typeFilter} options={typeOptions} onChange={setTypeFilter} />
            <button
              className="db-clear-button"
              onClick={() => {
                setFeatureFilter("all");
                setSymbolFilter("all");
                setTypeFilter("all");
              }}
              type="button"
            >
              clear filters
            </button>
          </div>
          <div className="db-event-table">
            <div className="db-event-head">
              <span>family</span>
              <span>symbol</span>
              <span>type</span>
              <span>side</span>
              <span>time</span>
            </div>
            {filteredEvents.slice(0, 80).map((row) => {
              const key = eventKey(row);
              return (
                <button
                  className={selectedEvent && eventKey(selectedEvent) === key ? "db-event-row active" : "db-event-row"}
                  key={key}
                  onClick={() => setSelectedEventKey(key)}
                  type="button"
                >
                  <span>{asString(row.feature_name)}</span>
                  <span>{asString(row.primary_symbol)}</span>
                  <span>{asString(row.event_type)}</span>
                  <span>{asString(row.side)}</span>
                  <span>{formatDateTime(row.bar_end_utc)}</span>
                </button>
              );
            })}
            {filteredEvents.length === 0 ? <Empty text="No events match the current filters." /> : null}
          </div>
          <p className="small-muted">
            Loaded range: <strong>{formatDateTime(earliestEventTs)}</strong> to{" "}
            <strong>{formatDateTime(latestEventTs)}</strong>. This is a browser slice, not the full DB total.
          </p>
        </article>

        <EventDetailCard event={selectedEvent} />
      </section>

      <section className="db-browser-grid">
        <DistributionCard
          title="Event Families"
          label={`${featureCounts.length} families`}
          rows={featureCounts}
        />
        <DistributionCard
          title="Symbols"
          label={`${symbolCounts.length} symbols`}
          rows={symbolCounts}
        />
        <DistributionCard
          title="Event Types"
          label={`${eventTypeCounts.length} types`}
          rows={eventTypeCounts}
        />
      </section>

      <section className="db-browser-grid">
        <article className="card db-panel db-panel-wide">
          <CardHeader title="Feature Primitives" tone={probes.features?.ok ? "good" : "warn"} label={`${features.length} registered`} />
          <div className="db-feature-grid">
            {features.map((feature) => (
              <FeatureCard feature={feature} key={asString(feature.name)} />
            ))}
            {features.length === 0 ? <Empty text="No feature primitive registry response yet." /> : null}
          </div>
        </article>
        <DistributionCard title="Primitive Roles" label={`${roleCounts.length} roles`} rows={roleCounts} />
      </section>

      <section className="db-browser-grid">
        <DataCoverageCard rows={datasetRows} coverageProbe={probes.coverage} datasetsProbe={probes.datasets} />
        <R2DatabaseCard status={probes.r2Status} freshness={probes.r2Freshness} />
        <ResearchProtocolCard
          candidates={candidates}
          groups={groups}
          hypotheses={hypotheses}
          locks={locks}
          validation={probes.validation}
        />
      </section>
    </main>
  );
}

function EventDetailCard({ event }: { event: JsonRow | null }) {
  if (!event) {
    return (
      <article className="card db-panel">
        <CardHeader title="Event Detail" tone="warn" label="empty" />
        <Empty text="Select a research event to inspect its data, context, outcomes, and replay pointer." />
      </article>
    );
  }

  const eventData = asObject(event.event_data);
  const context = asObject(event.context);
  const outcomes = asObject(event.outcomes);
  const replayPointer = asObject(event.replay_pointer);

  return (
    <article className="card db-panel db-detail-card">
      <CardHeader title="Event Detail" tone="good" label={asString(event.feature_name)} />
      <div className="db-detail-title">
        <strong>{asString(event.event_type)}</strong>
        <span>{asString(event.primary_symbol)} · {formatDateTime(event.bar_end_utc)}</span>
      </div>
      <div className="line-list compact">
        <div>
          <span>event id</span>
          <strong>{asString(event.event_id, asString(event.id))}</strong>
        </div>
        <div>
          <span>timeframe</span>
          <strong>{asString(event.timeframe)}</strong>
        </div>
        <div>
          <span>detector</span>
          <strong>{asString(event.detector_version)}</strong>
        </div>
        <div>
          <span>source run</span>
          <strong>{asString(event.source_run_id)}</strong>
        </div>
      </div>
      <KeyBlock title="event_data" value={eventData} />
      <KeyBlock title="context" value={context} />
      <KeyBlock title="outcomes" value={outcomes} />
      <KeyBlock title="replay pointer" value={replayPointer} />
    </article>
  );
}

function FeatureCard({ feature }: { feature: JsonRow }) {
  const roles = asArray(feature.roles).map((role) => asString(role)).filter((role) => role !== "-");
  const params = Object.keys(asObject(feature.param_schema));
  return (
    <div className="db-feature-card">
      <div>
        <strong>{asString(feature.label, asString(feature.name))}</strong>
        <span>{asString(feature.name)}</span>
      </div>
      <p>{asString(feature.description, "No description supplied.")}</p>
      <div className="db-chip-row">
        {roles.map((role) => (
          <span className="pill ok" key={role}>
            {role}
          </span>
        ))}
        <span className="pill">{params.length} params</span>
      </div>
    </div>
  );
}

function DataCoverageCard({
  rows,
  coverageProbe,
  datasetsProbe,
}: {
  rows: JsonRow[];
  coverageProbe?: ProbeResult;
  datasetsProbe?: ProbeResult;
}) {
  const ok = coverageProbe?.ok || datasetsProbe?.ok;
  return (
    <article className="card db-panel db-panel-wide">
      <CardHeader title="Dataset Coverage" tone={ok ? "good" : "warn"} label={`${rows.length} rows`} />
      <div className="db-coverage-table">
        <div className="db-coverage-head">
          <span>dataset</span>
          <span>schema</span>
          <span>status</span>
          <span>parts</span>
          <span>latest</span>
          <span>size</span>
        </div>
        {rows.slice(0, 12).map((row, idx) => (
          <div className="db-coverage-row" key={`${asString(row.name, asString(row.dataset_code))}-${idx}`}>
            <span>{asString(row.name, asString(row.dataset_code))}</span>
            <span>{asString(row.schema, asString(row.data_schema))}</span>
            <span className={`pill ${asString(row.status)}`}>{asString(row.status)}</span>
            <span>{formatNumber(row.partition_count)}</span>
            <span>{asString(row.latest_date)}</span>
            <span>{formatBytes(row.total_bytes)}</span>
          </div>
        ))}
        {rows.length === 0 ? <Empty text="Dataset coverage is empty or the scan has not run yet." /> : null}
      </div>
    </article>
  );
}

function R2DatabaseCard({
  status,
  freshness,
}: {
  status?: ProbeResult;
  freshness?: ProbeResult;
}) {
  const fresh = freshness?.data;
  const inv = status?.data;
  const bucketObjects = readPath(fresh, "bucket_objects");
  const local = readPath(fresh, "local");
  const inventory = readPath(fresh, "inventory");
  const tone = freshness?.ok || status?.ok ? "good" : "warn";
  return (
    <article className="card db-panel">
      <CardHeader title="R2 / Cloud Warehouse" tone={tone} label={asString(readPath(fresh, "status"), status?.ok ? "reachable" : "check")} />
      <div className="metric-row">
        <Metric label="bucket objects" value={formatNumber(readPath(bucketObjects, "partition_count"))} />
        <Metric label="bucket size" value={formatFixed(readPath(bucketObjects, "total_gb"), 2)} />
        <Metric label="inventory age" value={formatAgeSeconds(readPath(inv, "age_seconds"))} />
      </div>
      <div className="line-list compact">
        <div>
          <span>bucket</span>
          <strong>{asString(readPath(fresh, "bucket"), asString(readPath(inv, "bucket")))}</strong>
        </div>
        <div>
          <span>local partitions</span>
          <strong>{formatNumber(readPath(local, "partition_count"))}</strong>
        </div>
        <div>
          <span>inventory partitions</span>
          <strong>{formatNumber(readPath(inventory, "partition_count"))}</strong>
        </div>
        <div>
          <span>latest cloud date</span>
          <strong>{asString(readPath(bucketObjects, "latest_date"))}</strong>
        </div>
      </div>
    </article>
  );
}

function ResearchProtocolCard({
  candidates,
  groups,
  hypotheses,
  locks,
  validation,
}: {
  candidates: JsonRow[];
  groups: JsonRow[];
  hypotheses: JsonRow[];
  locks: JsonRow[];
  validation?: ProbeResult;
}) {
  const hasValidation = readPath(validation?.data, "has_report") === true;
  return (
    <article className="card db-panel">
      <CardHeader title="Trials / ML Protocol" tone={candidates.length || locks.length ? "good" : "warn"} label="lockdown" />
      <div className="metric-row">
        <Metric label="candidates" value={formatNumber(candidates.length)} />
        <Metric label="groups" value={formatNumber(groups.length)} />
        <Metric label="locks" value={formatNumber(locks.length)} />
      </div>
      <div className="line-list compact">
        <div>
          <span>hypotheses</span>
          <strong>{formatNumber(hypotheses.length)}</strong>
        </div>
        <div>
          <span>latest validation</span>
          <strong>{hasValidation ? asString(readPath(validation?.data, "status")) : "no report"}</strong>
        </div>
        <div>
          <span>snapshot</span>
          <strong>{asString(readPath(validation?.data, "snapshot_id"))}</strong>
        </div>
      </div>
      <div className="db-mini-list">
        {locks.slice(0, 4).map((lock) => (
          <div key={asString(lock.id)}>
            <strong>{asString(lock.lock_type)}</strong>
            <span>{asString(lock.dataset_snapshot_id)} · {shortSha(asString(lock.code_commit_sha))}</span>
          </div>
        ))}
        {locks.length === 0 ? <span className="empty inline-empty">No lock records returned yet.</span> : null}
      </div>
    </article>
  );
}

function DistributionCard({
  title,
  label,
  rows,
}: {
  title: string;
  label: string;
  rows: CountRow[];
}) {
  return (
    <article className="card db-panel">
      <CardHeader title={title} tone={rows.length ? "good" : "warn"} label={label} />
      <div className="db-bars">
        {rows.map((row) => (
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
        {rows.length === 0 ? <Empty text="No rows available yet." /> : null}
      </div>
    </article>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="db-filter">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="all">all</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function KeyBlock({ title, value }: { title: string; value: JsonRow }) {
  const entries = Object.entries(value);
  return (
    <div className="db-key-block">
      <div>
        <strong>{title}</strong>
        <span>{entries.length} keys</span>
      </div>
      <div className="db-key-grid">
        {entries.slice(0, 12).map(([key, raw]) => (
          <span key={key} title={previewValue(raw)}>
            {key}
          </span>
        ))}
        {entries.length > 12 ? <span>+{entries.length - 12} more</span> : null}
      </div>
    </div>
  );
}

function CardHeader({
  title,
  tone,
  label,
}: {
  title: string;
  tone: "good" | "warn" | "bad" | "idle";
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
}: {
  label: string;
  value: string;
  sublabel: string;
}) {
  return (
    <article className="db-big-metric">
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

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}

function rowsFrom(value: unknown): JsonRow[] {
  return asArray(value).map(asObject).filter((row) => Object.keys(row).length > 0);
}

function uniqueSorted(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

function topCounts(rows: JsonRow[], getKey: (row: JsonRow) => string, limit: number): CountRow[] {
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

function eventKey(row: JsonRow): string {
  return asString(row.event_id, asString(row.id, `${asString(row.feature_name)}-${asString(row.bar_end_utc)}`));
}

function latestTimestamp(rows: JsonRow[], key: string): string {
  return timestampBoundary(rows, key, "latest");
}

function earliestTimestamp(rows: JsonRow[], key: string): string {
  return timestampBoundary(rows, key, "earliest");
}

function timestampBoundary(rows: JsonRow[], key: string, mode: "earliest" | "latest"): string {
  let chosen = 0;
  let chosenRaw = "";
  for (const row of rows) {
    const raw = asString(row[key], "");
    const ts = raw ? new Date(raw).getTime() : Number.NaN;
    if (Number.isNaN(ts)) continue;
    if (!chosen || (mode === "latest" ? ts > chosen : ts < chosen)) {
      chosen = ts;
      chosenRaw = raw;
    }
  }
  return chosenRaw;
}

function previewValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value).slice(0, 240);
  return String(value);
}

function formatAgeSeconds(value: unknown): string {
  const n = asNumber(value);
  if (n === null) return "-";
  if (n < 60) return `${n}s`;
  if (n < 3600) return `${Math.round(n / 60)}m`;
  if (n < 86_400) return `${Math.round(n / 3600)}h`;
  return `${Math.round(n / 86_400)}d`;
}

function shortSha(value: string): string {
  if (!value || value === "-") return "-";
  return value.slice(0, 8);
}

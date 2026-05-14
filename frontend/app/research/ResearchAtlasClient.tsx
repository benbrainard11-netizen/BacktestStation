"use client";

import {
  BarChart3,
  Database,
  Layers3,
  PackageCheck,
  Search,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Card, CardHead, Chip, PageHeader, Stat } from "@/components/atoms";
import { cn } from "@/lib/utils";

type AtlasPayload = {
  generated_utc: string | null;
  catalog_path: string | null;
  totals: AtlasTotals;
  export: AtlasExport;
  concepts: AtlasConcept[];
  warnings: string[];
};

type AtlasTotals = {
  research_events: number;
  feature_matrices: number;
  anchor_artifacts: number;
  export_datasets: number;
  active_symbol_count: number;
  active_symbols: string[];
  one_minute_earliest_date: string | null;
  one_minute_latest_date: string | null;
  latest_export: string | null;
  latest_export_size_bytes: number | null;
};

type AtlasExport = {
  current_package: string | null;
  release_tag: string | null;
  zip_name: string | null;
  size_bytes: number | null;
  sha256: string | null;
  generated_utc: string | null;
  datasets: ExportDataset[];
};

type ExportDataset = {
  name: string;
  matrix: string;
  schema: string;
  rows: number;
  feature_column_count: number;
  label_column_count: number;
};

type AtlasConcept = {
  short_name: string;
  title: string;
  description: string;
  feature_name: string;
  rows: number;
  columns: number;
  matrix_path: string | null;
  matrix_bytes: number | null;
  modified_utc: string | null;
  min_bar_end_utc: string | null;
  max_bar_end_utc: string | null;
  event_types: string[];
  event_type_count: number;
  event_type_breakdown: EventTypeBreakdown[];
  sides: string[];
  primary_symbols: string[];
  column_counts: Record<string, number>;
  label_count: number;
  binary_label_count: number;
  sample_labels: string[];
  sample_binary_labels: string[];
  docs: { readme: string | null; stats: string | null };
  artifacts: AtlasArtifact[];
  artifact_counts: Record<string, number>;
  export_datasets: ExportDataset[];
};

type EventTypeBreakdown = {
  event_type: string;
  rows: number;
  outcomes_non_null: number;
  outcomes_non_null_pct: number;
};

type AtlasArtifact = {
  name: string;
  group: string;
  kind: string;
  rows: number | null;
  columns: number | null;
  status_counts: Record<string, number>;
  path: string | null;
  bytes: number | null;
  modified_utc: string | null;
};

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "data"; data: AtlasPayload };

function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toLocaleString();
}

function formatBytes(value: number | null | undefined): string {
  if (value == null || value <= 0) return "-";
  if (value < 1e6) return `${(value / 1e3).toFixed(1)} KB`;
  if (value < 1e9) return `${(value / 1e6).toFixed(1)} MB`;
  return `${(value / 1e9).toFixed(2)} GB`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value.slice(0, 10);
  return d.toISOString().slice(0, 10);
}

function statusSummary(status: Record<string, number>): string {
  const entries = Object.entries(status);
  if (entries.length === 0) return "-";
  return entries.map(([k, v]) => `${k}:${v}`).join("  ");
}

function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return `${(value * 100).toFixed(0)}%`;
}

function LoadingState() {
  return (
    <div className="mx-auto max-w-[1400px] px-6 py-8">
      <PageHeader
        eyebrow="research database"
        title="Research Atlas"
        sub="Loading the generated ML catalog and export index."
      />
      <Card className="mx-6 px-5 py-8 text-sm text-ink-3">
        <span className="live-pulse mr-2 inline-block h-2 w-2 rounded-full bg-accent" />
        Loading atlas...
      </Card>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="mx-auto max-w-[1400px] px-6 py-8">
      <PageHeader
        eyebrow="research database"
        title="Research Atlas"
        sub="The atlas endpoint did not respond."
      />
      <Card className="mx-6 px-5 py-8 text-sm text-neg">Failed to load: {message}</Card>
    </div>
  );
}

function StatStrip({ data }: { data: AtlasPayload }) {
  const t = data.totals;
  return (
    <div className="mx-6 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-6">
      <div className="bg-bg-1">
        <Stat label="Events" value={formatNumber(t.research_events)} sub="research event rows" tone="accent" />
      </div>
      <div className="bg-bg-1">
        <Stat label="Concepts" value={formatNumber(t.feature_matrices)} sub="feature matrices" />
      </div>
      <div className="bg-bg-1">
        <Stat label="Artifacts" value={formatNumber(t.anchor_artifacts)} sub="anchors, results, schemas" />
      </div>
      <div className="bg-bg-1">
        <Stat label="Symbols" value={formatNumber(t.active_symbol_count)} sub={t.active_symbols.join(", ")} />
      </div>
      <div className="bg-bg-1">
        <Stat
          label="1m coverage"
          value={t.one_minute_earliest_date ?? "-"}
          sub={`through ${t.one_minute_latest_date ?? "-"}`}
        />
      </div>
      <div className="bg-bg-1">
        <Stat label="Export" value={formatBytes(t.latest_export_size_bytes)} sub={t.latest_export ?? "none"} tone="pos" />
      </div>
    </div>
  );
}

function ConceptCard({
  concept,
  maxRows,
  active,
  onClick,
}: {
  concept: AtlasConcept;
  maxRows: number;
  active: boolean;
  onClick: () => void;
}) {
  const width = maxRows > 0 ? Math.max(4, Math.round((concept.rows / maxRows) * 100)) : 0;
  const exported = concept.export_datasets.length > 0;
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group w-full rounded-xl border bg-bg-1 p-4 text-left transition hover:-translate-y-0.5 hover:border-accent-line hover:bg-bg-2",
        active ? "border-accent-line shadow-[0_0_0_1px_var(--accent-line)]" : "border-line",
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-4">
            {concept.short_name}
          </div>
          <div className="mt-1 text-base font-semibold text-ink-0">{concept.title}</div>
        </div>
        <Chip tone={exported ? "pos" : "default"}>{exported ? "exported" : "local"}</Chip>
      </div>
      <p className="min-h-[38px] text-[12px] leading-5 text-ink-3">{concept.description}</p>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-bg-3">
        <div className="h-full rounded-full bg-accent" style={{ width: `${width}%` }} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
        <div>
          <div className="font-mono text-ink-4">rows</div>
          <div className="font-mono font-semibold text-ink-1">{formatNumber(concept.rows)}</div>
        </div>
        <div>
          <div className="font-mono text-ink-4">labels</div>
          <div className="font-mono font-semibold text-ink-1">{formatNumber(concept.label_count)}</div>
        </div>
        <div>
          <div className="font-mono text-ink-4">types</div>
          <div className="font-mono font-semibold text-ink-1">{formatNumber(concept.event_type_count)}</div>
        </div>
      </div>
    </button>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-2 font-mono text-[10.5px] font-semibold uppercase tracking-[0.1em] text-ink-4">
        {title}
      </div>
      {children}
    </div>
  );
}

function PathLine({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="mb-2 rounded border border-line bg-bg-2 px-3 py-2">
      <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">{label}</div>
      <div className="mt-1 break-all font-mono text-[11px] text-ink-2">{value ?? "not generated yet"}</div>
    </div>
  );
}

function ConceptDetail({ concept }: { concept: AtlasConcept }) {
  return (
    <Card className="sticky top-4 overflow-hidden">
      <CardHead
        title={concept.title}
        eyebrow={concept.feature_name}
        right={<Chip tone={concept.export_datasets.length ? "pos" : "default"}>{concept.short_name}</Chip>}
      />
      <div className="space-y-5 p-4">
        <p className="text-sm leading-6 text-ink-2">{concept.description}</p>
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line">
          <div className="bg-bg-1"><Stat label="Rows" value={formatNumber(concept.rows)} /></div>
          <div className="bg-bg-1"><Stat label="Columns" value={formatNumber(concept.columns)} /></div>
          <div className="bg-bg-1"><Stat label="Labels" value={formatNumber(concept.label_count)} sub={`${concept.binary_label_count} binary`} /></div>
          <div className="bg-bg-1"><Stat label="Span" value={formatDate(concept.min_bar_end_utc)} sub={`to ${formatDate(concept.max_bar_end_utc)}`} /></div>
        </div>

        <Section title="Symbols and sides">
          <div className="flex flex-wrap gap-2">
            {concept.primary_symbols.map((s) => <Chip key={s}>{s}</Chip>)}
            {concept.sides.map((s) => <Chip key={s} tone="accent">{s}</Chip>)}
          </div>
        </Section>

        <Section title="Event types">
          <div className="max-h-[230px] overflow-auto rounded-lg border border-line">
            <table className="w-full text-[12px]">
              <thead className="sticky top-0 bg-bg-1">
                <tr className="border-b border-line text-left text-ink-4">
                  <th className="px-3 py-2 font-mono uppercase tracking-[0.08em]">type</th>
                  <th className="px-3 py-2 text-right font-mono uppercase tracking-[0.08em]">rows</th>
                  <th className="px-3 py-2 text-right font-mono uppercase tracking-[0.08em]">outcomes</th>
                </tr>
              </thead>
              <tbody>
                {concept.event_type_breakdown.slice(0, 20).map((row) => (
                  <tr key={row.event_type} className="border-b border-line last:border-b-0 hover:bg-bg-2">
                    <td className="px-3 py-2 font-mono text-ink-1">{row.event_type}</td>
                    <td className="px-3 py-2 text-right font-mono text-ink-2">{formatNumber(row.rows)}</td>
                    <td className="px-3 py-2 text-right font-mono text-ink-2">{pct(row.outcomes_non_null_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        <Section title="Docs and files">
          <PathLine label="matrix" value={concept.matrix_path} />
          <PathLine label="README" value={concept.docs.readme} />
          <PathLine label="stats" value={concept.docs.stats} />
        </Section>

        <Section title="Export datasets">
          {concept.export_datasets.length === 0 ? (
            <div className="text-[12px] text-ink-4">Not in the current strategy-lab export.</div>
          ) : (
            <div className="space-y-2">
              {concept.export_datasets.map((d) => (
                <div key={d.name} className="rounded-lg border border-line bg-bg-2 p-3">
                  <div className="font-mono text-[12px] font-semibold text-ink-1">{d.name}</div>
                  <div className="mt-1 text-[11px] text-ink-4">
                    {formatNumber(d.rows)} rows, {formatNumber(d.feature_column_count)} features, {formatNumber(d.label_column_count)} labels
                  </div>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section title="Artifacts">
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(concept.artifact_counts).map(([k, v]) => (
              <div key={k} className="rounded border border-line bg-bg-2 px-2 py-2">
                <div className="font-mono text-[10px] uppercase text-ink-4">{k.replace("_", " ")}</div>
                <div className="font-mono text-sm font-semibold text-ink-1">{v}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 max-h-[220px] overflow-auto rounded-lg border border-line">
            {concept.artifacts.length === 0 ? (
              <div className="p-3 text-[12px] text-ink-4">No artifacts found.</div>
            ) : (
              <table className="w-full text-[12px]">
                <tbody>
                  {concept.artifacts.map((a) => (
                    <tr key={`${a.group}-${a.name}`} className="border-b border-line last:border-b-0 hover:bg-bg-2">
                      <td className="px-3 py-2">
                        <div className="font-mono text-ink-1">{a.name}</div>
                        <div className="text-[10px] text-ink-4">{a.group} {statusSummary(a.status_counts)}</div>
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-ink-3">
                        {a.rows != null ? formatNumber(a.rows) : formatBytes(a.bytes)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Section>
      </div>
    </Card>
  );
}

function ExportCard({ data }: { data: AtlasPayload }) {
  const exp = data.export;
  return (
    <Card>
      <CardHead title="Current share package" eyebrow="github release export" right={<PackageCheck className="h-4 w-4 text-pos" />} />
      <div className="space-y-3 p-4 text-[12px] text-ink-2">
        <PathLine label="package" value={exp.current_package} />
        <PathLine label="zip" value={exp.zip_name} />
        <PathLine label="release tag" value={exp.release_tag} />
        <PathLine label="sha256" value={exp.sha256} />
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded border border-line bg-bg-2 p-3">
            <div className="font-mono text-[10px] uppercase text-ink-4">size</div>
            <div className="font-mono text-sm font-semibold text-ink-1">{formatBytes(exp.size_bytes)}</div>
          </div>
          <div className="rounded border border-line bg-bg-2 p-3">
            <div className="font-mono text-[10px] uppercase text-ink-4">datasets</div>
            <div className="font-mono text-sm font-semibold text-ink-1">{formatNumber(exp.datasets.length)}</div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function WarningsCard({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null;
  return (
    <Card>
      <CardHead title="Manifest warnings" eyebrow="read before sharing" />
      <div className="space-y-2 p-4">
        {warnings.map((warning) => (
          <div key={warning} className="rounded border border-warn/30 bg-warn/10 px-3 py-2 text-[12px] leading-5 text-warn">
            {warning}
          </div>
        ))}
      </div>
    </Card>
  );
}

export function ResearchAtlasClient() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [query, setQuery] = useState("");
  const [selectedShort, setSelectedShort] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/research/atlas", { cache: "no-store" })
      .then(async (res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText || "request failed"}`);
        const payload = (await res.json()) as AtlasPayload;
        if (!cancelled) {
          setState({ kind: "data", data: payload });
          setSelectedShort(payload.concepts[0]?.short_name ?? null);
        }
      })
      .catch((err) => {
        if (!cancelled) setState({ kind: "error", message: err instanceof Error ? err.message : "Network error" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    if (state.kind !== "data") return [];
    const q = query.trim().toLowerCase();
    if (!q) return state.data.concepts;
    return state.data.concepts.filter((concept) => {
      const haystack = [
        concept.short_name,
        concept.title,
        concept.feature_name,
        concept.description,
        ...concept.event_types,
        ...concept.sample_labels,
      ].join(" ").toLowerCase();
      return haystack.includes(q);
    });
  }, [state, query]);

  if (state.kind === "loading") return <LoadingState />;
  if (state.kind === "error") return <ErrorState message={state.message} />;

  const data = state.data;
  const maxRows = Math.max(...data.concepts.map((c) => c.rows), 1);
  const selected = data.concepts.find((c) => c.short_name === selectedShort) ?? filtered[0] ?? data.concepts[0];

  return (
    <div className="mx-auto max-w-[1500px] px-6 pb-10">
      <PageHeader
        eyebrow="research database"
        title="Research Atlas"
        sub="A clickable map of the feature database, ML matrices, model artifacts, docs, and current share package."
        right={
          <div className="hidden items-center gap-2 rounded-full border border-line bg-bg-1 px-3 py-2 font-mono text-[11px] text-ink-3 md:flex">
            <Database className="h-3.5 w-3.5 text-accent" />
            {data.catalog_path}
          </div>
        }
      />

      <StatStrip data={data} />

      <div className="mx-6 mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_460px]">
        <div className="space-y-5">
          <Card className="overflow-hidden">
            <CardHead
              title="Concept map"
              eyebrow={`${filtered.length} visible of ${data.concepts.length}`}
              right={
                <div className="flex h-9 min-w-[260px] items-center gap-2 rounded border border-line bg-bg-2 px-3">
                  <Search className="h-4 w-4 text-ink-4" />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="search concepts, event types, labels"
                    className="w-full bg-transparent text-[12px] text-ink-1 outline-none placeholder:text-ink-4"
                  />
                </div>
              }
            />
            <div className="grid gap-3 p-4 md:grid-cols-2 2xl:grid-cols-3">
              {filtered.map((concept) => (
                <ConceptCard
                  key={concept.short_name}
                  concept={concept}
                  maxRows={maxRows}
                  active={selected?.short_name === concept.short_name}
                  onClick={() => setSelectedShort(concept.short_name)}
                />
              ))}
            </div>
          </Card>

          <Card>
            <CardHead title="Largest matrices" eyebrow="row count by concept" right={<BarChart3 className="h-4 w-4 text-accent" />} />
            <div className="space-y-3 p-4">
              {data.concepts.slice(0, 12).map((concept) => {
                const width = Math.max(3, Math.round((concept.rows / maxRows) * 100));
                return (
                  <button
                    key={concept.short_name}
                    type="button"
                    onClick={() => setSelectedShort(concept.short_name)}
                    className="grid w-full grid-cols-[86px_minmax(0,1fr)_90px] items-center gap-3 text-left"
                  >
                    <div className="font-mono text-[11px] font-semibold uppercase text-ink-3">{concept.short_name}</div>
                    <div className="h-3 overflow-hidden rounded-full bg-bg-3">
                      <div className="h-full rounded-full bg-accent" style={{ width: `${width}%` }} />
                    </div>
                    <div className="text-right font-mono text-[11px] text-ink-2">{formatNumber(concept.rows)}</div>
                  </button>
                );
              })}
            </div>
          </Card>
        </div>

        <div className="space-y-5">
          {selected && <ConceptDetail concept={selected} />}
          <ExportCard data={data} />
          <WarningsCard warnings={data.warnings} />
          <Card>
            <CardHead title="What this solves" eyebrow="orientation layer" right={<Layers3 className="h-4 w-4 text-accent" />} />
            <div className="space-y-3 p-4 text-[13px] leading-6 text-ink-2">
              <p>This page is the top-level map of the research warehouse. Use it to see what concepts exist, how much data each has, what labels are attached, and which matrices are shareable.</p>
              <p>It does not replace the event browser. It tells you where to click next and what the database currently contains.</p>
              <div className="rounded-lg border border-line bg-bg-2 p-3 font-mono text-[11px] text-ink-3">
                Data source: generated catalog, asset manifest, and export index. Refresh those scripts after big builds to update this page.
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

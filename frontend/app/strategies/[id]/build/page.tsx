"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import { AsyncButton } from "@/components/ui/AsyncButton";
import { EmptyState } from "@/components/ui/EmptyState";
import { usePoll } from "@/lib/poll";

type Feature = {
  // The /api/features endpoint returns: name (code id), label (display),
  // description, param_schema. No `id`, `category`, `inputs`, or `outputs`
  // fields — those were assumptions from the FRONTEND_API_REFERENCE doc
  // that don't match the actual response.
  name: string;
  label?: string;
  description?: string;
  param_schema?: Record<string, unknown>;
};

type StrategyVersion = {
  id: number;
  version: string;
  spec_json: Record<string, unknown> | null;
  archived_at: string | null;
  created_at: string;
};

type StrategyDetail = {
  id: number;
  name: string;
  slug: string;
  status: string;
  versions: StrategyVersion[];
};

const VERIFY_KEY = "bs.strategy_builder.spec_verified";

export default function StrategyBuildPage() {
  const params = useParams<{ id: string }>();
  const strategyId = params?.id ? Number.parseInt(params.id, 10) : NaN;

  const strategy = usePoll<StrategyDetail>(
    Number.isNaN(strategyId) ? "" : `/api/strategies/${strategyId}`,
    60_000,
  );
  const features = usePoll<Feature[]>("/api/features", 5 * 60_000);

  const [versionId, setVersionId] = useState<number | null>(null);
  const [verified, setVerified] = useState(false);

  // Load + persist verification toggle in localStorage (per-machine).
  useEffect(() => {
    if (typeof window === "undefined") return;
    setVerified(window.localStorage.getItem(VERIFY_KEY) === "1");
  }, []);

  function toggleVerified(next: boolean) {
    setVerified(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(VERIFY_KEY, next ? "1" : "0");
    }
  }

  // Default to the newest non-archived version
  useEffect(() => {
    if (versionId == null && strategy.kind === "data") {
      const live = strategy.data.versions.find((v) => v.archived_at == null);
      if (live) setVersionId(live.id);
    }
  }, [strategy, versionId]);

  if (Number.isNaN(strategyId)) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-12">
        <EmptyState
          title="bad strategy id"
          blurb="Open from /strategies/builder."
        />
      </div>
    );
  }

  const stratName =
    strategy.kind === "data" ? strategy.data.name : `Strategy #${strategyId}`;
  const versions = strategy.kind === "data" ? strategy.data.versions : [];
  const selectedVersion = versions.find((v) => v.id === versionId) ?? null;

  // Backend's /api/features doesn't return a category field, so just
  // render a flat alphabetized list rather than synthesize category
  // groupings client-side.
  const allFeatures: Feature[] =
    features.kind === "data"
      ? [...features.data].sort((a, b) =>
          (a.label ?? a.name).localeCompare(b.label ?? b.name),
        )
      : [];
  const paramCount = (f: Feature): number =>
    f.param_schema ? Object.keys(f.param_schema).length : 0;

  async function save() {
    if (!verified) throw new Error('Toggle "I verified the contract" first.');
    if (selectedVersion == null) throw new Error("Pick a version first.");
    // For now, a no-op save that just round-trips the existing spec
    // unchanged. The actual builder UI hasn't been ported. This proves
    // the wire is intact when Ben does verify the contract.
    const r = await fetch(`/api/strategy-versions/${selectedVersion.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec_json: selectedVersion.spec_json ?? {} }),
    });
    if (!r.ok) {
      let msg = `${r.status} ${r.statusText}`;
      try {
        const j = (await r.json()) as { detail?: string };
        if (j.detail) msg = j.detail;
      } catch {
        /* ignore */
      }
      throw new Error(msg);
    }
  }

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow="STRATEGY BUILDER · EXPERIMENTAL"
        title={`Build: ${stratName}`}
        sub="Compose entry / exit / stop / target rules from the feature pantry. Save persists to the version's spec_json field."
        right={
          <Link href="/strategies/builder" className="btn">
            ← Pick another
          </Link>
        }
      />

      <Card className="mt-2 border-warn/30 bg-warn/10">
        <div className="px-5 py-4 text-[12px] text-warn">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em]">
              EXPERIMENTAL
            </span>
            <span className="font-mono text-[10.5px] text-warn/70">
              spec_json contract not verified against backend
            </span>
          </div>
          <p className="mt-1 leading-relaxed">
            Save is disabled until you toggle below. Verify the round-trip shape
            between this UI and{" "}
            <code className="font-mono">app.strategies.spec_json</code> in a
            code review first; the previous{" "}
            <code className="font-mono">ComposableBuilder.tsx</code> (775 lines,
            deleted 2026-05-01) is the reference. The full visual
            pantry-and-recipe UI is deferred — this scaffold currently shows the
            available feature library and proves the PATCH wire works without
            changing spec content.
          </p>
          <label className="mt-3 inline-flex items-center gap-2 text-[12px] text-warn">
            <input
              type="checkbox"
              checked={verified}
              onChange={(e) => toggleVerified(e.target.checked)}
              className="h-3.5 w-3.5"
            />
            I verified the spec_json contract — enable Save
          </label>
        </div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
        <Card>
          <CardHead title="Version" eyebrow="pick one" />
          <div className="px-4 py-4">
            {strategy.kind === "loading" && (
              <div className="text-[12px] text-ink-3">Loading…</div>
            )}
            {strategy.kind === "error" && (
              <div className="text-[12px] text-neg">{strategy.message}</div>
            )}
            {strategy.kind === "data" && versions.length === 0 && (
              <EmptyState
                title="no versions"
                blurb="Create a version under /strategies first."
              />
            )}
            {strategy.kind === "data" && versions.length > 0 && (
              <ul className="m-0 list-none p-0">
                {versions.map((v) => (
                  <li
                    key={v.id}
                    className="flex items-center gap-2 border-b border-line py-2 last:border-b-0"
                  >
                    <button
                      type="button"
                      onClick={() => setVersionId(v.id)}
                      className={
                        versionId === v.id
                          ? "flex-1 text-left font-mono text-[12px] text-accent"
                          : "flex-1 text-left font-mono text-[12px] text-ink-1 hover:text-accent"
                      }
                    >
                      {v.version}
                    </button>
                    {v.archived_at && <Chip tone="neg">archived</Chip>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHead
              title="Feature pantry"
              eyebrow={
                features.kind === "data"
                  ? `${features.data.length} features registered`
                  : "loading"
              }
            />
            {features.kind === "loading" && (
              <div className="px-4 py-8 text-center text-[12px] text-ink-3">
                Loading…
              </div>
            )}
            {features.kind === "error" && (
              <div className="px-4 py-8 text-center text-[12px] text-neg">
                {features.message}
              </div>
            )}
            {features.kind === "data" && allFeatures.length === 0 && (
              <EmptyState
                title="empty registry"
                blurb="No features registered in /api/features."
              />
            )}
            {features.kind === "data" && allFeatures.length > 0 && (
              <ul className="m-0 grid list-none gap-1.5 p-4 sm:grid-cols-2">
                {allFeatures.map((f) => (
                  <li
                    key={f.name}
                    className="rounded border border-line bg-bg-2 px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[12px] font-semibold text-ink-0">
                        {f.label ?? f.name}
                      </span>
                      <span className="ml-auto font-mono text-[9.5px] text-ink-3">
                        {paramCount(f)} param{paramCount(f) === 1 ? "" : "s"}
                      </span>
                    </div>
                    <div className="mt-0.5 font-mono text-[9.5px] text-ink-4">
                      {f.name}
                    </div>
                    {f.description && (
                      <p className="mt-1 text-[11px] leading-relaxed text-ink-2">
                        {f.description}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHead title="Recipe" eyebrow="entry · exit · stop · target" />
            <div className="px-5 py-5">
              <EmptyState
                title="builder UI deferred"
                blurb="The pantry-to-recipe drag-drop UI (entry/exit/stop/target composition) is the next port. For now the scaffold shows what's available and proves the PATCH wire works."
                action={
                  <AsyncButton
                    onClick={save}
                    variant="primary"
                    disabled={!verified || selectedVersion == null}
                  >
                    {verified
                      ? "Save (no-op round-trip)"
                      : "Save (locked — verify above)"}
                  </AsyncButton>
                }
              />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

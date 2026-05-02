"use client";

import Link from "next/link";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import { ago, usePoll } from "@/lib/poll";

type FirmProfile = {
  profile_id: string;
  firm_name: string;
  account_name: string;
  account_size: number;
  profit_target: number;
  max_drawdown: number;
  daily_loss_limit: number | null;
  is_seed: boolean;
  archived_at: string | null;
  verified_at: string | null;
  verified_by: string | null;
  created_at: string;
  updated_at: string;
};

function money(v: number): string {
  return v.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

export default function PropFirmsPage() {
  const profiles = usePoll<FirmProfile[]>(
    "/api/prop-firm/profiles?include_archived=false",
    60_000,
  );

  const all = profiles.kind === "data" ? profiles.data : [];

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={
          profiles.kind === "data" ? `FIRMS · ${all.length} ACTIVE` : "FIRMS"
        }
        title="Firm Rules"
        sub="Prop-firm rule profiles. Built-in presets (TopstepX, Apex, etc.) plus any custom firms you've configured."
      />

      <div className="mt-2">
        {profiles.kind === "loading" && (
          <Card className="px-6 py-12 text-center text-[12px] text-ink-3">
            Loading…
          </Card>
        )}
        {profiles.kind === "error" && (
          <Card className="border-neg/30 px-6 py-12 text-center text-[12px] text-neg">
            {profiles.message}
          </Card>
        )}
        {profiles.kind === "data" && all.length === 0 && (
          <Card>
            <EmptyState
              title="no firms"
              blurb="No firm profiles configured. The seed presets should auto-load on first run."
            />
          </Card>
        )}
        {profiles.kind === "data" && all.length > 0 && (
          <Card>
            <CardHead title="Active firms" eyebrow={`${all.length} profiles`} />
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b border-line text-left">
                    {[
                      "Firm",
                      "Account",
                      "Size",
                      "Target",
                      "Max DD",
                      "Daily loss",
                      "Source",
                      "Updated",
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
                  {all.map((p) => (
                    <tr
                      key={p.profile_id}
                      className="border-b border-line last:border-b-0 hover:bg-bg-2"
                    >
                      <td className="px-3 py-2 font-mono font-semibold text-ink-0">
                        <Link
                          href={`/prop-firm/firms/${encodeURIComponent(p.profile_id)}`}
                          className="hover:text-accent"
                        >
                          {p.firm_name}
                        </Link>
                      </td>
                      <td className="px-3 py-2 text-ink-1">{p.account_name}</td>
                      <td className="px-3 py-2 text-right font-mono text-ink-1">
                        {money(p.account_size)}
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-ink-1">
                        {money(p.profit_target)}
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-neg">
                        {money(p.max_drawdown)}
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-ink-2">
                        {p.daily_loss_limit != null
                          ? money(p.daily_loss_limit)
                          : "—"}
                      </td>
                      <td className="px-3 py-2">
                        {p.is_seed ? (
                          <Chip>preset</Chip>
                        ) : (
                          <Chip tone="accent">custom</Chip>
                        )}
                        {p.verified_at && (
                          <span className="ml-1 font-mono text-[9.5px] text-pos">
                            ✓
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 font-mono text-[10.5px] text-ink-3">
                        {ago(p.updated_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

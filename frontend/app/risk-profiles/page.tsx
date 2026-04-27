import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import RiskProfileList from "@/components/risk-profiles/RiskProfileList";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type RiskProfile = components["schemas"]["RiskProfileRead"];

export const dynamic = "force-dynamic";

export default async function RiskProfilesPage() {
  const profiles = await apiGet<RiskProfile[]>("/api/risk-profiles");

  return (
    <div>
      <PageHeader
        title="Risk profiles"
        description="Named bundles of caps that can prefill the Run-a-Backtest form (strategy params) and apply post-run rule checks (max daily loss, drawdown, etc.). Conservative / Live-mirror / Aggressive seed automatically."
      />
      <div className="px-6 pb-12">
        <div className="mb-4 flex items-center gap-3">
          <Link
            href="/risk-profiles/new"
            className="border border-zinc-700 bg-zinc-900 px-4 py-2 font-mono text-xs uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
          >
            + New profile
          </Link>
        </div>
        <RiskProfileList profiles={profiles} />
      </div>
    </div>
  );
}

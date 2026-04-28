import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import FirmRulesTable from "@/components/prop-simulator/firms/FirmRulesTable";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { MOCK_FIRMS } from "@/lib/prop-simulator/mocks";
import { presetToFirmProfile } from "@/lib/prop-simulator/preset-mapping";
import type { FirmRuleProfile } from "@/lib/prop-simulator/types";

type Preset = components["schemas"]["PropFirmPresetRead"];

export const dynamic = "force-dynamic";

export default async function FirmRulesPage() {
  // Source of truth: backend `/api/prop-firm/presets`. Falls back to local
  // mocks only if the API is unreachable so the page is never blank.
  const presets = await apiGet<Preset[]>("/api/prop-firm/presets").catch(
    () => [] as Preset[],
  );
  const fromBackend: FirmRuleProfile[] = presets.map(presetToFirmProfile);
  const firms: FirmRuleProfile[] =
    fromBackend.length > 0 ? fromBackend : MOCK_FIRMS;
  const liveData = fromBackend.length > 0;

  const total = firms.length;
  const verified = firms.filter((f) => f.verification_status === "verified").length;
  const unverified = firms.filter(
    (f) => f.verification_status === "unverified",
  ).length;
  const demo = firms.filter((f) => f.verification_status === "demo").length;

  return (
    <div className="pb-10">
      <div className="px-6 pt-4">
        <Link
          href="/prop-simulator"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← Simulator
        </Link>
      </div>
      <PageHeader
        title="Firm Rules"
        description="Editable firm / account rule profiles. Prop firm rules change constantly — every entry is approximate. Verify against the source URL before trusting any number."
        meta={`${total} profiles · ${verified} verified · ${unverified} unverified · ${demo} demo`}
      />
      <div className="flex flex-col gap-4 px-6">
        <Panel
          title="All profiles"
          meta={liveData ? "live · /api/prop-firm/presets" : "fallback · local mocks"}
        >
          <FirmRulesTable firms={firms} />
          <p className="mt-3 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
            All seeded firm rules are approximations as of late 2025. Click a
            firm&apos;s source URL on the firm-detail editor to verify current
            rules. Editor lands with firm-rule persistence.
          </p>
        </Panel>
      </div>
    </div>
  );
}

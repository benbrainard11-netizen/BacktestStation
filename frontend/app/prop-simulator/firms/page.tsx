import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import FirmRulesTable from "@/components/prop-simulator/firms/FirmRulesTable";
import { MOCK_FIRMS } from "@/lib/prop-simulator/mocks";

export default function FirmRulesPage() {
  const total = MOCK_FIRMS.length;
  const demo = MOCK_FIRMS.filter((f) => f.verification_status === "demo").length;

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
        description="Editable firm / account rule profiles. Prop firm rules change constantly — treat every profile as unverified until you personally check and edit the numbers."
        meta={`${total} profiles · ${demo} demo`}
      />
      <div className="flex flex-col gap-4 px-6">
        <Panel
          title="All profiles"
          meta="design scaffold · editor stub only"
        >
          <FirmRulesTable firms={MOCK_FIRMS} />
          <p className="mt-3 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
            The edit button is intentionally disabled in this scaffold — firm
            rule persistence, versioning, and verification workflow land with
            the backend engine.
          </p>
        </Panel>
      </div>
    </div>
  );
}

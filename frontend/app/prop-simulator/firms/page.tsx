import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import Btn from "@/components/ui/Btn";
import FirmRulesTable from "@/components/prop-simulator/firms/FirmRulesTable";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { profileToFirmProfile } from "@/lib/prop-simulator/preset-mapping";
import type { FirmRuleProfile } from "@/lib/prop-simulator/types";

type ProfileRead = components["schemas"]["FirmRuleProfileRead"];

export const dynamic = "force-dynamic";

export default async function FirmRulesPage() {
  const profiles = await apiGet<ProfileRead[]>(
    "/api/prop-firm/profiles",
  ).catch(() => [] as ProfileRead[]);
  const firms: FirmRuleProfile[] = profiles.map(profileToFirmProfile);

  const total = firms.length;
  const verified = firms.filter((f) => f.verification_status === "verified").length;
  const unverified = firms.filter(
    (f) => f.verification_status === "unverified",
  ).length;
  const demo = firms.filter((f) => f.verification_status === "demo").length;

  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href="/prop-simulator">← Simulator</Btn>
      </div>
      <PageHeader
        title="Firm Rules"
        description="Editable firm / account rule profiles. Click a row's Edit button to modify any field, paste in current rules from the firm's site, and stamp it verified."
        meta={
          total === 0
            ? "no profiles"
            : `${total} profiles · ${verified} verified · ${unverified} unverified · ${demo} demo`
        }
      />
      <div className="flex flex-col gap-4 px-8">
        <Panel
          title="All profiles"
          meta={total === 0 ? "—" : "live · /api/prop-firm/profiles"}
        >
          {total === 0 ? (
            <p className="m-0 text-[13px] text-text-dim">
              No firm rule profiles yet. Seed the database with{" "}
              <code className="text-text">
                python -m backend.scripts.seed_prop_firm_profiles
              </code>{" "}
              or create one via the backend.
            </p>
          ) : (
            <>
              <FirmRulesTable firms={firms} editable />
              <p className="m-0 mt-3 text-xs text-text-mute">
                Verify each profile against the firm&apos;s site (source URL on
                the editor) and stamp it verified before trusting any number
                in a simulation.
              </p>
            </>
          )}
        </Panel>
      </div>
    </div>
  );
}

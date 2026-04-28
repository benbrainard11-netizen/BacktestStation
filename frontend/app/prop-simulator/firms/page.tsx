import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import Btn from "@/components/ui/Btn";
import FirmRulesTable from "@/components/prop-simulator/firms/FirmRulesTable";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { MOCK_FIRMS } from "@/lib/prop-simulator/mocks";
import { profileToFirmProfile } from "@/lib/prop-simulator/preset-mapping";
import type { FirmRuleProfile } from "@/lib/prop-simulator/types";

type ProfileRead = components["schemas"]["FirmRuleProfileRead"];

export const dynamic = "force-dynamic";

export default async function FirmRulesPage() {
 // Source of truth: backend `/api/prop-firm/profiles` (editable). Falls
 // back to local MOCK_FIRMS only if the API is unreachable so the page
 // is never blank.
 const profiles = await apiGet<ProfileRead[]>(
 "/api/prop-firm/profiles",
 ).catch(() => [] as ProfileRead[]);
 const fromBackend: FirmRuleProfile[] = profiles.map(profileToFirmProfile);
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
 <div className="px-8 pt-4">
 <Btn href="/prop-simulator">← Simulator</Btn>
 </div>
 <PageHeader
 title="Firm Rules"
 description="Editable firm / account rule profiles. Click a row's Edit button to modify any field, paste in current rules from the firm's site, and stamp it verified."
 meta={`${total} profiles · ${verified} verified · ${unverified} unverified · ${demo} demo`}
 />
 <div className="flex flex-col gap-4 px-8">
 <Panel
 title="All profiles"
 meta={liveData ? "live · /api/prop-firm/profiles" : "fallback · local mocks"}
 >
 <FirmRulesTable firms={firms} editable={liveData} />
 <p className="m-0 mt-3 text-xs text-text-mute">
 All seeded firm rules are approximations as of late 2025. Verify
 against each firm&apos;s site (source URL on the editor) and stamp
 the profile verified before trusting any number.
 </p>
 </Panel>
 </div>
 </div>
 );
}

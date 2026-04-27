import { notFound } from "next/navigation";

import PageHeader from "@/components/PageHeader";
import RiskProfileForm from "@/components/risk-profiles/RiskProfileForm";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type RiskProfile = components["schemas"]["RiskProfileRead"];

export const dynamic = "force-dynamic";

export default async function EditRiskProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let profile: RiskProfile;
  try {
    profile = await apiGet<RiskProfile>(`/api/risk-profiles/${id}`);
  } catch {
    return notFound();
  }
  return (
    <div>
      <PageHeader
        title={`Edit · ${profile.name}`}
        description={`Profile #${profile.id}. Status: ${profile.status}.`}
      />
      <div className="px-6 pb-12">
        <RiskProfileForm initial={profile} />
      </div>
    </div>
  );
}

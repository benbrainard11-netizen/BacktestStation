import Link from "next/link";
import { notFound } from "next/navigation";

import PageHeader from "@/components/PageHeader";
import FirmEditor from "@/components/prop-simulator/firms/FirmEditor";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type ProfileRead = components["schemas"]["FirmRuleProfileRead"];

interface FirmEditPageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

export default async function FirmEditPage({ params }: FirmEditPageProps) {
  const { id } = await params;
  const profile = await apiGet<ProfileRead>(
    `/api/prop-firm/profiles/${encodeURIComponent(id)}`,
  ).catch((error) => {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  });

  return (
    <div className="pb-10">
      <div className="px-6 pt-4">
        <Link
          href="/prop-simulator/firms"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← Firm Rules
        </Link>
      </div>
      <PageHeader
        title={profile.firm_name}
        description={profile.account_name}
        meta={`profile · ${profile.profile_id}${profile.is_seed ? " · seed" : " · custom"}`}
      />
      <div className="px-6">
        <FirmEditor initialProfile={profile} />
      </div>
    </div>
  );
}

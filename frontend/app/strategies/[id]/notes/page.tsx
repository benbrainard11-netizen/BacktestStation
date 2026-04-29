import { notFound } from "next/navigation";

import NotesPanel from "@/components/strategies/NotesPanel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type NoteTypes = components["schemas"]["NoteTypesRead"];

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

export default async function NotesPage({ params }: PageProps) {
  const { id } = await params;
  const [strategy, noteTypesResponse] = await Promise.all([
    apiGet<Strategy>(`/api/strategies/${id}`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
    apiGet<NoteTypes>("/api/notes/types").catch(
      () => ({ types: [] }) as NoteTypes,
    ),
  ]);

  return (
    <section className="flex flex-col gap-3">
      <header className="border-b border-border pb-2">
        <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
          Notes
        </h2>
        <p className="m-0 mt-0.5 text-xs text-text-mute">
          Research observations, hypotheses, decisions. Tag and link
          to versions or specific runs.
        </p>
      </header>
      <NotesPanel
        strategyId={strategy.id}
        versions={strategy.versions}
        noteTypes={noteTypesResponse.types ?? []}
      />
    </section>
  );
}

import { notFound } from "next/navigation";

import WorkspaceHeader from "@/components/strategies/WorkspaceHeader";
import WorkspaceSidebar from "@/components/strategies/WorkspaceSidebar";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];

interface LayoutProps {
  params: Promise<{ id: string }>;
  children: React.ReactNode;
}

/**
 * Strategy-scoped layout. Persists across every sub-route under
 * `/strategies/[id]/*` (Overview, Build, Backtest, Replay, Prop firm
 * sim, Experiments, Live).
 *
 * Owns:
 *   - WorkspaceHeader   — back / archive / edit / ship / pill / tags
 *   - WorkspaceSidebar  — left nav between sub-routes
 *   - {children}        — the active sub-page's content
 *
 * The strategy is fetched here once; sub-pages fetch their own data
 * (per-request memoization makes any duplicate strategy fetch free).
 *
 * Pattern mirrors `app/prop-simulator/layout.tsx` — Next.js App
 * Router nested layouts.
 */
export default async function StrategyLayout({
  params,
  children,
}: LayoutProps) {
  const { id } = await params;
  const strategy = await apiGet<Strategy>(`/api/strategies/${id}`).catch(
    (error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    },
  );

  return (
    <div className="pb-10">
      <WorkspaceHeader strategy={strategy} />
      <div className="flex flex-col gap-4 px-8 lg:flex-row lg:gap-8">
        <WorkspaceSidebar strategyId={strategy.id} />
        <div className="flex min-w-0 flex-1 flex-col gap-6">
          {children}
        </div>
      </div>
    </div>
  );
}

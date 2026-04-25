import Link from "next/link";

import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";

export default function RunNotFound() {
  return (
    <div className="pb-10">
      <div className="px-6 pt-4">
        <Link
          href="/prop-simulator/runs"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← All runs
        </Link>
      </div>
      <PageHeader
        title="Run not found"
        description="That simulation ID does not exist in the mock dataset."
      />
      <div className="px-6">
        <EmptyState
          label="No simulation with that ID."
          detail="The runs list above shows every scaffolded run."
        />
      </div>
    </div>
  );
}

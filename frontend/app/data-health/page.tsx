import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";

export default function DataHealthPage() {
  return (
    <div>
      <PageHeader
        title="Data Health"
        description="Dataset inventory, gap/duplicate reports, sha256 checksums"
        meta="PHASE 3 · NOT STARTED"
      />
      <div className="px-6 pb-6">
        <EmptyState
          label="Data Health lands with Phase 3"
          detail="Arrives with the Databento ingestion pipeline. Phase 1-2 focus on imported result files only."
          willContain={[
            "Registered datasets with row counts",
            "Gap / duplicate / out-of-order reports",
            "sha256 checksums per file",
            "Last-verified timestamp",
          ]}
        />
      </div>
    </div>
  );
}

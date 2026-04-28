import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import Btn from "@/components/ui/Btn";

export default function RunNotFound() {
  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href="/prop-simulator/runs">← All runs</Btn>
      </div>
      <PageHeader
        title="Run not found"
        description="That simulation ID does not exist in the mock dataset."
      />
      <div className="px-8">
        <EmptyState
          label="No simulation with that ID."
          detail="The runs list above shows every scaffolded run."
        />
      </div>
    </div>
  );
}

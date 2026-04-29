import PageHeader from "@/components/PageHeader";
import NotImplemented from "@/components/prop-simulator/NotImplemented";
import Btn from "@/components/ui/Btn";

export default function ComparePage() {
  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href="/prop-simulator">← Simulator</Btn>
      </div>
      <PageHeader
        title="Compare"
        description="Side-by-side comparison of saved simulation runs across firms, account sizes, risk levels, and sampling modes."
      />
      <div className="flex flex-col gap-4 px-8">
        <NotImplemented
          title="No comparison view yet"
          description="Multi-select compare requires a /api/prop-firm/simulations/compare endpoint that doesn't exist yet. In the meantime, open individual runs from the Simulation Runs list."
          href="/prop-simulator/runs"
          hrefLabel="Simulation runs →"
        />
      </div>
    </div>
  );
}

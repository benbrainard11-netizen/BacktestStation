import PageHeader from "@/components/PageHeader";
import NotImplemented from "@/components/prop-simulator/NotImplemented";
import Btn from "@/components/ui/Btn";

export default function NewSimulationPage() {
  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href="/prop-simulator">← Simulator</Btn>
      </div>
      <PageHeader
        title="New simulation"
        description="Assemble a Monte Carlo prop-firm simulation from imported backtests, firm rules, sampling mode, risk model, and personal rules."
      />
      <div className="flex flex-col gap-4 px-8">
        <NotImplemented
          title="Simulation wizard isn't wired up"
          description="The wizard previously ran on placeholder data. The real flow needs (a) imported backtests, (b) firm presets, and (c) a POST endpoint to create simulations. Firms and runs already exist — once a create endpoint lands, this wizard goes back online."
          href="/prop-simulator/runs"
          hrefLabel="Existing simulation runs →"
        />
      </div>
    </div>
  );
}

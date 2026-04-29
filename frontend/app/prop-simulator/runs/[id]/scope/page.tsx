import PageHeader from "@/components/PageHeader";
import NotImplemented from "@/components/prop-simulator/NotImplemented";
import Btn from "@/components/ui/Btn";

interface ScopePageProps {
  params: Promise<{ id: string }>;
}

export default async function RunScopePage({ params }: ScopePageProps) {
  const { id } = await params;
  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href={`/prop-simulator/runs/${id}`}>← Run detail</Btn>
      </div>
      <PageHeader
        title="Tearsheet"
        description="Editorial one-page summary of a Monte Carlo simulation run."
      />
      <div className="flex flex-col gap-4 px-8">
        <NotImplemented
          title="Tearsheet view isn't wired to real data"
          description="The tearsheet rendered against placeholder data only. The full panel breakdown for this run is available on the standard detail view."
          href={`/prop-simulator/runs/${id}`}
          hrefLabel="Run detail →"
        />
      </div>
    </div>
  );
}

import PageHeader from "@/components/PageHeader";
import RiskProfileForm from "@/components/risk-profiles/RiskProfileForm";

export default function NewRiskProfilePage() {
  return (
    <div>
      <PageHeader
        title="New risk profile"
        description="Define caps + optional default strategy params. Profiles are pure metadata; trade data is never modified."
      />
      <div className="px-6 pb-12">
        <RiskProfileForm />
      </div>
    </div>
  );
}

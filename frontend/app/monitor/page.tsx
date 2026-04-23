import PageHeader from "@/components/PageHeader";
import Placeholder from "@/components/Placeholder";

export default function MonitorPage() {
  return (
    <div>
      <PageHeader
        title="Monitor"
        description="Live strategy status, latest signals, session state, errors"
      />
      <Placeholder phase="Phase 5 — Live Monitor" />
    </div>
  );
}

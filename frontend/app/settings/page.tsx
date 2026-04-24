import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";

export default function SettingsPage() {
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Local terminal configuration"
        meta="PHASE 1 · STUB"
      />
      <div className="px-6 pb-6">
        <EmptyState
          label="No configurable settings yet"
          detail="Local paths, session hours, contract specs, and theme will live here."
          willContain={[
            "Data directory paths",
            "Futures contract configuration (tick size, value, commission)",
            "Session hours (RTH/ETH)",
            "Theme preference",
          ]}
        />
      </div>
    </div>
  );
}

import EquitySnapshotPanel from "@/components/command-center/EquitySnapshotPanel";
import KpiRow from "@/components/command-center/KpiRow";
import PhaseProgressStrip from "@/components/command-center/PhaseProgressStrip";
import QuickAccessGrid from "@/components/command-center/QuickAccessGrid";
import RecentActivityPanel from "@/components/command-center/RecentActivityPanel";
import RecentBacktestsTable from "@/components/command-center/RecentBacktestsTable";
import SystemStatusPanel from "@/components/command-center/SystemStatusPanel";
import MockDataBanner from "@/components/MockDataBanner";
import PageHeader from "@/components/PageHeader";

export default function CommandCenter() {
  return (
    <div className="flex flex-col gap-4 pb-6">
      <MockDataBanner />
      <PageHeader
        title="Command Center"
        description="System overview, latest research activity, and import status"
      />

      <section className="px-6">
        <KpiRow />
      </section>

      <section className="px-6">
        <PhaseProgressStrip />
      </section>

      <section className="grid grid-cols-1 gap-4 px-6 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <RecentBacktestsTable />
        </div>
        <div className="lg:col-span-4">
          <SystemStatusPanel />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 px-6 lg:grid-cols-12">
        <div className="lg:col-span-3">
          <QuickAccessGrid />
        </div>
        <div className="lg:col-span-5">
          <EquitySnapshotPanel />
        </div>
        <div className="lg:col-span-4">
          <RecentActivityPanel />
        </div>
      </section>
    </div>
  );
}

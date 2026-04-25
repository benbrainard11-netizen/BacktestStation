import Panel from "@/components/Panel";
import EquityOverlayChart from "@/components/prop-simulator/EquityOverlayChart";
import type { SelectedPath } from "@/lib/prop-simulator/types";

interface SamplePathsPanelProps {
  paths: SelectedPath[];
  meta?: string;
}

export default function SamplePathsPanel({
  paths,
  meta = "5 buckets · best / near-pass / median / near-fail / worst",
}: SamplePathsPanelProps) {
  return (
    <Panel title="Sample equity paths" meta={meta}>
      <EquityOverlayChart paths={paths} height={220} />
    </Panel>
  );
}

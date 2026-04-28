import Sparkline from "@/components/Sparkline";
import { syntheticEquityCurve } from "@/lib/prop-simulator/sparkline";
import type { SimulationRunListRow } from "@/lib/prop-simulator/types";

interface RowSparklineProps {
 row: SimulationRunListRow;
 width?: number;
 height?: number;
}

export default function RowSparkline({
 row,
 width = 64,
 height = 16,
}: RowSparklineProps) {
 const data = syntheticEquityCurve(row);
 const stroke =
 row.ev_after_fees > 0
 ? "stroke-pos/85"
 : row.ev_after_fees < 0
 ? "stroke-neg/85"
 : "stroke-text-mute";
 return (
 <Sparkline
 data={data}
 width={width}
 height={height}
 strokeClassName={stroke}
 />
 );
}

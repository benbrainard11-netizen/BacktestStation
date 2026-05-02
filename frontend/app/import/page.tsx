import { PageStub } from "@/components/atoms";

export default function Page() {
  return (
    <PageStub
      title="Import"
      blurb="Drop a CSV, parquet, or paste a broker-export. Map columns to OHLCV. Re-runs the data-health gauntlet on ingest. Wires to /api/import/backtest."
    />
  );
}

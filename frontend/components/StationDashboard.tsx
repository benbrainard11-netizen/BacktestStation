"use client";

import { useState } from "react";

import { DatabaseBrowser } from "@/components/DatabaseBrowser";
import { OpsMonitor } from "@/components/OpsMonitor";

type StationView = "database" | "ops";

const VIEWS: { key: StationView; label: string; helper: string }[] = [
  {
    key: "database",
    label: "Research Database",
    helper: "events, features, labels, R2",
  },
  {
    key: "ops",
    label: "Ops Monitor",
    helper: "health, feeds, sync",
  },
];

export function StationDashboard() {
  const [view, setView] = useState<StationView>("database");

  return (
    <>
      <div className="station-nav-wrap">
        <div className="station-nav">
          <div>
            <p className="eyebrow">BacktestStation</p>
            <strong>Control Room</strong>
          </div>
          <div className="station-tabs" role="tablist" aria-label="BacktestStation view">
            {VIEWS.map((item) => (
              <button
                aria-selected={view === item.key}
                className={view === item.key ? "station-tab active" : "station-tab"}
                key={item.key}
                onClick={() => setView(item.key)}
                role="tab"
                type="button"
              >
                <span>{item.label}</span>
                <small>{item.helper}</small>
              </button>
            ))}
          </div>
        </div>
      </div>
      {view === "database" ? <DatabaseBrowser /> : <OpsMonitor />}
    </>
  );
}

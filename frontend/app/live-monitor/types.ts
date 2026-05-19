import type { components } from "@/lib/api/generated";

export type LiveActiveCandidates =
  components["schemas"]["DashboardLiveActiveCandidates"];
export type LiveCandidate = components["schemas"]["DashboardLiveCandidate"];
export type LiveDriftReport = components["schemas"]["DashboardLiveDriftReport"];
export type LivePositions = components["schemas"]["DashboardLivePositions"];
export type LiveSignals = components["schemas"]["DashboardLiveSignals"];

export type LiveMonitorBundle = {
  active: LiveActiveCandidates;
  signals: LiveSignals;
  drift: LiveDriftReport;
  positions: LivePositions;
};

import type { components } from "@/lib/api/generated";

export type HypothesisItem = components["schemas"]["DashboardHypothesisItem"];
export type HypothesisList = components["schemas"]["DashboardHypothesisList"];
export type TrialGroupItem = components["schemas"]["DashboardTrialGroupItem"];
export type TrialGroupList = components["schemas"]["DashboardTrialGroupList"];
export type TrialGroupDetail = components["schemas"]["DashboardTrialGroupDetail"];
export type TrialItem = components["schemas"]["DashboardTrialItem"];
export type TrialLockItem = components["schemas"]["DashboardTrialLockItem"];
export type TrialLockList = components["schemas"]["DashboardTrialLockList"];

export type TrialsBundle = {
  hypotheses: HypothesisList;
  groups: TrialGroupList;
  locks: TrialLockList;
};

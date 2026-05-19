import type { components } from "@/lib/api/generated";

export type R2Status = components["schemas"]["DashboardR2Status"];
export type LocalCoverage = components["schemas"]["DashboardLocalCoverage"];
export type CoverageItem = components["schemas"]["DashboardCoverageItem"];
export type LatestValidation =
  components["schemas"]["DashboardLatestValidation"];
export type ValidationFindings =
  components["schemas"]["DashboardValidationFindings"];
export type ValidationFinding =
  components["schemas"]["DashboardValidationFinding"];

export type FindingsFilters = {
  severity: string;
  schema: string;
  symbol: string;
  date: string;
};

export type DataHealthBundle = {
  r2: R2Status;
  coverage: LocalCoverage;
  validation: LatestValidation;
  findings: ValidationFindings;
};

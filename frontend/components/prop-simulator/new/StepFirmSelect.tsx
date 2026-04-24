import { cn } from "@/lib/utils";
import FirmRuleStatusBadge from "@/components/prop-simulator/shared/FirmRuleStatusBadge";
import type { FirmRuleProfile, PhaseMode } from "@/lib/prop-simulator/types";

interface StepFirmSelectProps {
  firms: FirmRuleProfile[];
  selectedProfileId: string | null;
  onSelectFirm: (profileId: string) => void;
  phaseMode: PhaseMode;
  onSelectPhase: (phase: PhaseMode) => void;
}

const PHASE_MODES: { key: PhaseMode; label: string; detail: string }[] = [
  { key: "eval_only", label: "Eval only", detail: "Pass the evaluation. Stop there." },
  { key: "funded_only", label: "Funded only", detail: "Start with a funded account." },
  { key: "eval_to_payout", label: "Eval → funded → payout", detail: "Full lifecycle with fees and payout rules." },
];

export default function StepFirmSelect({
  firms,
  selectedProfileId,
  onSelectFirm,
  phaseMode,
  onSelectPhase,
}: StepFirmSelectProps) {
  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="mb-2 text-xs text-zinc-400">
          Pick a firm profile. All profiles below are DEMO — edit the values in
          Firm Rules before trusting them.
        </p>
        <ul className="flex flex-col gap-2">
          {firms.map((firm) => {
            const isSelected = firm.profile_id === selectedProfileId;
            return (
              <li key={firm.profile_id}>
                <button
                  type="button"
                  onClick={() => onSelectFirm(firm.profile_id)}
                  className={cn(
                    "flex w-full items-center justify-between gap-3 border px-3 py-2 text-left",
                    isSelected
                      ? "border-emerald-900 bg-emerald-950/20"
                      : "border-zinc-800 bg-zinc-950 hover:bg-zinc-900/60",
                  )}
                >
                  <div className="flex min-w-0 flex-col gap-1">
                    <span className="text-sm text-zinc-100">
                      {firm.firm_name} · {firm.account_name}
                    </span>
                    <span className="font-mono text-[11px] text-zinc-500">
                      ${firm.account_size.toLocaleString()} · target $
                      {firm.profit_target?.toLocaleString() ?? "—"} · max DD $
                      {firm.max_drawdown.toLocaleString()} · split{" "}
                      {firm.payout_split}%
                    </span>
                  </div>
                  <FirmRuleStatusBadge
                    status={firm.verification_status}
                    lastVerifiedAt={firm.rule_last_verified_at}
                  />
                </button>
              </li>
            );
          })}
        </ul>
      </div>
      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Phase mode
        </p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {PHASE_MODES.map((mode) => {
            const isActive = mode.key === phaseMode;
            return (
              <button
                key={mode.key}
                type="button"
                onClick={() => onSelectPhase(mode.key)}
                className={cn(
                  "flex flex-col gap-1 border px-3 py-2 text-left",
                  isActive
                    ? "border-zinc-600 bg-zinc-800 text-zinc-100"
                    : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900",
                )}
              >
                <span className="font-mono text-[11px] uppercase tracking-widest">
                  {mode.label}
                </span>
                <span className="text-xs text-zinc-500">{mode.detail}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

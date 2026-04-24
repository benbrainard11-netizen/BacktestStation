import { cn } from "@/lib/utils";
import type { RuleVerificationStatus } from "@/lib/prop-simulator/types";

interface FirmRuleStatusBadgeProps {
  status: RuleVerificationStatus;
  lastVerifiedAt?: string | null;
}

const TONES: Record<RuleVerificationStatus, string> = {
  verified: "border-emerald-900 bg-emerald-950/40 text-emerald-300",
  unverified: "border-amber-900 bg-amber-950/40 text-amber-300",
  demo: "border-zinc-700 bg-zinc-900 text-zinc-300",
};

const LABELS: Record<RuleVerificationStatus, string> = {
  verified: "Verified",
  unverified: "Unverified",
  demo: "Demo",
};

function formatVerified(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString().slice(0, 10);
}

export default function FirmRuleStatusBadge({
  status,
  lastVerifiedAt,
}: FirmRuleStatusBadgeProps) {
  const verifiedDate = formatVerified(lastVerifiedAt);
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={cn(
          "border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest",
          TONES[status],
        )}
      >
        {LABELS[status]}
      </span>
      <span className="font-mono text-[10px] text-zinc-500">
        {verifiedDate ? `verified ${verifiedDate}` : "not verified"}
      </span>
    </span>
  );
}

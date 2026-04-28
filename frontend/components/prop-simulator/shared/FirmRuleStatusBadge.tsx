import { cn } from "@/lib/utils";
import type { RuleVerificationStatus } from "@/lib/prop-simulator/types";

interface FirmRuleStatusBadgeProps {
 status: RuleVerificationStatus;
 lastVerifiedAt?: string | null;
}

const TONES: Record<RuleVerificationStatus, string> = {
 verified: "border-pos/30 bg-pos/10 text-pos",
 unverified: "border-warn/30 bg-warn/10 text-warn",
 demo: "border-border-strong bg-surface-alt text-text-dim",
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
 "rounded-full border px-2 py-[2px] text-xs",
 TONES[status],
 )}
 >
 {LABELS[status]}
 </span>
 <span className="text-xs text-text-mute">
 {verifiedDate ? `verified ${verifiedDate}` : "not verified"}
 </span>
 </span>
 );
}

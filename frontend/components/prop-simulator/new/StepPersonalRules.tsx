import { cn } from "@/lib/utils";

export interface PersonalRulesState {
 dailyLossStop: number | null;
 dailyProfitStop: number | null;
 dailyTradeLimit: number | null;
 maxLossesPerDay: number | null;
 reduceRiskAfterLoss: boolean;
 walkawayAfterWinner: boolean;
 feesEnabled: boolean;
 payoutRulesEnabled: boolean;
}

interface StepPersonalRulesProps {
 rules: PersonalRulesState;
 onChange: (next: PersonalRulesState) => void;
}

function NullableNumber({
 label,
 value,
 step,
 onChange,
 hint,
}: {
 label: string;
 value: number | null;
 step: number;
 onChange: (next: number | null) => void;
 hint: string;
}) {
 return (
 <label className="flex flex-col gap-1 tabular-nums text-[11px] text-text-dim">
 <span className=" text-text-mute">{label}</span>
 <input
 type="text"
 value={value === null ? "" : value.toString()}
 placeholder="off"
 onChange={(e) => {
 const raw = e.target.value.trim();
 if (raw === "") {
 onChange(null);
 return;
 }
 const n = Number(raw);
 onChange(Number.isFinite(n) ? n : null);
 }}
 inputMode="numeric"
 step={step}
 className="border border-border bg-surface px-2 py-1 text-text focus:border-border focus:outline-none"
 />
 <span className="text-[10px] text-text-mute">{hint}</span>
 </label>
 );
}

function Toggle({
 label,
 hint,
 value,
 onChange,
}: {
 label: string;
 hint: string;
 value: boolean;
 onChange: (next: boolean) => void;
}) {
 return (
 <div className="flex flex-col gap-1 tabular-nums text-[11px] text-text-dim">
 <span className=" text-text-mute">{label}</span>
 <button
 type="button"
 onClick={() => onChange(!value)}
 className={cn(
 "border px-2 py-1 text-left",
 value
 ? "border-pos/30 bg-pos/10 text-pos"
 : "border-border bg-surface text-text-dim hover:bg-surface-alt",
 )}
 >
 {value ? "on" : "off"}
 </button>
 <span className="text-[10px] text-text-mute">{hint}</span>
 </div>
 );
}

export default function StepPersonalRules({
 rules,
 onChange,
}: StepPersonalRulesProps) {
 const set = <K extends keyof PersonalRulesState>(
 key: K,
 value: PersonalRulesState[K],
 ) => onChange({ ...rules, [key]: value });

 return (
 <div className="flex flex-col gap-5">
 <p className="text-xs text-text-dim">
 Personal rules run on top of the firm&apos;s rules. They can only make a
 day stop earlier — never later.
 </p>
 <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
 <NullableNumber
 label="Daily loss stop ($)"
 value={rules.dailyLossStop}
 step={50}
 onChange={(v) => set("dailyLossStop", v)}
 hint="Stop trading after this loss for the day."
 />
 <NullableNumber
 label="Daily profit stop ($)"
 value={rules.dailyProfitStop}
 step={50}
 onChange={(v) => set("dailyProfitStop", v)}
 hint="Walk away after hitting this profit."
 />
 <NullableNumber
 label="Daily trade limit"
 value={rules.dailyTradeLimit}
 step={1}
 onChange={(v) => set("dailyTradeLimit", v)}
 hint="Max trades per day."
 />
 <NullableNumber
 label="Max losses per day"
 value={rules.maxLossesPerDay}
 step={1}
 onChange={(v) => set("maxLossesPerDay", v)}
 hint="Stop after N consecutive losers."
 />
 </div>
 <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
 <Toggle
 label="Reduce risk after loss"
 hint="Cut size after a losing trade."
 value={rules.reduceRiskAfterLoss}
 onChange={(v) => set("reduceRiskAfterLoss", v)}
 />
 <Toggle
 label="Walk away after winner"
 hint="Stop for the day after first winner."
 value={rules.walkawayAfterWinner}
 onChange={(v) => set("walkawayAfterWinner", v)}
 />
 <Toggle
 label="Fees enabled"
 hint="Include eval / activation / reset fees in EV."
 value={rules.feesEnabled}
 onChange={(v) => set("feesEnabled", v)}
 />
 <Toggle
 label="Payout rules enabled"
 hint="Simulate min days + min profit gates."
 value={rules.payoutRulesEnabled}
 onChange={(v) => set("payoutRulesEnabled", v)}
 />
 </div>
 </div>
 );
}

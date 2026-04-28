import { cn } from "@/lib/utils";

export type Tone = "positive" | "negative" | "neutral";

interface MetricCardProps {
  label: string;
  value: string;
  valueTone?: Tone;
  delta?: string;
  deltaTone?: Tone;
}

const VALUE_TONE: Record<Tone, string> = {
  positive: "text-pos",
  negative: "text-neg",
  neutral: "text-text",
};

const DELTA_TONE: Record<Tone, string> = {
  positive: "text-pos",
  negative: "text-neg",
  neutral: "text-text-mute",
};

/**
 * Direction A metric tile. Border + surface, sentence-case label, large
 * tabular value, optional delta line. Calmer than the legacy lift-on-hover
 * card — matches StatTile from `components/ui/`.
 */
export default function MetricCard({
  label,
  value,
  valueTone = "neutral",
  delta,
  deltaTone = "neutral",
}: MetricCardProps) {
  return (
    <div className="rounded-lg border border-border bg-surface px-[18px] py-4 transition-colors hover:bg-surface-alt">
      <p className="m-0 text-xs text-text-mute">{label}</p>
      <p
        className={cn(
          "m-0 mt-2 text-[24px] font-normal leading-none tracking-[-0.01em] tabular-nums",
          VALUE_TONE[valueTone],
        )}
      >
        {value}
      </p>
      {delta ? (
        <p className="m-0 mt-1.5 text-xs tabular-nums">
          <span className={DELTA_TONE[deltaTone]}>{delta.split(" ")[0]}</span>
          <span className="ml-1 text-text-mute">
            {delta.split(" ").slice(1).join(" ")}
          </span>
        </p>
      ) : null}
    </div>
  );
}

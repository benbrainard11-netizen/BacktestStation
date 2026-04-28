import Btn from "@/components/ui/Btn";

export default function StrategyNotFound() {
  return (
    <div className="px-8 pb-10 pt-6">
      <div className="mb-4">
        <Btn href="/strategies">← All strategies</Btn>
      </div>
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="m-0 text-xs text-text-mute">Not found</p>
        <p className="m-0 mt-2 text-[13px] text-text-dim">
          No strategy exists with that ID.
        </p>
      </div>
    </div>
  );
}

export default function MockDataBanner() {
  return (
    <div className="flex items-center gap-2.5 border-b border-warn/30 bg-warn/10 px-6 py-2">
      <span
        aria-hidden="true"
        className="h-1.5 w-1.5 rounded-full bg-warn"
      />
      <p className="m-0 text-xs text-warn">
        Prop Firm Simulator · mock design scaffold · not real Monte Carlo data
      </p>
    </div>
  );
}

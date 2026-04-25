export default function MockDataBanner() {
  return (
    <div className="flex items-center gap-3 border-b border-amber-900/40 bg-amber-950/15 px-6 py-1.5">
      <span
        aria-hidden="true"
        className="ambient-pulse h-1.5 w-1.5 rounded-full bg-amber-400/80 shadow-[0_0_6px_rgba(251,191,36,0.55)]"
      />
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-amber-200/85">
        Prop Firm Simulator · mock design scaffold · not real Monte Carlo data
      </p>
    </div>
  );
}

import Link from "next/link";

export default function StrategyNotFound() {
  return (
    <div className="px-6 pb-10 pt-6">
      <Link
        href="/strategies"
        className="mb-4 inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
      >
        ← All strategies
      </Link>
      <div className="border border-zinc-800 bg-zinc-950 p-4">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Not found
        </p>
        <p className="mt-2 text-sm text-zinc-300">
          No strategy exists with that ID.
        </p>
      </div>
    </div>
  );
}

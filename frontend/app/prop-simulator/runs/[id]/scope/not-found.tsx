import Link from "next/link";

export default function ScopeNotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-[10px] uppercase tracking-[0.5em] text-zinc-500">
        Tearsheet · run not found
      </p>
      <h1 className="text-2xl font-light text-zinc-100">No such simulation.</h1>
      <Link
        href="/prop-simulator/runs"
        className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-zinc-300 hover:bg-zinc-900"
      >
        ← All runs
      </Link>
    </div>
  );
}

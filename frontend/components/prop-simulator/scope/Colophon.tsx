// Tearsheet colophon — printer's-mark footer with attribution, mock
// disclaimer, and engine provenance.

interface ColophonProps {
  simulationId: string;
  seed: number;
  createdAt: string;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}

export default function Colophon({
  simulationId,
  seed,
  createdAt,
}: ColophonProps) {
  return (
    <footer className="flex flex-col gap-3">
      <div className="flex items-center gap-3" aria-hidden="true">
        <span className="h-px flex-1 bg-zinc-800" />
        <span className="h-px w-12 bg-zinc-100/60" />
        <span className="h-px flex-1 bg-zinc-800" />
      </div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2 text-[10px] uppercase tracking-[0.32em] text-zinc-600">
        <span>
          ©{" "}
          <span className="text-zinc-300">BacktestStation</span>{" "}
          <span className="text-zinc-700">/</span> Tearsheet
        </span>
        <span>
          run <span className="text-zinc-300">{simulationId}</span>{" "}
          <span className="text-zinc-700">·</span>{" "}
          seed <span className="text-zinc-300">{seed}</span>{" "}
          <span className="text-zinc-700">·</span>{" "}
          revision <span className="text-zinc-300">01</span>
        </span>
        <span>
          engine <span className="text-zinc-300">v0.1.0</span>{" "}
          <span className="text-zinc-700">·</span>{" "}
          impressed <span className="text-zinc-300">{formatDate(createdAt)}</span>
        </span>
        <span>
          <span className="text-amber-300">data · mock</span>
          <span className="text-zinc-700"> · </span>
          not an investment recommendation
        </span>
      </div>
    </footer>
  );
}

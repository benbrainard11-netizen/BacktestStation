// Tearsheet masthead — printer's-mark header. Folio number + diamond
// register marks in the corners; identity + revision metadata across the
// middle rule.

interface MastheadProps {
  simulationId: string;
  seed: number;
  createdAt: string;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}

function Diamond() {
  return (
    <span aria-hidden="true" className="inline-block h-1.5 w-1.5 rotate-45 bg-zinc-500" />
  );
}

export default function Masthead({
  simulationId,
  seed,
  createdAt,
}: MastheadProps) {
  return (
    <header className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-4 text-[10px] uppercase tracking-[0.32em] text-zinc-500">
        <div className="flex items-center gap-2">
          <Diamond />
          <span className="text-zinc-200">BS</span>
          <span className="text-zinc-700">/</span>
          <span className="text-zinc-300">Tearsheet</span>
        </div>
        <div className="hidden items-center gap-3 sm:flex">
          <span>{simulationId}</span>
          <span className="text-zinc-700">·</span>
          <span>seed {seed}</span>
          <span className="text-zinc-700">·</span>
          <span>{formatDate(createdAt)}</span>
        </div>
        <div className="flex items-center gap-2">
          <span>folio</span>
          <span className="text-zinc-200">01</span>
          <span className="text-zinc-700">/</span>
          <span>01</span>
          <Diamond />
        </div>
      </div>
      <div className="flex items-center gap-3" aria-hidden="true">
        <span className="h-px flex-1 bg-zinc-800" />
        <span className="h-px w-12 bg-zinc-100/60" />
        <span className="h-px flex-1 bg-zinc-800" />
      </div>
    </header>
  );
}

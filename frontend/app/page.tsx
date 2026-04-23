import PageHeader from "@/components/PageHeader";

const CARDS: { label: string; hint: string }[] = [
  { label: "Data Health", hint: "No datasets yet" },
  { label: "Latest Signal", hint: "No live monitor yet" },
  { label: "Latest Run", hint: "No backtests yet" },
  { label: "Today P&L", hint: "No live trades yet" },
];

export default function CommandCenter() {
  return (
    <div>
      <PageHeader
        title="Command Center"
        description="Overview of data health, signals, runs, and performance"
      />
      <div className="grid grid-cols-1 gap-4 p-6 md:grid-cols-2 lg:grid-cols-4">
        {CARDS.map((card) => (
          <div
            key={card.label}
            className="rounded border border-zinc-800 bg-zinc-950 p-4"
          >
            <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              {card.label}
            </p>
            <p className="mt-2 font-mono text-2xl text-zinc-100">—</p>
            <p className="mt-1 text-xs text-zinc-500">{card.hint}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

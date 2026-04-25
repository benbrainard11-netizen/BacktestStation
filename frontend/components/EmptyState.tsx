interface EmptyStateProps {
  label: string;
  detail?: string;
  willContain?: string[];
}

export default function EmptyState({
  label,
  detail,
  willContain,
}: EmptyStateProps) {
  return (
    <div className="rounded-md border border-dashed border-zinc-800 bg-zinc-950 px-6 py-6">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Empty · placeholder
      </p>
      <p className="mt-2 text-sm text-zinc-300">{label}</p>
      {detail ? (
        <p className="mt-1 text-xs text-zinc-500">{detail}</p>
      ) : null}
      {willContain && willContain.length > 0 ? (
        <>
          <p className="mt-4 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
            Will contain
          </p>
          <ul className="mt-2 space-y-1">
            {willContain.map((item) => (
              <li
                key={item}
                className="flex items-start gap-2 text-xs text-zinc-500"
              >
                <span
                  aria-hidden="true"
                  className="mt-1.5 h-px w-3 shrink-0 bg-zinc-700"
                />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}

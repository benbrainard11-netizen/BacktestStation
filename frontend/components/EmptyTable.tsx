interface EmptyTableProps {
  columns: string[];
  emptyLabel: string;
  emptyDetail?: string;
}

export default function EmptyTable({
  columns,
  emptyLabel,
  emptyDetail,
}: EmptyTableProps) {
  return (
    <div className="border border-zinc-800">
      <table className="w-full table-fixed">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/40">
            {columns.map((col) => (
              <th
                key={col}
                className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-zinc-500"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
      </table>
      <div className="bg-stripes flex min-h-[160px] items-center justify-center border-t border-zinc-800/50 px-6 py-10 text-center">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Empty · placeholder
          </p>
          <p className="mt-2 text-sm text-zinc-300">{emptyLabel}</p>
          {emptyDetail ? (
            <p className="mt-1 text-xs text-zinc-500">{emptyDetail}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

interface EmptyTableProps {
  columns: string[];
  emptyLabel: string;
  emptyDetail?: string;
}

/**
 * Direction A empty-table placeholder. Headers render as a real thead so
 * the column shape is visible; body shows an inline "Empty · placeholder"
 * message. Border + surface, no atmospheric background.
 */
export default function EmptyTable({
  columns,
  emptyLabel,
  emptyDetail,
}: EmptyTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface">
      <table className="w-full table-fixed text-[13px]">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="border-b border-border px-[18px] py-2.5 text-left text-xs font-normal text-text-mute"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
      </table>
      <div className="flex min-h-[160px] items-center justify-center px-6 py-10 text-center">
        <div>
          <p className="m-0 text-xs text-text-mute">Empty · placeholder</p>
          <p className="m-0 mt-2 text-[13px] text-text">{emptyLabel}</p>
          {emptyDetail ? (
            <p className="m-0 mt-1 text-xs text-text-dim">{emptyDetail}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

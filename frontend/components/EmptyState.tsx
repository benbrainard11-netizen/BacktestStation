interface EmptyStateProps {
  label: string;
  detail?: string;
  willContain?: string[];
}

/**
 * Direction A empty state. Dashed border + surface, sentence-case copy,
 * optional bulleted list of upcoming features. Used when a panel/page has
 * no data yet but does have a defined shape.
 */
export default function EmptyState({
  label,
  detail,
  willContain,
}: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface px-[18px] py-5">
      <p className="m-0 text-xs text-text-mute">Empty · placeholder</p>
      <p className="m-0 mt-2 text-[13px] text-text">{label}</p>
      {detail ? (
        <p className="m-0 mt-1 text-xs text-text-dim">{detail}</p>
      ) : null}
      {willContain && willContain.length > 0 ? (
        <>
          <p className="m-0 mt-4 text-xs text-text-mute">Will contain</p>
          <ul className="m-0 mt-2 list-none space-y-1.5 p-0">
            {willContain.map((item) => (
              <li
                key={item}
                className="flex items-start gap-2 text-xs text-text-dim"
              >
                <span
                  aria-hidden="true"
                  className="mt-[7px] h-px w-3 shrink-0 bg-border-strong"
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

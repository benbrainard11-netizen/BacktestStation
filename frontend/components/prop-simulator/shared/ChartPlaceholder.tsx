interface ChartPlaceholderProps {
  title: string;
  detail?: string;
  minHeight?: number;
}

export default function ChartPlaceholder({
  title,
  detail,
  minHeight = 180,
}: ChartPlaceholderProps) {
  return (
    <div
      className="bg-stripes flex items-center justify-center border border-zinc-800 text-center"
      style={{ minHeight }}
    >
      <div className="px-6 py-8">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Chart · placeholder
        </p>
        <p className="mt-2 text-sm text-zinc-300">{title}</p>
        {detail ? <p className="mt-1 text-xs text-zinc-500">{detail}</p> : null}
      </div>
    </div>
  );
}

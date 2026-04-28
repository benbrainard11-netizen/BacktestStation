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
 className=" flex items-center justify-center border border-border text-center"
 style={{ minHeight }}
 >
 <div className="px-6 py-8">
 <p className="tabular-nums text-[10px] text-text-mute">
 Chart · placeholder
 </p>
 <p className="mt-2 text-sm text-text-dim">{title}</p>
 {detail ? <p className="mt-1 text-xs text-text-mute">{detail}</p> : null}
 </div>
 </div>
 );
}

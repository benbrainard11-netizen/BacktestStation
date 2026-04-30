import Btn from "@/components/ui/Btn";

interface NotImplementedProps {
  title: string;
  description: string;
  /** Optional secondary nav target (e.g. "/prop-simulator/runs"). */
  href?: string;
  hrefLabel?: string;
}

/**
 * Honest empty state for prop-simulator pages whose backend isn't wired
 * yet. No fake data, no "MOCK" banners — just a clear "this hasn't been
 * built yet" Panel-shaped card.
 */
export default function NotImplemented({
  title,
  description,
  href,
  hrefLabel,
}: NotImplementedProps) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface px-[18px] py-10">
      <p className="m-0 text-xs text-text-mute">not yet implemented</p>
      <h3 className="m-0 mt-1 text-[15px] font-medium text-text">{title}</h3>
      <p className="m-0 mt-2 max-w-prose text-[13px] text-text-dim">
        {description}
      </p>
      {href ? (
        <div className="mt-4">
          <Btn href={href}>{hrefLabel ?? "Open"}</Btn>
        </div>
      ) : null}
    </div>
  );
}

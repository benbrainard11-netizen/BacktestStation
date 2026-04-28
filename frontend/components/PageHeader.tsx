interface PageHeaderProps {
  title: string;
  description?: string;
  meta?: string;
}

export default function PageHeader({
  title,
  description,
  meta,
}: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-6 px-8 pb-4 pt-8">
      <div>
        <h2 className="text-[26px] font-medium leading-tight tracking-[-0.02em] text-text">
          {title}
        </h2>
        {description ? (
          <p className="mt-1 text-[13px] text-text-dim">{description}</p>
        ) : null}
      </div>
      {meta ? (
        <span className="shrink-0 text-xs text-text-mute">{meta}</span>
      ) : null}
    </div>
  );
}

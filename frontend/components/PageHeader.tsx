interface PageHeaderProps {
  title: string;
  description?: string;
  meta?: string;
}

export default function PageHeader({ title, description, meta }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-6 px-6 pt-6 pb-4">
      <div>
        <h2 className="text-2xl font-medium tracking-tight text-zinc-100">
          {title}
        </h2>
        {description ? (
          <p className="mt-1 text-sm text-zinc-400">{description}</p>
        ) : null}
      </div>
      {meta ? (
        <span className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          {meta}
        </span>
      ) : null}
    </div>
  );
}

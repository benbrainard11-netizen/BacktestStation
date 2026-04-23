interface PageHeaderProps {
  title: string;
  description?: string;
}

export default function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <div className="border-b border-zinc-800 px-6 py-4">
      <h2 className="text-xl font-medium text-zinc-100">{title}</h2>
      {description ? (
        <p className="text-sm text-zinc-400">{description}</p>
      ) : null}
    </div>
  );
}

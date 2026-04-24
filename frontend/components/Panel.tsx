import { cn } from "@/lib/utils";

interface PanelProps {
  title: string;
  meta?: string;
  className?: string;
  children: React.ReactNode;
}

export default function Panel({ title, meta, className, children }: PanelProps) {
  return (
    <section className={cn("border border-zinc-800 bg-zinc-950", className)}>
      <header className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
          {title}
        </h3>
        {meta ? (
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
            {meta}
          </span>
        ) : null}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

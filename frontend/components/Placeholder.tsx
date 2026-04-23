interface PlaceholderProps {
  phase: string;
  note?: string;
}

export default function Placeholder({ phase, note }: PlaceholderProps) {
  return (
    <div className="flex h-[calc(100vh-5rem)] items-center justify-center px-6">
      <div className="text-center">
        <p className="font-mono text-xs uppercase tracking-widest text-zinc-500">
          {phase}
        </p>
        <p className="mt-2 text-zinc-400">Not built yet</p>
        {note ? (
          <p className="mt-1 max-w-md text-xs text-zinc-600">{note}</p>
        ) : null}
      </div>
    </div>
  );
}

// Tearsheet colophon — printer's-mark footer with attribution and engine
// provenance.

interface ColophonProps {
 simulationId: string;
 seed: number;
 createdAt: string;
}

function formatDate(iso: string): string {
 const d = new Date(iso);
 if (Number.isNaN(d.getTime())) return iso;
 return d.toISOString().slice(0, 10);
}

export default function Colophon({
 simulationId,
 seed,
 createdAt,
}: ColophonProps) {
 return (
 <footer className="flex flex-col gap-3">
 <div className="flex items-center gap-3" aria-hidden="true">
 <span className="h-px flex-1 bg-surface-alt" />
 <span className="h-px w-12 bg-text-dim" />
 <span className="h-px flex-1 bg-surface-alt" />
 </div>
 <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2 text-[10px] tracking-[0.32em] text-text-mute">
 <span>
 ©{" "}
 <span className="text-text-dim">BacktestStation</span>{" "}
 <span className="text-text-mute">/</span> Tearsheet
 </span>
 <span>
 run <span className="text-text-dim">{simulationId}</span>{" "}
 <span className="text-text-mute">·</span>{" "}
 seed <span className="text-text-dim">{seed}</span>{" "}
 <span className="text-text-mute">·</span>{" "}
 revision <span className="text-text-dim">01</span>
 </span>
 <span>
 engine <span className="text-text-dim">v0.1.0</span>{" "}
 <span className="text-text-mute">·</span>{" "}
 impressed <span className="text-text-dim">{formatDate(createdAt)}</span>
 </span>
 <span>not an investment recommendation</span>
 </div>
 </footer>
 );
}

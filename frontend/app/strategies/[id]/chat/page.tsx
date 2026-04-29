import ChatPanel from "@/components/strategies/ChatPanel";

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

/**
 * Per-strategy chat sub-route. Currently a single shared thread
 * (Stage 3 will fork ChatPanel into section-specific agents).
 */
export default async function ChatPage({ params }: PageProps) {
  const { id } = await params;
  const strategyId = Number(id);
  return (
    <section className="flex flex-col gap-3">
      <header className="border-b border-border pb-2">
        <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
          Chat
        </h2>
        <p className="m-0 mt-0.5 text-xs text-text-mute">
          Talk to Claude or Codex. Strategy context (rules, latest run
          metrics) is auto-loaded.
        </p>
      </header>
      <ChatPanel strategyId={strategyId} />
    </section>
  );
}

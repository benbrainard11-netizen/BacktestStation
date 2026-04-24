"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import { cn } from "@/lib/utils";

interface ArchiveVersionButtonProps {
  versionId: number;
  archived: boolean;
}

type Phase =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

export default function ArchiveVersionButton({
  versionId,
  archived,
}: ArchiveVersionButtonProps) {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  async function toggle() {
    const path = archived ? "unarchive" : "archive";
    setPhase({ kind: "saving" });
    try {
      const response = await fetch(
        `/api/strategy-versions/${versionId}/${path}`,
        { method: "PATCH" },
      );
      if (!response.ok) {
        setPhase({ kind: "error", message: await describe(response) });
        return;
      }
      setPhase({ kind: "idle" });
      router.refresh();
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  return (
    <span className="flex items-center gap-2">
      <button
        type="button"
        onClick={toggle}
        disabled={phase.kind === "saving"}
        className={cn(
          "border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900",
          phase.kind === "saving" && "opacity-50",
        )}
      >
        {phase.kind === "saving"
          ? archived
            ? "restoring…"
            : "archiving…"
          : archived
            ? "unarchive"
            : "archive"}
      </button>
      {phase.kind === "error" ? (
        <span className="font-mono text-[11px] text-rose-400">
          {phase.message}
        </span>
      ) : null}
    </span>
  );
}

async function describe(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    /* fall through */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}

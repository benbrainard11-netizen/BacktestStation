"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import { cn } from "@/lib/utils";

interface DeleteRunButtonProps {
  runId: number;
  /** What the user must type to confirm — prevents fat-finger deletes. */
  confirmPhrase: string;
}

type State =
  | { kind: "idle" }
  | { kind: "confirming"; typed: string }
  | { kind: "deleting" }
  | { kind: "error"; message: string };

export default function DeleteRunButton({
  runId,
  confirmPhrase,
}: DeleteRunButtonProps) {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "idle" });

  function startConfirm() {
    setState({ kind: "confirming", typed: "" });
  }

  function cancel() {
    setState({ kind: "idle" });
  }

  async function doDelete() {
    setState({ kind: "deleting" });
    try {
      const response = await fetch(`/api/backtests/${runId}`, {
        method: "DELETE",
      });
      if (!response.ok && response.status !== 204) {
        const message = await extractError(response);
        setState({ kind: "error", message });
        return;
      }
      // Run is gone — bounce back to the list. The list is force-dynamic so
      // it'll refetch.
      router.push("/backtests");
      router.refresh();
    } catch (error) {
      setState({
        kind: "error",
        message: error instanceof Error ? error.message : "Network error",
      });
    }
  }

  if (state.kind === "idle") {
    return (
      <button
        type="button"
        onClick={startConfirm}
        className="border border-rose-900 bg-rose-950/40 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-rose-300 hover:bg-rose-950/60"
        title="Permanently delete this run and its trades"
      >
        delete
      </button>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="inline-flex flex-col gap-1">
        <span className="font-mono text-[11px] text-rose-400">{state.message}</span>
        <button
          type="button"
          onClick={cancel}
          className="self-start border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-zinc-400"
        >
          close
        </button>
      </div>
    );
  }

  const typed = state.kind === "confirming" ? state.typed : "";
  const matches = typed === confirmPhrase;
  const disabled = state.kind === "deleting";

  return (
    <div className="inline-flex flex-col gap-1.5">
      <span className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
        Type <span className="text-rose-100">{confirmPhrase}</span> to confirm
      </span>
      <div className="flex items-center gap-1.5">
        <input
          type="text"
          autoFocus
          value={typed}
          onChange={(event) =>
            setState({ kind: "confirming", typed: event.target.value })
          }
          disabled={disabled}
          className="w-56 border border-zinc-700 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-rose-700 focus:outline-none disabled:opacity-60"
          placeholder={confirmPhrase}
        />
        <button
          type="button"
          onClick={doDelete}
          disabled={!matches || disabled}
          className={cn(
            "border px-2 py-1 font-mono text-[10px] uppercase tracking-widest",
            matches && !disabled
              ? "border-rose-700 bg-rose-900 text-rose-100 hover:bg-rose-800"
              : "cursor-not-allowed border-zinc-800 bg-zinc-950 text-zinc-600",
          )}
        >
          {state.kind === "deleting" ? "deleting…" : "delete"}
        </button>
        <button
          type="button"
          onClick={cancel}
          disabled={disabled}
          className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900 disabled:opacity-60"
        >
          cancel
        </button>
      </div>
    </div>
  );
}

async function extractError(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    // fall through
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type RiskProfile = components["schemas"]["RiskProfileRead"];

type SubmitState =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

interface Props {
  initial?: RiskProfile | null;
}

export default function RiskProfileForm({ initial }: Props) {
  const router = useRouter();
  const isEdit = initial != null;

  const [name, setName] = useState(initial?.name ?? "");
  const [maxDailyLossR, setMaxDailyLossR] = useState(
    initial?.max_daily_loss_r ?? "",
  );
  const [maxDrawdownR, setMaxDrawdownR] = useState(
    initial?.max_drawdown_r ?? "",
  );
  const [maxConsecLosses, setMaxConsecLosses] = useState(
    initial?.max_consecutive_losses ?? "",
  );
  const [maxPositionSize, setMaxPositionSize] = useState(
    initial?.max_position_size ?? "",
  );
  const [allowedHoursRaw, setAllowedHoursRaw] = useState(
    initial?.allowed_hours ? initial.allowed_hours.join(",") : "",
  );
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [strategyParamsJson, setStrategyParamsJson] = useState(
    initial?.strategy_params
      ? JSON.stringify(initial.strategy_params, null, 2)
      : "",
  );
  const [state, setState] = useState<SubmitState>({ kind: "idle" });

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    let strategyParams: Record<string, unknown> | null = null;
    if (strategyParamsJson.trim().length > 0) {
      try {
        const parsed = JSON.parse(strategyParamsJson);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          strategyParams = parsed as Record<string, unknown>;
        } else {
          throw new Error("must be a JSON object");
        }
      } catch (err) {
        setState({
          kind: "error",
          message: `strategy params not valid JSON: ${
            err instanceof Error ? err.message : "parse error"
          }`,
        });
        return;
      }
    }

    const allowedHours = allowedHoursRaw
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
      .map((s) => Number.parseInt(s, 10))
      .filter((n) => Number.isFinite(n));

    const body = {
      name: name.trim(),
      max_daily_loss_r: emptyOrNumber(maxDailyLossR),
      max_drawdown_r: emptyOrNumber(maxDrawdownR),
      max_consecutive_losses: emptyOrInt(maxConsecLosses),
      max_position_size: emptyOrInt(maxPositionSize),
      allowed_hours: allowedHours.length > 0 ? allowedHours : null,
      notes: notes.trim() || null,
      strategy_params: strategyParams,
    };

    setState({ kind: "saving" });
    try {
      const url = isEdit
        ? `/api/risk-profiles/${initial!.id}`
        : "/api/risk-profiles";
      const method = isEdit ? "PATCH" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        setState({
          kind: "error",
          message: await extractErrorMessage(res),
        });
        return;
      }
      router.push("/risk-profiles");
      router.refresh();
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "Network error",
      });
    }
  }

  async function handleDelete() {
    if (!isEdit) return;
    if (
      !window.confirm(
        `Delete profile "${initial!.name}"? Trade data is unaffected; this only removes the profile.`,
      )
    ) {
      return;
    }
    setState({ kind: "saving" });
    try {
      const res = await fetch(`/api/risk-profiles/${initial!.id}`, {
        method: "DELETE",
      });
      if (!res.ok && res.status !== 204) {
        setState({
          kind: "error",
          message: await extractErrorMessage(res),
        });
        return;
      }
      router.push("/risk-profiles");
      router.refresh();
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "Network error",
      });
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto flex max-w-3xl flex-col gap-6"
    >
      <Section title="Identity">
        <TextField label="Name" value={name} onChange={setName} />
        <TextAreaField
          label="Notes"
          value={notes}
          onChange={setNotes}
          rows={3}
        />
      </Section>

      <Section title="Post-run rule caps (R-multiples; blank = no cap)">
        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Max daily loss (R)"
            value={String(maxDailyLossR)}
            onChange={(v) => setMaxDailyLossR(v as never)}
          />
          <TextField
            label="Max drawdown (R)"
            value={String(maxDrawdownR)}
            onChange={(v) => setMaxDrawdownR(v as never)}
          />
          <TextField
            label="Max consecutive losses"
            value={String(maxConsecLosses)}
            onChange={(v) => setMaxConsecLosses(v as never)}
          />
          <TextField
            label="Max position size"
            value={String(maxPositionSize)}
            onChange={(v) => setMaxPositionSize(v as never)}
          />
        </div>
        <TextField
          label="Allowed UTC hours (comma-separated, blank = any)"
          value={allowedHoursRaw}
          onChange={setAllowedHoursRaw}
          placeholder="13, 14, 15, 16, 17"
        />
      </Section>

      <Section title="Strategy params (prefills the Run-a-Backtest form)">
        <p className="font-mono text-[11px] text-zinc-500">
          JSON object whose keys match the chosen strategy&apos;s param schema.
          Blank = this profile has no opinion on params; it only enforces the
          rule caps above.
        </p>
        <textarea
          value={strategyParamsJson}
          onChange={(e) => setStrategyParamsJson(e.target.value)}
          rows={8}
          spellCheck={false}
          placeholder='{\n  "max_risk_dollars": 300,\n  "target_r": 3.0\n}'
          className="border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
        />
      </Section>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={state.kind === "saving"}
          className={cn(
            "border border-zinc-700 bg-zinc-900 px-4 py-2 font-mono text-xs uppercase tracking-widest",
            state.kind === "saving"
              ? "cursor-not-allowed text-zinc-600"
              : "text-zinc-100 hover:bg-zinc-800",
          )}
        >
          {state.kind === "saving"
            ? "Saving…"
            : isEdit
              ? "Save changes"
              : "Create profile"}
        </button>
        {isEdit ? (
          <button
            type="button"
            onClick={handleDelete}
            disabled={state.kind === "saving"}
            className="border border-rose-900 bg-rose-950/40 px-4 py-2 font-mono text-xs uppercase tracking-widest text-rose-200 hover:bg-rose-950/60"
          >
            Delete
          </button>
        ) : null}
      </div>

      {state.kind === "error" ? (
        <div className="border border-rose-900 bg-rose-950/40 p-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
            Save failed
          </p>
          <p className="mt-2 font-mono text-xs text-zinc-200">
            {state.message}
          </p>
        </div>
      ) : null}
    </form>
  );
}

function emptyOrNumber(v: unknown): number | null {
  if (v === "" || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function emptyOrInt(v: unknown): number | null {
  const n = emptyOrNumber(v);
  return n === null ? null : Math.round(n);
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border border-zinc-800 bg-zinc-950 p-4">
      <p className="mb-4 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {title}
      </p>
      <div className="flex flex-col gap-3">{children}</div>
    </section>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="font-mono uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
      />
    </label>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
  rows,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  rows?: number;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="font-mono uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows ?? 3}
        className="border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
      />
    </label>
  );
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody & {
      detail?: unknown;
    };
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
      return parsed.detail
        .map((entry: unknown) => {
          if (
            entry &&
            typeof entry === "object" &&
            "msg" in entry &&
            typeof (entry as { msg: unknown }).msg === "string"
          ) {
            return (entry as { msg: string }).msg;
          }
          return JSON.stringify(entry);
        })
        .join("; ");
    }
  } catch {
    // fall through
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}

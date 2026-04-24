"use client";

import { useEffect, useState } from "react";

import StatusPill from "@/components/StatusPill";
import type { StatusTone } from "@/components/StatusDot";

type ConnState = "checking" | "online" | "offline";

interface HealthBody {
  status?: string;
  version?: string;
}

async function pingHealth(): Promise<{ ok: boolean; version: string | null }> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2000);
    const res = await fetch("/api/health", {
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timer);
    if (!res.ok) return { ok: false, version: null };
    const body = (await res.json()) as HealthBody;
    return { ok: body.status === "ok", version: body.version ?? null };
  } catch {
    return { ok: false, version: null };
  }
}

export default function ConnectionStatus() {
  const [state, setState] = useState<ConnState>("checking");

  useEffect(() => {
    let cancelled = false;

    async function tick() {
      const { ok } = await pingHealth();
      if (cancelled) return;
      setState(ok ? "online" : "offline");
    }

    tick();
    const id = setInterval(tick, 10_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const value =
    state === "online" ? "ONLINE" : state === "checking" ? "CHECKING" : "OFFLINE";
  const dot: StatusTone =
    state === "online" ? "live" : state === "checking" ? "idle" : "off";

  return <StatusPill label="API" value={value} dot={dot} pulse={state === "checking"} />;
}

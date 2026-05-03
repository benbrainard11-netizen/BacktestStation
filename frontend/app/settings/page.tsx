"use client";

import { useEffect, useState } from "react";

import { useAppearance, type Density, type MotionPref, type Theme } from "@/components/AppearanceProvider";
import { Card, CardHead, Chip, PageHeader, StatusDot } from "@/components/atoms";
import { cn } from "@/lib/utils";

const ACCENT_PRESETS: { id: string; label: string; hue: number; sat: number; light: number }[] = [
  { id: "cyan", label: "Cyan", hue: 188, sat: 84, light: 53 },
  { id: "violet", label: "Violet", hue: 262, sat: 91, light: 70 },
  { id: "emerald", label: "Emerald", hue: 152, sat: 64, light: 52 },
  { id: "amber", label: "Amber", hue: 38, sat: 92, light: 55 },
  { id: "rose", label: "Rose", hue: 350, sat: 89, light: 62 },
  { id: "sky", label: "Sky", hue: 205, sat: 90, light: 60 },
  { id: "pink", label: "Pink", hue: 330, sat: 85, light: 65 },
  { id: "lime", label: "Lime", hue: 80, sat: 80, light: 55 },
];

export default function SettingsPage() {
  const { appearance, setAppearance, reset } = useAppearance();

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        eyebrow="SETTINGS · LOCAL ONLY"
        title="Settings"
        sub="Stored in this browser. Backend endpoints are read-only inspection — appearance never round-trips."
        right={
          <button type="button" onClick={reset} className="btn btn-sm">
            Reset all
          </button>
        }
      />

      <div className="mt-6 grid gap-6">
        <AppearanceCard />
        <BehaviorCard />
        <BackendCard />
        <AboutCard />
      </div>
    </div>
  );

  // Sections defined as inner functions so they can read appearance/setAppearance
  // without prop-drilling.
  function AppearanceCard() {
    const a = appearance;
    const swatchSelected = ACCENT_PRESETS.find(
      (p) => p.hue === a.accentHue && p.sat === a.accentSat && p.light === a.accentLight,
    );

    return (
      <Card>
        <CardHead
          eyebrow="appearance"
          title="Accent, theme, density, motion"
          right={
            <Chip tone="accent">
              <span className="lowercase">live</span>
            </Chip>
          }
        />
        <div className="grid gap-6 px-5 py-5">
          {/* Accent presets */}
          <div className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between">
              <Label>Accent color</Label>
              <span className="font-mono text-[11px] text-ink-3">
                hsl({a.accentHue}, {a.accentSat}%, {a.accentLight}%)
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {ACCENT_PRESETS.map((p) => {
                const isSel = swatchSelected?.id === p.id;
                const color = `hsl(${p.hue} ${p.sat}% ${p.light}%)`;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() =>
                      setAppearance({
                        accentHue: p.hue,
                        accentSat: p.sat,
                        accentLight: p.light,
                      })
                    }
                    aria-pressed={isSel}
                    title={p.label}
                    className={cn(
                      "group flex flex-col items-center gap-1.5 rounded-lg border p-2.5 transition-all",
                      isSel
                        ? "border-accent-line bg-accent-soft"
                        : "border-line bg-bg-2 hover:border-line-3",
                    )}
                  >
                    <span
                      aria-hidden
                      className="h-7 w-7 rounded-full"
                      style={{
                        background: color,
                        boxShadow: isSel ? `0 0 12px ${color}` : `0 0 6px ${color}55`,
                      }}
                    />
                    <span
                      className={cn(
                        "font-mono text-[10px] font-semibold uppercase tracking-[0.06em]",
                        isSel ? "text-accent" : "text-ink-3",
                      )}
                    >
                      {p.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom HSL */}
          <div className="grid gap-3 rounded-lg border border-line bg-bg-2 p-4">
            <div className="flex items-baseline justify-between">
              <Label>Custom</Label>
              <PreviewSwatch a={a} />
            </div>
            <Slider
              label="Hue"
              value={a.accentHue}
              min={0}
              max={360}
              suffix="°"
              onChange={(v) => setAppearance({ accentHue: v })}
              gradient={`linear-gradient(to right, ${Array.from({ length: 13 }, (_, i) => `hsl(${i * 30} ${a.accentSat}% ${a.accentLight}%)`).join(",")})`}
            />
            <Slider
              label="Saturation"
              value={a.accentSat}
              min={0}
              max={100}
              suffix="%"
              onChange={(v) => setAppearance({ accentSat: v })}
              gradient={`linear-gradient(to right, hsl(${a.accentHue} 0% ${a.accentLight}%), hsl(${a.accentHue} 100% ${a.accentLight}%))`}
            />
            <Slider
              label="Lightness"
              value={a.accentLight}
              min={20}
              max={80}
              suffix="%"
              onChange={(v) => setAppearance({ accentLight: v })}
              gradient={`linear-gradient(to right, hsl(${a.accentHue} ${a.accentSat}% 20%), hsl(${a.accentHue} ${a.accentSat}% 80%))`}
            />
          </div>

          {/* Live preview */}
          <div className="grid gap-2">
            <Label>Preview</Label>
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-bg-2 p-4">
              <button
                type="button"
                className="h-8 rounded px-3 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] text-bg-0"
                style={{ background: "var(--accent)", boxShadow: "0 0 8px var(--accent-glow)" }}
              >
                Primary
              </button>
              <button
                type="button"
                className="h-8 rounded border border-accent-line bg-accent-soft px-3 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] text-accent"
              >
                Soft
              </button>
              <Chip tone="accent">accent chip</Chip>
              <span className="font-mono text-[12px] text-accent">+1,329.75</span>
              <span className="text-ink-3">·</span>
              <StatusDot tone="pos" pulsing />
              <span className="font-mono text-[11px] text-ink-2">live</span>
            </div>
          </div>

          {/* Theme + Density + Motion */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Theme">
              <Segmented
                value={a.theme}
                options={[
                  { value: "default", label: "Slate" },
                  { value: "darker", label: "Black" },
                  { value: "dim", label: "Dim" },
                ]}
                onChange={(v) => setAppearance({ theme: v as Theme })}
              />
            </Field>
            <Field label="Density">
              <Segmented
                value={a.density}
                options={[
                  { value: "compact", label: "Compact" },
                  { value: "regular", label: "Regular" },
                  { value: "comfy", label: "Comfy" },
                ]}
                onChange={(v) => setAppearance({ density: v as Density })}
              />
            </Field>
            <Field label="Motion">
              <Segmented
                value={a.motion}
                options={[
                  { value: "on", label: "Full" },
                  { value: "off", label: "Reduced" },
                ]}
                onChange={(v) => setAppearance({ motion: v as MotionPref })}
              />
            </Field>
          </div>
        </div>
      </Card>
    );
  }
}

function BehaviorCard() {
  const [refreshSec, setRefreshSec] = useStored<number>("backteststation.refreshSec", 15);
  const [tz, setTz] = useStored<string>("backteststation.timezone", "America/New_York");
  const [precision, setPrecision] = useStored<number>("backteststation.precision", 2);

  return (
    <Card>
      <CardHead eyebrow="behavior" title="Refresh, timezone, precision" />
      <div className="grid gap-4 px-5 py-5 sm:grid-cols-3">
        <Field label="Live refresh">
          <NumberInput
            value={refreshSec}
            min={5}
            max={120}
            step={5}
            onChange={setRefreshSec}
            suffix="sec"
          />
        </Field>
        <Field label="Timezone">
          <Segmented
            value={tz}
            options={[
              { value: "America/New_York", label: "ET" },
              { value: "America/Chicago", label: "CT" },
              { value: "UTC", label: "UTC" },
            ]}
            onChange={setTz}
          />
        </Field>
        <Field label="Decimal places">
          <Segmented
            value={String(precision)}
            options={[
              { value: "2", label: "2" },
              { value: "3", label: "3" },
              { value: "4", label: "4" },
            ]}
            onChange={(v) => setPrecision(Number(v))}
          />
        </Field>
      </div>
    </Card>
  );
}

function BackendCard() {
  const [url, setUrl] = useStored<string>("backteststation.backendUrl", "http://localhost:8000");
  const [status, setStatus] = useState<"checking" | "ok" | "down">("checking");
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function ping() {
      setStatus("checking");
      try {
        const r = await fetch("/api/health", { cache: "no-store" });
        if (cancelled) return;
        if (r.ok) {
          setStatus("ok");
          try {
            const j = (await r.json()) as { version?: string };
            setVersion(j.version ?? null);
          } catch {
            setVersion(null);
          }
        } else {
          setStatus("down");
        }
      } catch {
        if (!cancelled) setStatus("down");
      }
    }
    ping();
    const id = setInterval(ping, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <Card>
      <CardHead
        eyebrow="backend"
        title="API endpoint and connection"
        right={
          <span className="flex items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
            <StatusDot
              tone={status === "ok" ? "pos" : status === "down" ? "neg" : "muted"}
              pulsing={status === "ok"}
            />
            {status}
          </span>
        }
      />
      <div className="grid gap-4 px-5 py-5">
        <Field label="Base URL">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="h-9 w-full rounded border border-line bg-bg-2 px-3 font-mono text-[12px] text-ink-1 outline-none transition-colors focus:border-accent-line"
            placeholder="http://localhost:8000"
          />
          <span className="mt-1 block text-[11px] text-ink-3">
            Currently proxied through Next.js at <span className="font-mono">/api/*</span> →{" "}
            <span className="font-mono">localhost:8000/api/*</span>. Changing this requires a
            restart to take effect.
          </span>
        </Field>
        {version && (
          <div className="flex items-center gap-2 font-mono text-[11px] text-ink-3">
            <span className="uppercase tracking-[0.06em]">backend version</span>
            <span className="text-ink-1">{version}</span>
          </div>
        )}
      </div>
    </Card>
  );
}

function AboutCard() {
  return (
    <Card>
      <CardHead eyebrow="about" title="BacktestStation" />
      <div className="grid gap-3 px-5 py-5 sm:grid-cols-2">
        <KV label="App version" value="0.2.0 — redesign" />
        <KV label="Frontend" value="Next.js 15 · React 19 · Tauri 2" />
        <KV label="Design system" value="Geist · cyan accent · slate cockpit" />
        <KV
          label="Repo"
          value={
            <a
              href="https://github.com/benbrainard11-netizen/BacktestStation"
              target="_blank"
              rel="noreferrer"
              className="text-accent hover:underline"
            >
              github.com/benbrainard11-netizen/BacktestStation
            </a>
          }
        />
      </div>
    </Card>
  );
}

/* ============================================================
   Field primitives — local to settings, kept dumb.
   ============================================================ */

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
      {children}
    </label>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function KV({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded border border-line bg-bg-2 px-3 py-2">
      <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-4">
        {label}
      </span>
      <span className="font-mono text-[12px] text-ink-1">{value}</span>
    </div>
  );
}

function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div
      role="radiogroup"
      className="inline-flex rounded border border-line-2 bg-bg-2 p-0.5"
    >
      {options.map((o) => {
        const sel = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={sel}
            onClick={() => onChange(o.value)}
            className={cn(
              "h-7 rounded px-3 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] transition-colors",
              sel ? "bg-accent text-bg-0" : "text-ink-3 hover:text-ink-0",
            )}
            style={sel ? { boxShadow: "0 0 8px var(--accent-glow)" } : undefined}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  suffix,
  gradient,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  suffix?: string;
  gradient?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      <div className="relative flex-1">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-y-0 left-0 right-0 my-auto h-1.5 rounded-full"
          style={{ background: gradient ?? "var(--bg-3)" }}
        />
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="settings-slider relative h-5 w-full appearance-none bg-transparent"
        />
      </div>
      <span className="w-12 text-right font-mono text-[12px] text-ink-1">
        {value}
        {suffix}
      </span>
      <style jsx>{`
        .settings-slider {
          /* override default track so the gradient shows through */
          background: transparent;
        }
        .settings-slider::-webkit-slider-runnable-track {
          height: 6px;
          background: transparent;
          border-radius: 999px;
        }
        .settings-slider::-moz-range-track {
          height: 6px;
          background: transparent;
          border-radius: 999px;
        }
        .settings-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          margin-top: -5px;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #fff;
          border: 2px solid var(--bg-1);
          box-shadow: 0 0 0 1px var(--line-3), 0 1px 3px rgba(0, 0, 0, 0.6);
          cursor: pointer;
        }
        .settings-slider::-moz-range-thumb {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #fff;
          border: 2px solid var(--bg-1);
          box-shadow: 0 0 0 1px var(--line-3), 0 1px 3px rgba(0, 0, 0, 0.6);
          cursor: pointer;
        }
      `}</style>
    </div>
  );
}

function NumberInput({
  value,
  min,
  max,
  step = 1,
  suffix,
  onChange,
}: {
  value: number;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="inline-flex items-center rounded border border-line bg-bg-2">
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-9 w-20 bg-transparent px-3 text-right font-mono text-[12px] tabular-nums text-ink-1 outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:m-0 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:m-0 [&::-webkit-outer-spin-button]:appearance-none"
      />
      {suffix && (
        <span className="px-2 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
          {suffix}
        </span>
      )}
    </div>
  );
}

function PreviewSwatch({
  a,
}: {
  a: { accentHue: number; accentSat: number; accentLight: number };
}) {
  const color = `hsl(${a.accentHue} ${a.accentSat}% ${a.accentLight}%)`;
  return (
    <span
      aria-hidden
      className="h-5 w-5 rounded-full"
      style={{ background: color, boxShadow: `0 0 8px ${color}` }}
    />
  );
}

/* ============================================================
   Tiny localStorage hook — only used by sections that aren't yet
   wired to the Appearance context (these are local prefs that
   don't need to drive CSS vars).
   ============================================================ */
function useStored<T>(key: string, initial: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(initial);
  useEffect(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw != null) setV(JSON.parse(raw) as T);
    } catch {
      /* ignore */
    }
  }, [key]);
  return [
    v,
    (next: T) => {
      setV(next);
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* ignore */
      }
    },
  ];
}

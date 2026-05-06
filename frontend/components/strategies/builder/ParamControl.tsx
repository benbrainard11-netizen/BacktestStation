"use client";

import { cn } from "@/lib/utils";

/**
 * One entry in a feature's `param_schema` object as returned by /api/features.
 *
 * Concrete shapes seen in the wild:
 *   { type: "integer", label: "Min score", min: 0, max: 8 }
 *   { type: "number",  label: "Body %", min: 0.1, max: 1.0, step: 0.05, description: "..." }
 *   { type: "string",  label: "Direction", enum: ["BULLISH", "BEARISH"] }
 */
export type ParamSchemaEntry = {
  type?: "integer" | "number" | "string" | "boolean" | string;
  label?: string;
  description?: string;
  min?: number;
  max?: number;
  step?: number;
  enum?: (string | number)[];
};

/**
 * ParamControl — render a single param input driven by its schema entry.
 *
 * - enum present → select
 * - type integer / number → numeric input with min/max/step
 * - type string → text input
 * - type boolean → checkbox
 * - anything else → text input fallback
 *
 * Caller owns value + onChange. Validation (min/max enforcement, required
 * checks) happens at the recipe level — this control is purely a renderer
 * with light constraints (HTML5 min/max attributes).
 */
export function ParamControl({
  name,
  schema,
  value,
  onChange,
  error,
  className,
}: {
  name: string;
  schema: ParamSchemaEntry | undefined;
  value: unknown;
  onChange: (v: unknown) => void;
  error?: string | null;
  className?: string;
}) {
  const label = schema?.label ?? name;
  const hint = schema?.description;
  const isEnum = Array.isArray(schema?.enum) && schema.enum.length > 0;
  const isNumeric = schema?.type === "integer" || schema?.type === "number";
  const isBoolean = schema?.type === "boolean";

  return (
    <div className={cn("grid gap-1", className)}>
      <div className="flex items-baseline gap-2">
        <label
          htmlFor={`param-${name}`}
          className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3"
        >
          {label}
        </label>
        <span className="font-mono text-[9.5px] text-ink-4">{name}</span>
      </div>

      {isEnum && (
        <select
          id={`param-${name}`}
          value={value == null ? "" : String(value)}
          onChange={(e) => onChange(coerce(e.target.value, schema))}
          className={inputClass(error)}
        >
          <option value="">— select —</option>
          {schema!.enum!.map((opt) => (
            <option key={String(opt)} value={String(opt)}>
              {String(opt)}
            </option>
          ))}
        </select>
      )}

      {!isEnum && isNumeric && (
        <input
          id={`param-${name}`}
          type="number"
          value={value == null || value === "" ? "" : Number(value)}
          onChange={(e) =>
            onChange(e.target.value === "" ? null : Number(e.target.value))
          }
          min={schema?.min}
          max={schema?.max}
          step={schema?.step ?? (schema?.type === "integer" ? 1 : "any")}
          className={inputClass(error)}
        />
      )}

      {!isEnum && isBoolean && (
        <input
          id={`param-${name}`}
          type="checkbox"
          checked={value === true}
          onChange={(e) => onChange(e.target.checked)}
          className="h-4 w-4 accent-accent"
        />
      )}

      {!isEnum && !isNumeric && !isBoolean && (
        <input
          id={`param-${name}`}
          type="text"
          value={value == null ? "" : String(value)}
          onChange={(e) => onChange(e.target.value)}
          className={inputClass(error)}
        />
      )}

      {hint && !error && (
        <span className="text-[10.5px] leading-snug text-ink-3">{hint}</span>
      )}
      {error && (
        <span className="font-mono text-[10.5px] text-neg">{error}</span>
      )}
    </div>
  );
}

function inputClass(error?: string | null): string {
  return cn(
    "rounded border bg-bg-2 px-2 py-1 font-mono text-[12px]",
    error ? "border-neg/50 text-neg" : "border-line text-ink-1",
  );
}

function coerce(raw: string, schema: ParamSchemaEntry): unknown {
  if (raw === "") return null;
  if (schema.type === "integer") return Number.parseInt(raw, 10);
  if (schema.type === "number") return Number.parseFloat(raw);
  return raw;
}

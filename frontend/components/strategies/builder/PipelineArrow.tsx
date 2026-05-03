"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Arrow connecting two PipelineStages. Horizontal at xl widths, vertical
 * (downward) below that. Optionally renders an inline label (e.g. "pass →")
 * and a control widget (e.g. SetupWindowControl on the setup→trigger arrow).
 */
export function PipelineArrow({
  label,
  control,
  className,
}: {
  label?: string;
  control?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center xl:flex-col xl:px-1",
        className,
      )}
    >
      <div className="flex flex-col items-center gap-0.5 px-2 xl:px-0 xl:py-1">
        {label && (
          <span className="font-mono text-[9px] uppercase tracking-[0.08em] text-ink-3">
            {label}
          </span>
        )}
        {control}
        {/* Arrow glyph: → on xl, ↓ below */}
        <span className="font-mono text-[18px] leading-none text-accent">
          <span className="hidden xl:inline">→</span>
          <span className="xl:hidden">↓</span>
        </span>
      </div>
    </div>
  );
}

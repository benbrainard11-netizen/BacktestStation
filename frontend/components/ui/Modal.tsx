"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

/**
 * Modal — fixed-overlay dialog.
 *
 * - Click backdrop or press Esc to dismiss.
 * - Focuses the first focusable child on open; restores prior focus on close.
 * - `size` controls max-width (sm = max-w-md, md = max-w-xl, lg = max-w-3xl).
 * - Pass `footer` for a sticky bottom bar with action buttons.
 *
 * Pattern reference: NewStrategyDialog in app/strategies/page.tsx.
 */
export function Modal({
  open,
  onClose,
  title,
  eyebrow,
  size = "md",
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  eyebrow?: string;
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const focusable = dialogRef.current?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    focusable?.focus();
    return () => {
      previouslyFocused?.focus();
    };
  }, [open]);

  if (!open) return null;

  const sizeClass =
    size === "sm" ? "max-w-md" : size === "lg" ? "max-w-3xl" : "max-w-xl";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg-0/80 p-4 backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "modal-title" : undefined}
        className={cn(
          "w-full rounded-lg border border-line bg-bg-1 shadow-2xl",
          sizeClass,
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {(title || eyebrow) && (
          <div className="border-b border-line px-5 py-4">
            {eyebrow && <div className="card-eyebrow mb-0.5">{eyebrow}</div>}
            {title && (
              <h2 id="modal-title" className="card-title">
                {title}
              </h2>
            )}
          </div>
        )}
        <div className="px-5 py-5">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-line bg-bg-0 px-5 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

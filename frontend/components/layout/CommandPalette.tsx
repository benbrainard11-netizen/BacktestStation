"use client";

import { Search, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Icon } from "@/components/Icon";
import { ALL_NAV_ITEMS } from "@/lib/navigation";

type Item = (typeof ALL_NAV_ITEMS)[number];

/**
 * Command palette v1 — read-only nav launcher.
 *
 * Opens via:
 *  - Cmd/Ctrl+K
 *  - "open-cmd" CustomEvent (fired by topbar cmd icon and subnav search pill)
 *
 * Searches every nav item by label / group / profile / id. Arrow keys move
 * the active row, Enter navigates, Escape closes. No mutating commands yet.
 */
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);

  // Open via Cmd/Ctrl+K and via the "open-cmd" CustomEvent.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    function onOpenCmd() {
      setOpen(true);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("open-cmd", onOpenCmd as EventListener);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("open-cmd", onOpenCmd as EventListener);
    };
  }, []);

  // Reset on every open and focus the input.
  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActive(0);
    requestAnimationFrame(() => inputRef.current?.focus());
  }, [open]);

  const close = useCallback(() => setOpen(false), []);

  const results = useMemo<Item[]>(() => {
    const q = query.trim().toLowerCase();
    if (!q) return ALL_NAV_ITEMS.slice(0, 20);
    return ALL_NAV_ITEMS.filter((it) => {
      const hay =
        `${it.label} ${it.group} ${it.profileLabel} ${it.id} ${it.href}`.toLowerCase();
      return q.split(/\s+/).every((tok) => hay.includes(tok));
    }).slice(0, 25);
  }, [query]);

  // Clamp active index when results shrink.
  useEffect(() => {
    if (active >= results.length) setActive(0);
  }, [active, results.length]);

  const navigate = useCallback(
    (it: Item) => {
      router.push(it.href);
      setOpen(false);
    },
    [router],
  );

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      close();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (results.length === 0 ? 0 : (i + 1) % results.length));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) =>
        results.length === 0 ? 0 : (i - 1 + results.length) % results.length,
      );
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      const target = results[active];
      if (target) navigate(target);
      return;
    }
  }

  // Scroll the active item into view.
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const el = list.querySelector<HTMLElement>(
      `[data-cmd-row="${active}"]`,
    );
    el?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (!open) return null;

  return (
    <div
      className="cmd-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="cmd-box" onKeyDown={onKeyDown}>
        <div className="cmd-input-row">
          <Search size={14} aria-hidden />
          <input
            ref={inputRef}
            className="cmd-input"
            placeholder="Jump to a page…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActive(0);
            }}
            spellCheck={false}
            autoComplete="off"
            aria-label="Search commands"
            aria-autocomplete="list"
            aria-controls="cmd-list"
            aria-activedescendant={
              results[active] ? `cmd-row-${active}` : undefined
            }
          />
          <button
            type="button"
            className="cmd-close"
            onClick={close}
            aria-label="Close command palette"
          >
            <X size={14} />
          </button>
        </div>

        <div
          id="cmd-list"
          ref={listRef}
          className="cmd-list"
          role="listbox"
        >
          {results.length === 0 ? (
            <div className="cmd-empty">No matches.</div>
          ) : (
            results.map((it, i) => (
              <div
                key={`${it.profile}-${it.id}`}
                id={`cmd-row-${i}`}
                data-cmd-row={i}
                role="option"
                aria-selected={i === active}
                className={`cmd-item${i === active ? " active" : ""}`}
                onMouseEnter={() => setActive(i)}
                onClick={() => navigate(it)}
              >
                <span className="cmd-item-icon">
                  <Icon name={it.icon} size={14} />
                </span>
                <span className="cmd-item-label">{it.label}</span>
                <span className="cmd-item-meta">
                  {it.profileLabel} · {it.group}
                </span>
                <span className="cmd-item-kbd">{it.href}</span>
              </div>
            ))
          )}
        </div>

        <div className="cmd-foot">
          <span>
            <span className="kbd-mini">↑</span>
            <span className="kbd-mini">↓</span> navigate
          </span>
          <span>
            <span className="kbd-mini">↵</span> open
          </span>
          <span>
            <span className="kbd-mini">esc</span> close
          </span>
        </div>
      </div>
    </div>
  );
}

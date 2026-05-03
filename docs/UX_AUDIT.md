# UX Audit — 2026-05-02 (foundation + correctness pass)

Snapshot of the frontend after the overnight UX foundation pass and the
follow-up correctness pass the same day. Source of truth for the visual
language is `docs/DESIGN_SYSTEM_REFERENCE.md`.

## What was improved this pass

- **Build is green.** `npm run build` and `npm run typecheck` both clean.
  Two ESLint errors blocked compile (unescaped quotes in
  `app/experiments/page.tsx` and `app/risk-profiles/page.tsx`); both fixed.
  Hook-deps warnings around `const all = state.kind === "data" ? data : []`
  fallbacks fixed across the tree (overview, backtests, data-health,
  knowledge, notes, prompts, prop-firm/new, trade-replay, replay,
  strategies/[id]/{build,research}). Build now emits zero lint warnings.
- **Real shared button styles.** `.btn`, `.btn-primary`, `.btn-ghost`,
  `.btn-danger`, `.btn-sm`, `.btn-xs` defined in `app/globals.css` against
  the design tokens. Existing usages (Import, Notes, Knowledge, Prompts,
  Prop Firm, Strategies build/research) now share one visual language.
  Hover/focus-visible/disabled all wired.
- **Command palette v1.** New `components/layout/CommandPalette.tsx` mounted
  in `AppShell`. Opens via Cmd/Ctrl+K, the topbar command icon, the subnav
  search pill, and the existing `open-cmd` CustomEvent. Searches every nav
  item by label / group / profile / id / route. Arrow keys + Enter +
  Escape; mouse hover + click. Accessible: `role="dialog"`,
  `aria-modal="true"`, focus moves to the input on open, listbox + options
  semantics. Read-only (navigation only) per scope.
- **Replay page redesigned in the design system.** `ReplayLoader` and
  `ReplayChart` rewritten with `Card` / `CardHead` / `Chip` and the shared
  `.btn` classes. Chart still uses lightweight-charts; logic untouched.
  The control bar is clearer: lucide play / pause / step icons, a real
  segmented "speed" control with active-state, an FVG on/off toggle that
  mirrors its state, and the cursor's bar count + UTC time + close price
  shown as chips in the card head. The chart now sources its own colors
  from the CSS tokens so theme switches actually apply.
- **Overview is a real "what now?" page.** Stat row stays. The right column
  becomes a vertical action list with icon + label + live sub-text:
  Live monitor (shows bot status), Data health, Inspect last backtest
  (deep-links to the actual run id), Import results, Replay a trading day,
  Run a new backtest. No invented data; everything reads from existing
  `/api/...` polls.
- **Smoke tests match current routes.** Stale routes removed (`/journal`,
  `/data`, `/prop-simulator/*`); coverage added for `/`, `/monitor`,
  `/notes`, `/data-health`, `/settings`, `/import`, `/experiments`,
  `/knowledge`, `/research`, `/prompts`, `/backtests`, `/replay`,
  `/trade-replay`, `/compare`, `/strategies`, `/risk-profiles`,
  `/strategies/builder`, `/prop-firm`, `/prop-firm/runs`,
  `/prop-firm/firms`, `/prop-firm/new`. Plus a command-palette test:
  open with Ctrl+K → type `monitor` → Enter → assert `/monitor` loads.

## 2026-05-02 follow-up — correctness pass

After the foundation pass landed, a focused correctness pass closed the
obvious sharp edges:

- **`usePoll` accepts `string | null` to disable.** `frontend/lib/poll.ts`
  short-circuits when the URL is null/undefined — no fetch, no timer. Fixes
  `DataQualityTab` calling `usePoll("")` (which fetched the current page
  HTML) before the user picked a run. Existing string callers are
  unaffected.
- **Overview "Run a new backtest" lands where the action lives.**
  `/backtests` now reads `?new=1` and auto-opens the Run-backtest modal
  on mount, then strips the param so reload doesn't re-pop. The Overview
  CTA points to `/backtests?new=1` instead of `/strategies`.
- **Command palette: focus capture/restore + focus trap.** Mirrors
  `components/ui/Modal.tsx`: saves the previously-focused element on open,
  restores it on close, traps Tab/Shift+Tab inside the dialog. All existing
  semantics preserved (Cmd/Ctrl+K, listbox/dialog, arrow nav, Enter,
  Escape, mouse).
- **Replay chart is theme-reactive.** Subscribes to `useAppearance()` so
  switching theme / accent / density in Settings re-applies chart layout
  + series colors via `chart.applyOptions` and `series.applyOptions`. No
  remount, no reload. Markers re-emit with new colors. FVG primitive
  unchanged (its visuals don't depend on theme).
- **`/research` is a real landing page.** Replaces the `PageStub` with
  four honest stat cards (strategies / open experiments / knowledge cards
  / notes) sourced from existing polls, a strategies list deep-linking
  to each `/strategies/[id]/research`, and a quick-link block to the
  cross-strategy ledgers (Experiments, Knowledge, Notes, AI Prompts,
  Compare). No invented data; empty states render when polls are empty
  or backend is down.
- **Active docs truth-pass.** `PROJECT_STATE.md`, `ROADMAP.md`,
  `DESIGN_SYSTEM_REFERENCE.md` updated for: Settings is fully editable
  (was claimed read-only), `/replay` FVG rendering shipped (was
  "deferred"), prop firm routes live at `/prop-firm` (was
  `/prop-simulator`), command palette is v1 navigation-only.
- **More CTAs migrated to the shared `.btn` family.** `+ Run backtest`
  (backtests page header), `+ New experiment` (experiments header),
  `+ New profile` (risk-profiles header), `Reset all` (settings header)
  all use `btn btn-primary btn-sm` / `btn btn-sm` instead of bespoke
  Tailwind strings. Form save/cancel buttons inside modals were left
  alone (they styling-match their input cluster — separate sweep).
- **Dead code dropped.** `weekAgo()` helper in `app/backtests/page.tsx`
  (placeholder, returned `false`) removed.

## Remaining UX gaps

- **In-form buttons still drift.** Save/Cancel buttons *inside* the
  experiments/risk-profiles/notes/knowledge create-and-edit forms still
  use bespoke Tailwind strings. They style-match their input clusters,
  so converting them is bigger than a simple class swap. Separate sweep.
- **Command palette is read-only.** v1 only navigates. No "Run new
  backtest" action, no "Import results" action, no recent-runs section
  (per `docs/DESIGN_SYSTEM_REFERENCE.md` §5). Adding actions requires a
  `kind: "navigate" | "action"` discriminator and a small action registry.
- **Palette focus restoration not asserted in Playwright.**
  `document.activeElement` checks via `page.evaluate` are brittle; we
  rely on visual review and the trap+escape coverage instead. If a
  regression slips through, add an assertion via the `:focus` CSS
  pseudo-class on a known element.
- **No global keyboard hints.** The footer of the palette explains its
  own shortcuts, but there's no "?" overlay listing the rest (`⌘1/2/3`
  for profiles, `⌘K` to open palette). Cheap to add: a single
  `KeyboardHelp` modal triggered by `?`.
- **Loading skeletons are inconsistent.** Some pages show `Loading…`
  text, some a spinner, some nothing. The design reference prescribes
  `bg-2` 1-px-line skeleton rows at table-row height. A `Skeleton`
  primitive in `components/atoms.tsx` would unify this.
- **Empty states are inconsistent.** Some pages render a card with
  centered `empty state` mono caption; some render just plain text.
  Promote the existing pattern into `EmptyState` (already present at
  `components/ui/EmptyState.tsx`) and use it everywhere.
- **Replay control bar is dense at narrow widths.** It wraps acceptably
  but the speed segmented control and the slider compete for space below
  ~900px. Either move the slider to its own row at narrow widths, or
  drop the slider and rely on play/pause/step.
- **Overview's TPT card has a placeholder.** "Trailing drawdown" reads
  zero with a `awaiting /api/prop-firm/profiles wiring` note. Wire the
  read once a single firm profile is locked in (see project memory).

## Recommended next UI pass

1. **Migrate every primary CTA to `.btn` / `.btn-primary`.** Sweep
   `experiments`, `risk-profiles`, `knowledge`, `notes`, `prop-firm` and
   delete the local Tailwind button strings. One PR per page; each one
   shrinks the design surface area.
2. **Command palette v2: actions + recent runs.** Add a small registry
   of "actions" (Run new backtest, Open last run's CSV, Import results)
   and a "recent runs" section sourced from `/api/backtests` (top 5).
   Same nav semantics; arrow keys span both sections.
3. **Skeleton + empty-state primitives.** Bring all page-level loading
   and empty UIs through one component each. Cuts a class of "this page
   feels different" complaints in one shot.
4. **Settings wiring.** `/settings` is a stub. Wire theme variants
   (`darker` / `dim`), accent hue (`--accent-h` slider), motion off
   toggle, and the Tauri-only "always on top" knob. All four pieces
   exist in CSS already; just need a real form.
5. **Replay polish.** Move the timeline scrubber to its own row at
   narrow widths and surface a "jump to next entry" button alongside
   step.

## Files changed this pass

- `frontend/app/globals.css` — buttons + command palette CSS
- `frontend/components/layout/CommandPalette.tsx` — new
- `frontend/components/layout/AppShell.tsx` — mount palette
- `frontend/app/page.tsx` — overview rewrite
- `frontend/components/replay/ReplayLoader.tsx` — design-system rewrite
- `frontend/components/replay/ReplayChart.tsx` — design-system rewrite
- `frontend/app/experiments/page.tsx` — escape quotes in empty state
- `frontend/app/risk-profiles/page.tsx` — escape quotes in evaluate panel
- `frontend/app/backtests/page.tsx` — `useMemo` array fallback
- `frontend/app/data-health/page.tsx` — `useMemo` array fallback
- `frontend/app/knowledge/page.tsx` — `useMemo` array fallback
- `frontend/app/notes/page.tsx` — `useMemo` array fallback
- `frontend/app/prompts/page.tsx` — `useMemo` array fallback
- `frontend/app/prop-firm/new/page.tsx` — `useMemo` array fallback
- `frontend/app/strategies/[id]/build/page.tsx` — `useMemo` array fallback
- `frontend/app/strategies/[id]/research/page.tsx` — `useMemo` array fallback
- `frontend/app/trade-replay/page.tsx` — `useMemo` array fallback
- `frontend/e2e/smoke.spec.ts` — fresh route table + palette test

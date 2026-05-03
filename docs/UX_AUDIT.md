# UX Audit — 2026-05-02

Snapshot of the frontend after the overnight UX foundation pass. Source of
truth for the visual language is `docs/DESIGN_SYSTEM_REFERENCE.md`.

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

## Remaining UX gaps

- **Inline buttons still drift.** Several pages (experiments, risk-profiles,
  knowledge, notes, prop-firm) still hand-roll their primary action button
  with custom `accent-soft / pos / neg` Tailwind strings instead of the
  shared `.btn-primary`. Migrate one page at a time so the button family
  reaches every CTA. Easy follow-up: replace the inline `accent-line bg-accent-soft px-...` patterns with `btn btn-primary`.
- **Command palette is read-only.** v1 only navigates. No "Run new
  backtest" action, no "Import results" action, no recent-runs section
  (per `docs/DESIGN_SYSTEM_REFERENCE.md` §5). Adding actions requires a
  `kind: "navigate" | "action"` discriminator and a small action registry.
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

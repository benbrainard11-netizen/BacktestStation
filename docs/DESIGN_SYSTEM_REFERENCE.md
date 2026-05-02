# BacktestStation — Design System Reference

Single source of truth for the dark-mode quant cockpit visual language extracted from the Claude Artifacts bundle in `design_extract/`. Use this to rebuild the entire frontend (51 endpoints across 18 routers) in the same idiom.

Source files audited: `02.jsx` (mock data), `03.jsx` (3D scenes), `04.jsx` (icons + atoms), `05.jsx` (10 pages), `06.jsx` (Strategy Builder + Feature Builder), `07.jsx` (app shell + cmd palette), `__template.html.json` (CSS).

---

## 1. Brand & visual identity

A **deep-slate, terminal-grade quant cockpit**. Near-black background (`#08090b`), three subtle elevations (`bg-1`/`bg-2`/`bg-3`), surgically thin hairlines (`#1d2128`) for separation rather than fills. Typography is dual: **Geist** (sans, tight `-0.02em` heading tracking, no italics anywhere) for prose and titles; **Geist Mono** with tabular numbers for every number, ID, code block, kbd chip, eyebrow label, and column header. The single bright accent is **electric cyan `#22d3ee`** with a soft 10% wash and a glowing 40% line — used sparingly for current state, top-tab underlines (with a real CSS box-shadow neon glow), validity OKs, and primary buttons. A secondary violet `#a78bfa` shows up in 3D shadow ribbons and the brand-mark gradient. Status semantics are strict: **green `#34d399` positive · red `#f87171` negative · amber `#fbbf24` warn · blue `#60a5fa` info**. Decoration is rare — borders, dotted "add rule" affordances, 6px / 10px radii, and the only motion is a 1.6s `live-pulse` dot, a 2s `blink` on live badges, and gentle 3D camera drift. Three WebGL scenes (equity ribbon, trade scatter, monte-carlo fan) inject visual weight without losing the spreadsheet-on-a-Bloomberg-terminal feel. Glassmorphism appears once: the cmd-palette overlay uses `backdrop-filter: blur(8px)` over `rgba(0,0,0,0.6)`.

---

## 2. Design tokens (verbatim from `<style>`)

### Backgrounds (default theme)
```
--bg-0: #08090b   page / topbar
--bg-1: #0f1115   surface, sidebar, card, sub-nav
--bg-2: #161a20   raised / hover / inputs / chips
--bg-3: #1f242c   second raise (kbd, scrollbar thumb)
--bg-4: #2a3038   highest raise (rare)
```

### Ink / text
```
--ink-0: #f5f7fa     headings, key values
--ink-1: #d6dae0     body
--ink-2: #a0a8b3     secondary
--ink-3: #6b7480     captions, "muted"
--ink-4: #454c56     "dim", grid lines, ticks
--text-0..-4         alias chain → ink-0..-4
```

### Lines
```
--line:   #1d2128   default hairline
--line-2: #2a3038   raised border
--line-3: #3a414b   hover border
```

### Accent / semantic
```
--accent-h:    188 (CSS hue var, runtime-tunable 0–360)
--accent:      #22d3ee  (cyan)
--accent-2:    #a78bfa  (violet, brand gradient + 3D shadow)
--accent-soft: rgba(34,211,238,0.10)
--accent-line: rgba(34,211,238,0.40)
--pos:         #34d399  --pos-soft: rgba(52,211,153,0.12)
--neg:         #f87171  --neg-soft: rgba(248,113,113,0.12)
--warn:        #fbbf24
--info:        #60a5fa
```

### Radii / fonts
```
--r:    6px       buttons, inputs, chips, nav items
--r-lg: 10px      cards, canvas, stat-grid, presets
--mono: 'Geist Mono', ui-monospace, monospace
--sans: 'Geist', system-ui, sans-serif
--serif: same as --sans (no real serif)
```
No spacing or shadow scale tokens — values are inline (8 / 10 / 12 / 14 / 18 / 24 / 32 px). Typical card shadow is just `1px solid var(--line)`; only the cmd-box gets `0 24px 60px rgba(0,0,0,0.5)` and accent glows use `box-shadow: 0 0 12px var(--accent), 0 0 4px var(--accent)`.

### Theme variants (data-attribute on `<html>`)
```
[data-theme="darker"]  bg-0 #000  bg-1 #08090b  bg-2 #0f1115  bg-3 #161a20  line #15181d
[data-theme="raised"]  bg-0 #0d1117 bg-1 #161b22 bg-2 #21262d  bg-3 #30363d  line #21262d
[data-motion="off"]    disables all animations + transitions
```

---

## 3. Typography

- **Display / sans**: Geist 400 / 500 / 600 / 700 (woff2 self-hosted). Body 14px / 1.5 / `letter-spacing -0.005em`.
- **Mono**: Geist Mono 400 / 500 / 600. Always with `font-feature-settings:'tnum' on` and `letter-spacing -0.005em`.
- **Headings**:
  - `.page-title` — 32px / 600 / `-0.03em` / line-height 1.05
  - `.card-title` — 13px / 600 / `-0.005em`
  - `.stat-value` — 28px / 600 / `-0.025em` / tabular-nums
  - `.brand-name` — 14px / 600 / `-0.01em` (mini), `-0.02em` (full)
- **Body**: 13.5–14px sans, line-height 1.5
- **Captions / sub**: 11–12px, `var(--text-3)`
- **Mono used for**: every number, every `#id`, every timestamp, table column headers (`th` 10.5px uppercase), eyebrows (`.page-eyebrow` 11px uppercase 0.08em accent-color), kbd chips, code preview, nav-section titles, top-meta strip, tags, brand-version label.
- **Uppercase conventions**: page eyebrows, table headers, nav-section titles, stat labels, sb-meta labels, sub-nav group titles — all paired with letter-spacing 0.06–0.12em.
- **No italics** anywhere — explicit comment in CSS: "No italics."

---

## 4. Component catalog

### Atoms (`04.jsx` + `__template.html.json`)
| Name | Purpose | Variants | Where |
|---|---|---|---|
| `Ic` | Inline SVG icon set, 16px viewBox, `currentColor`, `strokeWidth=1.5` | search, home, bolt, layers, flask, pulse, shield, film, database, clipboard, cog, alert, cmd, play, arrow, plus, download, filter, bell, beaker, compare | nav icons, buttons |
| `Sparkline` | 80×24 polyline with rounded caps | accepts `color`, default `var(--accent)` | inside `.stat` (absolute right) |
| `MiniChart` | Responsive area+line chart with linear-gradient fill | accepts `color`, `fill` | Backtests equity card |
| `Stat` | Label + 28px value + delta + optional sparkline | `delta-pos` / `delta-neg` | every page top |
| `Chip` | Pill 11px / radius 4px | default, `pos`, `neg`, `accent`, `warn`; with `chip-dot` | sources, decisions, statuses |
| `Tag` | Mono 10.5px, radius 3px, no color variant | – | strategy tags, exit reasons, symbol lists |
| `Bar` | 5px tall progress | default, `pos`, `neg` | risk caps, rule violations |
| `Card` | `bg-1` surface, `r-lg`, optional title/sub/action header, `flush` body | – | universal container |
| `StatusDot` | 6px dot with `live-pulse` animation when `kind="live"` | `live`, `warn`, `err`, default | pipeline health, top meta |

### Buttons
| Class | Visual | Use |
|---|---|---|
| `.btn` | 36px high, `bg-2` + `line-2` border, `ink-0` text, 13px / 500 | default action |
| `.btn-primary` | accent fill, dark `#031419` text, 600 weight | one per page-head right |
| `.btn-ghost` | transparent, `text-2`, hover bg-2 | secondary toolbar |
| `.btn-sm` | 28px high / 12px / 10px pad | inline card actions |
| `.icon-btn` | 32×32 grid, radius 6px | top-bar utility |
| `.search-btn` / `.search-pill` | full-width inset search field with kbd hint `⌘K` | sidebar / sub-nav |

### Inputs (Strategy Builder)
| Class | Visual |
|---|---|
| `.sb-input` | `bg-2` + `line-2` border, focus = accent border + 3px `accent-soft` ring + `bg-3` |
| `.sb-input.mono` | Geist Mono 12px |
| `.sb-input-sm` / `.sb-input-xs` | tighter pads, `min-width:90px` / `width:64px` centered |
| `<select>` and `<textarea>` | reuse `.sb-input` |
| `.sb-toggle` | 38×22 pill, off = `bg-3`/text-3 thumb, on = `accent-soft` bg + accent thumb with 8px glow |

### Navigation
| Component | Spec |
|---|---|
| `TopTabs` (`.top-tabs`) | 54px tall, `bg-0`, brand-mini left (mark gradient cyan→violet), three `.ttab` profile buttons; active = ink-0 + 600 + 2px accent underline with `0 0 12px accent` glow; right side `top-meta` (mono live indicators) + cmd / bell / cog icon buttons |
| `SubNav` (`.subnav`) | 48px tall, `bg-1`, horizontal scroll, divided into `.subnav-group`s separated by 1px right border; each item `.subnav-item` 30px / 13px / radius 6, active = accent text + `accent-soft` bg + inset 1px `accent-line` ring; live items get a green `.subnav-live` mini-badge |
| `.search-pill` | right-end of subnav, 30px / `bg-2` / 12px text-3, opens cmd palette |
| `.sidebar` (legacy) | 240px wide, present in CSS but `app-tabbed` hides it — keep for an optional collapsed-drawer mode |

### Tabs (in-page)
- `.tabs` / `.tab` — 36px high, 13px, `aria-selected="true"` paints `border-bottom-color:var(--accent)` and ink-0 color
- `.sb-tabs` / `.sb-tab` — same pattern with a `.sb-tab-count` mono pill (`bg-2` border, accent when current)

### Pills / segmented controls (Strategy Builder)
- `.sb-pill-group` + `.sb-pill` — AND/OR toggle, current-state = solid accent fill on `bg-0` text with glow
- `.sb-format-group` + `.sb-format-btn` — DSL/Python format selector, same active pattern
- `.sb-feat-tab` — Current/Builder feature tabs

### Surfaces / cards
- `.card` — `bg-1`, 1px line, `r-lg`, optional `card-head` (14×18 pad, bottom border) + `card-body` (18 pad, set `flush` to remove)
- `.stat-grid` — 4-col grid on a 1px gap shown as a darker line (`background:var(--line)` underneath), each `.stat` 108px min, sparkline absolutely positioned right
- `.canvas3d` — host for `<canvas>`, 1px line + radius 10
- `.cmd-box` — 580×max-90vw, `bg-1` + `line-3`, large drop-shadow

### Strategy-Builder–specific
| Class | Purpose |
|---|---|
| `.sb-grid` | `1fr / 380px` two-col layout; collapses below 1100px |
| `.sb-meta` / `.sb-meta-grid` | 4-col header (Symbol/TF/Session/Side) |
| `.sb-entry` | Card-in-card holding rules |
| `.sb-rule` / `.sb-rule-body` | Block row (left ind → op → right ind) with hover and `is-active` accent ring; `.sb-rule-glue` shows the inter-rule AND/OR badge |
| `.sb-add-rule` | Dashed `line-2` add-zone, hover paints accent |
| `.sb-icon-btn` | 24×24 close button, hover red wash |
| `.sb-exit` + `.sb-exit-kind` | row with kind-color label: stop=red, target=green, time=cyan, trailing=violet |
| `.sb-risk-row` | label/hint left + control right, on `bg-2` |
| `.sb-preset` / `.sb-preset-tag` | preset card with hover lift `translateY(-1px)` and accent border |
| `.sb-validity` | `.ok` (green) / `.warn` (amber) — pill with pulsing dot |
| `.sb-code` | mono 11.5px / line 1.6 / pre, max-height 280, scrollable |
| `.sb-feat` / `.sb-feat-dot` | live-feature summary row with colored glow dot (cyan/green/red/amber/violet for market/entry/exits/risk/filters) |
| `.fb-*` (Feature Builder) | `.fb-item` (saved feature card with `.fb-item-name` accent + `.fb-item-kind` color-coded), `.fb-form` (snake-case validated input + textarea + helper-fn buttons + add btn), `.fb-error` |

### Research-specific
| Class | Purpose |
|---|---|
| `.research-grid` | 2×2 grid of research cards |
| `.r-list` / `.r-item` | hairline-separated rows of `[ID-tag] [title+meta] [chip]`, hover bg-2 |
| `.r-item-tag` | mono 10px UPPERCASE pill (`H-042`, `K-118`, `D-088`, `E-019`) |
| `.r-empty` | centered 32px-pad empty state |

### Cmd palette
- `.cmd-overlay` — `rgba(0,0,0,0.6)` + 8px backdrop-blur, opens at 14vh from top
- `.cmd-input-row` — 14×18 padded, search icon + transparent input
- `.cmd-item` / `.cmd-item.active` — 10×18 row, active = bg-2 + ink-0; `.cmd-item-kbd` mono right-aligned hint
- `.cmd-foot` — mono 11px tri-instruction strip ("↑↓ navigate · ↵ open · esc close")

### Misc
- `.kbd-mini` / `.search-btn-kbd` — inset mono chip on `bg-1`/`bg-2` with `line` border
- `.profile-tabs` / `.ptab` — alternative browser-tab style (defined but not used by `App` — keep available)
- `.foot-dot` — 8px green dot with 2.4s pulse
- `.live-pulse` — 6px dot with 1.6s scale-pulse and 3px soft halo
- `.pdots` / `.pdot` — progress dots (defined, unused in extracted pages)

---

## 5. Page / view inventory

10 implemented pages + 7 stub pages, organized by 3 top-level **Profiles** (Dashboard / Research / Strategies), each with sub-nav groups. App is single-page-tabbed: profile = top tab, page = sub-nav item. Layout for every page: `.page-head` (eyebrow + 32px title + sub) flanked right by 1–3 buttons, then `.stat-grid` row, then a 1- or 2-column card grid. Max width 1500px (1480px in Strategy Builder's `content-wide`).

| # | Page (`PAGES` key) | Profile / group | Backend feature | Layout | Key components |
|---|---|---|---|---|---|
| 1 | `overview` | Dashboard / Live | aggregate of monitor + recent runs + alerts | head → 4-stat → `g-2-1` (EquityRibbon3D + Live Monitor card) → `g-2-1` (Recent Runs table + Alerts list) | `EquityRibbon3D`, `Stat`, `Card`, `tbl`, `Chip`, `StatusDot` |
| 2 | `monitor` | Dashboard / Live | monitor router | head + green pill → 4-stat → `g-2-1` (drift SVG line chart + Pipeline Health checklist) → Session Journal table | inline SVG line chart with two polylines, `StatusDot`, `tbl` |
| 3 | `datahealth` | Dashboard / System | data-health router | head → 4-stat → "By schema" table | `tbl`, `Tag`, `Chip` (ok/warn) |
| 4 | `research_hub` (`PageResearch`) | Research / Research | notes + experiments (hypotheses/decisions) | head → 4-stat → `research-grid` 2×2 (Open research / Pending experiments / Knowledge / Decisions) → audit-log table | `r-list`, `r-item`, `Chip`, `Tag` |
| 5 | `experiments` | Research / Research | experiments router | head → flush card with full-width experiments table | `tbl`, `Chip` color-coded by decision |
| 6 | `backtests` | Research / Test | backtests + backtest_export + autopsy + data_quality | head with run chips → `260px / 1fr` (Run picker list + 5-stat row + TradeScatter3D) → `g-2` (Equity MiniChart + Autopsy strengths/weaknesses) → flush trades table (max-height scroll) | `TradeScatter3D`, `MiniChart`, `Stat`, `tbl`, picker rows with active accent left-border |
| 7 | `replay` | Research / Test | trade-replay router (TBBO ticks) | head → `g-2-1` (Order Book Tape SVG + range slider + Tick L1 card) | inline SVG dual polyline (bid red / ask cyan), native `<input type="range">` with accent thumb |
| 8 | `strategies_list` (`PageStrategies`) | Strategies / Build | strategies router (lifecycle stages) | head → 6-column kanban (one per stage) → drag-style cards | per-card mini stat row (versions/runs + pnl), `Tag` |
| 9 | `strategy_builder` (`PageStrategyBuilder`) | Strategies / Build | strategies + strategy-versions (compose entry/exit/risk DSL) | `content-wide` 1480px / `sb-grid` 1fr+380px, sticky right column → meta header → `sb-tabs` (entries/exits/risk/filters) → live preview + custom-feature builder right rail | `SBRule`, `sb-pill-group`, `sb-toggle`, `SBNumberRow`, `sb-preset`, `FeatureBuilder` |
| 10 | `risk` (`PageRisk`) | Strategies / Build | risk-profiles router | head → `g-3` of profile cards, each with 24-cell hour grid (active hours = accent-soft) | per-row label/value + `Bar` |
| 11 | `simulator` | Strategies / Prop Firm | prop-firm router (Monte Carlo) | head → 4-stat → MonteCarloFan3D card → `g-2` (Rule Violations bars + Risk Sweep inline SVG) | `MonteCarloFan3D`, `Bar`, scatterplot SVG |

### Stubs (`PageStub` — real chrome, "scaffolded" eyebrow, empty state)
| Stub key | Profile / group | Blurb (already drafted in `07.jsx`) |
|---|---|---|
| `journal` | Dashboard / Live | Hand-written notes against live trades |
| `settings` | Dashboard / System | Connections, API keys, telemetry, theme, keybindings |
| `import` | Research / Research | CSV/parquet uploader + column mapper |
| `knowledge` | Research / Research | Curated knowledge cards |
| `firm_rules` | Strategies / Prop Firm | Funded-firm rule sets |
| `simulation_runs` | Strategies / Prop Firm | Sim execution log + re-run/fork |
| `compare` | Strategies / Prop Firm | Diff two runs side-by-side |

### Top-level chrome present on every page
- `TopTabs` — brand mini · 3 profile tabs · live `top-meta` (bot RUNNING dot + NQ price + P&L) · cmd / bell / cog icon buttons
- `SubNav` — grouped sub-nav for the active profile + `.search-pill ⌘K`
- `CommandPalette` — global, opens on `⌘K` / `ctrl+K` or topbar cmd icon — searches all nav items + actions (Run new backtest / Export run as CSV / Create experiment) + recent runs

---

## 6. Coverage map: design vs backend (18 routers, 51 endpoints)

| # | Router | Status | Designed page(s) | Gap notes |
|---|---|---|---|---|
| 1 | `health` | MISSING | – | Not surfaced; trivially shown in topbar status |
| 2 | `imports` | MISSING (stub) | `import` stub only | Need: file-drop zone, column mapper, validation summary, success → jump to new run |
| 3 | `strategies` | COVERED | `strategies_list` (kanban) + `strategy_builder` consumes the entity | Detail/edit page for a single strategy + versions list missing — currently inline in builder |
| 4 | `backtests` | COVERED | `backtests` (run picker + metrics + scatter + trades + autopsy + equity) | Re-run form is just a `Re-run` button with no parameter dialog; create-via-engine flow needs a modal |
| 5 | `backtest_export` | COVERED | `backtests` page CSV button + per-table download icons | Wire-up only |
| 6 | `data_quality` | MISSING | – | Need: per-run data-quality panel with reliability score, issue list (severity colors), deferred-checks footer. Likely belongs as a new tab/card on `backtests` |
| 7 | `datasets` | PARTIAL | `datahealth` aggregates schemas | Per-dataset row drilldown + `POST /scan` action button missing |
| 8 | `data_health` | COVERED | `datahealth` (4-stat + by-schema table) | Scheduled-tasks list and disk widget not yet rendered — extend stat grid or add second card |
| 9 | `autopsy` | COVERED | Inline card on `backtests` page | Strengths/weaknesses bullet lists shown; could promote to a full-width section with overfitting + risk-notes lists |
| 10 | `notes` | PARTIAL | `research_hub` shows notes-as-hypotheses styling but not the notes CRUD | Need: note composer (body + type + tags + attach pickers), notes feed per strategy/run/trade |
| 11 | `experiments` | COVERED | `experiments` table + `research_hub` "Pending experiments" card | Create-experiment modal missing (button exists) |
| 12 | `prompts` | MISSING | – | Need: AI Prompt Generator page — mode picker (`researcher / critic / statistician / risk_manager / engineer / live_monitor`), focus-question textarea, generated markdown blob with copy button + `bundled_context_summary` chips + char count |
| 13 | `prop_firm` | PARTIAL | `simulator` (MC fan + violations + risk sweep) | Firm-profile editor (`firm_rules` stub), simulation history (`simulation_runs` stub), and verification stamp UI (`unverified/verified/demo` chip) all missing |
| 14 | `risk_profiles` | COVERED | `risk` (3-card grid + 24-hour heat strip) | Evaluate-against-run flow not wired (no UI to pick a run and show violations) |
| 15 | `settings` | MISSING (stub) | `settings` stub | Need: connections, env paths, theme variants (already have `data-theme="darker"|"raised"`), keybindings, telemetry toggles |
| 16 | `monitor` | COVERED | `monitor` (drift chart + pipeline health + journal) | Forward-drift detail breakdown (chi² components) and ingester metrics drill-down could expand |
| 17 | `replay` | MISSING | – | NOT the same as `trade_replay`. Need: per-day 1m chart for one symbol/date with optional entry/exit markers + auto-detected FVG zones (5m). Distinct from page #7 |
| 18 | `trade_replay` | COVERED | `replay` page (TBBO ticks for live run) | tbbo_available disabled-row treatment + run-picker not yet drawn |

**Tally:**
- COVERED ✅ — 8 routers (strategies, backtests, backtest_export, data_health, autopsy, experiments, risk_profiles, monitor, trade_replay) → 9 actually
- PARTIAL 🟡 — 3 routers (datasets, notes, prop_firm)
- MISSING ❌ — 6 routers (health, imports, data_quality, prompts, settings, replay)

(Counts: COVERED=9, PARTIAL=3, MISSING=6 → 18.)

---

## 7. Interaction patterns

- **Loading**: not represented in the bundle (mock data is synchronous). For real data, follow the convention: keep card chrome, replace body with a `bg-2` 1px-line skeleton row at table-row height; use `live-pulse` only for "data is fresh and streaming," never for "spinner."
- **Errors**: `Chip kind="warn"` and `kind="neg"` for inline errors; the only error-style block in the bundle is `.fb-error` — `font-size:11px; color:var(--neg); background:rgba(239,68,68,0.08); padding:5px 8px; border-radius:4px; border:1px solid rgba(239,68,68,0.25)`. Use that pattern for form validation messages.
- **Empty state**: two patterns:
  - `.r-empty` — centered text in card body for missing list items ("No open hypotheses or questions.")
  - `PageStub` empty card — 48×32 padded centered, 48px rounded `bg-2` icon tile, 16px bold ink-0 headline + 13px text-3 480-max paragraph
  - Kanban column empty: muted "empty" caption (`text-4`, 11.5px, centered, 20px vertical pad)
- **Live / streaming**:
  - `.live-pulse` — 6×6 dot, green, 3px soft halo, 1.6s scale animation
  - `.subnav-live` — green text "LIVE" badge on nav items
  - `.foot-dot` — 8×8 with `pulse` 2.4s opacity animation
  - `.nav-badge.live` — solid accent fill with `::before` blinking dot (2s)
  - `Chip kind="pos"` with inner `<span className="chip-dot"/>` for `RUNNING`/`ALL SYSTEMS GREEN`
- **Validation**: `.sb-validity.ok` (green) and `.sb-validity.warn` (amber) — `4×8 padding`, `box-shadow` glow on the inner dot via `currentColor`. Disabled buttons use the native `disabled` attribute (Strategy Builder's Backtest button gates on `valid`).
- **Keyboard**:
  - `⌘K` / `Ctrl+K` opens cmd palette
  - `1` / `2` / `3` switch profile tabs (skipped when focus is in an INPUT)
  - Inside palette: `↑↓` navigate, `↵` open, `esc` close (footer always shows these)
  - `:focus-visible` global outline = 2px accent + 2px offset, radius 4px
- **Motion**:
  - Hover transitions 80–160ms on background/border/color (never longer)
  - 3D scenes: ambient + directional + accent fill light, gentle `Math.sin(t*0.05–0.08)*0.06–0.18*intensity` camera/scene drift — intensity is a tweak slider 0–2
  - `keyframes`: `blink` (live badge) 2s, `pulse` (foot-dot, validity dot) 2–2.4s, `dot` (live-pulse) 1.6s
  - `[data-motion="off"]` and `prefers-reduced-motion` disable everything

---

## 8. What CANNOT be reproduced from the bundle

- **No raster assets**: zero PNG / JPG / SVG file references. Every icon is inline JSX SVG in `Ic` (`04.jsx`). The only image-like decoration is the brand-mark — a 28×28 (mini) / 30×30 (full) `linear-gradient(135deg, var(--accent), var(--accent-2))` square with a single white "B" glyph and a soft cyan `box-shadow`. Re-create as a `<div>`; no logo file needed.
- **Fonts**: Geist + Geist Mono served as **self-hosted woff2** in the extract. Files are present as opaque hashes:
  - Geist 400/500/600/700: `0520250a-…` (cyrillic), `e8dff80b-…` (latin-ext), `40f04942-…` (latin)
  - Geist Mono 400/500/600: `096b830c-…` (cyrillic), `8dca9a24-…` (latin-ext), `ccc96891-…` (latin)
  - Rename and ship in `frontend/public/fonts/` or load from Vercel CDN: `https://vercel.com/font` (Geist is OFL-licensed, MIT'd by Vercel).
- **External JS dependencies** loaded by script tags (UUID-named, in `__template.html.json`):
  - React + ReactDOM (UMD)
  - Babel standalone (for JSX in-browser)
  - **three.js** — required for `EquityRibbon3D`, `TradeScatter3D`, `MonteCarloFan3D` (used as global `THREE`)
  - The `useTweaks`, `TweaksPanel`, `TweakSection`, `TweakSlider`, `TweakSelect`, `TweakToggle` helpers come from `01_app.jsx` (the Artifacts runtime tweak panel). NOT app code — drop in production. Replace with a real Settings page.
- **No charting library**: all 2D charts (sparkline, area chart, drift line chart, replay tape, risk-sweep scatter) are **hand-rolled inline SVG**. Three.js is the only viz dep. No d3, recharts, echarts, chart.js, or lightweight-charts.

---

## 9. Stack the bundle uses

- **Framework**: React (UMD via script tag, JSX compiled in-browser by Babel standalone). For the rebuild use React 18 + Vite or Next.js — the components map 1:1 to `.tsx`.
- **State**: only `React.useState` and `React.useEffect`. Three independent state islands: `App` (profile, page, cmdOpen, tweaks), `PageStrategyBuilder` (full strategy object + activeRule + tab + presetOpen + featView + customFeatures), `PageBacktests` (`sel` run id), `PageReplay` (slider position). No context, no Redux, no Zustand, no router (single-page tabbed switch). For the rebuild: introduce a router (file-based or React Router) and a tiny store only if a page needs to share state.
- **Charts**: three.js (3D) + inline SVG (2D). Keep this — it's part of the aesthetic. If you need OHLC candles for the missing `replay` page, lightweight-charts would match the dark-mode finance feel with minimal styling.
- **Resize**: every chart uses a `ResizeObserver` to track its container width (`MiniChart`, `useThree`).
- **Data**: all reads are from `window.MOCK` (defined in `02.jsx`). Replace with `fetch('http://localhost:8000/api/...')` or generated SDK from `shared/openapi.json` (mentioned in the API ref doc).
- **Other notable**:
  - Global `window.PAGES` map (`05.jsx` and `06.jsx` both register into it) — replace with module imports
  - Global custom event `'open-cmd'` for opening palette from anywhere — replace with a small store or context
  - `PROFILES` array in `07.jsx` is the navigation source of truth (3 profiles → groups → items with `id`, `label`, `icon`, optional `live`); preserve this shape
  - `PAGE_MAP` and `PAGE_TITLES` in `07.jsx` define the routing table — every new sub-nav item either points to a `PAGES` key or falls back to `PageStub`
  - Theme switching is purely CSS-driven via `[data-theme]` on `<html>`; accent hue is also runtime-tunable via `--accent-h` (the bundle uses fixed `#22d3ee`, but the variable is wired)
  - Reduced-motion both via `@media(prefers-reduced-motion:reduce)` and `[data-motion="off"]` selector

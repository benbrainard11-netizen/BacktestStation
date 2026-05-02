# Decisions for Ben + Elijah

Status: 2026-05-01. Live as of the redesign port. Open questions where the backend, the original design, and the archived frontend disagree — pick one direction per row.

This doc is a triage list. Mark each with ✂️ (drop), 🔗 (merge into another page), or ✅ (keep as-is). Once decided, I'll consolidate the navigation and prune the route tree.

---

## A. Routes the design does NOT include but the old frontend HAD

| Route | What it does | Backend support | Recommendation |
|---|---|---|---|
| `/data` (now `/datasets`) | Dataset catalog with schema + bar count | `GET /api/datasets`, `POST /datasets/{id}/scan` | 🔗 surface as a tab/section inside Data Health, OR keep as a top-level item under Dashboard › System |
| `/trade-replay` | TBBO tick-level playback of a single live trade | `GET /api/trade-replay/runs`, `GET /trade-replay/ticks` | ✅ keep — completely different feature from `/replay`. Suggest renaming the design's "Trade Replay" item to "1m Replay" and adding a sibling "Tick Replay" for this. |
| `/journal` | Hand-written notes against trades; the old impl was the actual notes UI | `GET /api/notes` + CRUD | 🔗 the design has Journal as a stub. Backend has `/api/notes`. Treat Journal = Notes (one page) OR split: Journal = freestanding notes, Notes = run-attached notes. **Probably 🔗 — one page.** |

## B. Routes the BACKEND supports but neither design nor old frontend covers

| Route | Backend endpoint | Recommendation |
|---|---|---|
| `/data-quality` | `GET /api/data-quality` | 🔗 add as a tab on Data Health page. Don't make it a separate top-level item — the SYSTEM nav group is already two items. |
| `/health` (system uptime) | `GET /api/health` (returns `{status, version}`) | ✂️ delete the page. Backend status is already shown in the TopTabs meta strip + Settings → Backend card. A whole page for `{status: ok}` is overkill. |
| `/prompts` (AI Prompt Generator) | `GET /api/prompts/modes`, `POST /api/prompts/generate` | 🔗 surface inside Research group as a sibling to Knowledge. Or ✅ make it its own item under Research → "AI Prompts". The mockup is polished; the backend is real. **Probably ✅.** |
| `/autopsy` | `GET /api/autopsy` | 🔗 link from a backtest run detail page (Trades table → click trade → Autopsy panel). Not a top-level page. |

## C. Pages the DESIGN includes but the BACKEND doesn't really support

| Design item | Backend gap | Recommendation |
|---|---|---|
| `Knowledge` (Research group) | No `/api/knowledge` endpoints in the FastAPI router list | ✂️ drop until backend lands, OR ✅ keep as a stub page that says "coming soon". |
| `Hypotheses` (`/research`) | No dedicated endpoint; the closest is Experiments | 🔗 merge with Experiments (a hypothesis IS an experiment). Drop the "Hypotheses" item from sub-nav. |
| `Compare` (`/compare`) | No backend `/compare` endpoint — old frontend assembled it client-side from per-run reads | ✅ keep but build it client-side using `GET /api/backtests/{id}` × 2. Confirm with Ben. |

## D. Prop firm — biggest chunk of unresolved scope

The old `/prop-simulator/` had **40+ components** across 6 sub-pages: list, new-sim wizard (5 steps), runs table, run detail (10+ panels), compare workspace, scope tearsheet (printable).

The design's nav has 4 items in the Strategies › Prop Firm group: Simulator / Firm Rules / Simulation Runs / Compare.

| Old surface | Suggested new surface | Decision |
|---|---|---|
| `/prop-simulator/firms` (list) | Strategies › Prop Firm › **Firm Rules** | ✅ port |
| `/prop-simulator/firms/[id]/edit` (firm editor) | Drill from Firm Rules row | ✅ port |
| `/prop-simulator/new` (5-step wizard) | "New Simulation" button on Simulator page → modal/inline form | ✅ port; replace the multi-step wizard with a single dense form (the design language favors density over wizards) |
| `/prop-simulator/runs` (runs table) | Strategies › Prop Firm › **Simulation Runs** | ✅ port |
| `/prop-simulator/runs/[id]` (run detail with 10+ panels) | Drill from Simulation Runs row → `/prop-simulator/runs/{id}` | ✅ port; collapse the 10+ panels into 4-5 cards (DailyPnL, Equity overlay, Outcome distribution, Failure reasons) — the rest are noise, ask Ben which he actually opens |
| `/prop-simulator/compare` (workspace) | Strategies › Prop Firm › **Compare** | ✅ port |
| `/prop-simulator/runs/[id]/scope` (printable tearsheet) | Print stylesheet on the run detail page | 🔗 merge — don't keep as a separate route |

## E. Strategy Builder

`design_extract/anthropic_design_2/backtestui/project/strategy-builder.jsx` is the design — a polished entry/exit/risk/feature builder. Backend has `/api/strategies` + `/api/strategy-versions` for storage but no live "validate this strategy" endpoint that I can see.

| Question | Recommendation |
|---|---|
| Is the visual builder backed by a JSON schema in the backend? | Need Ben's word. The design has a "code preview" panel showing the strategy as YAML/JSON — confirm the backend round-trips that exact shape. |
| Does the "Test feature expression" panel hit a backend endpoint or evaluate client-side? | Likely client-side; the backend has no expression evaluator endpoint. |
| Should the Feature Builder persist features to the backend or just attach them to the strategy version? | Probably attach. |

**Recommendation: don't port the Strategy Builder until Ben confirms the data contract.** Leave the stub.

## F. Settings page — what's purely client-side vs server-side

The Settings page I shipped is 100% client-side (localStorage). Confirm if any of these should round-trip to the backend (`/api/settings/system` is read-only):

- Accent hue / theme / density / motion → **client-side, OK as-is**
- Refresh interval → client-side
- Timezone → client-side
- Decimal precision → client-side
- Backend URL → currently hardcoded in `next.config.mjs`; changing it requires a rebuild. **Should this become an env var?** Probably yes for production.

---

## Pages currently shipped, working against live backend

- ✅ `/` (Overview) — basic, polish later
- ✅ `/monitor` — full port, 6 endpoints wired
- ✅ `/settings` — full UI

## Pages porting in this session (subagents in flight)

- 🔄 `/strategies`, `/risk-profiles`
- 🔄 `/backtests`, `/backtests/[id]`
- 🔄 `/replay`, `/trade-replay`
- 🔄 `/data-health`, `/experiments`, `/datasets`

## Pages still stubbed (for next session, after Ben + Elijah review this doc)

- `/journal` — see B/A row about Notes vs Journal
- `/import` — backend has only POST /import/backtest; old frontend had a full mapper. Need scope decision.
- `/knowledge` — see C row
- `/research` — see C row (suggest dropping)
- `/prompts` — small, ready to port if you say ✅
- `/health` — recommend ✂️ delete the page
- `/data-quality` — recommend 🔗 merge into Data Health
- `/autopsy` — recommend 🔗 merge into backtest detail
- `/strategy-builder` — biggest single port; needs data contract confirmation from Ben
- `/prop-simulator` (and all sub-routes) — see section D
- `/prop-firm` (firm profiles) — covered by section D Firm Rules
- `/compare` — see section D

---

## Final action for you both

Read sections A–F. For each row, mark ✅ / ✂️ / 🔗 in the right margin (or just message back the line numbers + decisions). I'll then prune the navigation, delete the unused routes, and ship the next round of ports without ambiguity.

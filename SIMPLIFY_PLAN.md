# BacktestStation — Simplification + Sidecar Bridge Plan

**Author:** Claude (working with Elijah, for review by Ben)
**Date:** 2026-05-05
**Status:** Draft — for Ben + Elijah review before any code moves

---

## 1. Goal

Turn BacktestStation into a **server-deployed, Discord-driven idea-validation loop**:

```
research_sidecar finds a high-scoring idea
  ─► pings Discord with [Backtest now] / [Skip] buttons
       ─► Ben/Elijah click [Backtest now]
            ─► sidecar HTTP-calls BacktestStation
                 ─► run executes, score posts back
                      ─► Discord embed updates with PF / expectancy / confidence
```

The frontend exists for **deeper inspection**, not as the primary way of interacting. Most days you'll never open it — Discord is the interaction surface.

## 2. Non-goals (to prevent scope creep)

- ❌ Auto-promotion of ideas to live trading — sidecar V1 forbids this and we honor it.
- ❌ LLM-generated strategy code from natural-language ideas. Ideas map to existing **template** strategies in the catalog; the click pre-fills params.
- ❌ Public-internet exposure. Tailscale-only.
- ❌ Re-porting all the cut routes. `/trade-replay`, `/prompts`, `/autopsy`, the prop-firm group, etc. stay deleted unless explicitly revived.

---

## 3. End-state UI shape

Cut from 11 → **6 routes**, no top-tab profiles, just a flat horizontal nav:

| Route | What it's for | Built from |
|---|---|---|
| **Inbox** | Pending sidecar ideas, score-sorted. Each row has a [Backtest] button that opens the pre-filled config. | NEW page; data from sidecar HTTP |
| **Backtests** | Run-a-backtest form + run history + results detail. Existing page, lightly extended for "started by idea_id". | Existing `/backtests` |
| **Replay** | Time-machine through a completed backtest — bars, trades, FVG zones, every loss bar-by-bar. | Existing `/replay` (kept per Elijah 2026-05-05) |
| **Catalog** | Strategy templates + risk profiles, merged into one page. Each template is what an idea gets mapped onto. | Existing `/strategy-catalog` + `/risk-profiles` collapsed |
| **Library** | Knowledge cards (orderflow formulas, indicators, setup archetypes). Restored from archive. | Backend already alive; UI from `_frontend_archive_2026_05_01/` |
| **Settings** | Sidecar URL, Discord webhook, accent color, density, theme — plus Data Health, Live Bot, Admin tabs. | Existing `/settings` + folded-in pages |

**Cut routes** — DECIDED 2026-05-05 (Elijah): delete `/overview`, `/monitor` (→ Settings → Live Bot tab), `/notes`, `/import` (→ Settings → Admin tab), `/experiments`, `/data-health` (→ Settings → Data tab). All deletions hard — no archive restore path planned.

Top tabs (Dashboard / Research / Strategies) go away. Single horizontal nav: **Inbox · Backtests · Replay · Catalog · Library · Settings**.

## 4. The Discord-driven loop in detail

Sidecar's existing flow:

```
worker poll → ingest → extract → score → if final_score >= 0.75: discord webhook embed
```

What we add:

```
worker poll → ingest → extract → score → if final_score >= 0.75:
    sidecar Discord BOT (not webhook) posts an interactive message:
      [embed with idea title, score, archetype, summary]
      [🧪 Backtest now] [⏭️ Skip] [📖 Open in BacktestStation]
```

**Button behavior:**

- **[🧪 Backtest now]** — opens a Discord modal with editable defaults pulled from the idea (symbol, timeframe, date range, qty, slippage). On submit, sidecar HTTP-POSTs `BacktestStation /backtests/run` with `{idea_id, ...config}`. Replies *"Running #142 → result in ~30s…"*. When BacktestStation finishes, it HTTP-POSTs back to sidecar `/ideas/{id}/result`, which **edits the original Discord message** to append the score.
- **[⏭️ Skip]** — sets idea `recommendation_label='rejected'` in the sidecar DB, edits message to grey out the buttons.
- **[📖 Open in BacktestStation]** — link button to `https://<server-tailscale>:8000/inbox?idea=142`.

**Why discord.py 2.4 makes this easy:** the `discord.ui.View` + `Button` API supports interactive components on bot messages (not webhook embeds). The sidecar already runs the bot process — we just extend `commands.py`.

**Async constraint:** Discord interactions have a 3-second response deadline; backtests can take **30s to multiple hours** depending on date range and timeframe. We use `interaction.response.defer()` then `interaction.followup.send()`. BacktestStation's `/backtests/run` MUST run async (returns `run_id` immediately, executes in a background task) and expose a progress field (`progress_pct`, `eta_seconds`) for the Discord embed to show live progress on long runs.

## 5. Sidecar ↔ BacktestStation contract

Both run on the server, talk over `localhost`. Two new HTTP surfaces:

### 5a. Sidecar exposes (NEW — small FastAPI process alongside worker + bot)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/ideas?label=promising&limit=50` | List pending ideas for the Inbox UI |
| `GET` | `/ideas/{id}` | Single idea detail |
| `POST` | `/ideas/{id}/result` | Receive backtest score from BacktestStation; edits original Discord msg |
| `POST` | `/ideas/{id}/skip` | Set label=rejected, grey out Discord buttons |
| `GET` | `/health` | Liveness for the BacktestStation Settings page |

Read-only writes only — sidecar V1 separation guarantees stay intact.

### 5b. BacktestStation exposes (extends existing API)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/backtests/run` | Already exists — extend to accept `idea_id` and run async, return `{run_id}` immediately |
| `POST` | `/backtests/{id}/result-callback` | Internal; sidecar webhook target (or sidecar polls `/backtests/{id}` until status=complete — simpler) |

Pulling vs callback: I lean **sidecar polls BacktestStation `/backtests/{id}`** every 5s after dispatch. No new BacktestStation endpoint needed, no callback auth complexity, simpler failure recovery (sidecar crash mid-poll → replay on restart).

## 6. Volume profile + order flow

Already partly there:

- ✅ `backend/app/features/_orderflow.py` — `compute_continuation_of` ported from Fractal-AMD, regression-tested against pandas reference.
- ❌ Volume profile (POC / VAH / VAL / HVN / LVN) — **missing**. Needs a new module `backend/app/features/_volume_profile.py`.

Once the volume profile module exists, both order-flow and volume-profile features get registered as **Knowledge Library cards** (`kind='orderflow_formula'` and `'indicator_formula'`). Then idea matching becomes:

```
sidecar idea.indicators = ["VWAP", "POC"]
  ─► Library lookup: cards where formula text matches "POC" or "VWAP"
       ─► card pre-fills config: which strategy template, which params
            ─► [Backtest now] button knows what to send
```

Building the volume profile feature module = ~1 session. Wiring into backtests + Library cards = ~½ session.

## 7. Deployment shape

Both apps run **on the server (`ben-247` / DESKTOP-98TRDA0)** as separate Windows services.

```
┌─ ben-247 ─────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌─ research_sidecar ─────────────┐  ┌─ BacktestStation ────────┐  │
│  │ worker.py    [NSSM service]   │  │ uvicorn   [NSSM service]  │  │
│  │ discord_bot  [NSSM service]   │  │   serves API + static     │  │
│  │ http_api     [NSSM service]   │◄─┤   Next.js bundle on :8000 │  │
│  │   :9000 (NEW)                  │  │   bound to Tailscale IP   │  │
│  └────────────────────────────────┘  └───────────────────────────┘  │
│                                                                    │
│  Postgres (separate DB users for sidecar vs BacktestStation)       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                                ▲
                                │ Tailscale only
                                │
                ┌───────────────┴───────────────┐
                │                               │
        Elijah's main PC                  Ben's laptop
        Browser → http://ben-247:8000     Browser → same URL
        (also runs Tauri locally          (also receives Discord pings)
         for dev work)
```

**Local dev on this machine stays unchanged:** `npm run tauri:dev` + uvicorn-as-Tauri-sidecar on localhost. No cross-machine concern at dev time. The only deploy-time difference is: server runs `python -m uvicorn` directly (no Tauri), serving the static Next.js export.

**Tailscale binding:** uvicorn launches with `--host <tailscale-ip>` (or `--host 0.0.0.0` and rely on Tailscale ACL). Need to confirm preference with Ben.

**Frontend production build:** `next build && next export` → static files served by FastAPI's `StaticFiles` mount at `/`. API routes still under `/api/`.

## 8. Phased work order

Phase boundaries are sized so you can stop after any phase and still have a working app.

### Phase A — Plan acceptance (this doc) ⏱ now
- Ben + Elijah read this, redline.
- Decide on the open questions in §10.

### Phase B — Frontend simplification ⏱ ~1 session  ✅ SHIPPED 2026-05-05
**B.1 (this PR):**
- Flat 6-item nav, profiles + 3-tab system removed.
- Hard-deleted: `/experiments`, `/notes`, `/import`, `/` overview content (root now redirects to `/inbox`).
- New placeholder `/inbox` page (real wiring in Phase D).
- New minimal `/library` page — read-only listing against existing backend Knowledge API.
- `/monitor`, `/data-health`, `/risk-profiles` removed from nav but remain on disk as deep-link-only routes.
- Fixed pre-existing `next build` blocker (unescaped quotes in `/risk-profiles`).
- Build green, typecheck clean.

**B.2 (deferred, ~½ session):**
- Fold `/monitor` and `/data-health` content into `/settings` as tabs.
- Fold `/risk-profiles` content into `/strategies` as a tab. Then delete those route folders.
- Rewrite the Knowledge Library editor (create/edit/delete) against the new atoms — bring back the archive's full UI without the legacy `@/components/ui/*` deps.

### Phase C — Sidecar HTTP API ⏱ ~1 session  ✅ SHIPPED 2026-05-05
- `research_sidecar/scripts/run_http_api.py` exposes 5 endpoints on `:9000`.
- 20 unit tests, all green.
- NSSM service definition lives in `BacktestStation/docs/SERVER_DEPLOYMENT.md`
  (Phase G).

### Phase D — Inbox UI ⏱ ~1 session  ✅ SHIPPED 2026-05-05
- `/inbox` page pulls from sidecar via `/api/sidecar/*` Next rewrite.
- Score-sorted IdeaCards with strategy spec, indicator/filter chips,
  last-backtest summary, source link.
- Filter toggle (promising / promising+review), optimistic Skip,
  retry-on-error banner.
- "Backtest" button → `/backtests?ideaId=…&timeframe=…&name=…`. The
  Backtests page reads those params, auto-opens the run modal pre-
  filled, and shows a "from idea #N" header badge. Submit posts
  `idea_id` to `/api/backtests/run` (sync) — the run picks up an
  `idea:N` tag, surfaced as a clickable accent chip in the runs list.

### Phase E — Discord buttons ⏱ ~1 session  ✅ SHIPPED 2026-05-05
- E.1 (BacktestStation backend, `ff7d82b`): async run mode at
  `POST /api/backtests/run-async`, status/progress/eta on the run-read
  shape, queued → running → complete state machine, 8 tests green.
- E.2 (research_sidecar, `f39d93c`): `discord.ui.View` with
  [🧪 Backtest now] / [⏭️ Skip] / [📖 Open]; Modal for editable run
  params; adaptive polling loop edits the original embed with progress
  and final result; 5 tests green.
- "Open" button URL goes to `http://<TS_IP>:3000/inbox?idea=<id>`.

### Phase F — Volume profile module ⏱ ~1 session  ✅ SHIPPED 2026-05-05
- `backend/app/features/_volume_profile.py` — `compute_profile`,
  `find_poc`, `find_value_area`, `position_vs_value_area`. Floor-anchored
  bucketing (no banker's-rounding collisions).
- `backend/app/features/volume_profile.py` — registered features
  `vp_zone` (trigger+filter, all 6 zones) and `vp_in_va` (filter).
- 32 tests green, 104/104 across the full feature suite.
- HVN/LVN deferred — POC/VAH/VAL covers the common patterns.

### Phase G — Server deployment ⏱ ~½ session + manual server steps
- ⚠️ PARTIALLY SHIPPED: documentation in `docs/SERVER_DEPLOYMENT.md`
  describing 5 NSSM services (4 new + 1 frontend), Tailscale-IP
  binding, env files, day-to-day ops. The actual server install is a
  manual step on `ben-247` and not yet performed.
- Static frontend export deferred — current recipe runs `next start`
  as a 6th NSSM service. Single-process FastAPI-served frontend is a
  later cleanup once the dynamic routes (`/backtests/[id]`,
  `/strategies/[id]/build`) are made static-export-friendly.

**Total: ~5–6 sessions of dev work.** Phase A through E gets you the working loop on this machine; F adds the missing feature; G is the move-to-server operation.

## 9. What stays unchanged

- The trading bot. We do not touch it.
- The sidecar's worker, extraction, scoring, dedupe, smoke check, slash commands. All of those keep working as today.
- BacktestStation's engine, runner, strategy registry, data layer. The simplification is UI-shape + new bridge endpoints, not a rewrite.
- Tauri dev workflow on this machine. Server-side runs without Tauri; dev runs with it.

## 10. Decisions (all locked 2026-05-05)

1. **Tailscale binding** — `--host <tailscale-ip>` (explicit). Server won't bind to LAN at all. ✅
2. **Idea modal in Discord** — all 5 fields editable (symbol, timeframe, date range, qty, slippage). Pre-filled from idea + defaults; user can override anything before submit. ✅
3. **Sidecar polls** — adaptive interval (5s → 30s → 2min), progress embed updates live for multi-hour backtests. ✅
4. **Library auto-promotion** — automatic. When a run completes with **n ≥ 30 trades AND PF ≥ 1.5 AND expectancy > 0**, BacktestStation auto-creates a `needs_testing` Library card linked to that run. Threshold tunable in Settings. ✅
5. **Risk Profiles + Catalog merge** — risk profiles as a tab inside Catalog. ✅
6. **Inbox default filter** — show both `promising` AND `review`, toggle to filter to promising-only. ✅
7. **Routes (decided 2026-05-05):** Replay KEPT. Experiments DELETE. Notes DELETE. Overview/Monitor/Import/Data Health DELETE (→ Settings tabs or Inbox). Final route count = **6**.

No remaining blockers — Phase B can begin.

---

## Appendix A — Files I'll touch (Phase B–E preview, not exhaustive)

**Add:**
- `frontend/app/inbox/page.tsx`
- `frontend/components/inbox/IdeaCard.tsx`, `IdeaList.tsx`
- `frontend/lib/api/sidecar.ts` (typed client for sidecar HTTP API)
- `research_sidecar/scripts/run_http_api.py`
- `research_sidecar/app/http_api/__init__.py`, `routes.py`
- `research_sidecar/app/discord_bot/views.py` (Button + Modal)
- `backend/app/features/_volume_profile.py`

**Modify:**
- `frontend/lib/navigation.ts` — flatten to 5 items, drop profiles
- `frontend/components/layout/TopTabs.tsx` → rename to `TopBar.tsx`, drop profile-tab logic
- `frontend/app/library/*` — restored from archive, lightly modernized
- `frontend/app/settings/page.tsx` — add Data Health, Admin (import) tabs
- `backend/app/api/backtests.py` — add async-mode + `idea_id` field on run
- `research_sidecar/app/discord_bot/commands.py` — wire View to high-score alerts
- `research_sidecar/app/alerts/*` — emit bot message instead of webhook for high-score class

**Delete:**
- `frontend/app/overview/`, `monitor/`, `notes/`, `import/`, `experiments/`, `replay/`, `data-health/` (but keep `replay/` components in archive — already done)
- `frontend/lib/profiles.ts` and any top-tab-profile state machinery

---

*Reviewed by:* ____________  *Date:* __________
*Reviewed by:* ____________  *Date:* __________

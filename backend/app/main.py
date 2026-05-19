from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import (
    ai_context,
    autopsy,
    backtest_export,
    backtests,
    chat,
    data_health,
    data_quality,
    datasets,
    experiments,
    features,
    health,
    imports,
    knowledge,
    monitor,
    notes,
    promotion_checks,
    prompts,
    prop_firm,
    replay,
    research,
    research_events,
    risk_profiles,
    settings as settings_api,
    strategies,
    trade_replay,
)
from app.api.dashboard import candidates as dashboard_candidates
from app.api.dashboard import data_health as dashboard_data_health
from app.api.dashboard import trials as dashboard_trials

app = FastAPI(
    title="BacktestStation",
    version=__version__,
    description="Futures strategy research & backtesting API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # BTS' own frontend
        "http://localhost:3000",
        "http://100.108.159.4:3000",
        # InsyncApp - Vite dev + Tauri shell
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "tauri://localhost",
        "http://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(imports.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(monitor.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(strategies.versions_router, prefix="/api")
app.include_router(backtests.router, prefix="/api")
app.include_router(backtest_export.router, prefix="/api")
app.include_router(data_quality.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(data_health.router, prefix="/api")
app.include_router(dashboard_data_health.router, prefix="/api")
app.include_router(dashboard_trials.router, prefix="/api")
app.include_router(dashboard_candidates.router, prefix="/api")
app.include_router(autopsy.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(experiments.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")
app.include_router(prop_firm.router, prefix="/api")
app.include_router(prop_firm.backtest_router, prefix="/api")
app.include_router(risk_profiles.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(replay.router, prefix="/api")
app.include_router(trade_replay.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(ai_context.router, prefix="/api")
app.include_router(features.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(research_events.router, prefix="/api")
app.include_router(promotion_checks.router, prefix="/api")

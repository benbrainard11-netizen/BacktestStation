from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import (
    autopsy,
    backtest_export,
    backtests,
    data_quality,
    datasets,
    experiments,
    health,
    imports,
    monitor,
    notes,
    prompts,
    prop_firm,
    risk_profiles,
    strategies,
)

app = FastAPI(
    title="BacktestStation",
    version=__version__,
    description="Futures strategy research & backtesting API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(imports.router, prefix="/api")
app.include_router(monitor.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(strategies.versions_router, prefix="/api")
app.include_router(backtests.router, prefix="/api")
app.include_router(backtest_export.router, prefix="/api")
app.include_router(data_quality.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(autopsy.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(experiments.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")
app.include_router(prop_firm.router, prefix="/api")
app.include_router(prop_firm.backtest_router, prefix="/api")
app.include_router(risk_profiles.router, prefix="/api")

"""Shared types for imported result-file workflows."""

from dataclasses import dataclass


class ImportValidationError(ValueError):
    """Raised when imported result files cannot be normalized."""


@dataclass(frozen=True)
class UploadedTextFile:
    filename: str
    content: str


@dataclass(frozen=True)
class BacktestImportPayload:
    strategy_name: str | None
    strategy_slug: str | None
    version: str | None
    run_name: str | None
    symbol: str | None
    timeframe: str | None
    session_label: str | None
    import_source: str | None
    trades_file: UploadedTextFile
    equity_file: UploadedTextFile
    metrics_file: UploadedTextFile | None
    config_file: UploadedTextFile | None


@dataclass(frozen=True)
class ImportResult:
    backtest_id: int
    strategy_id: int
    strategy_version_id: int
    trades_imported: int
    equity_points_imported: int
    metrics_imported: bool
    config_imported: bool

"""Import endpoints for existing backtest result files."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas import ImportBacktestResponse
from app.services.backtest_importer import import_backtest_payload
from app.services.import_types import (
    BacktestImportPayload,
    ImportValidationError,
    UploadedTextFile,
)

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/backtest", response_model=ImportBacktestResponse, status_code=201)
async def import_backtest(
    trades_file: UploadFile = File(...),
    equity_file: UploadFile = File(...),
    metrics_file: UploadFile | None = File(None),
    config_file: UploadFile | None = File(None),
    strategy_name: str | None = Form(None),
    strategy_slug: str | None = Form(None),
    version: str | None = Form(None),
    run_name: str | None = Form(None),
    symbol: str | None = Form(None),
    timeframe: str | None = Form(None),
    session_label: str | None = Form(None),
    import_source: str | None = Form(None),
    db: Session = Depends(get_session),
) -> ImportBacktestResponse:
    payload = BacktestImportPayload(
        strategy_name=strategy_name,
        strategy_slug=strategy_slug,
        version=version,
        run_name=run_name,
        symbol=symbol,
        timeframe=timeframe,
        session_label=session_label,
        import_source=import_source,
        trades_file=await _read_text_file(trades_file),
        equity_file=await _read_text_file(equity_file),
        metrics_file=await _read_optional_text_file(metrics_file),
        config_file=await _read_optional_text_file(config_file),
    )
    try:
        result = import_backtest_payload(db, payload)
    except ImportValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ImportBacktestResponse.model_validate(result)


async def _read_text_file(file: UploadFile) -> UploadedTextFile:
    content = (await file.read()).decode("utf-8-sig")
    return UploadedTextFile(filename=file.filename or "uploaded-file", content=content)


async def _read_optional_text_file(
    file: UploadFile | None,
) -> UploadedTextFile | None:
    if file is None:
        return None
    return await _read_text_file(file)

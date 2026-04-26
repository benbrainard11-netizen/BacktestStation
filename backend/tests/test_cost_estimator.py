"""Smoke tests for the Databento cost-estimator helper.

The estimator wraps `databento.Historical.metadata.get_cost`, which
needs an API key. We don't make real API calls in tests — instead we
verify the universe shape, the dataset constant, the CLI argument
plumbing, and the error paths that don't need a network round-trip.
"""

from __future__ import annotations

import pytest

from app.ingest.cost_estimator import DATASET, UNIVERSE, main


def test_universe_has_expected_categories() -> None:
    """The asset universe should at minimum cover the categories the
    bulk_free_pull script expects."""
    expected_categories = {
        "equity_index",
        "metals",
        "energy",
        "forex",
        "rates",
        "agriculture",
    }
    assert expected_categories <= set(UNIVERSE.keys())


def test_universe_categories_have_continuous_symbols() -> None:
    """Every symbol in UNIVERSE should follow Databento's continuous
    notation `ROOT.c.0` so callers can pass `stype_in='continuous'`."""
    for category, symbols in UNIVERSE.items():
        assert symbols, f"category {category} is empty"
        for sym in symbols:
            assert sym.endswith(".c.0"), (
                f"{sym} in {category} is not a continuous symbol"
            )


def test_universe_symbols_are_unique_per_category() -> None:
    for category, symbols in UNIVERSE.items():
        assert len(symbols) == len(set(symbols)), f"dupes in {category}"


def test_universe_no_overlap_between_categories() -> None:
    """A symbol shouldn't live in two categories — that would let
    cost estimates double-count it."""
    seen: set[str] = set()
    for symbols in UNIVERSE.values():
        for sym in symbols:
            assert sym not in seen, f"{sym} appears in multiple categories"
            seen.add(sym)


def test_dataset_is_glbx_mdp3() -> None:
    """Ben's plan covers GLBX.MDP3 (CME Globex MDP3) — pin so we don't
    silently estimate against the wrong dataset."""
    assert DATASET == "GLBX.MDP3"


# --- CLI argument validation (no API calls) -----------------------------


def test_main_without_api_key_returns_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No DATABENTO_API_KEY in env -> error before the API import path."""
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    rc = main(["--universe"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "DATABENTO_API_KEY" in err


def test_main_single_estimate_requires_symbols_start_end(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Single-estimate mode insists on the three positional inputs."""
    monkeypatch.setenv("DATABENTO_API_KEY", "fake-key-for-arg-validation")
    rc = main([])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--symbols" in err and "--start" in err and "--end" in err

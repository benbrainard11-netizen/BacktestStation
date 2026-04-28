"""Tests for /api/settings/system."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import system_info


@pytest.fixture
def api_client():
    with TestClient(app) as client:
        yield client


def test_system_endpoint_returns_required_fields(api_client) -> None:
    response = api_client.get("/api/settings/system")
    assert response.status_code == 200, response.text
    body = response.json()
    for field in (
        "bs_data_root",
        "bs_data_root_exists",
        "databento_api_key_set",
        "version",
        "git_sha",
        "git_dirty",
        "platform",
        "python_version",
        "free_disk_bytes",
        "server_time_utc",
        "server_time_et",
    ):
        assert field in body, f"missing {field}"


def test_databento_key_status_reflects_env(
    api_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    response = api_client.get("/api/settings/system")
    assert response.json()["databento_api_key_set"] is False

    monkeypatch.setenv("DATABENTO_API_KEY", "abc")
    response = api_client.get("/api/settings/system")
    assert response.json()["databento_api_key_set"] is True


def test_system_info_never_leaks_api_key_value(
    api_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defense in depth — the key value must never appear in the
    serialized payload, even if a future field accidentally widens."""
    secret = "test-databento-secret-NEVER-SERIALIZE"
    monkeypatch.setenv("DATABENTO_API_KEY", secret)
    response = api_client.get("/api/settings/system")
    assert secret not in response.text


def test_git_state_falls_back_when_git_unavailable() -> None:
    """If git rev-parse errors, the function returns (None, False)
    rather than raising. Frontend treats None as 'unknown'."""
    with patch.object(system_info.subprocess, "run") as mock_run:
        mock_run.side_effect = FileNotFoundError()
        sha, dirty = system_info._git_state()
    assert sha is None
    assert dirty is False


def test_system_info_python_version_format() -> None:
    """python_version is M.m.p — frontend parses as a string but the
    shape is part of the contract."""
    info = system_info.get_system_info()
    parts = info.python_version.split(".")
    assert len(parts) == 3
    for p in parts:
        int(p)  # raises if non-numeric

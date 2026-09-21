from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_health_endpoint_returns_configured_status(monkeypatch) -> None:
    monkeypatch.setenv("NBA_SEASON", "2025-26")
    monkeypatch.setenv("RAW_DATA_DIR", "./test-raw")
    monkeypatch.setenv("API_REQUEST_TIMEOUT_SECONDS", "12.5")
    get_settings.cache_clear()

    client = TestClient(create_app())
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "courtvision-api"
    assert body["nba_season"] == "2025-26"
    assert body["database_configured"] is True
    assert body["raw_data_dir"] == "./test-raw"
    assert body["request_timeout_seconds"] == 12.5

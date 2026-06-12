"""API smoke tests against the offline app (fixture schema, fakes, TestClient)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from text_to_sql_engine.api import create_app
from text_to_sql_engine.config import Settings


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_url=None,
        openai_api_key=None,
        default_row_limit=200,
        history_db_path=str(tmp_path / "history.sqlite"),
    )
    return TestClient(create_app(settings))


def test_healthz_reports_offline_backends(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "llm": "fake", "database": "fixture"}


def test_query_returns_validated_sql(client: TestClient) -> None:
    response = client.post(
        "/query", json={"question": "How many orders are in each status?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "LIMIT 200" in body["sql"]
    assert body["summary"] == "The query returned 0 rows."


def test_query_rejection_is_reported_not_500(client: TestClient) -> None:
    response = client.post(
        "/query", json={"question": "Show me everything about our customers."}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert "sensitive" in body["error"]
    assert body["corrections"]  # the loop's failed rounds are visible to clients


def test_history_lists_recent_queries(client: TestClient) -> None:
    client.post("/query", json={"question": "How many orders are in each status?"})
    response = client.get("/history")
    assert response.status_code == 200
    entries = response.json()
    assert entries[0]["question"] == "How many orders are in each status?"
    assert entries[0]["status"] == "ok"


def test_schema_refresh_returns_204(client: TestClient) -> None:
    response = client.post("/schema/refresh")
    assert response.status_code == 204


def test_unknown_fields_are_rejected(client: TestClient) -> None:
    response = client.post(
        "/query", json={"question": "How many orders?", "mode": "yolo"}
    )
    assert response.status_code == 422


def test_too_short_question_is_rejected(client: TestClient) -> None:
    response = client.post("/query", json={"question": "hi"})
    assert response.status_code == 422

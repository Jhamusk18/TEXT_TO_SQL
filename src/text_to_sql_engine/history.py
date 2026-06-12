"""Query history: protocol, in-memory store, and SQLite-backed persistence."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from text_to_sql_engine.models import HistoryEntry, QueryStatus

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS query_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    sql TEXT,
    status TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    created_at TEXT NOT NULL
)
"""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class HistoryStore(Protocol):
    """Persists one record per answered (or failed) question."""

    def add(
        self, question: str, sql: str | None, status: QueryStatus, latency_ms: float
    ) -> HistoryEntry:
        ...

    def recent(self, limit: int = 50) -> list[HistoryEntry]:
        ...


class InMemoryHistoryStore:
    """Volatile store for tests and throwaway sessions."""

    def __init__(self) -> None:
        self._entries: list[HistoryEntry] = []

    def add(
        self, question: str, sql: str | None, status: QueryStatus, latency_ms: float
    ) -> HistoryEntry:
        entry = HistoryEntry(
            id=len(self._entries) + 1,
            question=question,
            sql=sql,
            status=status,
            latency_ms=latency_ms,
            created_at=_now_iso(),
        )
        self._entries.append(entry)
        return entry

    def recent(self, limit: int = 50) -> list[HistoryEntry]:
        return list(reversed(self._entries[-limit:]))


class SqliteHistoryStore:
    """Durable history in a single SQLite file (stdlib only, offline-safe).

    Connections are opened per operation, which keeps the store trivially
    safe under FastAPI's threaded request handling.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def add(
        self, question: str, sql: str | None, status: QueryStatus, latency_ms: float
    ) -> HistoryEntry:
        created_at = _now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO query_history (question, sql, status, latency_ms, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (question, sql, status.value, latency_ms, created_at),
            )
            entry_id = cursor.lastrowid or 0
        return HistoryEntry(
            id=entry_id,
            question=question,
            sql=sql,
            status=status,
            latency_ms=latency_ms,
            created_at=created_at,
        )

    def recent(self, limit: int = 50) -> list[HistoryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, question, sql, status, latency_ms, created_at "
                "FROM query_history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            HistoryEntry(
                id=row[0],
                question=row[1],
                sql=row[2],
                status=QueryStatus(row[3]),
                latency_ms=row[4],
                created_at=row[5],
            )
            for row in rows
        ]

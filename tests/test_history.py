"""History stores: ordering, persistence, and round-tripping."""

from __future__ import annotations

from pathlib import Path

from text_to_sql_engine.history import InMemoryHistoryStore, SqliteHistoryStore
from text_to_sql_engine.models import QueryStatus


class TestInMemoryHistory:
    def test_recent_returns_newest_first(self) -> None:
        store = InMemoryHistoryStore()
        store.add("first", "SELECT 1", QueryStatus.OK, 10.0)
        store.add("second", "SELECT 2", QueryStatus.OK, 20.0)
        entries = store.recent()
        assert [entry.question for entry in entries] == ["second", "first"]

    def test_limit_is_respected(self) -> None:
        store = InMemoryHistoryStore()
        for index in range(5):
            store.add(f"q{index}", None, QueryStatus.ERROR, 1.0)
        assert len(store.recent(limit=2)) == 2


class TestSqliteHistory:
    def test_round_trip(self, tmp_path: Path) -> None:
        store = SqliteHistoryStore(tmp_path / "history.sqlite")
        entry = store.add("how many orders?", "SELECT count(*) FROM orders", QueryStatus.OK, 12.5)
        assert entry.id == 1
        [loaded] = store.recent()
        assert loaded.question == "how many orders?"
        assert loaded.status is QueryStatus.OK
        assert loaded.latency_ms == 12.5

    def test_persists_across_instances(self, tmp_path: Path) -> None:
        path = tmp_path / "history.sqlite"
        SqliteHistoryStore(path).add("q1", None, QueryStatus.REJECTED, 3.0)
        reopened = SqliteHistoryStore(path)
        [entry] = reopened.recent()
        assert entry.question == "q1"
        assert entry.sql is None
        assert entry.status is QueryStatus.REJECTED

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "nested" / "history.sqlite"
        SqliteHistoryStore(nested).add("q", "SELECT 1", QueryStatus.OK, 1.0)
        assert nested.exists()

    def test_newest_first_ordering(self, tmp_path: Path) -> None:
        store = SqliteHistoryStore(tmp_path / "history.sqlite")
        store.add("older", None, QueryStatus.OK, 1.0)
        store.add("newer", None, QueryStatus.OK, 1.0)
        questions = [entry.question for entry in store.recent()]
        assert questions == ["newer", "older"]

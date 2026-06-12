"""The offline demo runs end-to-end with no database, no network, no keys."""

from __future__ import annotations

from pathlib import Path

import pytest

from text_to_sql_engine.demo import main
from text_to_sql_engine.demo_data import DEMO_CASES, DEMO_SQL_TEMPLATES


@pytest.fixture
def offline_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)  # artifacts/ and any .env lookups stay in tmp
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_every_demo_question_has_a_template() -> None:
    for case in DEMO_CASES:
        assert any(
            needle.lower() in case.question.lower() for needle in DEMO_SQL_TEMPLATES
        ), f"no FakeLLM template matches: {case.question!r}"


@pytest.mark.usefixtures("offline_env")
def test_demo_runs_offline_and_shows_the_pipeline(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    out = capsys.readouterr().out
    assert "fully offline" in out
    # Guardrail effects are visible in the printed SQL.
    assert "LIMIT 200" in out  # injected limit on the status query
    assert "status=rejected" in out  # the SELECT * question was refused
    assert "sensitive" in out
    # Real fixture rows and summaries made it to the output.
    assert "4K Action Camera" in out
    assert "The query returned 5 rows." in out
    # The self-correction showcase recovered from an EXPLAIN-stage failure.
    assert "Self-correction showcase" in out
    assert "[explain] attempt 1" in out
    assert "must appear in the GROUP BY" in out
    assert "status=ok attempts=2" in out
    assert "History" in out


@pytest.mark.usefixtures("offline_env")
def test_demo_history_is_persisted(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    main()
    capsys.readouterr()
    assert (tmp_path / "artifacts" / "history.sqlite").exists()

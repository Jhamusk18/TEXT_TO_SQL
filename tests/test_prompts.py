"""Prompt construction: schema cards, exemplars, corrections, summaries."""

from __future__ import annotations

from text_to_sql_engine.embeddings.fake import FakeEmbedder
from text_to_sql_engine.execution.executor import ExecutionResult
from text_to_sql_engine.fewshot.exemplars import DEMO_EXEMPLARS
from text_to_sql_engine.prompts import PromptBuilder
from text_to_sql_engine.schema.cards import select_cards
from text_to_sql_engine.schema.fixtures import DEMO_SCHEMA


def test_initial_prompt_contains_cards_exemplars_and_question(
    prompts: PromptBuilder, embedder: FakeEmbedder
) -> None:
    cards = select_cards("orders by status", DEMO_SCHEMA, embedder, 10_000)
    prompt = prompts.initial("How many orders per status?", cards, DEMO_EXEMPLARS[:2])
    assert "table orders" in prompt
    assert DEMO_EXEMPLARS[0].question in prompt
    assert DEMO_EXEMPLARS[0].sql in prompt
    assert prompt.rstrip().endswith("SQL:")
    assert "How many orders per status?" in prompt
    assert "Dialect: postgres." in prompt


def test_correction_prompt_carries_sql_and_error(prompts: PromptBuilder) -> None:
    prompt = prompts.correction("the question", "SELECT bogus FROM orders", "[rule] boom")
    assert "SELECT bogus FROM orders" in prompt
    assert "[rule] boom" in prompt
    assert "the question" in prompt


def test_summary_prompt_embeds_row_count_marker(prompts: PromptBuilder) -> None:
    result = ExecutionResult(columns=["status", "n"], rows=[{"status": "paid", "n": 5}])
    prompt = prompts.summary("orders per status", result)
    assert "row_count=1" in prompt
    assert "status, n" in prompt
    assert '"paid"' in prompt

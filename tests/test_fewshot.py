"""Few-shot retrieval: relevance ordering, k handling, determinism."""

from __future__ import annotations

from text_to_sql_engine.embeddings.fake import FakeEmbedder
from text_to_sql_engine.fewshot.exemplars import DEMO_EXEMPLARS
from text_to_sql_engine.fewshot.store import FewShotStore


def test_bundled_set_has_fifteen_exemplars() -> None:
    assert len(DEMO_EXEMPLARS) == 15


def test_exact_question_match_ranks_first(embedder: FakeEmbedder) -> None:
    store = FewShotStore(DEMO_EXEMPLARS, embedder)
    top = store.top_k("How many orders are in each status?", k=3)
    assert top[0].question == "How many orders are in each status?"


def test_related_question_retrieves_related_exemplar(embedder: FakeEmbedder) -> None:
    store = FewShotStore(DEMO_EXEMPLARS, embedder)
    top = store.top_k("Which refund reasons come up most often?", k=3)
    assert any("refund" in exemplar.question.lower() for exemplar in top)


def test_top_k_respects_k(embedder: FakeEmbedder) -> None:
    store = FewShotStore(DEMO_EXEMPLARS, embedder)
    assert len(store.top_k("total revenue", k=3)) == 3
    assert len(store.top_k("total revenue", k=5)) == 5
    assert store.top_k("total revenue", k=0) == []


def test_empty_store_returns_nothing(embedder: FakeEmbedder) -> None:
    store = FewShotStore([], embedder)
    assert store.top_k("anything", k=3) == []


def test_retrieval_is_deterministic(embedder: FakeEmbedder) -> None:
    store = FewShotStore(DEMO_EXEMPLARS, embedder)
    first = store.top_k("average order value by country", k=3)
    second = store.top_k("average order value by country", k=3)
    assert first == second

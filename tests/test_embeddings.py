"""FakeEmbedder determinism and similarity behavior."""

from __future__ import annotations

import pytest

from text_to_sql_engine.embeddings.base import cosine_similarity
from text_to_sql_engine.embeddings.fake import FakeEmbedder


def test_embedding_is_deterministic(embedder: FakeEmbedder) -> None:
    first = embedder.embed(["how many orders shipped"])
    second = embedder.embed(["how many orders shipped"])
    assert first == second


def test_identical_texts_have_similarity_one(embedder: FakeEmbedder) -> None:
    [a, b] = embedder.embed(["refund totals by country", "refund totals by country"])
    assert cosine_similarity(a, b) == pytest.approx(1.0)


def test_shared_vocabulary_beats_disjoint(embedder: FakeEmbedder) -> None:
    [question, related, unrelated] = embedder.embed(
        [
            "how many refunds were issued",
            "refunds issued per month",
            "favorite painting of the museum",
        ]
    )
    assert cosine_similarity(question, related) > cosine_similarity(question, unrelated)


def test_snake_case_identifiers_match_their_words(embedder: FakeEmbedder) -> None:
    [question, card] = embedder.embed(["revenue from items", "table order_items"])
    assert cosine_similarity(question, card) > 0.0


def test_empty_text_yields_zero_vector(embedder: FakeEmbedder) -> None:
    [vector] = embedder.embed([""])
    assert all(value == 0.0 for value in vector)
    assert cosine_similarity(vector, vector) == 0.0


def test_vectors_are_normalized(embedder: FakeEmbedder) -> None:
    [vector] = embedder.embed(["orders orders orders refunds"])
    assert sum(value * value for value in vector) == pytest.approx(1.0)

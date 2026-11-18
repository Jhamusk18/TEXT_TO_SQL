"""Gemini embeddings adapter behind the Embedder protocol (official google-genai SDK)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from google.genai import types

from text_to_sql_engine.llm.gemini_provider import build_client

MAX_BATCH = 100  # embed_content accepts at most 100 texts per request


class GeminiEmbedder:
    """Batches texts into ``embed_content`` calls of up to 100.

    SEMANTIC_SIMILARITY is the symmetric task type: questions, schema cards and
    exemplar questions are all compared to each other with cosine similarity.
    """

    def __init__(
        self, api_key: str, model: str = "gemini-embedding-001", client: Any = None
    ) -> None:
        self._client: Any = client or build_client(api_key)
        self._model = model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), MAX_BATCH):
            batch = list(texts[start : start + MAX_BATCH])
            response = self._client.models.embed_content(
                model=self._model,
                contents=batch,
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
            )
            batch_vectors = [list(item.values or []) for item in response.embeddings or []]
            if len(batch_vectors) != len(batch):
                raise RuntimeError(
                    f"Gemini returned {len(batch_vectors)} embeddings for {len(batch)} texts"
                )
            vectors.extend(batch_vectors)
        return vectors

"""Embedders: a minimal protocol, the OpenAI adapter, and a deterministic fake."""

from text_to_sql_engine.embeddings.base import Embedder, cosine_similarity
from text_to_sql_engine.embeddings.fake import FakeEmbedder

__all__ = ["Embedder", "FakeEmbedder", "cosine_similarity"]

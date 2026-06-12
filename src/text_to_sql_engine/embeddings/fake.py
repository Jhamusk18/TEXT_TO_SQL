"""Deterministic offline embedder: bag-of-hashed-words into a fixed dimension.

Not a semantic model — but shared vocabulary between a question and a schema
card or exemplar produces meaningfully higher cosine similarity, which is all
the retrieval layers need for offline tests and the demo.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tokens(text: str) -> list[str]:
    """Lowercased word tokens; snake_case identifiers also yield their parts,
    so `order_items` in a schema card matches `items` in a question."""
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text.lower()):
        tokens.append(raw)
        if "_" in raw:
            tokens.extend(part for part in raw.split("_") if part)
    return tokens


def _bucket(token: str, dim: int) -> int:
    digest = hashlib.md5(token.encode("utf-8"), usedforsecurity=False).digest()
    return int.from_bytes(digest[:4], "big") % dim


class FakeEmbedder:
    """Hash-based embedder: zero network, zero model files, fully deterministic."""

    def __init__(self, dim: int = 256) -> None:
        self._dim = dim

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        for token in _tokens(text):
            vector[_bucket(token, self._dim)] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]

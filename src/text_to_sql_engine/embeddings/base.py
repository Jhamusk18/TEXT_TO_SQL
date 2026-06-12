"""Embedding protocol and similarity math used for retrieval."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol


class Embedder(Protocol):
    """Maps texts to fixed-dimension vectors. One method, easy to fake."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input text, in order."""
        ...


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity; returns 0.0 when either vector is all-zero."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

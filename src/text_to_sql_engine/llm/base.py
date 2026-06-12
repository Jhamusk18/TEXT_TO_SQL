"""The single seam between this engine and any hosted language model."""

from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Minimal completion interface every model backend implements.

    Keeping this surface tiny is deliberate: the whole pipeline — prompt
    building, guardrails, correction loop — is testable against a fake that
    implements one method.
    """

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return the model's text response for a single-turn prompt."""
        ...

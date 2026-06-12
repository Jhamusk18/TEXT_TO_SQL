"""OpenAI chat-completions adapter behind the LLMProvider protocol."""

from __future__ import annotations

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam


class OpenAIProvider:
    """Thin adapter over the OpenAI chat completions API.

    Temperature defaults to 0 — SQL generation should be as deterministic as
    the provider allows.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.0) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        messages: list[ChatCompletionMessageParam] = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._temperature,
        )
        return response.choices[0].message.content or ""

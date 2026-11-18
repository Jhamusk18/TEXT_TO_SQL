"""OpenAI chat-completions adapter behind the LLMProvider protocol."""

from __future__ import annotations

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam


class OpenAIProvider:
    """Thin adapter over the OpenAI chat completions API.

    Temperature defaults to 0 — SQL generation should be as deterministic as
    the provider allows.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        reasoning_effort: str | None = None,
    ) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._reasoning_effort = reasoning_effort
        # Token accounting, read by the evaluation harness to report run cost.
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        messages: list[ChatCompletionMessageParam] = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        effort = self._reasoning_effort
        extra_body = {"reasoning_effort": effort} if effort else None
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._temperature,
            extra_body=extra_body,
        )
        self.calls += 1
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
            self.completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        return response.choices[0].message.content or ""

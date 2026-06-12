"""Deterministic, scriptable stand-in for a hosted model. Used by tests and the demo."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

_ROW_COUNT_RE = re.compile(r"row_count=(\d+)")


class FakeLLM:
    """Resolves prompts deterministically, in priority order:

    1. **Scripted responses** — popped FIFO; lets tests choreograph exact
       fail-then-succeed sequences for the correction loop.
    2. **Row-count echo** — summary prompts embed ``row_count=N``; the fake
       answers with a deterministic one-liner so summaries work offline.
    3. **SQL templates** — ``{question substring: sql}``; needles are matched
       against the text after the last ``### Question`` marker (the actual
       question), so exemplar questions earlier in the prompt cannot collide.
       Powers the offline demo.
    4. **Default** — a constant fallback.
    """

    def __init__(
        self,
        script: Sequence[str] = (),
        sql_templates: Mapping[str, str] | None = None,
        default: str = "SELECT 1",
    ) -> None:
        self._script: list[str] = list(script)
        self._templates: dict[str, str] = dict(sql_templates or {})
        self._default = default
        self.calls: list[str] = []

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        self.calls.append(prompt)
        if self._script:
            return self._script.pop(0)
        match = _ROW_COUNT_RE.search(prompt)
        if match is not None:
            count = int(match.group(1))
            noun = "row" if count == 1 else "rows"
            return f"The query returned {count} {noun}."
        question_section = prompt.rsplit("### Question", 1)[-1].lower()
        for needle, sql in self._templates.items():
            if needle.lower() in question_section:
                return sql
        return self._default

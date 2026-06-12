"""Prompt construction for generation, correction, and summaries."""

from __future__ import annotations

import json
from collections.abc import Sequence

from text_to_sql_engine.execution.executor import ExecutionResult
from text_to_sql_engine.models import Exemplar
from text_to_sql_engine.schema.cards import SchemaCard

SYSTEM_PROMPT = (
    "You are a careful analytics engineer. You translate questions into a "
    "single read-only SQL SELECT statement for the given schema. You never "
    "invent tables or columns, never write DML or DDL, and you respond with "
    "SQL only — no prose, no markdown fences."
)


class PromptBuilder:
    """Renders the three prompt shapes the pipeline needs."""

    def __init__(self, dialect: str = "postgres") -> None:
        self._dialect = dialect

    def initial(
        self,
        question: str,
        cards: Sequence[SchemaCard],
        exemplars: Sequence[Exemplar],
    ) -> str:
        """First-shot generation prompt: rules, schema cards, exemplars, question."""
        sections = [
            f"Dialect: {self._dialect}.",
            "Rules: one SELECT statement only; use only the tables and columns "
            "below; qualify columns with their table name; do not add comments.",
            "",
            "### Schema",
            *[card.text for card in cards],
            "",
            "### Examples",
        ]
        for exemplar in exemplars:
            sections.append(f"Q: {exemplar.question}")
            sections.append(f"SQL: {exemplar.sql}")
        sections += ["", "### Question", question, "", "SQL:"]
        return "\n".join(sections)

    def correction(self, question: str, failed_sql: str, error: str) -> str:
        """Feedback prompt: the failed SQL plus the exact error, nothing else new."""
        return "\n".join(
            [
                f"Your previous {self._dialect} SQL for the question below failed.",
                "Fix the SQL. Respond with the corrected single SELECT statement only.",
                "",
                "### Question",
                question,
                "",
                "### Failed SQL",
                failed_sql,
                "",
                "### Error",
                error,
                "",
                "SQL:",
            ]
        )

    def summary(self, question: str, result: ExecutionResult) -> str:
        """Summary prompt; embeds row_count=N so the FakeLLM can answer offline."""
        sample = json.dumps(result.rows[0], default=str) if result.rows else "{}"
        return "\n".join(
            [
                "Summarize the result of a SQL query in one short plain sentence.",
                f"Question: {question}",
                f"row_count={result.row_count}",
                f"columns={', '.join(result.columns)}",
                f"first_row={sample[:300]}",
            ]
        )

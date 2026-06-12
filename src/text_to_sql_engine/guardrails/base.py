"""Guardrail plumbing: violation type, context, rule protocol, and the pipeline.

Each rule is a small object with one job: take an AST, either transform it or
raise. The pipeline parses once, folds the AST through every rule in order,
and renders the final SQL. Validation and rewriting share one mechanism, so
there is no window where a 'checked' string drifts from the SQL that runs.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from text_to_sql_engine.models import DatabaseSchema


class GuardrailViolation(Exception):
    """Raised by any rule that decides the statement must not run."""

    def __init__(self, rule: str, message: str) -> None:
        super().__init__(f"[{rule}] {message}")
        self.rule = rule
        self.message = message


@dataclass(frozen=True)
class GuardrailContext:
    """Everything a rule may consult: the live schema and policy knobs."""

    schema: DatabaseSchema
    default_limit: int = 200
    dialect: str = "postgres"


class GuardrailRule(Protocol):
    """One composable check/transform over the parsed statement."""

    name: str

    def apply(self, expression: exp.Expression, ctx: GuardrailContext) -> exp.Expression:
        ...


def parse_single_statement(sql: str, dialect: str) -> exp.Expression:
    """Parse and enforce exactly one statement.

    Multi-statement payloads (``SELECT 1; DROP TABLE ...``) die here, before
    any rule runs. A parse failure is also a rejection — unparseable SQL is
    never forwarded to the database.
    """
    try:
        statements: list[exp.Expression] = [
            s for s in sqlglot.parse(sql, read=dialect) if isinstance(s, exp.Expression)
        ]
    except ParseError as error:
        raise GuardrailViolation("parser", f"SQL could not be parsed: {error}") from error
    if not statements:
        raise GuardrailViolation("parser", "no SQL statement found")
    if len(statements) > 1:
        raise GuardrailViolation(
            "single-statement", f"expected exactly one statement, got {len(statements)}"
        )
    return statements[0]


class GuardrailPipeline:
    """Parses once, then folds the AST through every rule in order."""

    def __init__(self, rules: Sequence[GuardrailRule], ctx: GuardrailContext) -> None:
        self._rules = list(rules)
        self._ctx = ctx

    def validate(self, sql: str) -> str:
        """Return safe, rewritten SQL — or raise GuardrailViolation."""
        expression = parse_single_statement(sql, self._ctx.dialect)
        for rule in self._rules:
            expression = rule.apply(expression, self._ctx)
        return expression.sql(dialect=self._ctx.dialect, comments=False)

"""Database error classification.

The correction loop needs to know *why* a statement failed: a missing column
is worth sending back to the model, a permission error is not. Classification
prefers the SQLSTATE code (precise) and falls back to message patterns (for
errors surfaced without a code, e.g. from drivers or fakes).
"""

from __future__ import annotations

import re
from enum import StrEnum


class ErrorCategory(StrEnum):
    SYNTAX = "syntax"
    UNDEFINED_TABLE = "undefined_table"
    UNDEFINED_COLUMN = "undefined_column"
    AMBIGUOUS_COLUMN = "ambiguous_column"
    GROUPING = "grouping"
    TIMEOUT = "timeout"
    READ_ONLY = "read_only"
    PERMISSION = "permission"
    UNKNOWN = "unknown"


_SQLSTATE_CATEGORIES: dict[str, ErrorCategory] = {
    "42601": ErrorCategory.SYNTAX,
    "42P01": ErrorCategory.UNDEFINED_TABLE,
    "42703": ErrorCategory.UNDEFINED_COLUMN,
    "42702": ErrorCategory.AMBIGUOUS_COLUMN,
    "42803": ErrorCategory.GROUPING,
    "57014": ErrorCategory.TIMEOUT,
    "25006": ErrorCategory.READ_ONLY,
    "42501": ErrorCategory.PERMISSION,
}

_MESSAGE_PATTERNS: list[tuple[re.Pattern[str], ErrorCategory]] = [
    (re.compile(r"syntax error", re.IGNORECASE), ErrorCategory.SYNTAX),
    (re.compile(r'relation "[^"]*" does not exist', re.IGNORECASE), ErrorCategory.UNDEFINED_TABLE),
    (re.compile(r"column .* does not exist", re.IGNORECASE), ErrorCategory.UNDEFINED_COLUMN),
    (
        re.compile(r"column reference .* is ambiguous", re.IGNORECASE),
        ErrorCategory.AMBIGUOUS_COLUMN,
    ),
    (re.compile(r"must appear in the GROUP BY", re.IGNORECASE), ErrorCategory.GROUPING),
    (
        re.compile(r"statement timeout|canceling statement due to", re.IGNORECASE),
        ErrorCategory.TIMEOUT,
    ),
    (re.compile(r"read-only transaction", re.IGNORECASE), ErrorCategory.READ_ONLY),
    (re.compile(r"permission denied", re.IGNORECASE), ErrorCategory.PERMISSION),
]

# Categories the LLM has a realistic chance of fixing by rewriting the SQL.
# Timeouts, read-only violations, and permission errors are excluded on
# purpose: paraphrasing SQL rarely makes a slow query fast, and it should
# never be the mechanism that talks its way around a security boundary.
_RETRYABLE: frozenset[ErrorCategory] = frozenset(
    {
        ErrorCategory.SYNTAX,
        ErrorCategory.UNDEFINED_TABLE,
        ErrorCategory.UNDEFINED_COLUMN,
        ErrorCategory.AMBIGUOUS_COLUMN,
        ErrorCategory.GROUPING,
        ErrorCategory.UNKNOWN,
    }
)


def classify_error(message: str, sqlstate: str | None = None) -> ErrorCategory:
    """Map a database error to a category. SQLSTATE wins over message text."""
    if sqlstate is not None:
        category = _SQLSTATE_CATEGORIES.get(sqlstate)
        if category is not None:
            return category
    for pattern, category in _MESSAGE_PATTERNS:
        if pattern.search(message):
            return category
    return ErrorCategory.UNKNOWN


def is_retryable(category: ErrorCategory) -> bool:
    """Whether the correction loop should hand this failure back to the LLM."""
    return category in _RETRYABLE

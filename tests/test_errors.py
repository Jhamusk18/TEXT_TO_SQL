"""EXPLAIN/execution error classification and retryability policy."""

from __future__ import annotations

import pytest

from text_to_sql_engine.execution.errors import ErrorCategory, classify_error, is_retryable
from text_to_sql_engine.execution.executor import ExecutionError


class TestSqlstateClassification:
    @pytest.mark.parametrize(
        ("sqlstate", "expected"),
        [
            ("42601", ErrorCategory.SYNTAX),
            ("42P01", ErrorCategory.UNDEFINED_TABLE),
            ("42703", ErrorCategory.UNDEFINED_COLUMN),
            ("42702", ErrorCategory.AMBIGUOUS_COLUMN),
            ("42803", ErrorCategory.GROUPING),
            ("57014", ErrorCategory.TIMEOUT),
            ("25006", ErrorCategory.READ_ONLY),
            ("42501", ErrorCategory.PERMISSION),
        ],
    )
    def test_known_sqlstates(self, sqlstate: str, expected: ErrorCategory) -> None:
        assert classify_error("irrelevant message", sqlstate) == expected

    def test_sqlstate_wins_over_message(self) -> None:
        # Message says column, code says table: trust the code.
        category = classify_error('column "x" does not exist', sqlstate="42P01")
        assert category == ErrorCategory.UNDEFINED_TABLE

    def test_unknown_sqlstate_falls_back_to_message(self) -> None:
        category = classify_error("syntax error at or near 'FRMO'", sqlstate="99999")
        assert category == ErrorCategory.SYNTAX


class TestMessageClassification:
    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("syntax error at or near 'SELEC'", ErrorCategory.SYNTAX),
            ('relation "ordrs" does not exist', ErrorCategory.UNDEFINED_TABLE),
            ('column orders.bogus does not exist', ErrorCategory.UNDEFINED_COLUMN),
            ('column reference "id" is ambiguous', ErrorCategory.AMBIGUOUS_COLUMN),
            ('column "orders.status" must appear in the GROUP BY clause', ErrorCategory.GROUPING),
            ("canceling statement due to statement timeout", ErrorCategory.TIMEOUT),
            ("cannot execute INSERT in a read-only transaction", ErrorCategory.READ_ONLY),
            ("permission denied for table customers", ErrorCategory.PERMISSION),
            ("something completely unexpected", ErrorCategory.UNKNOWN),
        ],
    )
    def test_message_patterns(self, message: str, expected: ErrorCategory) -> None:
        assert classify_error(message) == expected


class TestRetryability:
    @pytest.mark.parametrize(
        "category",
        [
            ErrorCategory.SYNTAX,
            ErrorCategory.UNDEFINED_TABLE,
            ErrorCategory.UNDEFINED_COLUMN,
            ErrorCategory.AMBIGUOUS_COLUMN,
            ErrorCategory.GROUPING,
            ErrorCategory.UNKNOWN,
        ],
    )
    def test_model_fixable_errors_are_retryable(self, category: ErrorCategory) -> None:
        assert is_retryable(category)

    @pytest.mark.parametrize(
        "category",
        [ErrorCategory.TIMEOUT, ErrorCategory.READ_ONLY, ErrorCategory.PERMISSION],
    )
    def test_policy_errors_are_not_retryable(self, category: ErrorCategory) -> None:
        assert not is_retryable(category)


class TestExecutionError:
    def test_self_classifies_from_sqlstate(self) -> None:
        error = ExecutionError("whatever", sqlstate="42703")
        assert error.category == ErrorCategory.UNDEFINED_COLUMN

    def test_self_classifies_from_message(self) -> None:
        error = ExecutionError('relation "nope" does not exist')
        assert error.category == ErrorCategory.UNDEFINED_TABLE

    def test_explicit_category_wins(self) -> None:
        error = ExecutionError("anything", category=ErrorCategory.TIMEOUT)
        assert error.category == ErrorCategory.TIMEOUT

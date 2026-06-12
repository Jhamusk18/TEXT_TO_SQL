"""Query execution: error classification, real Postgres executor, scriptable fake."""

from text_to_sql_engine.execution.errors import ErrorCategory, classify_error, is_retryable
from text_to_sql_engine.execution.executor import (
    ExecutionError,
    ExecutionResult,
    FakeExecutor,
    QueryExecutor,
)

__all__ = [
    "ErrorCategory",
    "ExecutionError",
    "ExecutionResult",
    "FakeExecutor",
    "QueryExecutor",
    "classify_error",
    "is_retryable",
]

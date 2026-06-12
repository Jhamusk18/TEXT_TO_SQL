"""Query executors: the QueryExecutor protocol, real Postgres, and a fake.

The real executor stacks three independent defenses *under* the guardrails:
a read-only transaction (the server refuses writes even if one slipped
through), a per-statement timeout (no runaway scans), and EXPLAIN-first
preflight driven by the caller (bad references fail before any row is read).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row

from text_to_sql_engine.execution.errors import ErrorCategory, classify_error


@dataclass(frozen=True)
class ExecutionResult:
    """Rows plus ordered column names from one executed statement."""

    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return len(self.rows)


class ExecutionError(Exception):
    """A database failure, already classified for the correction loop."""

    def __init__(
        self,
        message: str,
        sqlstate: str | None = None,
        category: ErrorCategory | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.sqlstate = sqlstate
        self.category = category or classify_error(message, sqlstate)


class QueryExecutor(Protocol):
    """Two operations: cheap EXPLAIN preflight, then the real execution."""

    def explain(self, sql: str) -> None:
        ...

    def execute(self, sql: str) -> ExecutionResult:
        ...


class PostgresExecutor:
    """Runs validated SQL against Postgres with defense-in-depth settings.

    Every call opens a read-only transaction and carries a server-enforced
    ``statement_timeout`` set via connection options — neither can be unset
    by the SQL text itself because multi-statements were already rejected.
    """

    def __init__(self, dsn: str, statement_timeout_ms: int = 5000, connect_timeout_s: int = 5):
        self._dsn = dsn
        self._options = f"-c statement_timeout={int(statement_timeout_ms)}"
        self._connect_timeout = connect_timeout_s

    def explain(self, sql: str) -> None:
        self._run(f"EXPLAIN {sql}")

    def execute(self, sql: str) -> ExecutionResult:
        return self._run(sql)

    def _run(self, sql: str) -> ExecutionResult:
        try:
            with psycopg.connect(
                self._dsn, options=self._options, connect_timeout=self._connect_timeout
            ) as conn:
                conn.read_only = True
                with conn.cursor(row_factory=dict_row) as cur:
                    # By the time SQL reaches this executor it has already
                    # passed the full AST guardrail pipeline.
                    cur.execute(sql)
                    if cur.description is None:
                        return ExecutionResult()
                    columns = [column.name for column in cur.description]
                    rows = cur.fetchall()
                    return ExecutionResult(columns=columns, rows=[dict(row) for row in rows])
        except psycopg.Error as error:
            raise ExecutionError(str(error).strip(), sqlstate=error.sqlstate) from error


class FakeExecutor:
    """Scriptable executor for tests and the offline demo.

    ``explain_script`` / ``execute_script`` are consumed FIFO; an empty script
    means success. This makes fail-then-succeed correction-loop scenarios a
    one-line fixture.
    """

    def __init__(
        self,
        explain_script: Sequence[ExecutionError | None] = (),
        execute_script: Sequence[ExecutionError | ExecutionResult] = (),
        default_result: ExecutionResult | None = None,
    ) -> None:
        self._explain_script = list(explain_script)
        self._execute_script = list(execute_script)
        self._default_result = default_result or ExecutionResult()
        self.explained: list[str] = []
        self.executed: list[str] = []

    def explain(self, sql: str) -> None:
        self.explained.append(sql)
        if self._explain_script:
            outcome = self._explain_script.pop(0)
            if outcome is not None:
                raise outcome

    def execute(self, sql: str) -> ExecutionResult:
        self.executed.append(sql)
        if self._execute_script:
            outcome = self._execute_script.pop(0)
            if isinstance(outcome, ExecutionError):
                raise outcome
            return outcome
        return self._default_result

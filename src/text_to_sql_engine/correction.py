"""The self-correction loop: generate -> validate -> EXPLAIN -> execute.

Failures at any stage are classified and — when a rewrite could plausibly
help — fed back to the model with the failing SQL and the exact error, up to
``max_corrections`` rounds. Non-retryable failures (permissions, read-only
violations, timeouts) stop the loop immediately: retrying cannot fix policy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from text_to_sql_engine.execution.errors import ErrorCategory, is_retryable
from text_to_sql_engine.execution.executor import ExecutionError, ExecutionResult, QueryExecutor
from text_to_sql_engine.guardrails.base import GuardrailPipeline, GuardrailViolation
from text_to_sql_engine.llm.base import LLMProvider
from text_to_sql_engine.models import CorrectionRound, QueryStatus
from text_to_sql_engine.prompts import SYSTEM_PROMPT, PromptBuilder

_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def extract_sql(text: str) -> str:
    """Pull SQL out of a model response: unwrap fences, trim, drop trailing ';'."""
    match = _FENCE_RE.search(text)
    candidate = (match.group(1) if match else text).strip()
    return candidate.rstrip(";").strip()


@dataclass(frozen=True)
class _Failure:
    stage: str  # "guardrail" | "explain" | "execute"
    message: str
    category: ErrorCategory | None
    retryable: bool


@dataclass(frozen=True)
class _Attempt:
    """Outcome of one validate/EXPLAIN/execute pass."""

    validated_sql: str | None
    result: ExecutionResult | None
    failure: _Failure | None


@dataclass(frozen=True)
class LoopOutcome:
    """Everything the pipeline needs to build the final QueryResult."""

    status: QueryStatus
    sql: str | None
    result: ExecutionResult | None
    rounds: list[CorrectionRound]
    attempts: int
    error: str | None


class CorrectionLoop:
    def __init__(
        self,
        llm: LLMProvider,
        guardrails: GuardrailPipeline,
        executor: QueryExecutor,
        prompts: PromptBuilder,
        max_corrections: int = 2,
    ) -> None:
        self._llm = llm
        self._guardrails = guardrails
        self._executor = executor
        self._prompts = prompts
        self._max_corrections = max_corrections

    def run(self, question: str, initial_prompt: str) -> LoopOutcome:
        rounds: list[CorrectionRound] = []
        raw = self._llm.complete(initial_prompt, system=SYSTEM_PROMPT)
        for attempt in range(1, self._max_corrections + 2):
            candidate = extract_sql(raw)
            outcome = self._try_attempt(candidate)
            if outcome.failure is None and outcome.result is not None:
                return LoopOutcome(
                    QueryStatus.OK, outcome.validated_sql, outcome.result, rounds, attempt, None
                )
            failure = outcome.failure
            if failure is None:  # pragma: no cover — _try_attempt always sets one or the other
                raise RuntimeError("attempt produced neither result nor failure")
            rounds.append(
                CorrectionRound(
                    attempt=attempt,
                    stage=failure.stage,
                    sql=candidate,
                    error=failure.message,
                    category=failure.category.value if failure.category else None,
                )
            )
            if not failure.retryable or attempt > self._max_corrections:
                status = (
                    QueryStatus.REJECTED if failure.stage == "guardrail" else QueryStatus.ERROR
                )
                final_sql = outcome.validated_sql or candidate
                return LoopOutcome(status, final_sql, None, rounds, attempt, failure.message)
            raw = self._llm.complete(
                self._prompts.correction(question, candidate, failure.message),
                system=SYSTEM_PROMPT,
            )
        raise RuntimeError("unreachable: loop always returns within the attempt budget")

    def _try_attempt(self, candidate: str) -> _Attempt:
        """One pass through guardrails, EXPLAIN preflight, and execution."""
        try:
            validated = self._guardrails.validate(candidate)
        except GuardrailViolation as violation:
            return _Attempt(None, None, _Failure("guardrail", str(violation), None, True))
        try:
            self._executor.explain(validated)
        except ExecutionError as error:
            failure = _Failure(
                "explain", error.message, error.category, is_retryable(error.category)
            )
            return _Attempt(validated, None, failure)
        try:
            result = self._executor.execute(validated)
        except ExecutionError as error:
            failure = _Failure(
                "execute", error.message, error.category, is_retryable(error.category)
            )
            return _Attempt(validated, None, failure)
        return _Attempt(validated, result, None)

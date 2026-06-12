"""Shared fixtures. Everything here is offline: fixture schema, fakes only."""

from __future__ import annotations

import pytest

from text_to_sql_engine.embeddings.fake import FakeEmbedder
from text_to_sql_engine.guardrails.base import GuardrailContext, GuardrailPipeline
from text_to_sql_engine.guardrails.rules import default_rules
from text_to_sql_engine.models import DatabaseSchema
from text_to_sql_engine.prompts import PromptBuilder
from text_to_sql_engine.schema.fixtures import DEMO_SCHEMA


@pytest.fixture
def schema() -> DatabaseSchema:
    return DEMO_SCHEMA


@pytest.fixture
def ctx(schema: DatabaseSchema) -> GuardrailContext:
    return GuardrailContext(schema=schema, default_limit=200, dialect="postgres")


@pytest.fixture
def guardrails(ctx: GuardrailContext) -> GuardrailPipeline:
    return GuardrailPipeline(default_rules(), ctx)


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def prompts() -> PromptBuilder:
    return PromptBuilder(dialect="postgres")

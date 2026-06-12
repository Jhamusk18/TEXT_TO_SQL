"""Schema providers and a cache with on-demand invalidation."""

from __future__ import annotations

from typing import Protocol

from text_to_sql_engine.models import DatabaseSchema


class SchemaProvider(Protocol):
    """Anything that can produce a DatabaseSchema (live DB, fixture, ...)."""

    def load(self) -> DatabaseSchema:
        ...


class StaticSchemaProvider:
    """Serves a fixed in-memory schema. Used offline and in tests."""

    def __init__(self, schema: DatabaseSchema) -> None:
        self._schema = schema

    def load(self) -> DatabaseSchema:
        return self._schema


class SchemaCache:
    """Memoizes introspection; ``invalidate()`` forces a reload on next access.

    Introspection costs several round-trips, so it runs once and is reused for
    every query until someone hits POST /schema/refresh after a migration.
    """

    def __init__(self, provider: SchemaProvider) -> None:
        self._provider = provider
        self._cached: DatabaseSchema | None = None

    def get(self) -> DatabaseSchema:
        if self._cached is None:
            self._cached = self._provider.load()
        return self._cached

    def invalidate(self) -> None:
        self._cached = None

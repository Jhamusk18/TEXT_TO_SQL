"""Schema card rendering, token budgeting, and cache invalidation."""

from __future__ import annotations

from text_to_sql_engine.embeddings.fake import FakeEmbedder
from text_to_sql_engine.models import ColumnInfo, DatabaseSchema, TableInfo
from text_to_sql_engine.schema.cache import SchemaCache
from text_to_sql_engine.schema.cards import build_card, estimate_tokens, select_cards
from text_to_sql_engine.schema.fixtures import DEMO_SCHEMA


class TestBuildCard:
    def test_card_contains_name_comment_and_columns(self) -> None:
        table = DEMO_SCHEMA.get_table("orders")
        assert table is not None
        card = build_card(table)
        assert card.text.startswith("table orders -- One row per checkout")
        assert "  status text" in card.text
        assert "  id integer PK" in card.text

    def test_card_marks_foreign_keys(self) -> None:
        table = DEMO_SCHEMA.get_table("order_items")
        assert table is not None
        card = build_card(table)
        assert "order_id integer -> orders.id" in card.text
        assert "product_id integer -> products.id" in card.text

    def test_card_marks_sensitive_tables(self) -> None:
        table = DEMO_SCHEMA.get_table("customers")
        assert table is not None
        assert "[sensitive]" in build_card(table).text

    def test_token_estimate_tracks_length(self) -> None:
        assert estimate_tokens("x" * 40) == 10
        assert estimate_tokens("") == 1  # never zero, avoids divide-by-zero budgeting


class TestSelectCards:
    def test_most_relevant_table_comes_first(self, embedder: FakeEmbedder) -> None:
        cards = select_cards(
            "How many refunds were issued last month?", DEMO_SCHEMA, embedder, 10_000
        )
        assert cards[0].table == "refunds"

    def test_question_about_orders_ranks_orders_first(self, embedder: FakeEmbedder) -> None:
        cards = select_cards("How many orders were cancelled?", DEMO_SCHEMA, embedder, 10_000)
        assert cards[0].table == "orders"

    def test_large_budget_includes_every_table(self, embedder: FakeEmbedder) -> None:
        cards = select_cards("total revenue", DEMO_SCHEMA, embedder, 10_000)
        assert {card.table for card in cards} == DEMO_SCHEMA.table_names()

    def test_tiny_budget_still_returns_the_top_card(self, embedder: FakeEmbedder) -> None:
        cards = select_cards("How many refunds were issued?", DEMO_SCHEMA, embedder, 1)
        assert len(cards) == 1
        assert cards[0].table == "refunds"

    def test_budget_caps_the_selection(self, embedder: FakeEmbedder) -> None:
        all_cards = select_cards("orders by status", DEMO_SCHEMA, embedder, 10_000)
        budget = all_cards[0].tokens + all_cards[1].tokens
        capped = select_cards("orders by status", DEMO_SCHEMA, embedder, budget)
        assert 1 <= len(capped) < len(all_cards)
        assert capped[0].table == all_cards[0].table

    def test_empty_schema_returns_no_cards(self, embedder: FakeEmbedder) -> None:
        assert select_cards("anything", DatabaseSchema(tables=[]), embedder, 100) == []


class _CountingProvider:
    def __init__(self) -> None:
        self.loads = 0

    def load(self) -> DatabaseSchema:
        self.loads += 1
        return DatabaseSchema(
            tables=[TableInfo(name="t", columns=[ColumnInfo(name="id", data_type="int")])]
        )


class TestSchemaCache:
    def test_load_happens_once(self) -> None:
        provider = _CountingProvider()
        cache = SchemaCache(provider)
        cache.get()
        cache.get()
        assert provider.loads == 1

    def test_invalidate_forces_reload(self) -> None:
        provider = _CountingProvider()
        cache = SchemaCache(provider)
        cache.get()
        cache.invalidate()
        cache.get()
        assert provider.loads == 2

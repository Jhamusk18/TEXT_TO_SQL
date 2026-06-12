"""Tests for every guardrail rule, individually and through the pipeline."""

from __future__ import annotations

import pytest
import sqlglot

from text_to_sql_engine.guardrails.base import (
    GuardrailContext,
    GuardrailPipeline,
    GuardrailViolation,
    parse_single_statement,
)
from text_to_sql_engine.guardrails.rules import (
    LimitInjectRule,
    NoCommentsRule,
    SensitiveStarRule,
    TableAllowlistRule,
)


class TestStatementShape:
    def test_rejects_update(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="UPDATE"):
            guardrails.validate("UPDATE orders SET status = 'completed'")

    def test_rejects_delete(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="DELETE"):
            guardrails.validate("DELETE FROM orders")

    def test_rejects_insert(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="INSERT"):
            guardrails.validate("INSERT INTO orders (id) VALUES (1)")

    def test_rejects_ddl(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="DROP"):
            guardrails.validate("DROP TABLE orders")

    def test_rejects_dml_hidden_inside_cte(self, guardrails: GuardrailPipeline) -> None:
        # Postgres allows data-modifying CTEs; a root-only check would miss this.
        with pytest.raises(GuardrailViolation, match="DELETE"):
            guardrails.validate(
                "WITH gone AS (DELETE FROM refunds RETURNING id) SELECT id FROM gone"
            )

    def test_rejects_select_into(self, guardrails: GuardrailPipeline) -> None:
        # SELECT ... INTO creates a new table — a write dressed as a read.
        with pytest.raises(GuardrailViolation, match="INTO"):
            guardrails.validate("SELECT orders.id INTO orders_copy FROM orders")

    def test_rejects_row_locks(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="LOCK"):
            guardrails.validate("SELECT orders.id FROM orders FOR UPDATE")

    def test_rejects_multi_statement(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="exactly one statement"):
            guardrails.validate("SELECT orders.id FROM orders; DROP TABLE orders")

    def test_rejects_empty_input(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="no SQL statement"):
            guardrails.validate("")

    def test_rejects_unparseable(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="could not be parsed"):
            guardrails.validate("SELECT FROM WHERE !!")

    def test_semicolon_inside_string_is_one_statement(
        self, guardrails: GuardrailPipeline
    ) -> None:
        sql = guardrails.validate("SELECT products.name FROM products WHERE name = 'a; b'")
        assert "a; b" in sql

    def test_union_of_selects_is_allowed(self, guardrails: GuardrailPipeline) -> None:
        sql = guardrails.validate(
            "SELECT orders.id FROM orders UNION SELECT refunds.id FROM refunds"
        )
        assert "UNION" in sql


class TestTableAllowlist:
    def test_rejects_unknown_table(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="not in the allowlist"):
            guardrails.validate("SELECT u.usename FROM pg_user AS u")

    def test_rejects_unknown_table_in_join(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="secret_audit"):
            guardrails.validate(
                "SELECT orders.id FROM orders JOIN secret_audit ON secret_audit.id = orders.id"
            )

    def test_cte_names_are_not_flagged(self, guardrails: GuardrailPipeline) -> None:
        sql = guardrails.validate(
            "WITH totals AS (SELECT orders.customer_id, sum(orders.total_cents) AS spent "
            "FROM orders GROUP BY orders.customer_id) "
            "SELECT totals.customer_id, totals.spent FROM totals"
        )
        assert "WITH totals AS" in sql

    def test_rule_directly_flags_subquery_tables(self, ctx: GuardrailContext) -> None:
        expression = sqlglot.parse_one(
            "SELECT o.id FROM orders AS o WHERE o.id IN (SELECT order_id FROM mystery)",
            read="postgres",
        )
        with pytest.raises(GuardrailViolation, match="mystery"):
            TableAllowlistRule().apply(expression, ctx)


class TestNoComments:
    def test_comments_are_stripped(self, guardrails: GuardrailPipeline) -> None:
        sql = guardrails.validate(
            "SELECT orders.id /* hidden hint */ FROM orders -- trailing note"
        )
        assert "hidden hint" not in sql
        assert "trailing note" not in sql
        assert "--" not in sql

    def test_rule_directly_clears_all_nodes(self, ctx: GuardrailContext) -> None:
        expression = sqlglot.parse_one("SELECT id /* x */ FROM orders", read="postgres")
        cleaned = NoCommentsRule().apply(expression, ctx)
        assert all(not node.comments for node in cleaned.walk())


class TestSensitiveStar:
    def test_rejects_bare_star_on_sensitive_table(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="sensitive"):
            guardrails.validate("SELECT * FROM customers")

    def test_rejects_alias_qualified_star(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match=r"c\.\*"):
            guardrails.validate(
                "SELECT c.* FROM customers AS c JOIN orders AS o ON o.customer_id = c.id"
            )

    def test_star_on_non_sensitive_table_is_expanded(
        self, guardrails: GuardrailPipeline
    ) -> None:
        sql = guardrails.validate("SELECT * FROM products")
        assert "*" not in sql
        assert "products.price_cents" in sql

    def test_explicit_columns_on_sensitive_table_are_fine(
        self, guardrails: GuardrailPipeline
    ) -> None:
        sql = guardrails.validate("SELECT country FROM customers")
        assert "customers.country" in sql

    def test_rule_ignores_star_when_nothing_sensitive(self, ctx: GuardrailContext) -> None:
        expression = sqlglot.parse_one("SELECT * FROM products", read="postgres")
        assert SensitiveStarRule().apply(expression, ctx) is expression


class TestQualifyColumns:
    def test_columns_become_fully_qualified(self, guardrails: GuardrailPipeline) -> None:
        sql = guardrails.validate("SELECT id, status FROM orders")
        assert "orders.id" in sql
        assert "orders.status" in sql

    def test_unknown_column_is_rejected(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="bogus"):
            guardrails.validate("SELECT bogus FROM orders")

    def test_ambiguous_column_is_rejected(self, guardrails: GuardrailPipeline) -> None:
        with pytest.raises(GuardrailViolation, match="qualify-columns"):
            guardrails.validate(
                "SELECT id FROM orders JOIN refunds ON refunds.order_id = orders.id"
            )


class TestLimitInject:
    def test_limit_injected_when_absent(self, guardrails: GuardrailPipeline) -> None:
        sql = guardrails.validate("SELECT orders.id FROM orders")
        assert sql.endswith("LIMIT 200")

    def test_existing_limit_is_preserved(self, guardrails: GuardrailPipeline) -> None:
        sql = guardrails.validate("SELECT orders.id FROM orders LIMIT 7")
        assert sql.endswith("LIMIT 7")
        assert "200" not in sql

    def test_union_gets_an_outer_limit(self, guardrails: GuardrailPipeline) -> None:
        sql = guardrails.validate(
            "SELECT orders.id FROM orders UNION SELECT refunds.id FROM refunds"
        )
        assert sql.endswith("LIMIT 200")

    def test_rule_directly_respects_custom_default(self, ctx: GuardrailContext) -> None:
        custom = GuardrailContext(schema=ctx.schema, default_limit=25)
        expression = sqlglot.parse_one("SELECT orders.id FROM orders", read="postgres")
        limited = LimitInjectRule().apply(expression, custom)
        assert limited.sql(dialect="postgres").endswith("LIMIT 25")


class TestParseSingleStatement:
    def test_returns_single_expression(self) -> None:
        expression = parse_single_statement("SELECT 1", "postgres")
        assert expression.sql() == "SELECT 1"

    def test_counts_statements_not_semicolons(self) -> None:
        expression = parse_single_statement("SELECT 1;", "postgres")
        assert expression.sql() == "SELECT 1"

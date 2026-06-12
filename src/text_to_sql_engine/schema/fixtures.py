"""Bundled e-commerce schema fixture.

Mirrors db/init/01_schema.sql exactly, so tests and the offline demo exercise
the same shape the docker-compose database has.
"""

from __future__ import annotations

from text_to_sql_engine.models import ColumnInfo, DatabaseSchema, ForeignKey, TableInfo

DEMO_SCHEMA = DatabaseSchema(
    tables=[
        TableInfo(
            name="customers",
            comment="Registered shoppers; one row per account",
            sensitive=True,
            columns=[
                ColumnInfo(name="id", data_type="integer", nullable=False, primary_key=True),
                ColumnInfo(name="email", data_type="text", nullable=False, comment="Login email"),
                ColumnInfo(name="full_name", data_type="text", nullable=False),
                ColumnInfo(name="country", data_type="text", comment="ISO 3166 alpha-2 code"),
                ColumnInfo(name="created_at", data_type="timestamptz", nullable=False),
            ],
        ),
        TableInfo(
            name="products",
            comment="Catalog of sellable items",
            columns=[
                ColumnInfo(name="id", data_type="integer", nullable=False, primary_key=True),
                ColumnInfo(name="name", data_type="text", nullable=False),
                ColumnInfo(name="category", data_type="text", nullable=False),
                ColumnInfo(
                    name="price_cents",
                    data_type="integer",
                    nullable=False,
                    comment="Unit price in cents",
                ),
                ColumnInfo(name="created_at", data_type="timestamptz", nullable=False),
            ],
        ),
        TableInfo(
            name="orders",
            comment="One row per checkout; total includes all items",
            columns=[
                ColumnInfo(name="id", data_type="integer", nullable=False, primary_key=True),
                ColumnInfo(name="customer_id", data_type="integer", nullable=False),
                ColumnInfo(
                    name="status",
                    data_type="text",
                    nullable=False,
                    comment="pending | paid | shipped | completed | cancelled",
                ),
                ColumnInfo(
                    name="total_cents",
                    data_type="integer",
                    nullable=False,
                    comment="Order total in cents",
                ),
                ColumnInfo(name="created_at", data_type="timestamptz", nullable=False),
            ],
            foreign_keys=[
                ForeignKey(
                    column="customer_id", references_table="customers", references_column="id"
                )
            ],
        ),
        TableInfo(
            name="order_items",
            comment="Line items belonging to an order",
            columns=[
                ColumnInfo(name="id", data_type="integer", nullable=False, primary_key=True),
                ColumnInfo(name="order_id", data_type="integer", nullable=False),
                ColumnInfo(name="product_id", data_type="integer", nullable=False),
                ColumnInfo(name="quantity", data_type="integer", nullable=False),
                ColumnInfo(
                    name="unit_price_cents",
                    data_type="integer",
                    nullable=False,
                    comment="Price charged per unit at purchase time",
                ),
            ],
            foreign_keys=[
                ForeignKey(column="order_id", references_table="orders", references_column="id"),
                ForeignKey(
                    column="product_id", references_table="products", references_column="id"
                ),
            ],
        ),
        TableInfo(
            name="refunds",
            comment="Money returned against an order",
            columns=[
                ColumnInfo(name="id", data_type="integer", nullable=False, primary_key=True),
                ColumnInfo(name="order_id", data_type="integer", nullable=False),
                ColumnInfo(
                    name="amount_cents",
                    data_type="integer",
                    nullable=False,
                    comment="Refunded amount in cents",
                ),
                ColumnInfo(name="reason", data_type="text"),
                ColumnInfo(name="created_at", data_type="timestamptz", nullable=False),
            ],
            foreign_keys=[
                ForeignKey(column="order_id", references_table="orders", references_column="id")
            ],
        ),
    ]
)

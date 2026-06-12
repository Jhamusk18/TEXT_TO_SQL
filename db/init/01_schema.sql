-- E-commerce demo schema. Mirrored by src/text_to_sql_engine/schema/fixtures.py.

CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    email       TEXT        NOT NULL UNIQUE,
    full_name   TEXT        NOT NULL,
    country     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE customers IS 'Registered shoppers; one row per account';
COMMENT ON COLUMN customers.email IS 'Login email';
COMMENT ON COLUMN customers.country IS 'ISO 3166 alpha-2 code';

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        TEXT        NOT NULL,
    category    TEXT        NOT NULL,
    price_cents INTEGER     NOT NULL CHECK (price_cents >= 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE products IS 'Catalog of sellable items';
COMMENT ON COLUMN products.price_cents IS 'Unit price in cents';

CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER     NOT NULL REFERENCES customers (id),
    status      TEXT        NOT NULL CHECK (
        status IN ('pending', 'paid', 'shipped', 'completed', 'cancelled')
    ),
    total_cents INTEGER     NOT NULL CHECK (total_cents >= 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE orders IS 'One row per checkout; total includes all items';
COMMENT ON COLUMN orders.status IS 'pending | paid | shipped | completed | cancelled';
COMMENT ON COLUMN orders.total_cents IS 'Order total in cents';

CREATE TABLE order_items (
    id               SERIAL PRIMARY KEY,
    order_id         INTEGER NOT NULL REFERENCES orders (id),
    product_id       INTEGER NOT NULL REFERENCES products (id),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0)
);
COMMENT ON TABLE order_items IS 'Line items belonging to an order';
COMMENT ON COLUMN order_items.unit_price_cents IS 'Price charged per unit at purchase time';

CREATE TABLE refunds (
    id           SERIAL PRIMARY KEY,
    order_id     INTEGER     NOT NULL REFERENCES orders (id),
    amount_cents INTEGER     NOT NULL CHECK (amount_cents >= 0),
    reason       TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE refunds IS 'Money returned against an order';
COMMENT ON COLUMN refunds.amount_cents IS 'Refunded amount in cents';

CREATE INDEX idx_orders_customer_id ON orders (customer_id);
CREATE INDEX idx_order_items_order_id ON order_items (order_id);
CREATE INDEX idx_order_items_product_id ON order_items (product_id);
CREATE INDEX idx_refunds_order_id ON refunds (order_id);

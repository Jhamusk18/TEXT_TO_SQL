"""Generates db/init/02_seed.sql deterministically.

Order totals are computed from their line items, and the script prints the
aggregate answers for the bundled demo questions — the offline fixture rows
in `text_to_sql_engine/demo_data.py` are copied from this output, so the
offline demo and the live docker-compose database agree.

Usage: python scripts/generate_seed.py
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

CUSTOMERS: list[tuple[str, str, str, str]] = [
    ("Alice Hartman", "alice.hartman@example.com", "US", "2025-08-03"),
    ("Benjamin Cole", "ben.cole@example.com", "US", "2025-08-11"),
    ("Carmen Diaz", "carmen.diaz@example.com", "US", "2025-08-25"),
    ("Derek Olson", "derek.olson@example.com", "US", "2025-09-02"),
    ("Emily Tran", "emily.tran@example.com", "CA", "2025-09-14"),
    ("Felix Moreau", "felix.moreau@example.com", "CA", "2025-09-29"),
    ("Grace Whitfield", "grace.whitfield@example.com", "GB", "2025-10-06"),
    ("Harry Pemberton", "harry.pemberton@example.com", "GB", "2025-10-18"),
    ("Ingrid Bauer", "ingrid.bauer@example.com", "DE", "2025-11-01"),
    ("Jonas Keller", "jonas.keller@example.com", "DE", "2025-11-12"),
    ("Katrina Reyes", "katrina.reyes@example.com", "PH", "2025-11-23"),
    ("Luis Santos", "luis.santos@example.com", "PH", "2025-12-04"),
]

PRODUCTS: list[tuple[str, str, int]] = [
    ("Wireless Earbuds Pro", "electronics", 12900),
    ("4K Action Camera", "electronics", 54900),
    ("Smart Home Hub", "electronics", 9900),
    ("Espresso Grinder", "home", 18900),
    ("Cast Iron Skillet", "home", 4500),
    ("Air Purifier", "home", 24900),
    ("Carbon Bike Helmet", "sports", 14500),
    ("Trail Running Shoes", "sports", 11900),
    ("Yoga Mat Premium", "sports", 6900),
    ("Data Engineering Handbook", "books", 5400),
    ("SQL Performance Explained", "books", 4900),
    ("The Pragmatic Analyst", "books", 3900),
]

STATUSES = (
    ["completed"] * 11 + ["shipped"] * 7 + ["paid"] * 5 + ["pending"] * 4 + ["cancelled"] * 3
)

ORDER_DATES = [f"2025-{9 + i % 4:02d}-{(3 * i) % 27 + 1:02d}" for i in range(16)] + [
    f"2026-{1 + i % 5:02d}-{(5 * i) % 27 + 1:02d}" for i in range(14)
]

# Refund targets are all completed/shipped orders — no refunds on unpaid carts.
REFUNDS: list[tuple[int, float, str, str]] = [
    (3, 1.0, "damaged in transit", "2026-01-08"),
    (6, 0.5, "wrong item shipped", "2026-01-21"),
    (9, 1.0, "changed mind", "2026-02-03"),
    (12, 0.25, "late delivery", "2026-02-19"),
    (15, 1.0, "damaged in transit", "2026-03-07"),
    (20, 0.5, "changed mind", "2026-04-15"),
]


def main() -> None:
    orders: list[tuple[int, int, str, str]] = []  # id, customer_id, status, date
    items: list[tuple[int, int, int, int, int]] = []  # id, order_id, product_id, qty, unit price
    item_id = 1
    for order_id in range(1, 31):
        customer_id = (order_id * 7) % len(CUSTOMERS) + 1
        status = STATUSES[(order_id * 11) % len(STATUSES)]
        date = ORDER_DATES[order_id - 1]
        orders.append((order_id, customer_id, status, date))
        for j in range(1 + (order_id % 3)):
            product_id = (order_id * 5 + j * 3) % len(PRODUCTS) + 1
            quantity = 1 + (order_id + j) % 3
            unit_price = PRODUCTS[product_id - 1][2]
            items.append((item_id, order_id, product_id, quantity, unit_price))
            item_id += 1

    totals = defaultdict(int)
    for _iid, order_id, _pid, quantity, unit_price in items:
        totals[order_id] += quantity * unit_price

    lines = ["-- Do not edit by hand; regenerate with scripts/generate_seed.py.", ""]
    for i, (name, email, country, created) in enumerate(CUSTOMERS, start=1):
        lines.append(
            "INSERT INTO customers (id, email, full_name, country, created_at) VALUES "
            f"({i}, '{email}', '{name}', '{country}', '{created}');"
        )
    lines.append("")
    for i, (name, category, price) in enumerate(PRODUCTS, start=1):
        lines.append(
            "INSERT INTO products (id, name, category, price_cents, created_at) VALUES "
            f"({i}, '{name}', '{category}', {price}, '2025-07-01');"
        )
    lines.append("")
    for order_id, customer_id, status, date in orders:
        lines.append(
            "INSERT INTO orders (id, customer_id, status, total_cents, created_at) VALUES "
            f"({order_id}, {customer_id}, '{status}', {totals[order_id]}, '{date}');"
        )
    lines.append("")
    for iid, order_id, product_id, quantity, unit_price in items:
        lines.append(
            "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price_cents) "
            f"VALUES ({iid}, {order_id}, {product_id}, {quantity}, {unit_price});"
        )
    lines.append("")
    for i, (order_id, fraction, reason, date) in enumerate(REFUNDS, start=1):
        amount = int(totals[order_id] * fraction)
        lines.append(
            "INSERT INTO refunds (id, order_id, amount_cents, reason, created_at) VALUES "
            f"({i}, {order_id}, {amount}, '{reason}', '{date}');"
        )
    lines.append("")
    for table in ("customers", "products", "orders", "order_items", "refunds"):
        lines.append(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"(SELECT max(id) FROM {table}));"
        )
    lines.append("")

    out = Path(__file__).resolve().parents[1] / "db" / "init" / "02_seed.sql"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"wrote {out} ({len(orders)} orders, {len(items)} items)")

    _print_demo_answers(orders, items, totals)


def _print_demo_answers(
    orders: list[tuple[int, int, str, str]],
    items: list[tuple[int, int, int, int, int]],
    totals: dict[int, int],
) -> None:
    """Compute the answers to the bundled demo questions from the seed data."""
    revenue: defaultdict[int, int] = defaultdict(int)
    for _iid, _oid, product_id, quantity, unit_price in items:
        revenue[product_id] += quantity * unit_price
    top5 = sorted(revenue.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    print("\nTop 5 products by revenue:")
    for product_id, cents in top5:
        print(f"  {PRODUCTS[product_id - 1][0]!r}: {cents}")

    by_status: defaultdict[str, int] = defaultdict(int)
    for _oid, _cid, status, _date in orders:
        by_status[status] += 1
    print("\nOrders per status:", dict(sorted(by_status.items(), key=lambda kv: -kv[1])))

    spend_by_country: defaultdict[str, list[int]] = defaultdict(list)
    for order_id, customer_id, _status, _date in orders:
        country = CUSTOMERS[customer_id - 1][2]
        spend_by_country[country].append(totals[order_id])
    print("\nAverage order value by country:")
    for country, values in sorted(
        spend_by_country.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])
    ):
        print(f"  {country}: {sum(values) / len(values):.2f} over {len(values)} orders")

    print("\nTotal spend per country:")
    for country, values in sorted(spend_by_country.items(), key=lambda kv: -sum(kv[1])):
        print(f"  {country}: {sum(values)}")

    spend_by_customer: defaultdict[int, int] = defaultdict(int)
    for order_id, customer_id, _status, _date in orders:
        spend_by_customer[customer_id] += totals[order_id]
    top3 = sorted(spend_by_customer.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    print("\nTop 3 customers by total spend:")
    for customer_id, cents in top3:
        print(f"  {CUSTOMERS[customer_id - 1][0]!r}: {cents}")

    status_by_order = {oid: status for oid, _cid, status, _date in orders}
    print("\nRefunds (most recent first):")
    for i, (order_id, fraction, reason, date) in sorted(
        enumerate(REFUNDS, start=1), key=lambda pair: pair[1][3], reverse=True
    ):
        amount = int(totals[order_id] * fraction)
        print(f"  id={i} order={order_id} amount={amount} reason={reason!r} "
              f"status={status_by_order[order_id]!r} date={date}")


if __name__ == "__main__":
    main()

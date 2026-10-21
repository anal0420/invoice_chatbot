from db import get_connection

SCHEMA_SQL = """
DROP TABLE IF EXISTS invoice_embeddings, invoice_items, invoices CASCADE;

CREATE TABLE invoices (
    invoice_id      SERIAL PRIMARY KEY,
    invoice_number  TEXT UNIQUE NOT NULL,
    customer_id     TEXT,
    customer_name   TEXT NOT NULL,
    industry        TEXT,
    billing_city    TEXT,
    billing_state   TEXT,
    invoice_date    DATE,
    due_date        DATE,
    status          TEXT,
    terms           TEXT,
    subtotal        NUMERIC(12,2),
    discount        NUMERIC(12,2) DEFAULT 0,
    tax_amount      NUMERIC(12,2),
    total_amount    NUMERIC(12,2),
    currency        TEXT DEFAULT 'USD',
    notes           TEXT,
    source_file     TEXT,
    doc_type        TEXT DEFAULT 'INVOICE',
    data_flag       TEXT
);

CREATE TABLE invoice_items (
    item_id      SERIAL PRIMARY KEY,
    invoice_id   INT REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    sku          TEXT,
    description  TEXT,
    quantity     NUMERIC(10,2),
    unit_price   NUMERIC(12,2),
    line_total   NUMERIC(12,2)
);
"""

def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' ORDER BY table_name;
            """)
            tables = [row[0] for row in cur.fetchall()]
    print("Tables in database:", tables)

if __name__ == "__main__":
    main()
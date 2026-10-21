from db import get_connection

SQL = """
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS counts_as_revenue BOOLEAN DEFAULT TRUE;

UPDATE invoices SET counts_as_revenue = TRUE;

-- void and superseded invoices are not revenue
UPDATE invoices SET counts_as_revenue = FALSE
WHERE status IN ('VOID', 'SUPERSEDED');

-- credit memos are not invoices (they are subtracted separately as credits)
UPDATE invoices SET counts_as_revenue = FALSE
WHERE doc_type = 'CREDIT_MEMO';
"""

CHECK = """
SELECT counts_as_revenue, doc_type, COUNT(*), SUM(total_amount)
FROM invoices GROUP BY counts_as_revenue, doc_type ORDER BY 1, 2;
"""

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(SQL)
        cur.execute(CHECK)
        for row in cur.fetchall():
            print(row)
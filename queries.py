from decimal import Decimal
import pandas as pd
from db import get_connection

REV = "counts_as_revenue = TRUE"

QUERIES = {
    "kpis": f"""
        SELECT
         SUM(total_amount) FILTER (WHERE {REV}) AS revenue,
         COUNT(*) FILTER (WHERE {REV}) AS invoices,
         AVG(total_amount) FILTER (WHERE {REV}) AS avg_invoice,
         SUM(tax_amount) FILTER (WHERE {REV}) AS tax,
         SUM(discount) FILTER (WHERE {REV}) AS discounts,
         SUM(total_amount) FILTER (WHERE doc_type='CREDIT_MEMO') AS credits,
         SUM(total_amount) FILTER (WHERE {REV} OR doc_type='CREDIT_MEMO') AS net_spend,
         SUM(total_amount) FILTER (WHERE {REV} AND status IN ('OPEN','PARTIAL')) AS unpaid,
         COUNT(*) FILTER (WHERE {REV} AND status IN ('OPEN','PARTIAL')
                          AND due_date < CURRENT_DATE) AS overdue
        FROM invoices""",
    "monthly": f"""
        SELECT TO_CHAR(DATE_TRUNC('month', invoice_date),'YYYY-MM') AS month,
               SUM(total_amount) AS revenue
        FROM invoices WHERE {REV} GROUP BY 1 ORDER BY 1""",
    "top_customers": f"""
        SELECT customer_name, SUM(total_amount) AS revenue
        FROM invoices WHERE {REV} GROUP BY 1 ORDER BY 2 DESC LIMIT 10""",
    "industry": f"""
        SELECT industry, SUM(total_amount) AS revenue
        FROM invoices WHERE {REV} GROUP BY 1 ORDER BY 2 DESC""",
    "status": f"""
        SELECT status, COUNT(*) AS invoices, SUM(total_amount) AS amount
        FROM invoices WHERE {REV} GROUP BY 1 ORDER BY 3 DESC""",
    "tax_month": f"""
        SELECT TO_CHAR(DATE_TRUNC('month', invoice_date),'YYYY-MM') AS month,
               SUM(tax_amount) AS tax
        FROM invoices WHERE {REV} GROUP BY 1 ORDER BY 1""",
    "tax_state": f"""
        SELECT billing_state, SUM(tax_amount) AS tax
        FROM invoices WHERE {REV} GROUP BY 1 ORDER BY 2 DESC""",
    "distribution": f"SELECT total_amount FROM invoices WHERE {REV}",
    "sku": f"""
        SELECT i.sku, SUM(i.line_total) AS revenue
        FROM invoice_items i JOIN invoices v USING (invoice_id)
        WHERE v.{REV} GROUP BY 1 ORDER BY 2 DESC""",
    "outliers": f"""
        SELECT invoice_number, customer_name, total_amount FROM invoices
        WHERE {REV} AND total_amount >
          (SELECT AVG(total_amount) + 2*STDDEV(total_amount) FROM invoices WHERE {REV})
        ORDER BY 3 DESC""",
    "flagged": """
        SELECT invoice_number, customer_name, data_flag
        FROM invoices WHERE data_flag IS NOT NULL ORDER BY 1""",
    "excluded": """
        SELECT invoice_number, status, total_amount FROM invoices
        WHERE counts_as_revenue = FALSE ORDER BY 1""",
}


def get_df(sql):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    finally:
        conn.close()
    df = pd.DataFrame(rows, columns=cols)
    for c in df.columns:
        if df[c].map(lambda v: isinstance(v, Decimal)).any():
            df[c] = df[c].astype(float)
    return df


def q(name):
    return get_df(QUERIES[name])
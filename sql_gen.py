import sys
import re
import ollama

MODEL = "qwen2.5-coder:3b"

SCHEMA_PROMPT = """You write PostgreSQL queries. Reply with ONE SQL query only, no explanation.

Tables:
invoices(invoice_id, invoice_number, customer_id, customer_name, industry,
         billing_city, billing_state, invoice_date DATE, due_date DATE,
         status, terms, subtotal, discount, tax_amount, total_amount,
         currency, notes, source_file, doc_type, data_flag, counts_as_revenue BOOLEAN)
invoice_items(item_id, invoice_id, sku, description, quantity, unit_price, line_total)

Rules:
- status values: OPEN, PAID, PARTIAL, CREDIT, VOID, SUPERSEDED
- doc_type values: INVOICE, CREDIT_MEMO
- For revenue, totals, counts or rankings of invoices, ALWAYS add: WHERE counts_as_revenue = TRUE
- Credit memos have negative total_amount. Net spend = SUM(total_amount) WHERE counts_as_revenue = TRUE OR doc_type = 'CREDIT_MEMO'.
- invoice_items joins to invoices on invoice_id. For item/SKU revenue use SUM(line_total) and also filter invoices.counts_as_revenue = TRUE.
- "Overdue" means: counts_as_revenue = TRUE AND status IN ('OPEN', 'PARTIAL') AND due_date < CURRENT_DATE.
- "Unpaid" or "pending" or "outstanding" means ONLY: counts_as_revenue = TRUE AND status IN ('OPEN', 'PARTIAL'). Do NOT add any due_date condition.
- "Paid" means status = 'PAID'.
- "Per month" or "trend": use DATE_TRUNC('month', invoice_date) AS month, ORDER BY month.
- If a chart is requested, return exactly two columns: label first, numeric value second.
- Only write SELECT queries.
"""


def extract_sql(text):
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    sql = m.group(1) if m else text
    return sql.strip().rstrip(";") + ";"


def question_to_sql(question):
    resp = ollama.chat(
        model=MODEL,
        messages=[{"role": "system", "content": SCHEMA_PROMPT},
                  {"role": "user", "content": question}],
        options={"temperature": 0},
    )
    return extract_sql(resp["message"]["content"])


if __name__ == "__main__":
    print(question_to_sql(" ".join(sys.argv[1:])))
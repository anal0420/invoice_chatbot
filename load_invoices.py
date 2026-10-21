import sys
import glob
import os
from db import get_connection
from extract_invoice import parse_invoice, check_invoice

INVOICE_COLS = [
    "invoice_number", "customer_id", "customer_name", "industry",
    "billing_city", "billing_state", "invoice_date", "due_date",
    "status", "terms", "subtotal", "discount", "tax_amount",
    "total_amount", "notes", "source_file", "doc_type", "data_flag",
]


def insert_invoice(cur, inv):
    placeholders = ", ".join(["%s"] * len(INVOICE_COLS))
    cur.execute(
        f"INSERT INTO invoices ({', '.join(INVOICE_COLS)}) "
        f"VALUES ({placeholders}) RETURNING invoice_id",
        [inv[c] for c in INVOICE_COLS],
    )
    invoice_id = cur.fetchone()[0]
    for it in inv["items"]:
        cur.execute(
            "INSERT INTO invoice_items "
            "(invoice_id, sku, description, quantity, unit_price, line_total) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (invoice_id, it["sku"], it["description"],
             it["quantity"], it["unit_price"], it["line_total"]),
        )


def main(folder):
    files = sorted(glob.glob(os.path.join(folder, "*.pdf")))
    print(f"Found {len(files)} PDF files")

    loaded, failed = 0, []
    conn = get_connection()
    try:
        for path in files:
            name = os.path.basename(path)
            try:
                inv = parse_invoice(path)
                hard, soft = check_invoice(inv)
                if hard:
                    failed.append((name, "CHECK FAILED: " + "; ".join(hard)))
                    continue
                inv["data_flag"] = "; ".join(soft) if soft else None
                with conn.cursor() as cur:
                    insert_invoice(cur, inv)
                conn.commit()
                loaded += 1
            except Exception as e:
                conn.rollback()
                reason = str(e).strip().splitlines()[0]
                failed.append((name, f"ERROR: {reason}"))
    finally:
        conn.close()

    print(f"Loaded: {loaded}")
    print(f"Failed: {len(failed)}")
    if failed:
        with open("failed_invoices.txt", "w", encoding="utf-8") as f:
            for name, reason in failed:
                f.write(f"{name}: {reason}\n")
        print("Details saved to failed_invoices.txt")


if __name__ == "__main__":
    main(sys.argv[1])
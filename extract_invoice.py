import re
import sys
from decimal import Decimal
import pdfplumber

LABELS = ("Subtotal", "Discount", "Tax", "Total", "Notes", "Status",
          "Billing", "Invoice", "Customer", "SKU")
AMT = r"(\$-?[\d,.]+)"

KNOWN_NOTES = [
    "Services accepted by client operations lead.",
    "PO number appears in email thread.",
]


def money(text):
    """'$28,032.23' -> Decimal; '$-1480.00' -> Decimal('-1480.00')"""
    return Decimal(text.replace("$", "").replace(",", ""))


def clean_text(raw):
    """Remove watermark letters from extracted page text."""
    cleaned = []
    for line in raw.splitlines():
        line = line.strip()
        if re.fullmatch(r"[A-Z]", line):
            continue
        # letter glued in front of a label: "KSubtotal" -> "Subtotal"
        line = re.sub(r"^[A-Z](?=(?:%s))" % "|".join(LABELS), "", line)
        # letter + space before a capitalised word: "H Subtotal"
        line = re.sub(r"^[A-Z] (?=[A-Z][a-z])", "", line)
        # letter glued to the end of a word: "spendC"
        line = re.sub(r"(?<=[a-z])[A-Z]$", "", line)
        # letter glued to a word before punctuation: "spendC," -> "spend,"
        line = re.sub(r"(?<=[a-z])[A-Z](?=[,.;:])", "", line)
        # letter glued to a quantity: "packet C1 $2150" -> "packet 1 $2150"
        line = re.sub(r" [A-Z](?=\d+ \$)", " ", line)
        cleaned.append(line)
    return "\n".join(cleaned)


def fix_notes(notes):
    """Repair watermark letters inside notes text."""
    if not notes:
        return notes
    # compare letters only (ignore case/spacing) against the known sentences
    squeezed = re.sub(r"[^a-z]", "", notes.lower())
    for known in KNOWN_NOTES:
        if squeezed == re.sub(r"[^a-z]", "", known.lower()):
            return known
    # otherwise remove a capital sitting inside a lowercase word
    notes = re.sub(r"(?<=[a-z])[A-Z](?=[a-z])", "", notes)
    return notes


def parse_invoice(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        raw = pdf.pages[0].extract_text()
    text = clean_text(raw)
    source_file = pdf_path.replace("\\", "/").split("/")[-1]

    def find(pattern):
        m = re.search(pattern, text)
        if not m:
            raise ValueError(f"Pattern not found: {pattern}")
        return m

    inv = {}
    # Fix A: allow a revision suffix such as -R1
    m = find(r"(?:INVOICE|CREDIT MEMO)\s+((?:INV|CM)-\d{4}-\d+(?:-R\d+)?)")
    inv["invoice_number"] = m.group(1)
    inv["doc_type"] = "CREDIT_MEMO" if m.group(1).startswith("CM-") else "INVOICE"

    m = find(r"Customer (.+?) Customer ID (\S+)")
    inv["customer_name"], inv["customer_id"] = m.group(1), m.group(2)

    m = find(r"Invoice Date (\d{4}-\d{2}-\d{2}) Due Date (\d{4}-\d{2}-\d{2})")
    inv["invoice_date"], inv["due_date"] = m.group(1), m.group(2)

    m = find(r"Status (\S+) Terms (.+)")
    inv["status"], inv["terms"] = m.group(1), m.group(2).strip()

    m = find(r"Billing City (.+?), ([A-Z]{2}) Industry (.+)")
    inv["billing_city"] = m.group(1)
    inv["billing_state"] = m.group(2)
    inv["industry"] = m.group(3).strip()

    inv["subtotal"] = money(find(r"Subtotal " + AMT).group(1))
    inv["discount"] = money(find(r"Discount " + AMT).group(1))
    inv["tax_amount"] = money(find(r"Tax " + AMT).group(1))
    inv["total_amount"] = money(find(r"(?<![a-z])Total " + AMT).group(1))

    # Fix B: clean the notes text
    m = re.search(r"Notes:\s*(.+)", text)
    inv["notes"] = fix_notes(m.group(1).strip()) if m else None
    inv["source_file"] = source_file

    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("SKU Description")) + 1
    end = next(i for i, l in enumerate(lines) if l.startswith("Subtotal"))
    item_re = re.compile(r"^(\S+) (.+?) (\d+(?:\.\d+)?) " + AMT + " " + AMT + "$")

    items = []
    for line in lines[start:end]:
        m = item_re.match(line)
        if m:
            items.append({
                "sku": m.group(1),
                "description": m.group(2),
                "quantity": Decimal(m.group(3)),
                "unit_price": money(m.group(4)),
                "line_total": money(m.group(5)),
            })
        else:
            # Fix C: show which file has the unparseable line
            print(f"  WARNING ({source_file}): could not parse line: {line}")
    inv["items"] = items
    return inv


def check_invoice(inv):
    """Return (hard_problems, soft_flags).
    hard = we probably misread the page (reject)
    soft = the invoice itself has a data problem (load and flag)"""
    hard, soft = [], []
    items_sum = sum(i["line_total"] for i in inv["items"])
    if items_sum != inv["subtotal"]:
        hard.append(f"items sum {items_sum} != subtotal {inv['subtotal']}")
    if inv["subtotal"] - inv["discount"] + inv["tax_amount"] != inv["total_amount"]:
        hard.append("subtotal-discount+tax != total")
    for i in inv["items"]:
        if i["quantity"] * i["unit_price"] != i["line_total"]:
            soft.append(f"LINE_MISMATCH:{i['sku']}")
    return hard, soft


if __name__ == "__main__":
    inv = parse_invoice(sys.argv[1])
    for k, v in inv.items():
        if k != "items":
            print(f"{k:15}: {v}")
    print("items:")
    for i in inv["items"]:
        print("  ", i)
    hard, soft = check_invoice(inv)
    print("\nHARD:", hard or "none", "| FLAGS:", soft or "none")
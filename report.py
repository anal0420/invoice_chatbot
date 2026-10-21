import re
import ollama
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from queries import q
from sql_gen import MODEL

styles = getSampleStyleSheet()


def narrate(task, facts):
    prompt = (f"{task}\nFacts (exact, do not change or add numbers):\n{facts}\n"
              "Write 3-4 plain sentences. No markdown, no bullet symbols.")
    try:
        r = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}],
                        options={"temperature": 0})
        return re.sub(r"[*#`]", "", r["message"]["content"]).strip().replace("\n", "<br/>")
    except Exception:
        return facts.replace("\n", "<br/>")


def table(df, max_rows=12):
    data = [list(df.columns)]
    for row in df.head(max_rows).values.tolist():
        data.append([f"{v:,.2f}" if isinstance(v, float) else str(v) for v in row])
    t = Table(data, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#244c3a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    return t


def chart(df, x, y, path, kind="bar"):
    plt.figure(figsize=(6.5, 3))
    if kind == "line":
        plt.plot(df[x], df[y], marker="o")
    else:
        plt.bar(df[x], df[y])
    plt.xticks(rotation=45, ha="right", fontsize=7)
    plt.tight_layout()
    plt.savefig(path, dpi=130)
    plt.close()
    return Image(path, width=16 * cm, height=7.4 * cm)


def build_report(path="invoice_report.pdf"):
    k = q("kpis").iloc[0]
    monthly, top = q("monthly"), q("top_customers")
    flagged, excluded, outliers = q("flagged"), q("excluded"), q("outliers")
    S = []
    h = lambda t: S.extend([Spacer(1, 10), Paragraph(t, styles["Heading2"])])

    S.append(Paragraph("Invoice Analysis Report", styles["Title"]))

    kfacts = (f"Revenue ${k.revenue:,.2f} from {int(k.invoices)} invoices; average invoice ${k.avg_invoice:,.2f}; "
              f"tax ${k.tax:,.2f}; discounts ${k.discounts:,.2f}; credit memos ${k.credits:,.2f}; "
              f"net spend ${k.net_spend:,.2f}; unpaid ${k.unpaid:,.2f}; overdue invoices {int(k.overdue)}.")
    h("1. Executive summary")
    S.append(Paragraph(narrate("Summarize these invoice results for management.", kfacts), styles["BodyText"]))

    h("2. Key metrics")
    S.append(table(k.to_frame("value").reset_index().rename(columns={"index": "metric"})))

    h("3. Customer analysis")
    S.append(chart(top, "customer_name", "revenue", "c_top.png"))
    S.append(Paragraph(narrate("Comment on customer concentration.",
             top.head(5).to_string(index=False)), styles["BodyText"]))
    S.append(table(top))

    h("4. Trends")
    S.append(chart(monthly, "month", "revenue", "c_month.png", "line"))
    best = monthly.loc[monthly.revenue.idxmax()]
    S.append(Paragraph(narrate("Comment on the monthly revenue trend.",
             f"Highest month {best.month} at ${best.revenue:,.2f}.\n" + monthly.to_string(index=False)),
             styles["BodyText"]))

    h("5. Anomalies and risks")
    S.append(Paragraph(f"{len(flagged)} invoices have a line amount that does not equal qty x unit price. "
                       f"{len(excluded)} documents are excluded from revenue (void, superseded, credit memos). "
                       f"{len(outliers)} invoices are unusually large.", styles["BodyText"]))
    for name, df in (("Line mismatches", flagged), ("Excluded documents", excluded), ("Outliers", outliers)):
        if len(df):
            S.append(Paragraph(name, styles["Heading4"]))
            S.append(table(df))

    h("6. Recommendations")
    S.append(Paragraph(narrate("Give practical recommendations about collections, billing errors and customer risk.",
             kfacts + f" Line mismatches: {len(flagged)}."), styles["BodyText"]))

    SimpleDocTemplate(path, pagesize=A4).build(S)
    return path


if __name__ == "__main__":
    print("Saved", build_report())
import plotly.express as px
from queries import q


def dashboard():
    figs = {}
    figs["Monthly revenue trend"] = px.line(q("monthly"), x="month", y="revenue", markers=True)
    figs["Top customers"] = px.bar(q("top_customers"), x="customer_name", y="revenue")
    figs["Revenue by industry"] = px.pie(q("industry"), names="industry", values="revenue")
    figs["Invoice amount distribution"] = px.histogram(q("distribution"), x="total_amount", nbins=20)
    figs["Tax per month"] = px.bar(q("tax_month"), x="month", y="tax")
    figs["Tax by state"] = px.bar(q("tax_state"), x="billing_state", y="tax")
    figs["Status split"] = px.bar(q("status"), x="status", y="amount", text="invoices")
    out = q("outliers")
    if len(out):
        figs["Outlier invoices"] = px.bar(out, x="invoice_number", y="total_amount")
    return figs


def chat_chart(cols, rows, title=""):
    """Chart for a chat answer: first column = label, second = number."""
    import pandas as pd
    from decimal import Decimal
    if len(cols) < 2 or not rows:
        return None
    df = pd.DataFrame(rows, columns=cols)
    df[cols[1]] = df[cols[1]].map(lambda v: float(v) if isinstance(v, (Decimal, int, float)) else v)
    x, y = cols[0], cols[1]
    if any(k in x.lower() for k in ("month", "date", "year")):
        return px.line(df, x=x, y=y, markers=True, title=title)
    return px.bar(df, x=x, y=y, title=title)
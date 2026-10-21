import requests
import streamlit as st
import plotly.io as pio

API = "http://127.0.0.1:8000"
st.set_page_config(page_title="Invoice Chatbot", layout="wide")
st.title("Invoice Analysis Chatbot")

tab_chat, tab_dash, tab_report = st.tabs(["Chat", "Dashboard", "Report"])

with tab_chat:
    if "history" not in st.session_state:
        st.session_state.history = []
    for m in st.session_state.history:
        with st.chat_message(m["role"]):
            st.write(m["text"])
            if m.get("chart"):
                st.plotly_chart(pio.from_json(m["chart"]), use_container_width=True)
            if m.get("sql"):
                with st.expander("SQL used"):
                    st.code(m["sql"], language="sql")
    question = st.chat_input("Ask about the invoices (add 'chart' to get a graph)")
    if question:
        st.session_state.history.append({"role": "user", "text": question})
        with st.spinner("Thinking..."):
            r = requests.post(f"{API}/chat", json={"question": question}, timeout=300).json()
        st.session_state.history.append({"role": "assistant", "text": r["answer"],
                                         "chart": r["chart"], "sql": r["sql"]})
        st.rerun()

with tab_dash:
    k = requests.get(f"{API}/kpis").json()
    c = st.columns(4)
    c[0].metric("Revenue", f"${k['revenue']:,.0f}")
    c[1].metric("Net spend", f"${k['net_spend']:,.0f}")
    c[2].metric("Unpaid", f"${k['unpaid']:,.0f}")
    c[3].metric("Overdue invoices", int(k["overdue"]))
    figs = requests.get(f"{API}/dashboard").json()
    cols = st.columns(2)
    for i, (name, js) in enumerate(figs.items()):
        with cols[i % 2]:
            st.subheader(name)
            st.plotly_chart(pio.from_json(js), use_container_width=True)

with tab_report:
    st.write("Generate the PDF report (about a minute, Qwen writes the wording).")
    if st.button("Generate report"):
        with st.spinner("Building report..."):
            pdf = requests.get(f"{API}/report", timeout=600).content
        st.download_button("Download PDF", pdf, "invoice_report.pdf", "application/pdf")
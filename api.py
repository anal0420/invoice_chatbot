import re
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from chatbot_core import ask
from charts import dashboard, chat_chart
from queries import q
from report import build_report

app = FastAPI()


class Chat(BaseModel):
    question: str


@app.post("/chat")
def chat(body: Chat):
    r = ask(body.question)
    fig = None
    if re.search(r"chart|plot|graph|visuali|trend", body.question, re.I) and r["rows"]:
        f = chat_chart(r["cols"], r["rows"], body.question)
        fig = f.to_json() if f else None
    return {"answer": r["answer"], "sql": r["sql"],
            "cols": r["cols"], "rows": [[str(c) for c in row] for row in r["rows"][:50]],
            "chart": fig}


@app.get("/kpis")
def kpis():
    return q("kpis").iloc[0].to_dict()


@app.get("/dashboard")
def dash():
    return {name: fig.to_json() for name, fig in dashboard().items()}


@app.get("/report")
def report():
    return FileResponse(build_report(), media_type="application/pdf", filename="invoice_report.pdf")
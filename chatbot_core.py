import re
import sys
import ollama
from db import get_connection
from sql_gen import question_to_sql, MODEL

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy)\b", re.I)


def is_safe(sql):
    body = sql.strip().rstrip(";")
    if ";" in body:
        return False
    if not body.lower().startswith(("select", "with")):
        return False
    return not FORBIDDEN.search(body)


def run_sql(sql):
    conn = get_connection()
    try:
        conn.set_session(readonly=True)
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        return cols, rows
    finally:
        conn.close()


def explain(question, cols, rows):
    prompt = (
        f"Question: {question}\nColumns: {cols}\nRows (exact, from the database): {rows[:20]}\n"
        "Answer in 1-3 sentences using ONLY these numbers. Do not calculate or invent anything."
    )
    resp = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}],
                       options={"temperature": 0})
    return resp["message"]["content"].strip()


def ask(question):
    """Returns dict: answer, sql, cols, rows"""
    sql = question_to_sql(question)
    out = {"answer": "", "sql": sql, "cols": [], "rows": []}
    if not is_safe(sql):
        out["answer"] = "Blocked: only a single SELECT query is allowed."
        return out
    try:
        cols, rows = run_sql(sql)
    except Exception as e:
        out["answer"] = f"SQL error: {str(e).splitlines()[0]}"
        return out
    out["cols"], out["rows"] = cols, rows
    out["answer"] = explain(question, cols, rows) if rows else "No matching data."
    return out


if __name__ == "__main__":
    r = ask(" ".join(sys.argv[1:]))
    print("SQL:", r["sql"])
    print(r["answer"])
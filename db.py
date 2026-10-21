import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "invoice_chatbot",
    "user": "postgres",
    "password": "Anal!@20062003"
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

if __name__ == "__main__":
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            print(cur.fetchone()[0])
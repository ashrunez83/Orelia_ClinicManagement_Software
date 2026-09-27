# CS 499 Enhancement:
# Centralizes PostgreSQL connection and query execution in a dedicated
# database layer, reducing duplicated database code and separating
# data-access responsibilities from API routing and business logic.

import psycopg2

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

def get_db_connection():
    missing = [
        name for name, value in {
            "DB_HOST": DB_HOST,
            "DB_PORT": DB_PORT,
            "DB_NAME": DB_NAME,
            "DB_USER": DB_USER,
            "DB_PASSWORD": DB_PASSWORD,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            f"Missing database environment variables: {', '.join(missing)}"
        )

    return psycopg2.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )

def execute_query(query, params=None, fetch=True):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(query, params or ())
        if fetch:
            result = cur.fetchall()
        else:
            result = None
        conn.commit()
        return result
    finally:
        cur.close()
        conn.close()

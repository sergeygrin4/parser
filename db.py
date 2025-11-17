# db.py
import os
import psycopg2
from psycopg2.extras import DictCursor

DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL")


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL не установлен")
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

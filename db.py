# db.py
import os
import psycopg2
from psycopg2.extras import DictCursor

# Railway даёт либо DATABASE_URL, либо DATABASE_PUBLIC_URL
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")


def get_conn():
    """
    Возвращает соединение с Postgres.
    Используется и миниаппой, и парсером.
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL не установлен в окружении")
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

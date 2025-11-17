# mini_app_bot.py
import os
import logging
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from psycopg2.errors import UniqueViolation

from db import get_conn

# ----------------- Логирование -----------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mini_app_bot")

# ----------------- Конфиг из ENV -----------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")
WEB_APP_URL = os.getenv("WEB_APP_URL", "http://localhost:8000")
SHARED_SECRET = os.getenv("SHARED_SECRET", "changeme")

PORT = int(os.getenv("PORT", 8080))

# ----------------- Flask -----------------

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)


# ----------------- БД: инициализация схемы -----------------

def init_db():
    """Инициализация таблиц в Postgres."""
    conn = get_conn()
    cur = conn.cursor()

    # Вакансии
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            group_name TEXT,
            text TEXT,
            link TEXT,
            content_hash TEXT UNIQUE,
            source_type TEXT DEFAULT 'facebook',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    # FB-группы
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fb_groups (
            id SERIAL PRIMARY KEY,
            group_id TEXT UNIQUE,
            group_name TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            added_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    # Индексы
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_content_hash
        ON jobs(content_hash);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_created_at
        ON jobs(created_at DESC);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_fb_groups_group_id
        ON fb_groups(group_id);
    """)

    conn.commit()
    conn.close()
    logger.info("База данных Postgres инициализирована")


# ----------------- Telegram-бот -----------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Это бот-парсер FB вакансий.\n"
        "Открой мини-апп, добавь группы и жди уведомлений ✨"
    )


async def run_bot():
    """Запуск Telegram-бота. ЭТО нужно вызывать в ГЛАВНОМ потоке (через asyncio.run)."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен, бот не будет запущен")
        return

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))

    logger.info("Запускаю Telegram-бота...")
    # Здесь мы уже в главном потоке, можно безопасно использовать run_polling
    await application.run_polling()


# ----------------- Flask endpoints -----------------

@app.route("/")
@app.route("/index.html")
def index():
    # Если фронт лежит в static/index.html
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/groups", methods=["GET"])
def get_groups():
    """Список отслеживаемых FB-групп."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, group_id, group_name, enabled, added_at
            FROM fb_groups
            ORDER BY added_at DESC;
        """)
        rows = cur.fetchall()
        conn.close()

        groups = []
        for row in rows:
            groups.append({
                "id": row["id"],
                "group_id": row["group_id"],
                "group_name": row["group_name"],
                "enabled": row["enabled"],
                "added_at": row["added_at"].isoformat() if row["added_at"] else None,
            })

        return jsonify({"groups": groups})
    except Exception as e:
        logger.error(f"Ошибка получения групп: {e}")
        return jsonify({"error": "db_error"}), 500


@app.route("/api/groups", methods=["POST"])
def add_group():
    """
    Добавление новой FB-группы.
    Ожидает JSON: { "group_id": "<url или id>", "group_name": "..." }
    """
    data = request.get_json(force=True)
    group_id = data.get("group_id")
    group_name = data.get("group_name") or group_id

    if not group_id:
        return jsonify({"error": "group_id is required"}), 400

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO fb_groups (group_id, group_name)
            VALUES (%s, %s)
            ON CONFLICT (group_id) DO UPDATE
              SET group_name = EXCLUDED.group_name
            RETURNING id, enabled, added_at;
            """,
            (group_id, group_name),
        )
        row = cur.fetchone()
        conn.commit()
        conn.close()

        group = {
            "id": row["id"],
            "group_id": group_id,
            "group_name": group_name,
            "enabled": row["enabled"],
            "added_at": row["added_at"].isoformat() if row["added_at"] else None,
        }

        return jsonify({"status": "success", "group": group})
    except Exception as e:
        logger.error(f"Ошибка добавления группы: {e}")
        return jsonify({"error": "db_error"}), 500


@app.route("/api/groups/<int:group_pk>", methods=["DELETE"])
def delete_group(group_pk: int):
    """Удаление группы по id (pk строки)."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM fb_groups WHERE id = %s;", (group_pk,))
        deleted = cur.rowcount
        conn.commit()
        conn.close()

        if deleted == 0:
            return jsonify({"error": "not_found"}), 404

        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Ошибка удаления группы: {e}")
        return jsonify({"error": "db_error"}), 500


@app.route("/api/groups/<int:group_pk>/toggle", methods=["POST"])
def toggle_group(group_pk: int):
    """Включить/выключить группу."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT enabled FROM fb_groups WHERE id = %s;", (group_pk,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "not_found"}), 404

        new_enabled = not row["enabled"]
        cur.execute(
            "UPDATE fb_groups SET enabled = %s WHERE id = %s;",
            (new_enabled, group_pk),
        )
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "enabled": new_enabled})
    except Exception as e:
        logger.error(f"Ошибка переключения группы: {e}")
        return jsonify({"error": "db_error"}), 500


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """
    Список вакансий для миниаппы.
    query param: limit (по умолчанию 50)
    """
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, group_name, text, link, created_at
            FROM jobs
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()

        jobs = []
        for row in rows:
            jobs.append({
                "id": row["id"],
                "group_name": row["group_name"],
                "text": row["text"],
                "link": row["link"],
                "created_at": row["created_at"].isoformat()
                if row["created_at"] else None,
            })

        return jsonify({"jobs": jobs})
    except Exception as e:
        logger.error(f"Ошибка получения вакансий: {e}")
        return jsonify({"error": "db_error"}), 500


@app.route("/post", methods=["POST"])
def receive_job():
    """
    Endpoint для fb_parser.
    Ожидает JSON:
    {
      "group_name": "...",
      "text": "...",
      "link": "...",
      "content_hash": "...",
      "source_type": "facebook"
    }
    """
    data = request.get_json(force=True)

    group_name = data.get("group_name")
    text = data.get("text")
    link = data.get("link")
    content_hash = data.get("content_hash")
    source_type = data.get("source_type", "facebook")

    if not text or not content_hash:
        return jsonify({"error": "missing fields"}), 400

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO jobs (group_name, text, link, content_hash, source_type)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (group_name, text, link, content_hash, source_type),
        )
        conn.commit()
        conn.close()
        logger.info(f"Новая вакансия сохранена: {group_name}")
        return jsonify({"status": "ok"})
    except UniqueViolation:
        conn.rollback()
        conn.close()
        logger.info("Дубликат вакансии, пропускаю")
        return jsonify({"status": "duplicate"})
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"Ошибка записи вакансии: {e}")
        return jsonify({"error": "db_error"}), 500


# ----------------- Запуск Flask (отдельная функция) -----------------

def run_flask():
    logger.info(f"Запуск Flask на порту {PORT}")
    logger.info(f"Web App URL: {WEB_APP_URL}")
    app.run(host="0.0.0.0", port=PORT, debug=False)

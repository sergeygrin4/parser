import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from threading import Thread
from datetime import datetime

from db import get_conn  # <— НОВОЕ
from psycopg2.errors import UniqueViolation  # <— для обработки дублей

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
MANAGER_CHAT_ID = os.getenv('MANAGER_CHAT_ID')
SHARED_SECRET = os.getenv('SHARED_SECRET', 'default-secret-key')
PORT = int(os.getenv('PORT', 8000))
WEB_APP_URL = os.getenv('WEB_APP_URL', 'http://localhost:8000')

app = Flask(__name__, static_folder='static')
CORS(app)

# Глобальная переменная для бота
bot_app = None

# Инициализация БД
def init_db():
    """Инициализация базы данных (Postgres)"""
    conn = get_conn()
    cur = conn.cursor()

    # Таблица вакансий
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

    # Таблица FB-групп
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_content_hash ON jobs(content_hash);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fb_groups_group_id ON fb_groups(group_id);")

    conn.commit()
    conn.close()
    logger.info("База данных Postgres инициализирована")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start с кнопкой для открытия мини-апа"""
    keyboard = {
        "inline_keyboard": [[
            {
                "text": "🔍 Открыть поиск вакансий",
                "web_app": {"url": f"{WEB_APP_URL}/index.html"}
            }
        ]]
    }
    
    await update.message.reply_text(
        "👋 Привет! Нажми на кнопку ниже, чтобы открыть поиск вакансий из Facebook:",
        reply_markup=keyboard
    )

async def send_telegram_message(chat_id: str, message: str):
    """Отправка сообщения через Telegram бота"""
    if bot_app and bot_app.bot:
        try:
            await bot_app.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False
    return False

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "fb-job-parser"})

@app.route('/post', methods=['POST'])
def post_job():
    """Endpoint для получения вакансий от FB парсера"""
    # Проверка секретного ключа
    secret = request.headers.get('X-SECRET')
    if secret != SHARED_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        import hashlib
        
        data = request.json
        group_name = data.get('chat_title', 'Неизвестная группа')
        text = data.get('text', '')
        link = data.get('link', '')
        source_type = data.get('source_type', 'facebook')
        
        # Создаем хеш для дедупликации
        content = f"{group_name}:{text[:200]}"
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Сохранение в БД с проверкой дубликатов
       from psycopg2.errors import UniqueViolation

@app.route('/post', methods=['POST'])
def post_job():
    ...
    # Сохранение в БД с проверкой дубликатов
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO jobs (group_name, text, link, content_hash, source_type)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (group_name, text, link, content_hash, source_type),
        )
        conn.commit()
    except UniqueViolation:
        conn.rollback()
        conn.close()
        logger.info(f"Дубликат пропущен: {group_name[:30]}...")
        return jsonify({"status": "duplicate", "message": "Job already exists"}), 200
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"Ошибка записи вакансии: {e}")
        return jsonify({"error": "DB error"}), 500

    conn.close()
        
        # Формирование сообщения для менеджера
        message = f"📘 <b>Новая вакансия из Facebook</b>\n\n"
        message += f"📢 Группа: {group_name}\n"
        message += f"📝 Текст: {text[:200]}{'...' if len(text) > 200 else ''}\n"
        if link:
            message += f"🔗 Ссылка: {link}\n"
        
        # Отправка сообщения
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            send_telegram_message(MANAGER_CHAT_ID, message)
        )
        loop.close()
        
        if result:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"error": "Failed to send message"}), 500
            
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Получение списка вакансий для мини-апа"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, group_name, text, link, created_at FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?',
            (limit, offset)
        )
        jobs = cursor.fetchall()
        
        cursor.execute('SELECT COUNT(*) FROM jobs')
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "jobs": [
                {
                    "id": job[0],
                    "group_name": job[1],
                    "text": job[2],
                    "link": job[3],
                    "created_at": job[4]
                }
                for job in jobs
            ],
            "total": total
        })
    except Exception as e:
        logger.error(f"Ошибка получения вакансий: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/groups', methods=['GET'])
def get_groups():
    """Получение списка отслеживаемых FB групп"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, group_id, group_name, enabled, added_at "
            "FROM fb_groups ORDER BY added_at DESC"
        )
        rows = cur.fetchall()
        conn.close()

        return jsonify({
            "groups": [
                {
                    "id": row["id"],
                    "group_id": row["group_id"],
                    "group_name": row["group_name"],
                    "enabled": row["enabled"],
                    "added_at": row["added_at"].isoformat() if row["added_at"] else None,
                }
                for row in rows
            ]
        })
    except Exception as e:
        logger.error(f"Ошибка получения групп: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/groups', methods=['POST'])
def add_group():
    """Добавление FB группы для отслеживания"""
    try:
        data = request.json
        group_id = data.get('group_id', '').strip()
        group_name = data.get('group_name', '').strip()
        
        if not group_id:
            return jsonify({"error": "Group ID is required"}), 400
        
        # Извлечение ID из URL если нужно
        import re
        # Если это ссылка на группу - извлекаем ID
        url_match = re.search(r'facebook\.com/groups/([^/?]+)', group_id)
        if url_match:
            group_id = url_match.group(1)
        
        # Если имя группы не указано, используем ID
        if not group_name:
            group_name = group_id
        
        conn = get_conn()
cur = conn.cursor()
try:
    cur.execute(
        "INSERT INTO fb_groups (group_id, group_name) VALUES (%s, %s) RETURNING id;",
        (group_id, group_name),
    )
    new_id = cur.fetchone()["id"]
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "group": {
            "id": new_id,
            "group_id": group_id,
            "group_name": group_name,
        }
    })
except UniqueViolation:
    conn.rollback()
    conn.close()
    return jsonify({"error": "Group already exists"}), 409

            
    except Exception as e:
        logger.error(f"Ошибка добавления группы: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """Удаление FB группы"""
    try:
conn = get_conn()
cur = conn.cursor()
cur.execute("DELETE FROM fb_groups WHERE id = %s", (group_id,))
conn.commit()
conn.close()

        
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Ошибка удаления группы: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/groups/<int:group_id>/toggle', methods=['POST'])
def toggle_group(group_id):
    """Включение/отключение группы"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT enabled FROM fb_groups WHERE id = ?', (group_id,))
        result = cursor.fetchone()
        
        if not result:
conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT enabled FROM fb_groups WHERE id = %s", (group_id,))
row = cur.fetchone()

if not row:
    conn.close()
    return jsonify({"error": "Group not found"}), 404

current = row["enabled"]
new_status = not current  # bool -> меняем true/false

cur.execute("UPDATE fb_groups SET enabled = %s WHERE id = %s", (new_status, group_id))
conn.commit()
conn.close()

        
        return jsonify({"status": "success", "enabled": bool(new_status)})
    except Exception as e:
        logger.error(f"Ошибка переключения группы: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def root():
    """Главная страница"""
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """Статические файлы"""
    return send_from_directory('static', path)

def run_flask():
    """Запуск Flask сервера"""
    app.run(host='0.0.0.0', port=PORT, debug=False)

async def run_bot():
    """Запуск Telegram бота"""
    global bot_app
    
    bot_app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков
    bot_app.add_handler(CommandHandler("start", start_command))
    
    # Запуск бота
    await bot_app.initialize()
    await bot_app.start()
    logger.info("Бот запущен")
    
    # Держим бота активным
    await bot_app.updater.start_polling()
    await asyncio.Event().wait()

def main():
    """Главная функция запуска"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен!")
        return
    
    if not MANAGER_CHAT_ID:
        logger.error("MANAGER_CHAT_ID не установлен!")
        return
    
    # Инициализация БД
    init_db()
    
    logger.info(f"Запуск FB Job Parser на порту {PORT}")
    logger.info(f"Web App URL: {WEB_APP_URL}")
    
    # Запуск Flask в отдельном потоке
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запуск бота
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Остановка сервера...")

if __name__ == '__main__':
    main()

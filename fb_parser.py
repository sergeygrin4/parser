import os
import logging
import requests
from db import get_conn
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fb_parser")

# Конфигурация
BOT_API = os.getenv("BOT_API", "http://localhost:8000/post")
SHARED_SECRET = os.getenv("SHARED_SECRET")
FB_COOKIES = os.getenv("FB_COOKIES", "")
KEYWORDS = os.getenv("JOB_KEYWORDS", "вакансия,работа,job,hiring").lower().split(",")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))
DB_PATH = os.getenv("DB_PATH", "jobs.db")

headers = {"X-SECRET": SHARED_SECRET, "Content-Type": "application/json"} if SHARED_SECRET else {"Content-Type": "application/json"}

def contains_keywords(text: str) -> bool:
    """Проверяет наличие ключевых слов"""
    if not text or not KEYWORDS:
        return True
    text_lower = text.lower()
    return any(keyword.strip() in text_lower for keyword in KEYWORDS)

def send_to_api(group_name: str, text: str, link: str = None):
    """Отправляет вакансию в API"""
    payload = {
        "chat_title": f"[FACEBOOK] {group_name}",
        "text": text,
        "link": link,
        "source_type": "facebook"
    }
    
    try:
        r = requests.post(BOT_API, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            log.info(f"✅ Отправлено: {group_name}")
            return True
        else:
            log.warning(f"API ошибка {r.status_code}: {r.text}")
            return False
    except Exception as e:
        log.error(f"Ошибка отправки в API: {e}")
        return False

def get_fb_groups_from_():
    """Получает список активных FB групп из базы данных"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT group_id, group_name FROM fb_groups WHERE enabled = 1')
        groups = cursor.fetchall()
        conn.close()
        return groups
    except Exception as e:
        log.error(f"Ошибка чтения групп из БД: {e}")
        return []

def parse_facebook_group(group_id: str, group_name: str = None):
    """Парсинг FB группы с авторизацией через cookies"""
    try:
        from facebook_scraper import get_posts
        
        if not group_name:
            group_name = group_id
        
        log.info(f"Парсинг FB группы: {group_name}")
        
        # Парсим cookies из переменной окружения
        cookies = {}
        if FB_COOKIES:
            # Формат: name1=value1; name2=value2
            for cookie in FB_COOKIES.split(';'):
                if '=' in cookie:
                    name, value = cookie.strip().split('=', 1)
                    cookies[name] = value
        
        if not cookies:
            log.warning("⚠️ FB_COOKIES не заданы, попытка парсинга без авторизации")
        
        # Получаем посты с cookies
        posts = get_posts(
            group=group_id,
            pages=1,
            cookies=cookies,
            options={
                "comments": False,
                "reactors": False,
                "allow_extra_requests": False
            }
        )
        
        count = 0
        for post in posts:
            try:
                text = post.get('text', '')
                post_id = post.get('post_id', '')
                time_posted = post.get('time')
                
                if not text:
                    continue
                
                # Проверяем свежесть (не старше 24 часов)
                if time_posted and isinstance(time_posted, datetime):
                    if datetime.now() - time_posted > timedelta(hours=24):
                        log.debug(f"Старый пост пропущен: {time_posted}")
                        continue
                
                # Проверяем ключевые слова
                if not contains_keywords(text):
                    log.debug(f"Нет ключевых слов: {text[:50]}")
                    continue
                
                # Формируем ссылку
                link = f"https://facebook.com/{post_id}" if post_id else None
                
                # Отправляем
                if send_to_api(group_name, text, link):
                    count += 1
                    
            except Exception as e:
                log.error(f"Ошибка обработки поста: {e}")
                continue
        
        log.info(f"✅ Обработано {count} постов из группы {group_name}")
        return count
        
    except Exception as e:
        log.error(f"Ошибка парсинга FB группы {group_id}: {e}")
        return 0

def main():
    """Главная функция"""
    log.info("🚀 Запуск Facebook парсера")
    log.info(f"API: {BOT_API}")
    log.info(f"Ключевые слова: {KEYWORDS}")
    log.info(f"Cookies: {'✅ Установлены' if FB_COOKIES else '❌ Не заданы'}")
    log.info(f"⏰ Интервал проверки: {CHECK_INTERVAL} минут")
    
    while True:
        try:
            log.info("🔄 Начинаю цикл парсинга...")
            
            # Получаем группы из БД
          def get_fb_groups_from_db():
    """Получает список активных FB групп из Postgres"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT group_id, group_name FROM fb_groups WHERE enabled = TRUE"
        )
        rows = cur.fetchall()
        conn.close()
        # Возвращаем список кортежей, как и раньше
        return [(row["group_id"], row["group_name"]) for row in rows]
    except Exception as e:
        log.error(f"Ошибка чтения групп из БД: {e}")
        return []

            
            if not groups:
                log.warning("⚠️ Нет активных FB групп в базе данных")
                log.info("💡 Добавьте группы через мини-апп или напрямую в БД")
            else:
                total = 0
                for group_id, group_name in groups:
                    count = parse_facebook_group(group_id, group_name)
                    total += count
                    # Небольшая задержка между запросами к FB
                    time.sleep(2)
                
                log.info(f"✅ Цикл завершен. Обработано {total} постов")
            
            log.info(f"⏳ Ожидание {CHECK_INTERVAL} минут до следующей проверки...")
            time.sleep(CHECK_INTERVAL * 60)
            
        except KeyboardInterrupt:
            log.info("⛔ Остановка парсера...")
            break
        except Exception as e:
            log.error(f"❌ Ошибка в основном цикле: {e}")
            log.info("⏳ Повтор через 1 минуту...")
            time.sleep(60)

if __name__ == "__main__":
    main()

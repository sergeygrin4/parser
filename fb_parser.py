# fb_parser.py
import os
import logging
import time
import hashlib

from facebook_scraper import get_posts

import requests

from db import get_conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - fb_parser - %(levelname)s - %(message)s",
)
log = logging.getLogger("fb_parser")

API_URL = os.getenv("BOT_API") or os.getenv(
    "PARSER_API_URL",  # на всякий случай альтернативное имя
    "http://localhost:8080/post",
)

CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))

JOB_KEYWORDS = [
    kw.strip().lower()
    for kw in os.getenv(
        "JOB_KEYWORDS",
        "вакансия,работа,job,hiring,remote,developer,программист,amazon",
    ).split(",")
    if kw.strip()
]

FB_COOKIES = os.getenv("FB_COOKIES", "")

PAGE_LIMIT = int(os.getenv("FB_PAGE_LIMIT", "5"))


# -------------- Вспомогательное --------------


def extract_group_id(group_link: str) -> str:
    """
    Из полного URL группы достаём её slug/id для facebook_scraper.
    Примеры:
      https://www.facebook.com/groups/ProjectAmazon -> ProjectAmazon
      https://www.facebook.com/groups/187743251645949/ -> 187743251645949
    Если пришёл уже slug/id — возвращаем как есть.
    """
    from urllib.parse import urlparse

    parsed = urlparse(group_link)
    parts = [p for p in parsed.path.split("/") if p]

    if "groups" in parts:
        idx = parts.index("groups")
        if len(parts) > idx + 1:
            return parts[idx + 1]

    return group_link


def get_fb_groups_from_db():
    """
    Читает активные группы из Postgres.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT group_id, group_name
            FROM fb_groups
            WHERE enabled = TRUE;
            """
        )
        rows = cur.fetchall()
        conn.close()
        groups = [(row["group_id"], row["group_name"]) for row in rows]
        if not groups:
            log.warning("⚠️ Нет активных FB групп в базе данных")
        return groups
    except Exception as e:
        log.error(f"Ошибка чтения групп из БД: {e}")
        return []


def make_content_hash(text: str, link: str) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8", errors="ignore"))
    h.update((link or "").encode("utf-8", errors="ignore"))
    return h.hexdigest()


def post_job_to_api(group_name: str, text: str, link: str):
    payload = {
        "group_name": group_name,
        "text": text,
        "link": link,
        "content_hash": make_content_hash(text, link),
        "source_type": "facebook",
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        if resp.status_code != 200:
            log.warning(f"API вернул {resp.status_code}: {resp.text}")
    except Exception as e:
        log.error(f"Ошибка отправки в API: {e}")


# -------------- Парсинг группы --------------


def parse_facebook_group(group_link: str, group_name: str) -> int:
    group_id = extract_group_id(group_link)
    log.info(f"Парсинг FB группы: {group_link} (id={group_id}, pages={PAGE_LIMIT})")

    cookies = None
    if FB_COOKIES:
        # facebook_scraper принимает либо dict, либо "raw" строку
        cookies = FB_COOKIES

    processed = 0

    try:
        for post in get_posts(
            group=group_id,
            pages=PAGE_LIMIT,
            cookies=cookies,
            options={"allow_extra_requests": True},
        ):
            text = (post.get("text") or "").strip()
            if not text:
                continue

            link = post.get("post_url") or post.get("link")

            lower = text.lower()
            if not any(kw in lower for kw in JOB_KEYWORDS):
                continue

            processed += 1
            log.info(
                f"🎯 Найден пост в {group_name}: "
                f"{text[:80].replace(chr(10), ' ')}..."
            )
            post_job_to_api(group_name, text, link)

    except Exception as e:
        log.error(f"Ошибка парсинга группы {group_link}: {e}")

    log.info(f"✅ Обработано {processed} постов из группы {group_link}")
    return processed


# -------------- Главный цикл --------------


def run_parser_loop():
    log.info("🚀 Запуск Facebook парсера")
    log.info(f"API: {API_URL}")
    log.info(f"Ключевые слова: {JOB_KEYWORDS}")
    log.info(f"Cookies: {'✅ Установлены' if FB_COOKIES else '⛔️ НЕ заданы'}")
    log.info(f"⏰ Интервал проверки: {CHECK_INTERVAL_MINUTES} минут")

    while True:
        log.info("🔄 Начинаю цикл парсинга...")
        groups = get_fb_groups_from_db()
        total_posts = 0

        for group_link, group_name in groups:
            total_posts += parse_facebook_group(group_link, group_name)
            time.sleep(2)  # небольшая пауза между группами

        log.info(f"✅ Цикл завершен. Обработано {total_posts} постов")
        log.info(f"⏳ Ожидание {CHECK_INTERVAL_MINUTES} минут до следующей проверки...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    run_parser_loop()

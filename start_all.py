# start_all.py
from threading import Thread
import logging

from mini_app_bot import init_db, run_flask, run_bot
from fb_parser import run_parser_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - starter - %(levelname)s - %(message)s",
)
log = logging.getLogger("starter")


def main():
    # 1. Инициализируем БД
    init_db()

    # 2. Flask в отдельном потоке
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    log.info("Flask запущен в фоне")

    # 3. Парсер в отдельном потоке
    parser_thread = Thread(target=run_parser_loop, daemon=True)
    parser_thread.start()
    log.info("FB parser запущен в фоне")

    # 4. В главном потоке — Telegram-бот
    run_bot()


if __name__ == "__main__":
    main()

# start_all.py
from threading import Thread
import logging

from mini_app_bot import main as run_web_and_bot, init_db
from fb_parser import run_parser_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - starter - %(levelname)s - %(message)s",
)
log = logging.getLogger("starter")


def main():
    # Инициализируем БД один раз
    init_db()

    # Запускаем парсер фоном
    parser_thread = Thread(target=run_parser_loop, daemon=True)
    parser_thread.start()
    log.info("FB parser запущен в фоне")

    # Запускаем Flask + Telegram-бота (блокирующий вызов)
    run_web_and_bot()


if __name__ == "__main__":
    main()

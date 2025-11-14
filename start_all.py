# start_all.py
from threading import Thread

from mini_app_bot import main as bot_main, init_db
from fb_parser import main as parser_main


def run_parser():
    # просто отдельный поток с бесконечным циклом парсера
    parser_main()


def main():
    # Чтобы точно были таблицы в БД до старта парсера
    init_db()

    # Стартуем парсер фоном
    parser_thread = Thread(target=run_parser, daemon=True)
    parser_thread.start()

    # Стартуем бота (он внутри поднимет Flask + polling)
    bot_main()


if __name__ == "__main__":
    main()

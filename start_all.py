import threading
import asyncio
from mini_app_bot import main as bot_main
from fb_parser import main as parser_main  # или как у тебя там точка входа

def run_bot():
    bot_main()

def run_parser():
    parser_main()

if __name__ == "__main__":
    t1 = threading.Thread(target=run_bot, daemon=True)
    t1.start()
    # парсер можно в этом же потоке или тоже в отдельном
    run_parser()

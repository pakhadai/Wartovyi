import os
import logging
from dotenv import load_dotenv

# Завантажуємо змінні оточення з .env файлу
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except (TypeError, ValueError):
    logging.critical("ПОМИЛКА: Перевірте, що ADMIN_ID вказано у файлі .env і є числом.")
    exit()

# Шлях до SQLite: локально за замовчуванням файл у робочій директорії; у Docker — BOT_DB_PATH=/data/...
DB_NAME = os.getenv("BOT_DB_PATH", "bot_database_v6.db")
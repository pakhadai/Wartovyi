import sqlite3

from bot.config import DB_NAME


def get_global_settings() -> dict:
    """Отримує глобальні налаштування бота з таблиці 'settings'."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings_db = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()

    return {
        "spam_threshold": int(settings_db.get("spam_threshold", 10)),
        "captcha_enabled": bool(int(settings_db.get("captcha_enabled", 1))),
        "spam_filter_enabled": bool(int(settings_db.get("spam_filter_enabled", 1))),
        "use_global_list": bool(int(settings_db.get("use_global_list", 1))),
        "use_custom_list": bool(int(settings_db.get("use_custom_list", 0))),
        "antiflood_enabled": bool(int(settings_db.get("antiflood_enabled", 1))),
        "antiflood_sensitivity": int(settings_db.get("antiflood_sensitivity", 5)),
    }


def set_global_setting(key: str, value):
    """Встановлює глобальне налаштування в таблиці 'settings'."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if isinstance(value, bool):
        value = "1" if value else "0"
    cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

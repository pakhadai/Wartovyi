import logging
import sqlite3

from bot.config import DB_NAME

from .stats import setup_stats_tables


def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS warnings (user_id INTEGER, chat_id INTEGER, warning_count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (user_id, chat_id))"
    )
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

    cursor.execute("CREATE TABLE IF NOT EXISTS spam_triggers (trigger TEXT PRIMARY KEY, score INTEGER NOT NULL)")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS group_spam_triggers (group_id INTEGER, trigger TEXT, score INTEGER, PRIMARY KEY (group_id, trigger))"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS group_whitelists (group_id INTEGER, trigger TEXT, PRIMARY KEY (group_id, trigger))"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS suggested_triggers (trigger TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 1, added_by INTEGER)"
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS group_settings (
            group_id INTEGER PRIMARY KEY, group_name TEXT, spam_threshold INTEGER DEFAULT 10,
            captcha_enabled INTEGER DEFAULT 1, spam_filter_enabled INTEGER DEFAULT 1,
            use_global_list INTEGER DEFAULT 1, use_custom_list INTEGER DEFAULT 1,
            antiflood_enabled INTEGER DEFAULT 1,
            antiflood_sensitivity INTEGER DEFAULT 5
        )
    """
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS group_admins (group_id INTEGER, user_id INTEGER, PRIMARY KEY (group_id, user_id))"
    )

    cursor.execute(
        """
            CREATE TABLE IF NOT EXISTS punishment_settings (
                group_id INTEGER NOT NULL,
                warning_level INTEGER NOT NULL,
                action TEXT NOT NULL,
                duration_minutes INTEGER DEFAULT 0,
                PRIMARY KEY (group_id, warning_level)
            )
        """
    )

    try:
        cursor.execute("ALTER TABLE group_settings ADD COLUMN use_global_list INTEGER DEFAULT 1")
        cursor.execute("ALTER TABLE group_settings ADD COLUMN use_custom_list INTEGER DEFAULT 1")
        logging.info("Міграція БД: Додано стовпці 'use_global_list' та 'use_custom_list'.")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE group_settings ADD COLUMN antiflood_enabled INTEGER DEFAULT 1")
        cursor.execute("ALTER TABLE group_settings ADD COLUMN antiflood_sensitivity INTEGER DEFAULT 5")
        logging.info("Міграція БД: Додано стовпці 'antiflood_enabled' та 'antiflood_sensitivity'.")
    except sqlite3.OperationalError:
        pass

    default_settings = {
        "spam_threshold": "10",
        "captcha_enabled": "1",
        "spam_filter_enabled": "1",
        "use_global_list": "1",
        "use_custom_list": "0",
        "antiflood_enabled": "1",
        "antiflood_sensitivity": "5",
    }
    for key, value in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

    initial_triggers = {
        "пиши в лс": 8,
        "пишите в лс": 8,
        "в лс": 5,
        "заработке": 4,
        "заработок": 4,
        "без вложений": 7,
        "крипта": 6,
        "криптовалюта": 6,
        "binance": 5,
        "арбитраж": 8,
        "p2p": 7,
        "ищу людей": 6,
        "пассивный доход": 6,
        "пропоную роботу": 7,
        "легкие деньги": 9,
        "схема заработка": 10,
    }
    cursor.executemany(
        "INSERT OR IGNORE INTO spam_triggers (trigger, score) VALUES (?, ?)", initial_triggers.items()
    )

    setup_stats_tables(conn, cursor)

    conn.commit()
    conn.close()
    logging.info(f"База даних '{DB_NAME}' успішно налаштована та оновлена.")

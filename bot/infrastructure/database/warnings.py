import sqlite3

from bot.config import DB_NAME


def add_warning(user_id: int, chat_id: int) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT warning_count FROM warnings WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    result = cursor.fetchone()
    new_count = (result[0] + 1) if result else 1
    cursor.execute(
        "REPLACE INTO warnings (user_id, chat_id, warning_count) VALUES (?, ?, ?)",
        (user_id, chat_id, new_count),
    )
    conn.commit()
    conn.close()
    return new_count


def reset_warnings(user_id: int, chat_id: int):
    """Скидає попередження для користувача в конкретному чаті."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM warnings WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

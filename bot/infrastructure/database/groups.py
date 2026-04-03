import logging
import sqlite3

from bot.config import ADMIN_ID, DB_NAME


def add_group_if_not_exists(group_id: int, group_name: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO group_settings (group_id, group_name) VALUES (?, ?)",
        (group_id, group_name),
    )
    conn.commit()
    conn.close()


def set_group_admin(group_id: int, user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM group_admins WHERE group_id = ?", (group_id,))
    cursor.execute("INSERT INTO group_admins (group_id, user_id) VALUES (?, ?)", (group_id, user_id))
    conn.commit()
    conn.close()


def is_group_admin(user_id: int, group_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM group_admins WHERE group_id = ? AND user_id = ?",
        (group_id, user_id),
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_user_chats(user_id: int) -> list:
    """Отримує список чатів, якими керує користувач."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if user_id == ADMIN_ID:
        cursor.execute("SELECT group_id, group_name FROM group_settings ORDER BY group_name")
    else:
        cursor.execute(
            """
            SELECT gs.group_id, gs.group_name
            FROM group_settings gs
            JOIN group_admins ga ON gs.group_id = ga.group_id
            WHERE ga.user_id = ?
            ORDER BY gs.group_name
        """,
            (user_id,),
        )

    rows = cursor.fetchall()
    logging.info(f"DB query for user {user_id} returned {len(rows)} rows.")
    chats = [{"id": row[0], "name": row[1]} for row in rows]
    conn.close()
    return chats


def get_group_admin_id(group_id: int) -> int or None:
    """Знаходить ID адміна бота для конкретної групи."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM group_admins WHERE group_id = ?", (group_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def delete_all_group_data(group_id: int):
    """Видаляє всі дані, пов'язані з конкретною групою."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    tables_to_clean = [
        "group_settings",
        "group_admins",
        "warnings",
        "group_spam_triggers",
        "group_whitelists",
        "action_logs",
        "daily_stats",
    ]

    logging.info(f"Видалення всіх даних для групи {group_id}...")
    for table in tables_to_clean:
        id_column = "chat_id" if table == "warnings" else "group_id"
        cursor.execute(f"DELETE FROM {table} WHERE {id_column} = ?", (group_id,))

    conn.commit()
    conn.close()
    logging.info(f"Дані для групи {group_id} успішно видалено.")

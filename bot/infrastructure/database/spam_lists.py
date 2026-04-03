import sqlite3

from bot.config import DB_NAME


def get_spam_triggers() -> dict:
    """Отримує ГЛОБАЛЬНИЙ список спам-слів."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT trigger, score FROM spam_triggers")
    triggers = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return triggers


def add_spam_trigger(trigger: str, score: int):
    """Додає слово в ГЛОБАЛЬНИЙ список."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO spam_triggers (trigger, score) VALUES (?, ?)", (trigger.lower(), score))
    conn.commit()
    conn.close()


def delete_spam_trigger(trigger: str):
    """Видаляє слово з ГЛОБАЛЬНОГО списку."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM spam_triggers WHERE trigger = ?", (trigger.lower(),))
    conn.commit()
    conn.close()


def get_group_blocklist(group_id: int) -> dict:
    """Отримує ЛОКАЛЬНИЙ чорний список для групи."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT trigger, score FROM group_spam_triggers WHERE group_id = ?", (group_id,))
    triggers = {row["trigger"]: row["score"] for row in cursor.fetchall()}
    conn.close()
    return triggers


def add_group_spam_trigger(group_id: int, trigger: str, score: int):
    """Додає слово в ЛОКАЛЬНИЙ чорний список групи."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "REPLACE INTO group_spam_triggers (group_id, trigger, score) VALUES (?, ?, ?)",
        (group_id, trigger.lower(), score),
    )
    conn.commit()
    conn.close()


def delete_group_spam_trigger(group_id: int, trigger: str):
    """Видаляє слово з ЛОКАЛЬНОГО чорного списку групи."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM group_spam_triggers WHERE group_id = ? AND trigger = ?",
        (group_id, trigger.lower()),
    )
    conn.commit()
    conn.close()


def get_group_whitelist(group_id: int) -> list:
    """Отримує ЛОКАЛЬНИЙ білий список для групи."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT trigger FROM group_whitelists WHERE group_id = ?", (group_id,))
    triggers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return triggers


def add_group_whitelist_word(group_id: int, word: str):
    """Додає слово в ЛОКАЛЬНИЙ білий список групи."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO group_whitelists (group_id, trigger) VALUES (?, ?)",
        (group_id, word.lower()),
    )
    conn.commit()
    conn.close()


def delete_group_whitelist_word(group_id: int, word: str):
    """Видаляє слово з ЛОКАЛЬНОГО білого списку групи."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM group_whitelists WHERE group_id = ? AND trigger = ?",
        (group_id, word.lower()),
    )
    conn.commit()
    conn.close()

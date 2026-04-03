import sqlite3

from bot.config import DB_NAME


def get_punishment_settings(group_id: int) -> dict:
    """Отримує налаштування покарань для групи."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT warning_level, action, duration_minutes FROM punishment_settings WHERE group_id = ?",
        (group_id,),
    )

    settings = {}
    for row in cursor.fetchall():
        settings[row["warning_level"]] = {
            "action": row["action"],
            "duration": row["duration_minutes"],
        }
    conn.close()

    if not settings:
        return {
            1: {"action": "mute", "duration": 1440},
            2: {"action": "mute", "duration": 10080},
            3: {"action": "ban", "duration": 0},
        }
    return settings


def set_punishment_settings(group_id: int, level: int, action: str, duration: int):
    """Встановлює налаштування покарання для групи."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "REPLACE INTO punishment_settings (group_id, warning_level, action, duration_minutes) VALUES (?, ?, ?, ?)",
        (group_id, level, action, duration),
    )
    conn.commit()
    conn.close()

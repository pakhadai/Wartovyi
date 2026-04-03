import sqlite3

from bot.config import DB_NAME

from .global_settings import get_global_settings


def get_group_settings(group_id: int) -> dict:
    """
    Отримує налаштування для конкретної групи, коректно поєднуючи їх
    з глобальними налаштуваннями за замовчуванням.
    """
    final_settings = get_global_settings()

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM group_settings WHERE group_id = ?", (group_id,))
    group_specific_settings = cursor.fetchone()
    conn.close()

    if group_specific_settings:
        updates = dict(group_specific_settings)
        final_settings.update(
            {
                "spam_threshold": int(updates.get("spam_threshold", 10)),
                "captcha_enabled": bool(updates.get("captcha_enabled", 1)),
                "spam_filter_enabled": bool(updates.get("spam_filter_enabled", 1)),
                "use_global_list": bool(updates.get("use_global_list", 1)),
                "use_custom_list": bool(updates.get("use_custom_list", 1)),
                "antiflood_enabled": bool(updates.get("antiflood_enabled", 1)),
                "antiflood_sensitivity": int(updates.get("antiflood_sensitivity", 5)),
            }
        )

    return final_settings


def set_group_setting(group_id: int, key: str, value):
    """Встановлює налаштування для конкретної групи."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if isinstance(value, bool):
        value = 1 if value else 0
    cursor.execute("SELECT 1 FROM group_settings WHERE group_id = ?", (group_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO group_settings (group_id, group_name) VALUES (?, ?)",
            (group_id, ""),
        )
    cursor.execute(f"UPDATE group_settings SET {key} = ? WHERE group_id = ?", (value, group_id))
    conn.commit()
    conn.close()

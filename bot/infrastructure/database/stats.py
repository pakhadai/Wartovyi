import datetime
import sqlite3

from bot.config import DB_NAME


def setup_stats_tables(conn=None, cursor=None):
    """Створює таблиці для збору статистики."""
    close_connection = False
    if conn is None:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        close_connection = True

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            action_type TEXT,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_stats (
            group_id INTEGER,
            date DATE,
            messages_total INTEGER DEFAULT 0,
            messages_deleted INTEGER DEFAULT 0,
            users_joined INTEGER DEFAULT 0,
            users_left INTEGER DEFAULT 0,
            captcha_passed INTEGER DEFAULT 0,
            captcha_failed INTEGER DEFAULT 0,
            warnings_given INTEGER DEFAULT 0,
            bans_given INTEGER DEFAULT 0,
            PRIMARY KEY (group_id, date)
        )
    """
    )

    if close_connection:
        conn.commit()
        conn.close()


def log_action(group_id: int, user_id: int, user_name: str, action_type: str, details: str = None):
    """Логує дію для статистики, зберігаючи ім'я користувача."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO action_logs (group_id, user_id, user_name, action_type, details) VALUES (?, ?, ?, ?, ?)",
        (group_id, user_id, user_name, action_type, details),
    )
    conn.commit()
    conn.close()


def increment_daily_stat(group_id: int, stat_field: str, increment: int = 1):
    """Збільшує лічильник денної статистики."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.date.today()

    cursor.execute(
        "INSERT OR IGNORE INTO daily_stats (group_id, date) VALUES (?, ?)",
        (group_id, today),
    )

    cursor.execute(
        f"UPDATE daily_stats SET {stat_field} = {stat_field} + ? WHERE group_id = ? AND date = ?",
        (increment, group_id, today),
    )
    conn.commit()
    conn.close()


def get_group_stats(group_id: int, days: int = 30) -> dict:
    """Отримує статистику для групи за останні N днів."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            SUM(messages_total) as total_messages,
            SUM(messages_deleted) as total_deleted,
            SUM(users_joined) as total_joined,
            SUM(users_left) as total_left,
            SUM(captcha_passed) as total_captcha_passed,
            SUM(captcha_failed) as total_captcha_failed,
            SUM(warnings_given) as total_warnings,
            SUM(bans_given) as total_bans
        FROM daily_stats
        WHERE group_id = ? AND date >= date('now', '-' || ? || ' days')
    """,
        (group_id, days),
    )

    totals = cursor.fetchone()

    cursor.execute(
        """
        SELECT date, messages_total, messages_deleted, users_joined, users_left
        FROM daily_stats
        WHERE group_id = ? AND date >= date('now', '-' || ? || ' days')
        ORDER BY date
    """,
        (group_id, days),
    )

    daily_data = cursor.fetchall()

    cursor.execute(
        """
        SELECT user_id, user_name, COUNT(*) as violation_count
        FROM action_logs
        WHERE group_id = ?
            AND action_type IN ('spam_detected', 'warning_given', 'user_banned')
            AND datetime(timestamp) >= datetime('now', '-' || ? || ' days')
        GROUP BY user_id, user_name
        ORDER BY violation_count DESC
        LIMIT 5
    """,
        (group_id, days),
    )

    top_violators = cursor.fetchall()

    cursor.execute(
        """
        SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
        FROM action_logs
        WHERE group_id = ?
            AND action_type = 'message_sent'
            AND datetime(timestamp) >= datetime('now', '-7 days')
        GROUP BY hour
        ORDER BY hour
    """,
        (group_id,),
    )

    hourly_activity = cursor.fetchall()

    conn.close()

    return {
        "totals": dict(totals) if totals else {},
        "daily": [dict(row) for row in daily_data],
        "top_violators": [dict(row) for row in top_violators],
        "hourly_activity": [dict(row) for row in hourly_activity],
    }


def get_group_current_stats(group_id: int) -> dict:
    """Отримує поточну статистику групи (користувачі з попередженнями тощо)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(DISTINCT user_id) as users_with_warnings,
               SUM(warning_count) as total_warnings
        FROM warnings
        WHERE chat_id = ? AND warning_count > 0
    """,
        (group_id,),
    )

    warnings_data = cursor.fetchone()

    cursor.execute(
        """
        SELECT captcha_enabled, spam_filter_enabled, spam_threshold,
               use_global_list, use_custom_list
        FROM group_settings
        WHERE group_id = ?
    """,
        (group_id,),
    )

    settings = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as count FROM group_spam_triggers WHERE group_id = ?", (group_id,))
    blocklist_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM group_whitelists WHERE group_id = ?", (group_id,))
    whitelist_count = cursor.fetchone()["count"]

    conn.close()

    return {
        "warnings": dict(warnings_data) if warnings_data else {},
        "settings": dict(settings) if settings else {},
        "blocklist_count": blocklist_count,
        "whitelist_count": whitelist_count,
    }

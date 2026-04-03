"""
Доступ до SQLite: схема та операції розбиті на модулі за доменом.
Публічний API збігається з колишнім bot.infrastructure.database (один пакет замість одного файлу).
"""

from .global_settings import get_global_settings, set_global_setting
from .group_settings import get_group_settings, set_group_setting
from .groups import (
    add_group_if_not_exists,
    delete_all_group_data,
    get_group_admin_id,
    get_user_chats,
    is_group_admin,
    set_group_admin,
)
from .punishments import get_punishment_settings, set_punishment_settings
from .setup import setup_database
from .spam_lists import (
    add_group_spam_trigger,
    add_group_whitelist_word,
    add_spam_trigger,
    delete_group_spam_trigger,
    delete_group_whitelist_word,
    delete_spam_trigger,
    get_group_blocklist,
    get_group_whitelist,
    get_spam_triggers,
)
from .stats import (
    get_group_current_stats,
    get_group_stats,
    increment_daily_stat,
    log_action,
    setup_stats_tables,
)
from .warnings import add_warning, reset_warnings

__all__ = [
    "setup_database",
    "setup_stats_tables",
    "get_global_settings",
    "set_global_setting",
    "get_group_settings",
    "set_group_setting",
    "add_group_if_not_exists",
    "set_group_admin",
    "is_group_admin",
    "get_user_chats",
    "get_group_admin_id",
    "get_spam_triggers",
    "add_spam_trigger",
    "delete_spam_trigger",
    "get_group_blocklist",
    "add_group_spam_trigger",
    "delete_group_spam_trigger",
    "get_group_whitelist",
    "add_group_whitelist_word",
    "delete_group_whitelist_word",
    "add_warning",
    "reset_warnings",
    "log_action",
    "increment_daily_stat",
    "get_group_stats",
    "get_group_current_stats",
    "delete_all_group_data",
    "get_punishment_settings",
    "set_punishment_settings",
]

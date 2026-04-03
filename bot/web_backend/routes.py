import json
import logging
import base64
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Імпортуємо всі необхідні функції з інших модулів
from bot.infrastructure.localization import load_translation_file
from bot.infrastructure.database import (
    get_global_settings, set_global_setting,
    get_group_settings, set_group_setting,
    get_spam_triggers, add_spam_trigger, delete_spam_trigger,
    is_group_admin, get_user_chats,
    get_group_blocklist, add_group_spam_trigger, delete_group_spam_trigger,
    get_group_whitelist, add_group_whitelist_word, delete_group_whitelist_word
)
from bot.config import ADMIN_ID, BOT_TOKEN
from bot.web_backend.telegram_webapp_auth import resolve_webapp_user_id

router = APIRouter()

# --- Моделі для валідації даних, які приходять з Frontend ---
class SettingUpdate(BaseModel):
    key: str
    value: Any

class SpamTrigger(BaseModel):
    trigger: str = Field(..., min_length=2)
    score: int = Field(..., gt=0, lt=101)

class SpamTriggerDelete(BaseModel):
    trigger: str

class Chat(BaseModel):
    id: int
    name: str

# --- Функції для перевірки прав доступу ---
def get_user_id_from_header(user_data_raw: str) -> int:
    """Витягує user_id з хедеру X-User-Data, розкодовуючи його з Base64."""
    if not user_data_raw:
        raise HTTPException(status_code=401, detail="Not authorized: Missing user data header")
    try:
        decoded_bytes = base64.b64decode(user_data_raw)
        user_info_json = decoded_bytes.decode('utf-8')
        user_info = json.loads(user_info_json)
        return user_info['id']
    except (json.JSONDecodeError, KeyError, Exception) as e:
        logging.error(f"Could not decode user data: {e}")
        raise HTTPException(status_code=400, detail="Invalid user data format")


def get_authenticated_user_id(
    x_telegram_init_data: Annotated[Optional[str], Header(alias="X-Telegram-Init-Data")] = None,
    x_user_data: Annotated[Optional[str], Header(alias="X-User-Data")] = None,
) -> int:
    """Telegram initData (підписаний) або fallback X-User-Data для dev."""
    return resolve_webapp_user_id(
        x_telegram_init_data,
        x_user_data,
        BOT_TOKEN,
        get_user_id_from_header,
    )


def _ensure_group_admin(user_id: int, chat_id: int) -> None:
    if not is_group_admin(user_id, chat_id):
        raise HTTPException(status_code=403, detail="Forbidden: You are not an admin of this chat")


def _ensure_global_admin(user_id: int) -> None:
    if user_id != ADMIN_ID:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Global settings can only be changed by the bot owner",
        )

# --- API Роути ---

@router.get("/api/meta")
async def public_meta():
    """Публічні посилання на бота (лендінг, онбординг у Web App)."""
    from bot.config import BOT_USERNAME

    return {
        "bot_username": BOT_USERNAME,
        "bot_url": f"https://t.me/{BOT_USERNAME}",
        "add_bot_to_group_url": f"https://t.me/{BOT_USERNAME}?startgroup",
    }


@router.get("/api/translations/{lang_code}")
async def get_translations(lang_code: str):
    """Віддає файл перекладу у форматі JSON."""
    try:
        return JSONResponse(content=load_translation_file(lang_code))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load translations: {e}")


@router.get("/api/my-chats", response_model=List[Chat])
async def get_my_chats(user_id: int = Depends(get_authenticated_user_id)):
    """Повертає список чатів, якими керує користувач."""
    chats = get_user_chats(user_id)

    # Повертаємо результат
    return chats


# --- Роути для Налаштувань ---

@router.get("/api/settings/global")
async def get_default_settings(user_id: int = Depends(get_authenticated_user_id)):
    """Отримує глобальні налаштування за замовчуванням."""
    _ensure_global_admin(user_id)
    return get_global_settings()

@router.post("/api/settings/global")
async def update_default_setting(
    update: SettingUpdate,
    user_id: int = Depends(get_authenticated_user_id),
):
    """Оновлює глобальне налаштування."""
    _ensure_global_admin(user_id)
    allowed_keys = [
        "captcha_enabled",
        "spam_filter_enabled",
        "spam_threshold",
        "use_global_list",
        "use_custom_list",
        "antiflood_enabled",
        "antiflood_sensitivity",
    ]
    if update.key not in allowed_keys:
        raise HTTPException(status_code=400, detail="Invalid global setting key")
    set_global_setting(update.key, update.value)
    return {"status": "success"}

@router.get("/api/settings/{chat_id}")
async def get_chat_settings(chat_id: int, user_id: int = Depends(get_authenticated_user_id)):
    """Отримує налаштування для конкретної групи."""
    _ensure_group_admin(user_id, chat_id)
    return get_group_settings(chat_id)

@router.post("/api/settings/{chat_id}")
async def update_chat_setting(
    chat_id: int,
    update: SettingUpdate,
    user_id: int = Depends(get_authenticated_user_id),
):
    """Оновлює налаштування для конкретної групи."""
    _ensure_group_admin(user_id, chat_id)
    allowed_keys = ["captcha_enabled", "spam_filter_enabled", "spam_threshold", "use_global_list", "use_custom_list", "antiflood_enabled", "antiflood_sensitivity"]
    if update.key not in allowed_keys:
        raise HTTPException(status_code=400, detail="Invalid group setting key")
    set_group_setting(chat_id, update.key, update.value)
    return {"status": "success"}

# --- Роути для Спам-слів (глобальні) ---

@router.get("/api/spam-words")
async def get_all_spam_words():
    """Повертає глобальний список спам-слів."""
    return get_spam_triggers()

@router.post("/api/spam-words")
async def add_new_spam_word(item: SpamTrigger, user_id: int = Depends(get_authenticated_user_id)):
    """Додає нове слово до глобального списку (тільки для адміна)."""
    _ensure_global_admin(user_id)
    add_spam_trigger(item.trigger, item.score)
    return {"status": "success"}

@router.delete("/api/spam-words")
async def delete_existing_spam_word(
    item: SpamTriggerDelete = Body(...),
    user_id: int = Depends(get_authenticated_user_id),
):
    """Видаляє слово з глобального списку (тільки для адміна)."""
    _ensure_global_admin(user_id)
    delete_spam_trigger(item.trigger)
    return {"status": "success"}


@router.get("/api/spam-words/{chat_id}")
async def get_group_spam_words(chat_id: int, user_id: int = Depends(get_authenticated_user_id)):
    """Повертає локальний список спам-слів для групи."""
    _ensure_group_admin(user_id, chat_id)
    from bot.infrastructure.database import get_group_blocklist
    return get_group_blocklist(chat_id)

@router.post("/api/spam-words/{chat_id}")
async def add_group_spam_word(
    chat_id: int,
    item: SpamTrigger,
    user_id: int = Depends(get_authenticated_user_id),
):
    """Додає слово до локального списку групи."""
    _ensure_group_admin(user_id, chat_id)
    from bot.infrastructure.database import add_group_spam_trigger
    add_group_spam_trigger(chat_id, item.trigger, item.score)
    return {"status": "success"}

@router.delete("/api/spam-words/{chat_id}")
async def delete_group_spam_word(
    chat_id: int,
    item: SpamTriggerDelete = Body(...),
    user_id: int = Depends(get_authenticated_user_id),
):
    """Видаляє слово з локального списку групи."""
    _ensure_group_admin(user_id, chat_id)
    from bot.infrastructure.database import delete_group_spam_trigger
    delete_group_spam_trigger(chat_id, item.trigger)
    return {"status": "success"}

@router.get("/api/whitelist/{chat_id}")
async def get_group_whitelist(chat_id: int, user_id: int = Depends(get_authenticated_user_id)):
    """Повертає білий список для групи."""
    _ensure_group_admin(user_id, chat_id)
    from bot.infrastructure.database import get_group_whitelist
    return get_group_whitelist(chat_id)

@router.post("/api/whitelist/{chat_id}")
async def add_whitelist_word(
    chat_id: int,
    word: str = Body(..., embed=True),
    user_id: int = Depends(get_authenticated_user_id),
):
    """Додає слово до білого списку групи."""
    _ensure_group_admin(user_id, chat_id)
    from bot.infrastructure.database import add_group_whitelist_word
    add_group_whitelist_word(chat_id, word)
    return {"status": "success"}


@router.get("/api/stats/{chat_id}")
async def get_chat_statistics(
    chat_id: int,
    days: int = 30,
    user_id: int = Depends(get_authenticated_user_id),
):
    """Отримує статистику для конкретної групи."""
    _ensure_group_admin(user_id, chat_id)
    from bot.infrastructure.database import get_group_stats, get_group_current_stats

    historical_stats = get_group_stats(chat_id, days)
    current_stats = get_group_current_stats(chat_id)

    return {
        'historical': historical_stats,
        'current': current_stats
    }


@router.get("/api/stats/{chat_id}/export")
async def export_chat_statistics(
    chat_id: int,
    format: str = "json",
    user_id: int = Depends(get_authenticated_user_id),
):
    """Експортує статистику групи в різних форматах."""
    _ensure_group_admin(user_id, chat_id)
    from bot.infrastructure.database import get_group_stats
    import csv
    import io

    stats = get_group_stats(chat_id, 90)  # 3 місяці даних

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Записуємо заголовки
        writer.writerow(['Date', 'Messages', 'Deleted', 'Users Joined', 'Users Left'])

        # Записуємо дані
        for day in stats['daily']:
            writer.writerow([
                day['date'],
                day['messages_total'],
                day['messages_deleted'],
                day['users_joined'],
                day['users_left']
            ])

        return JSONResponse(
            content={'csv': output.getvalue()},
            headers={'Content-Type': 'text/csv'}
        )

    return stats


class PunishmentRule(BaseModel):
    level: int
    action: str
    duration: int


@router.get("/api/punishments/{chat_id}")
async def get_punishment_rules(chat_id: int, user_id: int = Depends(get_authenticated_user_id)):
    """Отримує налаштування гнучких покарань для групи."""
    _ensure_group_admin(user_id, chat_id)
    from bot.infrastructure.database import get_punishment_settings
    return get_punishment_settings(chat_id)


@router.post("/api/punishments/{chat_id}")
async def set_punishment_rule(
    chat_id: int,
    rule: PunishmentRule,
    user_id: int = Depends(get_authenticated_user_id),
):
    """Встановлює правило покарання для групи."""
    _ensure_group_admin(user_id, chat_id)
    # Валідація даних
    if rule.level not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Invalid warning level")
    if rule.action not in ["mute", "ban"]:
        raise HTTPException(status_code=400, detail="Invalid action type")

    from bot.infrastructure.database import set_punishment_settings
    set_punishment_settings(chat_id, rule.level, rule.action, rule.duration)
    return {"status": "success"}

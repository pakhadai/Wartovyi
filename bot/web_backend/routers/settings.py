from fastapi import APIRouter, Depends, HTTPException

from bot.infrastructure.database import (
    get_global_settings,
    get_group_settings,
    set_global_setting,
    set_group_setting,
)
from bot.web_backend.deps import ensure_global_admin, ensure_group_admin, get_authenticated_user_id
from bot.web_backend.schemas import SettingUpdate

router = APIRouter()

GLOBAL_SETTING_KEYS = [
    "captcha_enabled",
    "spam_filter_enabled",
    "spam_threshold",
    "use_global_list",
    "use_custom_list",
    "antiflood_enabled",
    "antiflood_sensitivity",
]

GROUP_SETTING_KEYS = [
    "captcha_enabled",
    "spam_filter_enabled",
    "spam_threshold",
    "use_global_list",
    "use_custom_list",
    "antiflood_enabled",
    "antiflood_sensitivity",
]


@router.get("/api/settings/global")
async def get_default_settings(user_id: int = Depends(get_authenticated_user_id)):
    """Отримує глобальні налаштування за замовчуванням."""
    ensure_global_admin(user_id)
    return get_global_settings()


@router.post("/api/settings/global")
async def update_default_setting(
    update: SettingUpdate,
    user_id: int = Depends(get_authenticated_user_id),
):
    """Оновлює глобальне налаштування."""
    ensure_global_admin(user_id)
    if update.key not in GLOBAL_SETTING_KEYS:
        raise HTTPException(status_code=400, detail="Invalid global setting key")
    set_global_setting(update.key, update.value)
    return {"status": "success"}


@router.get("/api/settings/{chat_id}")
async def get_chat_settings(chat_id: int, user_id: int = Depends(get_authenticated_user_id)):
    """Отримує налаштування для конкретної групи."""
    ensure_group_admin(user_id, chat_id)
    return get_group_settings(chat_id)


@router.post("/api/settings/{chat_id}")
async def update_chat_setting(
    chat_id: int,
    update: SettingUpdate,
    user_id: int = Depends(get_authenticated_user_id),
):
    """Оновлює налаштування для конкретної групи."""
    ensure_group_admin(user_id, chat_id)
    if update.key not in GROUP_SETTING_KEYS:
        raise HTTPException(status_code=400, detail="Invalid group setting key")
    set_group_setting(chat_id, update.key, update.value)
    return {"status": "success"}

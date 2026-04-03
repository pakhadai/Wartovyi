from fastapi import APIRouter, Depends, HTTPException

from bot.infrastructure.database import get_punishment_settings, set_punishment_settings
from bot.web_backend.deps import ensure_group_admin, get_authenticated_user_id
from bot.web_backend.schemas import PunishmentRule

router = APIRouter()


@router.get("/api/punishments/{chat_id}")
async def get_punishment_rules(chat_id: int, user_id: int = Depends(get_authenticated_user_id)):
    """Отримує налаштування гнучких покарань для групи."""
    ensure_group_admin(user_id, chat_id)
    return get_punishment_settings(chat_id)


@router.post("/api/punishments/{chat_id}")
async def set_punishment_rule(
    chat_id: int,
    rule: PunishmentRule,
    user_id: int = Depends(get_authenticated_user_id),
):
    """Встановлює правило покарання для групи."""
    ensure_group_admin(user_id, chat_id)
    if rule.level not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Invalid warning level")
    if rule.action not in ["mute", "ban"]:
        raise HTTPException(status_code=400, detail="Invalid action type")
    set_punishment_settings(chat_id, rule.level, rule.action, rule.duration)
    return {"status": "success"}

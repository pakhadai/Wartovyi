from fastapi import APIRouter, Body, Depends

from bot.infrastructure.database import (
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
from bot.web_backend.deps import ensure_global_admin, ensure_group_admin, get_authenticated_user_id
from bot.web_backend.schemas import SpamTrigger, SpamTriggerDelete

router = APIRouter()


@router.get("/api/spam-words")
async def get_all_spam_words():
    """Повертає глобальний список спам-слів."""
    return get_spam_triggers()


@router.post("/api/spam-words")
async def add_new_spam_word(item: SpamTrigger, user_id: int = Depends(get_authenticated_user_id)):
    """Додає нове слово до глобального списку (тільки для адміна)."""
    ensure_global_admin(user_id)
    add_spam_trigger(item.trigger, item.score)
    return {"status": "success"}


@router.delete("/api/spam-words")
async def delete_existing_spam_word(
    item: SpamTriggerDelete = Body(...),
    user_id: int = Depends(get_authenticated_user_id),
):
    """Видаляє слово з глобального списку (тільки для адміна)."""
    ensure_global_admin(user_id)
    delete_spam_trigger(item.trigger)
    return {"status": "success"}


@router.get("/api/spam-words/{chat_id}")
async def get_group_spam_words(chat_id: int, user_id: int = Depends(get_authenticated_user_id)):
    """Повертає локальний список спам-слів для групи."""
    ensure_group_admin(user_id, chat_id)
    return get_group_blocklist(chat_id)


@router.post("/api/spam-words/{chat_id}")
async def add_group_spam_word(
    chat_id: int,
    item: SpamTrigger,
    user_id: int = Depends(get_authenticated_user_id),
):
    """Додає слово до локального списку групи."""
    ensure_group_admin(user_id, chat_id)
    add_group_spam_trigger(chat_id, item.trigger, item.score)
    return {"status": "success"}


@router.delete("/api/spam-words/{chat_id}")
async def delete_group_spam_word(
    chat_id: int,
    item: SpamTriggerDelete = Body(...),
    user_id: int = Depends(get_authenticated_user_id),
):
    """Видаляє слово з локального списку групи."""
    ensure_group_admin(user_id, chat_id)
    delete_group_spam_trigger(chat_id, item.trigger)
    return {"status": "success"}


@router.get("/api/whitelist/{chat_id}")
async def get_whitelist(chat_id: int, user_id: int = Depends(get_authenticated_user_id)):
    """Повертає білий список для групи."""
    ensure_group_admin(user_id, chat_id)
    return get_group_whitelist(chat_id)


@router.post("/api/whitelist/{chat_id}")
async def add_whitelist_word(
    chat_id: int,
    word: str = Body(..., embed=True),
    user_id: int = Depends(get_authenticated_user_id),
):
    """Додає слово до білого списку групи."""
    ensure_group_admin(user_id, chat_id)
    add_group_whitelist_word(chat_id, word)
    return {"status": "success"}

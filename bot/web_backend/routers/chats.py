from typing import List

from fastapi import APIRouter, Depends

from bot.infrastructure.database import get_user_chats
from bot.web_backend.deps import get_authenticated_user_id
from bot.web_backend.schemas import Chat

router = APIRouter()


@router.get("/api/my-chats", response_model=List[Chat])
async def get_my_chats(user_id: int = Depends(get_authenticated_user_id)):
    """Повертає список чатів, якими керує користувач."""
    return get_user_chats(user_id)

import base64
import json
import logging
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException

from bot.config import ADMIN_ID, BOT_TOKEN
from bot.web_backend.telegram_webapp_auth import resolve_webapp_user_id


def get_user_id_from_header(user_data_raw: str) -> int:
    """Витягує user_id з хедеру X-User-Data, розкодовуючи його з Base64."""
    if not user_data_raw:
        raise HTTPException(status_code=401, detail="Not authorized: Missing user data header")
    try:
        decoded_bytes = base64.b64decode(user_data_raw)
        user_info_json = decoded_bytes.decode("utf-8")
        user_info = json.loads(user_info_json)
        return user_info["id"]
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


def ensure_group_admin(user_id: int, chat_id: int) -> None:
    from bot.infrastructure.database import is_group_admin

    if not is_group_admin(user_id, chat_id):
        raise HTTPException(status_code=403, detail="Forbidden: You are not an admin of this chat")


def ensure_global_admin(user_id: int) -> None:
    if user_id != ADMIN_ID:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Global settings can only be changed by the bot owner",
        )

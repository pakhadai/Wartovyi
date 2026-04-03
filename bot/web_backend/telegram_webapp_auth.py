"""
Валідація Telegram Web App initData (HMAC-SHA-256).
Див. docs/TELEGRAM_MINI_APPS_API.md (приклад 13.6).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qsl, unquote

from fastapi import HTTPException

from bot.config import ALLOW_X_USER_DATA_FALLBACK

logger = logging.getLogger(__name__)


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86400,
) -> Optional[Dict[str, Any]]:
    """
    Перевіряє підпис initData та актуальність auth_date.
    Повертає dict з ключами user (dict), auth_date (int), raw_params (dict) або None.
    """
    if not init_data or not init_data.strip() or not bot_token:
        return None

    try:
        pairs = parse_qsl(init_data.strip(), keep_blank_values=True)
    except ValueError:
        return None

    params: Dict[str, str] = dict(pairs)
    received_hash = params.pop("hash", None)
    if not received_hash:
        return None

    # Усі отримані поля крім hash, за алфавітом (див. core.telegram.org / Mini Apps).
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        logger.warning("initData: hash mismatch")
        return None

    try:
        auth_date = int(params.get("auth_date") or 0)
    except ValueError:
        return None

    if max_age_seconds > 0 and auth_date > 0:
        age = time.time() - auth_date
        if age > max_age_seconds or age < -300:
            logger.warning("initData: auth_date out of range")
            return None

    raw_user = params.get("user")
    if not raw_user:
        logger.warning("initData: no user field")
        return None

    try:
        user_obj = json.loads(raw_user)
    except json.JSONDecodeError:
        try:
            user_obj = json.loads(unquote(raw_user))
        except json.JSONDecodeError:
            return None

    if not isinstance(user_obj, dict) or "id" not in user_obj:
        return None

    return {"user": user_obj, "auth_date": auth_date, "raw_params": params}


def resolve_webapp_user_id(
    init_data_header: Optional[str],
    legacy_x_user_data: Optional[str],
    bot_token: Optional[str],
    legacy_decode_fn: Callable[[str], int],
) -> int:
    """
    Пріоритет: непорожній X-Telegram-Init-Data перевіряється HMAC (якщо є BOT_TOKEN).
    Інакше — X-User-Data (браузер / розробка).
    Якщо initData передано й перевірка не вдалася — 401 (без fallback на legacy).
    """
    init_data_header = (init_data_header or "").strip() or None
    legacy_x_user_data = legacy_x_user_data or None

    if init_data_header:
        if not bot_token:
            logger.warning("initData present but BOT_TOKEN is missing")
            raise HTTPException(
                status_code=503,
                detail="Server misconfiguration: cannot validate Telegram init data",
            )
        parsed = validate_telegram_init_data(init_data_header, bot_token)
        if parsed is None:
            raise HTTPException(status_code=401, detail="Invalid or expired Telegram init data")
        return int(parsed["user"]["id"])

    if legacy_x_user_data:
        if not ALLOW_X_USER_DATA_FALLBACK:
            raise HTTPException(
                status_code=401,
                detail="Open the control panel from Telegram (Mini App). Browser access is not allowed.",
            )
        return legacy_decode_fn(legacy_x_user_data)

    raise HTTPException(status_code=401, detail="Not authorized: missing authentication")

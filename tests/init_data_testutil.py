"""Підпис initData для тестів (алгоритм як у Telegram Web Apps)."""
import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import quote


def build_signed_init_data(
    bot_token: str,
    user_id: int,
    *,
    auth_date: Optional[int] = None,
) -> str:
    if auth_date is None:
        auth_date = int(time.time())
    user_json = json.dumps({"id": user_id, "first_name": "T"}, separators=(",", ":"))
    params = {"auth_date": str(auth_date), "user": user_json}
    data_check = "\n".join(f"{k}={params[k]}" for k in sorted(params))
    sk = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    hx = hmac.new(sk, data_check.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"auth_date={params['auth_date']}&user={quote(user_json)}&hash={hx}"

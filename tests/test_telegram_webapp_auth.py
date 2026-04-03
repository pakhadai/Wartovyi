import time

from bot.web_backend.telegram_webapp_auth import validate_telegram_init_data
from tests.init_data_testutil import build_signed_init_data


def test_validate_init_data_roundtrip():
    tok = "unit_test_bot_token"
    uid = 4242
    s = build_signed_init_data(tok, uid)
    out = validate_telegram_init_data(s, tok)
    assert out is not None
    assert out["user"]["id"] == uid


def test_validate_init_data_wrong_bot_token():
    s = build_signed_init_data("token_a", 1)
    assert validate_telegram_init_data(s, "token_b") is None


def test_validate_init_data_expired():
    tok = "tok"
    old = int(time.time()) - 200_000
    s = build_signed_init_data(tok, 1, auth_date=old)
    assert validate_telegram_init_data(s, tok, max_age_seconds=86400) is None

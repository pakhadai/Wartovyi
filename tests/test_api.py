import base64
import json
import os
from unittest.mock import patch

from tests.init_data_testutil import build_signed_init_data


def _x_user_data_header(user_dict: dict) -> str:
    """Той самий формат, що й у webapp: Base64(JSON користувача)."""
    raw = json.dumps(user_dict, ensure_ascii=False)
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


# Фікстура api_client автоматично підключиться з conftest.py
def test_public_meta(api_client):
    response = api_client.get("/api/meta")
    assert response.status_code == 200
    data = response.json()
    assert "bot_username" in data
    assert "bot_url" in data
    assert "add_bot_to_group_url" in data
    assert data["bot_url"].startswith("https://t.me/")


def test_get_my_chats_api(api_client):
    """
    Тест для ендпоінту /api/my-chats
    """
    # Arrange: Готуємо "користувача" і мокуємо відповідь від БД
    user_id = 12345
    user_data = _x_user_data_header({"id": user_id, "first_name": "Test"})

    with patch('bot.web_backend.routes.get_user_chats') as mock_get_chats:
        mock_get_chats.return_value = [{"id": -1001, "name": "Test Chat"}]

        # Act
        response = api_client.get(
            "/api/my-chats",
            headers={"X-User-Data": user_data}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['name'] == "Test Chat"


def test_update_chat_setting_unauthorized(api_client):
    """
    Тест перевіряє, що неавторизований користувач не може змінити налаштування.
    """
    # Arrange
    chat_id = -1001
    user_id = 99999  # "чужий" користувач
    user_data = _x_user_data_header({"id": user_id})

    # Мокуємо is_group_admin, щоб вона повертала False
    with patch('bot.web_backend.routes.is_group_admin', return_value=False):
        # Act
        response = api_client.post(
            f"/api/settings/{chat_id}",
            headers={"X-User-Data": user_data},
            json={"key": "captcha_enabled", "value": True}
        )

        # Assert
        assert response.status_code == 403  # Forbidden
        assert "not an admin" in response.json()['detail']


def test_get_my_chats_with_signed_init_data(api_client):
    token = os.environ["BOT_TOKEN"]
    user_id = 77701
    init = build_signed_init_data(token, user_id)

    with patch("bot.web_backend.routes.get_user_chats") as mock_get_chats:
        mock_get_chats.return_value = [{"id": -1001, "name": "From InitData"}]
        response = api_client.get(
            "/api/my-chats",
            headers={"X-Telegram-Init-Data": init},
        )

    assert response.status_code == 200
    mock_get_chats.assert_called_once_with(user_id)
    assert response.json()[0]["name"] == "From InitData"


def test_invalid_init_data_does_not_fallback_to_x_user_data(api_client):
    user_data = _x_user_data_header({"id": 12345})

    with patch("bot.web_backend.routes.get_user_chats") as mock_get:
        response = api_client.get(
            "/api/my-chats",
            headers={
                "X-Telegram-Init-Data": "auth_date=9999999999&user=%7B%22id%22%3A1%7D&hash=deadbeef",
                "X-User-Data": user_data,
            },
        )

    assert response.status_code == 401
    mock_get.assert_not_called()
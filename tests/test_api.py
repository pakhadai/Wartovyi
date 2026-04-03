import base64
import json
import pytest
from unittest.mock import patch


def _x_user_data_header(user_dict: dict) -> str:
    """Той самий формат, що й у webapp: Base64(JSON користувача)."""
    raw = json.dumps(user_dict, ensure_ascii=False)
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


# Фікстура api_client автоматично підключиться з conftest.py
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
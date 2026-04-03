from unittest.mock import patch

from bot.features.message_filtering.antispam_service import calculate_spam_score


@patch("bot.features.message_filtering.antispam_service.get_group_settings")
@patch("bot.features.message_filtering.antispam_service.get_group_whitelist")
@patch("bot.features.message_filtering.antispam_service.get_spam_triggers")
@patch("bot.features.message_filtering.antispam_service.get_group_blocklist")
def test_spam_score_calculation(
    mock_get_group_blocklist,
    mock_get_spam_triggers,
    mock_get_group_whitelist,
    mock_get_group_settings,
):
    chat_id = -1001
    mock_get_group_settings.return_value = {
        "spam_threshold": 10,
        "captcha_enabled": True,
        "spam_filter_enabled": True,
        "use_global_list": True,
        "use_custom_list": True,
    }
    mock_get_group_whitelist.return_value = ["білеслово"]
    mock_get_spam_triggers.return_value = {"глобальний": 5, "спам": 8}
    mock_get_group_blocklist.return_value = {"локальний": 10}

    r1 = calculate_spam_score("Привіт, це білеслово.", chat_id)
    assert r1.score == 0
    assert r1.whitelist_hit is True
    assert "whitelist" in r1.reasons[0]

    r2 = calculate_spam_score("Це глобальний і локальний спам.", chat_id)
    assert r2.score == 5 + 10 + 8
    assert len(r2.reasons) == 3
    assert r2.whitelist_hit is False

    r3 = calculate_spam_score("КУПЛЮ ГАРАЖ СРОЧНО T.ME/LINK", chat_id)
    assert r3.score == 8
    assert "КАПС (+5)" in r3.reasons
    assert "посилання x1 (+3)" in r3.reasons


@patch("bot.features.message_filtering.antispam_service.get_group_settings")
@patch("bot.features.message_filtering.antispam_service.get_group_whitelist")
@patch("bot.features.message_filtering.antispam_service.get_spam_triggers")
@patch("bot.features.message_filtering.antispam_service.get_group_blocklist")
def test_whitelist_word_boundary_no_false_positive_inside_word(
    mock_block,
    mock_global,
    mock_white,
    mock_settings,
):
    """Тригер у whitelist не спрацьовує як підрядок всередині іншого слова."""
    mock_settings.return_value = {
        "use_global_list": True,
        "use_custom_list": True,
    }
    mock_white.return_value = ["білеслово"]
    mock_global.return_value = {"спам": 10}
    mock_block.return_value = {}

    r = calculate_spam_score("надбілесловом все ще спам тут", -1001)
    assert r.whitelist_hit is False
    assert r.score >= 10


@patch("bot.features.message_filtering.antispam_service.get_group_settings")
@patch("bot.features.message_filtering.antispam_service.get_group_whitelist")
@patch("bot.features.message_filtering.antispam_service.get_spam_triggers")
@patch("bot.features.message_filtering.antispam_service.get_group_blocklist")
def test_repeated_chars_adds_score(mock_block, mock_global, mock_white, mock_settings):
    mock_settings.return_value = {"use_global_list": False, "use_custom_list": False}
    mock_white.return_value = []
    mock_global.return_value = {}
    mock_block.return_value = {}

    r = calculate_spam_score("ваааааааажливо нормально", -1)
    assert any("повтор символів" in x for x in r.reasons)
    assert r.score >= 4

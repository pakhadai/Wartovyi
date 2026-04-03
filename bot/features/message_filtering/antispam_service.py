import re
import unicodedata
from dataclasses import dataclass, field

from bot.infrastructure.database import (
    get_group_settings,
    get_spam_triggers,
    get_group_blocklist,
    get_group_whitelist,
)


@dataclass(frozen=True)
class SpamScoreResult:
    """Результат аналізу повідомлення на спам."""

    score: int
    reasons: list[str] = field(default_factory=list)
    whitelist_hit: bool = False


def _normalize(text: str) -> str:
    s = text.lower().strip()
    # Прибираємо деякі символи нульової ширини / форматування
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff"):
        s = s.replace(ch, "")
    return s


def _wordish_trigger_matches(norm_text: str, trigger_raw: str) -> bool:
    """
    Перевіряє збіг тригера/whitelist як окремого слова або фрази,
    а не як довільного підрядка всередині іншого слова.
    Для коротких або несловесних тригерів лишається перевірка підрядка.
    """
    raw = trigger_raw.strip().lower()
    if not raw:
        return False

    text = norm_text

    # Дуже короткі або без «літер/цифр_»: лишаємо підрядок (URL-фрагменти, смайли тощо)
    if len(raw) <= 2:
        return raw in text
    if not re.search(r"[\w]", raw, flags=re.UNICODE):
        return raw in text

    parts = raw.split()
    if len(parts) == 1:
        return (
            re.search(r"(?<!\w)" + re.escape(parts[0]) + r"(?!\w)", text, flags=re.UNICODE)
            is not None
        )

    between = r"[\s\W\d_]+"
    pattern = r"(?<!\w)" + between.join(re.escape(p) for p in parts) + r"(?!\w)"
    try:
        if re.search(pattern, text, flags=re.UNICODE):
            return True
    except re.error:
        pass
    return raw in text


def _repeated_character_penalty(message_text: str) -> tuple[int, list[str]]:
    """Той самий символ 8+ разів поспіль — типовий шум/спам."""
    bonus = 0
    reasons: list[str] = []
    if re.search(r"(.)\1{7,}", message_text, flags=re.DOTALL):
        bonus += 4
        reasons.append("повтор символів (+4)")
    return bonus, reasons


def _emoji_noise_penalty(message_text: str) -> tuple[int, list[str]]:
    """Багато символів класу Symbol/other у відносно короткому тексті."""
    if len(message_text) > 200:
        return 0, []
    emoji_like = 0
    for ch in message_text:
        cat = unicodedata.category(ch)
        o = ord(ch)
        if cat == "So" or 0x1F300 <= o <= 0x1FAFF or 0x2600 <= o <= 0x26FF:
            emoji_like += 1
    if emoji_like >= 12:
        return 5, [f"надмір емодзі/символів (+5), шт.: {emoji_like}"]
    return 0, []


def calculate_spam_score(message_text: str, chat_id: int) -> SpamScoreResult:
    """
    Підраховує рейтинг спаму: глобальний/локальний списки, білий список,
    посилання, згадки, КАПС, повтори символів, емодзі.
    """
    if not message_text or not message_text.strip():
        return SpamScoreResult(0, [], False)

    text_lower = message_text.lower()
    norm = _normalize(message_text)
    spam_score = 0
    reasons: list[str] = []

    settings = get_group_settings(chat_id)
    whitelist = get_group_whitelist(chat_id)

    for whitelisted_word in whitelist:
        if _wordish_trigger_matches(norm, whitelisted_word):
            return SpamScoreResult(0, [f"'{whitelisted_word}' (whitelist)"], True)

    final_triggers: dict[str, int] = {}
    if settings.get("use_global_list", True):
        final_triggers.update(get_spam_triggers())
    if settings.get("use_custom_list", True):
        final_triggers.update(get_group_blocklist(chat_id))

    for trigger, score in final_triggers.items():
        if _wordish_trigger_matches(norm, trigger):
            spam_score += score
            reasons.append(f"'{trigger}' ({score})")

    url_pattern = r"(https?://|www\.|t\.me/)[^\s]+"
    if re.search(url_pattern, text_lower):
        urls_count = len(re.findall(url_pattern, text_lower))
        spam_score += urls_count * 3
        reasons.append(f"посилання x{urls_count} (+{urls_count * 3})")

    mentions = re.findall(r"@\w+", text_lower)
    if len(mentions) > 2:
        spam_score += len(mentions) * 2
        reasons.append(f"згадки x{len(mentions)} (+{len(mentions) * 2})")

    if len(message_text) > 10 and (sum(1 for c in message_text if c.isupper()) / len(message_text)) > 0.7:
        spam_score += 5
        reasons.append("КАПС (+5)")

    extra, extra_r = _repeated_character_penalty(message_text)
    spam_score += extra
    reasons.extend(extra_r)

    extra_e, extra_er = _emoji_noise_penalty(message_text)
    spam_score += extra_e
    reasons.extend(extra_er)

    return SpamScoreResult(spam_score, reasons, False)

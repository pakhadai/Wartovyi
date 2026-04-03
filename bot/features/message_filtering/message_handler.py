# Wartovyi/bot/features/message_filtering/message_handler.py

import logging
import asyncio
import time
from datetime import datetime, timedelta, timezone

from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus

from bot.infrastructure.database import (
    increment_daily_stat,
    log_action,
    get_group_settings,
    add_warning,
    get_group_admin_id,
    get_punishment_settings,
    is_group_admin,
)
from bot.config import ADMIN_ID
from bot.infrastructure.localization import get_text
from .antispam_service import calculate_spam_score
from .delete_message_job import delete_message_job
from .antiflood_service import is_user_flooding

TG_MODERATOR_CACHE_TTL = 120


async def user_is_telegram_moderator(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    """
    creator / administrator у чаті Telegram (кеш на chat_data, щоб не штормити API).
    """
    cache = context.chat_data.setdefault("tg_moderator_cache", {})
    now = time.time()
    entry = cache.get(user_id)
    if entry is not None:
        is_mod, ts = entry
        if now - ts < TG_MODERATOR_CACHE_TTL:
            return is_mod
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_mod = member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except Exception as e:
        logging.debug("get_chat_member не вхопив %s у чаті %s: %s", user_id, chat_id, e)
        is_mod = False
    cache[user_id] = (is_mod, now)
    return is_mod


async def user_skips_spam_and_flood(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    """Власник бота / записані в БД адміни групи / реальні TG-адміністратори чату."""
    if is_group_admin(user_id, chat_id):
        return True
    return await user_is_telegram_moderator(context, chat_id, user_id)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє текстові повідомлення: антифлуд, скоринг спаму, покарання.
    """
    if not update.message or not update.message.text:
        return

    user = update.message.from_user
    chat = update.message.chat
    settings = get_group_settings(chat.id)

    if await user_skips_spam_and_flood(context, chat.id, user.id):
        increment_daily_stat(chat.id, "messages_total")
        return

    if settings.get("antiflood_enabled", True):
        if is_user_flooding(user.id, settings.get("antiflood_sensitivity", 5), context):
            try:
                mute_until = datetime.now(timezone.utc) + timedelta(minutes=5)
                await context.bot.restrict_chat_member(
                    chat_id=chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=mute_until,
                )

                warning_msg = await update.message.reply_text(
                    f"⚠️ {user.mention_html()}, ви надсилаєте повідомлення занадто часто!\n"
                    f"📵 Мут на 5 хвилин.",
                    parse_mode=ParseMode.HTML,
                )

                await update.message.delete()

                context.job_queue.run_once(
                    delete_message_job,
                    30,
                    data={"chat_id": chat.id, "message_id": warning_msg.message_id},
                )

                log_action(chat.id, user.id, user.full_name, "antiflood_triggered", "Muted for 5 minutes")

            except Exception as e:
                logging.error(f"Помилка під час обробки флуду від {user.id} в чаті {chat.id}: {e}")

            return

    increment_daily_stat(chat.id, "messages_total")
    if not settings["spam_filter_enabled"]:
        return

    group_admin_id = get_group_admin_id(chat.id)
    spam_result = calculate_spam_score(update.message.text, chat.id)
    if spam_result.whitelist_hit:
        return

    spam_score = spam_result.score
    triggered_words = spam_result.reasons

    if spam_score >= settings["spam_threshold"]:
        logging.info(
            f"Виявлено спам від {user.full_name} ({user.id}) з рахунком {spam_score} в чаті {chat.title}"
        )

        try:
            await update.message.delete()
        except Exception as e:
            logging.warning(f"Не вдалося видалити повідомлення {update.message.id} в чаті {chat.id}: {e}")

        warnings_count = add_warning(user.id, chat.id)
        lang = user.language_code

        punishment_rules = get_punishment_settings(chat.id)
        rule_key = warnings_count if warnings_count in punishment_rules else max(punishment_rules.keys())
        rule = punishment_rules.get(rule_key)

        action_taken_log = "Невідомо"
        warning_text = ""
        tasks_to_run = []

        try:
            if rule and rule.get("action") == "mute":
                mute_duration_minutes = rule["duration"]
                mute_until = datetime.now(timezone.utc) + timedelta(minutes=mute_duration_minutes)
                tasks_to_run.append(
                    context.bot.restrict_chat_member(
                        chat_id=chat.id,
                        user_id=user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=mute_until,
                    )
                )
                warning_text = (
                    f"⚠️ {user.mention_html()}, ваше повідомлення видалено за спам.\n"
                    f"📵 Мут на {mute_duration_minutes} хвилин."
                )
                action_taken_log = f"Мут на {mute_duration_minutes} хв."

            elif rule and rule.get("action") == "ban":
                tasks_to_run.append(context.bot.ban_chat_member(chat_id=chat.id, user_id=user.id))
                warning_text = get_text(lang, "spam_warning_3", user_mention=user.mention_html())
                action_taken_log = "Бан"

            if warning_text:
                warning_msg_task = context.bot.send_message(
                    chat_id=chat.id,
                    text=warning_text,
                    parse_mode=ParseMode.HTML,
                    disable_notification=True,
                )
                tasks_to_run.append(warning_msg_task)

        except Exception as e:
            logging.error(f"Помилка при підготовці покарання для {user.id} в чаті {chat.id}: {e}")

        log_recipient_id = group_admin_id or ADMIN_ID
        try:
            log_message = get_text(
                "uk",
                "log_spam_detected",
                user_mention=user.mention_html(),
                user_id=user.id,
                chat_title=chat.title,
                spam_score=spam_score,
                threshold=settings["spam_threshold"],
                triggered_words=", ".join(triggered_words),
                warnings_count=warnings_count,
                action_taken=action_taken_log,
                message_text=update.message.text,
            )
            log_keyboard = None
            tasks_to_run.append(
                context.bot.send_message(
                    chat_id=log_recipient_id,
                    text=log_message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=log_keyboard,
                )
            )
        except Exception as e:
            logging.error(f"Не вдалося підготувати лог власнику {log_recipient_id} для чату {chat.id}: {e}")

        results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logging.error(f"Помилка при виконанні фонового завдання: {result}")
            elif hasattr(result, "message_id") and result.chat_id == chat.id:
                context.job_queue.run_once(
                    delete_message_job,
                    30,
                    data={"chat_id": result.chat_id, "message_id": result.message_id},
                )

        log_action(chat.id, user.id, user.full_name, "spam_detected", f"Score: {spam_score}")
        increment_daily_stat(chat.id, "messages_deleted")

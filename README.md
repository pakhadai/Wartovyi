# WartovyiBot — Telegram-бот для захисту груп

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python) ![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite)

Документ описує **ідею проєкту**, **межі системи**, **архітектуру** та **напрями подальшої оптимізації**. Його можна використовувати як точку входу для розробників і для планування покращень.

Детальний практичний гайд для змін у коді: **[docs/MAINTENANCE.md](docs/MAINTENANCE.md)**.

---

## Навіщо існує проєкт

**Проблема.** У публічних і напівпублічних Telegram-групах швидко накопичуються спам, шахрайські пропозиції та автоматизовані акаунти. Ручне модерування не масштабується.

**Ідея.** Один бот поєднує:

- **автоматичну модерацію тексту** (скоринг за тригерами, глобальний і локальні списки, білий список);
- **верифікацію нових учасників** (CAPTCHA через inline-кнопки);
- **антиспам-логіку з прогресією покарань** (попередження → мут/бан згідно налаштувань);
- **антиспам за частотою повідомлень** (antiflood, увімкнено на рівні групи в БД);
- **веб-панель** як **Telegram Web App**: налаштування без окремого «великого» сайту, з **перевіркою `initData`** (HMAC за специфікацією Telegram) і резервним заголовком для локальної розробки.

**Цільова аудиторія адміністрування:** власник інстансу бота (`ADMIN_ID` у `.env`) керує глобальними налаштуваннями; **керівники груп** (записані в `group_admins`) керують параметрами своїх чатів через API/Web App.

---

## Ключові можливості (коротко)

| Область | Що робить система |
|--------|-------------------|
| Модерація | Видалення/покарання за набраним скором спаму, урахування глобального та групових списків, whitelist |
| Вхід у групу | CAPTCHA для нових учасників, таймаути (див. `bot/features/group_join/`) |
| Адміністрування | Команда `/settings` відкриває Web App; налаштування зберігаються в SQLite |
| Статистика | Таблиці для статистики створюються при ініціалізації БД (`setup_stats_tables`); відображення — у веб-інтерфейсі та API |
| Життєвий цикл бота в чаті | Подія `my_chat_member`: додавання групи й власника; **видалення бота** — очищення даних групи (`delete_all_group_data`) |

---

## Технічний стек

| Шар | Технології |
|-----|------------|
| Бот | Python 3, `python-telegram-bot` v21+, `asyncio` |
| API + статика Web App | FastAPI, Uvicorn, роздача `webapp/` через `StaticFiles` |
| База даних | SQLite, файл **`bot_database_v6.db`** (ім’я задається в `bot/config.py`) |
| Фронт Web App | HTML/CSS/vanilla JS (`webapp/`): сучасний мобільний UI, тема з **`themeParams`** / `themeChanged`, циклічне перемикання «як у Telegram» / світла / темна |
| Тести | `pytest` (залежність для розробки; див. [docs/MAINTENANCE.md](docs/MAINTENANCE.md)) |

---

## Архітектура репозиторію

```
Wartovyi/
├── bot/
│   ├── main.py              # Точка входу: БД → PTB Application → полінг + веб-сервер
│   ├── config.py            # BOT_TOKEN, WEB_APP_URL, ADMIN_ID, DB_NAME
│   ├── core/                # Створення Application, реєстрація хендлерів
│   ├── features/            # Функції за доменами (captcha, фільтрація, команди, web)
│   ├── infrastructure/      # SQLite, локалізація
│   ├── services/            # Допоміжні сервіси (наприклад, antispam)
│   └── web_backend/         # FastAPI: routes, telegram_webapp_auth (initData), main
├── webapp/                  # Telegram Web App (index.html, css, js)
├── tests/                   # pytest
├── start_ngrok.py           # Допомога для локального WEB_APP_URL
└── requirements.txt
```

**Потік запуску.** `python -m bot.main` викликає `setup_database()`, збирає застосунок бота, стартує **long polling**, паралельно піднімає **Uvicorn** на `0.0.0.0:8000` з тим же процесом (див. `bot/main.py`).

**Авторизація API (захищені маршрути).**

1. **У продакшені з Telegram-клієнта** клієнт надсилає **`X-Telegram-Init-Data`** — рядок `initData` з Web App. Сервер перевіряє **HMAC-SHA-256** (ключ «WebAppData» + `BOT_TOKEN`, див. офіційну документацію Mini Apps) і актуальність **`auth_date`**. Ідентифікатор користувача береться з поля **`user`** після успішної перевірки.
2. **Резерв (браузер, локальні тести)** — заголовок **`X-User-Data`**: Base64(JSON) з полем `id` (Telegram user id). Використовується лише якщо **`X-Telegram-Init-Data` не передано** (порожній/відсутній).
3. Якщо передано непорожній `initData`, але підпис або вік даних невалідні — відповідь **401**; **fallback на `X-User-Data` у цьому випадку не застосовується**.

Реалізація: `bot/web_backend/telegram_webapp_auth.py`, підключення через `Depends(get_authenticated_user_id)` у `routes.py`. Детальний довідник по API клієнта та темі: **[docs/TELEGRAM_MINI_APPS_API.md](docs/TELEGRAM_MINI_APPS_API.md)**.

Глобальні налаштування — лише для `ADMIN_ID`; налаштування чату — лише якщо `is_group_admin(user_id, chat_id)`.

---

## Конфігурація

Створіть `.env` у корені проєкту:

```env
BOT_TOKEN=              # токен від @BotFather
ADMIN_ID=123456789      # числовий Telegram ID власника бота
WEB_APP_URL=https://... # публічна URL-адреса, яка вказує на ваш FastAPI (зазвичай порт 8000), для Telegram Web App
```

**Важливо для Web App.** Telegram вимагає **HTTPS** для URL веб-додатка. Локально зазвичай використовують тунель (наприклад, ngrok) — у репозиторії є `start_ngrok.py` для орієнтира.

---

## Запуск

```bash
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt

python -m bot.main
```

### Docker (VPS + Nginx Proxy Manager)

У корені є **`Dockerfile`** та **`docker-compose.yml`** (мережа `npm_network`, volume для SQLite в `/data`). Шаблон змінних: **`.env.example`**. Детальні кроки та NPM: **[docs/VPS-DEPLOYMENT.md](docs/VPS-DEPLOYMENT.md)** (там же — **GitHub Actions** автодеплой після push у `main`).

Клонування (приклад):

```bash
git clone https://github.com/pakhadai/-WartovyiBot.git
cd -WartovyiBot
```

Розгортання: класично — venv + systemd + reverse proxy на порт **8000**. Якщо у вас **Docker і Nginx Proxy Manager** (спільна мережа `npm_network`, Cloudflare Full Strict), див. **[docs/VPS-DEPLOYMENT.md](docs/VPS-DEPLOYMENT.md)** — там узгодження з такою інфраструктурою та застереження щодо VPN для Web App.

---

## Основні API (огляд)

Повний перелік і моделі запитів — у `bot/web_backend/routes.py`.

| Метод | Шлях | Призначення |
|-------|------|-------------|
| GET | `/api/translations/{lang_code}` | Переклади для UI |
| GET | `/api/my-chats` | Чати, де користувач — адмін групи в сенсі бота |
| GET/POST | `/api/settings/{chat_id}`, `/api/settings/global` | Налаштування чату / глобальні (глобальні — тільки `ADMIN_ID`) |
| GET/POST/DELETE | `/api/spam-words/{chat_id}` та whitelist | Локальні списки |
| GET | `/api/stats/{chat_id}` | Статистика |

Усі захищені маршрути вимагають валідний **`X-Telegram-Init-Data`** (у Telegram) або коректний **`X-User-Data`** (локально / без підписаного `initData`).

---

## База даних (логічна модель)

Створення та міграції «на льоту» — у пакеті **`bot/infrastructure/database/`** (точка входу `setup_database` у `setup.py`). Файл БД: змінна **`BOT_DB_PATH`** (у Docker типово `/data/bot_database_v6.db`) або за замовчуванням `bot_database_v6.db` у робочій директорії. Ключові сутності:

- **`group_settings`** — поріг спаму, captcha, фільтр, глобальний/кастомний списки, antiflood;
- **`group_admins`** — хто може керувати групою через панель;
- **`spam_triggers`**, **`group_spam_triggers`**, **`group_whitelists`**;
- **`warnings`**, **`punishment_settings`** — прогресія покарань;
- таблиці статистики — через `setup_stats_tables`.

Перед зміною схеми прочитайте розділ про міграції в [docs/MAINTENANCE.md](docs/MAINTENANCE.md).

---

## Напрями оптимізації та розвитку (roadmap)

Стан на момент оновлення документації — перевіряйте код і issue у репозиторії.

**Вже є в кодовій базі (уточніть UX/тестами):**

- Обробка **виходу бота з чату**: `my_chat_member_handler` викликає `delete_all_group_data`;
- **Antiflood**: поля в `group_settings`, логіка в `bot/features/message_filtering/`;
- **Web App**: перевірка **`initData`** на API, тема з **`themeParams`** / подія **`themeChanged`**, довідник у `docs/TELEGRAM_MINI_APPS_API.md`.

**Логічні наступні кроки:**

- **Rate limiting** та додатковий захист публічного API (поверх перевірки `initData`);
- **Кілька «менеджерів»** на групу — розширити UX призначення адмінів і узгодити з `group_admins`;
- **Статистика та списки порушників**: імена замість сирих ID де це дозволяє політика приватності;
- **Преміум / розширені логи** — як окремий продуктовий шар поверх поточних таблиць;
- **Спостережуваність**: структуровані логи, метрики, health-check для процесу бота + API;
- **Тести та CI**: закріпити `pytest` у `requirements-dev.txt`, ганяти тести в pipeline.

---

## Безпека та обмеження

- Токен бота та `.env` не повинні потрапляти в git.
- У продакшені клієнт Telegram надсилає **`initData`**; резервний **`X-User-Data`** зручний для розробки, але **не слід покладатися на нього** як на єдиний захист у відкритому інтернеті (будь-хто може підробити Base64, якщо знати `id`). Тому для реальних користувачів має працювати перевірка підпису (**`BOT_TOKEN` обов’язковий** на сервері).
- SQLite підходить для одного інстансу; при горизонтальному масштабуванні потрібна інша СУБД або реплікація/шардінг за межами цього репозиторію.

---

## Ліцензія та авторство

Уточніть у репозиторії наявність файлу `LICENSE` та актуальних контактів мейнтейнерів.

---

## Документація для мейнтейнерів

- **[docs/MAINTENANCE.md](docs/MAINTENANCE.md)** — як вносити зміни, де що лежить, тести, міграції БД, чекліст перед релізом.
- **[docs/VPS-DEPLOYMENT.md](docs/VPS-DEPLOYMENT.md)** — Docker, NPM, Cloudflare, VPN vs публічний Web App, volume для SQLite.
- **[docs/TELEGRAM_MINI_APPS_API.md](docs/TELEGRAM_MINI_APPS_API.md)** — довідник Mini Apps (тема, події, валідація `initData`) узгоджений із поточною реалізацією Web App.

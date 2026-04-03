# Розгортання WartovyiBot на VPS (Docker + Nginx Proxy Manager)

Цей документ зв’язує **цей репозиторій** з типовою схемою хостингу: Ubuntu, Docker Compose, спільна мережа з NPM (`npm_network`), Cloudflare **Full (Strict)**. Дані про ваш сервер (IP, домени, VPN, порти) візьміть з вашого внутрішнього посібника — тут лише **що має бути сумісно** з ботом.

---

## 1. Критично: Web App не можна закрити лише під VPN

Адмін-панелі (NPM, Portainer тощо) у вашій архітектурі доступні через WireGuard — це нормально.

**Telegram Web App** відкривається клієнтом Telegram (телефон / десктоп) і завантажує `WEB_APP_URL` **напряму з інтернету**. Тому:

- хост (Proxy Host у NPM) для веб-частини бота має бути **доступний з інтернету по HTTPS** (443);
- Access List «тільки 10.8.0.0/24» **неможна** застосовувати до домену, який ви вказуєте в `WEB_APP_URL`, інакше панель не відкриється з Telegram.

За бажанням можна додати **rate limit**, окремий піддомен тощо. **Перевірка `initData`** на API вже реалізована в коді (потрібен коректний **`BOT_TOKEN`** у `.env` контейнера). Не використовуйте VPN-only Access List для домену Web App — інакше Telegram-клієнт не завантажить панель.

---

## 2. Що саме піднімає проєкт

Один процес (`python -m bot.main`):

- **Long polling** до Telegram API (вихідні з’єднання з контейнера/хоста — достатньо дозволити outbound);
- **Uvicorn** слухає **`0.0.0.0:8000`** і одночасно віддає API та статичний `webapp/` (див. `bot/web_backend/main.py`).

На VPS у Docker зазвичай:

- **не відкривають** порт 8000 у UFW на публічному інтерфейсі;
- NPM проксує `https://bot.приклад.pp.ua` → `http://<container>:8000` у внутрішній мережі.

---

## 3. Змінні оточення (production)

| Змінна | Призначення |
|--------|-------------|
| `BOT_TOKEN` | Токен від @BotFather (потрібен і для бота, і для **валідації Web App `initData`** на API) |
| `ADMIN_ID` | Числовий Telegram ID власника інстансу |
| `WEB_APP_URL` | Повний публічний URL **з HTTPS** без обмеження лише VPN, наприклад `https://wartovyi.ohmyrevit.pp.ua/` — має збігатися з тим, що відкриває NPM |
| `BOT_DB_PATH` | (опційно) Шлях до файлу SQLite; у Docker за замовчуванням `/data/bot_database_v6.db` через `docker-compose.yml` |

У контейнері тримайте `.env` через `env_file` або secrets, не вшивайте в образ.

---

## 4. Файли в репозиторії

| Файл | Призначення |
|------|-------------|
| `Dockerfile` | Збірка образу Python 3.12, залежності, `CMD python -m bot.main`, healthcheck на `/openapi.json` |
| `docker-compose.yml` | Сервіс `wartovyi`, volume `wartovyi_data` → `/data`, мережа `npm_network` (external), порт **8000** лише `expose` (не публікується на хост) |
| `.dockerignore` | Зайве не потрапляє в контекст білду |
| `.env.example` | Шаблон змінних для копіювання в `.env` на сервері |

### Кроки на сервері

```bash
mkdir -p ~/apps/wartovyi && cd ~/apps/wartovyi
# склонувати репозиторій або скопіювати файли проєкту
cp .env.example .env
nano .env   # BOT_TOKEN, ADMIN_ID, WEB_APP_URL

docker network create npm_network   # якщо мережа ще не створена (один раз)

docker compose up -d --build
docker compose logs -f wartovyi
```

Оновлення після `git pull`:

```bash
docker compose up -d --build
```

---

## 5. Nginx Proxy Manager

- **Proxy Host:** ваш публічний домен → **`http://wartovyi:8000`** (ім’я сервісу з `docker-compose.yml`; NPM має бути в тій самій `npm_network`).
- **Force SSL:** увімкнено; сертифікат на NPM (актуально для Cloudflare Full Strict).
- Якщо з’являються **502 / проблеми з буферами** при редіректах — можна додати в Advanced (як у вашому посібнику):

```nginx
proxy_buffer_size 128k;
proxy_buffers 4 256k;
proxy_busy_buffers_size 256k;
```

- **WebSocket:** для поточного коду бота не обов’язково; достатньо HTTP для Web App та API.

---

## 6. Cloudflare

- A-запис на IP сервера (або проксі-режим за вашою політикою).
- Режим SSL **Full (Strict)** сумісний з типовою схемою «Cloudflare → NPM → контейнер».

Переконайтеся, що не увімкнені правила WAF/Firewall, які блокують запити з **Telegram / мобільних мереж** до цього піддомену (рідко, але трапляється).

---

## 7. Безпека та бекапи

- Токен бота та `.env` не повинні потрапляти в бекапи на хмару без шифрування або окремого секретного сховища.
- SQLite (`bot_database_v6.db`) має потрапляти у **volume** і в ваш **щоденний бекап** (`backup.sh`), інакше після пересоздання контейнера дані зникнуть.

---

## 8. Моніторинг (Uptime Kuma)

Можна додати HTTP(S) check на кореневий URL Web App (код 200) або на `GET /docs` FastAPI — залежить від того, чи віддаєте ви OpenAPI публічно.

---

## 9. Зв’язок з README

Загальний опис продукту: [README.md](../README.md). Підтримка коду: [MAINTENANCE.md](MAINTENANCE.md).

---

## 10. GitHub Actions — автодеплой після `push` у `main`

У репозиторії є workflow **[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)**. Він підключається по SSH до VPS, виконує `git pull`, `docker compose up -d --build` і легке прибирання образів.

### Що відрізняється від інших ваших проєктів

- Бот працює в режимі **long polling** — кроку на кшталт `set-telegram-webhook` **немає** (і не потрібен).
- У цьому `docker-compose.yml` **немає** контейнера `nginx` — перезавантаження Nginx з workflow **не додається** (проксі — окремо, наприклад NPM).
- Змінні оточення для Compose беруться з файлу **`.env`** у каталозі проєкту (як у `env_file` у compose), а не з `.env.local` — якщо у вас на сервері інше ім’я файлу, змініть команду в workflow або уніфікуйте ім’я файлу на VPS.

### Secrets у GitHub (Settings → Secrets and variables → Actions)

| Secret | Приклад / примітка |
|--------|---------------------|
| `HOST` | Публічний IP або DNS сервера |
| `USERNAME` | Користувач SSH (наприклад `deploy`) |
| `SSH_PRIVATE_KEY` | Повний приватний ключ (вміст `id_ed25519`, з рядками `BEGIN` / `END`) |
| `SSH_PORT` | Порт SSH: **`22`** або ваш (наприклад **`2302`**) — secret обов’язковий, якщо у workflow вказано `port`; для стандарту задайте `22` |
| `DEPLOY_PATH` | **Абсолютний** шлях до клону репозиторію на сервері, наприклад `/home/deploy/apps/wartovyi` (tilde `~` у secret може не розгорнутися в лапках — краще повний шлях) |

### На VPS перед першим запуском workflow

1. Один раз клонувати репозиторій у `DEPLOY_PATH`, покласти **`.env`** поруч із `docker-compose.yml`.
2. Переконатися, що `docker compose up -d` з цього каталогу вже працює вручну.
3. Для **приватного** репозиторію: на сервері налаштувати доступ `git pull` (deploy key з read-only правами на repo, або `https` + PAT / credential helper).

### Ручний запуск

У вкладці **Actions** можна запустити workflow **Deploy to VPS** вручну (**workflow_dispatch**).

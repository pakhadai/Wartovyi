# Telegram Mini Apps — Повна документація API

> Джерело: https://core.telegram.org/bots/webapps  
> Актуально станом на: Bot API 9.5 (березень 2026)

---

## Зміст

1. [Загальна концепція](#1-загальна-концепція)
2. [Способи запуску Mini App](#2-способи-запуску-mini-app)
3. [Ініціалізація](#3-ініціалізація)
4. [Об'єкт WebApp — головний об'єкт](#4-обєкт-webapp--головний-обєкт)
5. [ThemeParams — тема оформлення](#5-themeparams--тема-оформлення)
6. [Кнопки інтерфейсу](#6-кнопки-інтерфейсу)
7. [Апаратні можливості пристрою](#7-апаратні-можливості-пристрою)
8. [Зберігання даних](#8-зберігання-даних)
9. [Події (Events)](#9-події-events)
10. [Безпека та валідація даних](#10-безпека-та-валідація-даних)
11. [Налагодження (Debug)](#11-налагодження-debug)
12. [Дизайн-гайдлайни](#12-дизайн-гайдлайни)
13. [Практичні патерни для розробника](#13-практичні-патерни-для-розробника)

---

## 1. Загальна концепція

Telegram Mini Apps — це веб-застосунки на JavaScript/HTML/CSS, що запускаються всередині Telegram. Вони мають доступ до:
- авторизації користувача (без окремого логіну)
- платежів через Telegram Stars, Google Pay, Apple Pay
- нативних UI-компонентів Telegram (кнопки, попапи, хаптики)
- апаратних можливостей пристрою (камера, геолокація, гіроскоп тощо)
- хмарного та локального сховища

Точка входу: `window.Telegram.WebApp`

---

## 2. Способи запуску Mini App

### 2.1 Keyboard Button (кнопка під полем вводу)
```
KeyboardButton { type: "web_app", web_app: { url: "https://..." } }
```
- Дані надсилаються назад боту через `Telegram.WebApp.sendData(string)`
- Дані передаються як service message (до 4096 байт)
- **Використовувати для:** кастомних форм вводу, каледарів, селекторів

### 2.2 Inline Button (кнопка під повідомленням)
```
InlineKeyboardButton { type: "web_app", web_app: { url: "https://..." } }
```
- Отримує `query_id` для надсилання відповіді через `answerWebAppQuery`
- Має доступ до базових даних користувача (ID, ім'я, username, мова)
- **Використовувати для:** повноцінних веб-сервісів

### 2.3 Menu Button (кнопка меню бота)
- Налаштовується через @BotFather або метод `setChatMenuButton`
- Працює ідентично до Inline Button
- Можна персоналізувати для кожного користувача окремо

### 2.4 Main Mini App (головний застосунок бота)
- Налаштовується через @BotFather → Bot Settings → Configure Mini App
- Показує кнопку "Launch app" у профілі бота
- Підтримує медіа-прев'ю (демо-відео/скріншоти з перекладом)
- Пряме посилання: `https://t.me/botusername?startapp` або `?startapp=command`
- За замовчуванням відкривається на повну висоту; `mode=compact` для половини екрану
- Підтримує `chat_type` та `chat_instance` для спільного використання в групах

### 2.5 Inline Mode Mini App
```
answerInlineQuery { button: { type: "web_app", ... } }
```
- Відкривається через кнопку "Switch to Mini App" над інлайн-результатами
- **Немає доступу** до чату (не може читати/надсилати повідомлення)
- Після завершення — виклик `Telegram.WebApp.switchInlineQuery()`

### 2.6 Direct Link Mini App
```
https://t.me/botusername/appname
https://t.me/botusername/appname?startapp=command
https://t.me/botusername/appname?startapp=command&mode=compact
```
- Відкривається у поточному чаті
- Підтримує `chat_type`, `chat_instance` для мультиплеєрних сценаріїв
- **Немає доступу** до надсилання повідомлень (тільки через inline mode)
- З Bot API 7.6: відкривається на повну висоту за замовчуванням

### 2.7 Attachment Menu
- Тільки для великих рекламодавців Telegram Ad Platform (або тестовий сервер для всіх)
- Посилання для додавання: `https://t.me/botusername?startattach`
- З вибором чату: `https://t.me/botusername?startattach&choose=users+bots+groups+channels`

---

## 3. Ініціалізація

### Підключення скрипту
```html
<head>
  <script src="https://telegram.org/js/telegram-web-app.js?61"></script>
  <!-- Інші скрипти ПІСЛЯ цього -->
</head>
```

### Базова ініціалізація в React/Next.js
```typescript
useEffect(() => {
  const tg = window.Telegram?.WebApp;
  if (!tg) return;

  tg.ready();          // Повідомляє Telegram, що застосунок готовий
  tg.expand();         // Розгортає на повну висоту
  
  // Опціонально — вимкнути вертикальні свайпи (якщо є власні жести)
  tg.disableVerticalSwipes();
}, []);
```

### Перевірка версії API
```typescript
if (tg.isVersionAtLeast('8.0')) {
  // Доступні fullscreen, геолокація, гіроскоп тощо
}
```

---

## 4. Об'єкт WebApp — головний об'єкт

`window.Telegram.WebApp` містить всі поля та методи Mini App.

### 4.1 Поля стану

| Поле | Тип | Опис |
|------|-----|------|
| `initData` | `string` | Рядок з сирими даними для валідації на сервері |
| `initDataUnsafe` | `WebAppInitData` | Об'єкт з даними користувача (НЕ довіряти без валідації!) |
| `version` | `string` | Версія Bot API у клієнті користувача |
| `platform` | `string` | Платформа (`ios`, `android`, `tdesktop`, `macos`, `web`) |
| `colorScheme` | `string` | `"light"` або `"dark"` |
| `themeParams` | `ThemeParams` | Поточні параметри теми |
| `isActive` | `boolean` | *Bot API 8.0+* Чи активний застосунок зараз |
| `isExpanded` | `boolean` | Чи розгорнуто на повну висоту |
| `viewportHeight` | `float` | Поточна висота видимої області (px) |
| `viewportStableHeight` | `float` | Стабільна висота (не змінюється під час анімацій) |
| `headerColor` | `string` | Колір хедера у форматі `#RRGGBB` |
| `backgroundColor` | `string` | Колір фону у форматі `#RRGGBB` |
| `bottomBarColor` | `string` | Колір нижнього бару у форматі `#RRGGBB` |
| `isClosingConfirmationEnabled` | `boolean` | Чи увімкнено підтвердження закриття |
| `isVerticalSwipesEnabled` | `boolean` | Чи увімкнені вертикальні свайпи |
| `isFullscreen` | `boolean` | *Bot API 8.0+* Чи активний повноекранний режим |
| `isOrientationLocked` | `boolean` | *Bot API 8.0+* Чи заблокована орієнтація |
| `safeAreaInset` | `SafeAreaInset` | *Bot API 8.0+* Відступи безпечної зони пристрою |
| `contentSafeAreaInset` | `ContentSafeAreaInset` | *Bot API 8.0+* Відступи безпечної зони контенту (під Telegram UI) |

### 4.2 Дочірні об'єкти

| Поле | Тип | Опис |
|------|-----|------|
| `BackButton` | `BackButton` | Кнопка "Назад" у хедері |
| `MainButton` | `BottomButton` | Головна кнопка знизу |
| `SecondaryButton` | `BottomButton` | Вторинна кнопка знизу (*Bot API 7.10+*) |
| `SettingsButton` | `SettingsButton` | Пункт "Налаштування" у контекстному меню |
| `HapticFeedback` | `HapticFeedback` | Тактильний зворотній зв'язок |
| `CloudStorage` | `CloudStorage` | Хмарне сховище (1024 ключі / користувач) |
| `BiometricManager` | `BiometricManager` | Біометрична автентифікація |
| `Accelerometer` | `Accelerometer` | *Bot API 8.0+* Акселерометр |
| `DeviceOrientation` | `DeviceOrientation` | *Bot API 8.0+* Орієнтація пристрою |
| `Gyroscope` | `Gyroscope` | *Bot API 8.0+* Гіроскоп |
| `LocationManager` | `LocationManager` | *Bot API 8.0+* Геолокація |
| `DeviceStorage` | `DeviceStorage` | *Bot API 9.0+* Локальне сховище пристрою (5 MB) |
| `SecureStorage` | `SecureStorage` | *Bot API 9.0+* Захищене сховище (Keychain/Keystore, 10 items) |

### 4.3 Методи керування виглядом

```typescript
tg.setHeaderColor('#1a1a2e');           // або 'bg_color' / 'secondary_bg_color'
tg.setBackgroundColor('#16213e');
tg.setBottomBarColor('bottom_bar_bg_color'); // Bot API 7.10+
tg.expand();                            // Розгорнути на повну висоту
tg.requestFullscreen();                 // Bot API 8.0+ — повноекранний режим
tg.exitFullscreen();                    // Bot API 8.0+
tg.lockOrientation();                   // Bot API 8.0+ — заблокувати поточну орієнтацію
tg.unlockOrientation();                 // Bot API 8.0+
```

### 4.4 Методи поведінки

```typescript
tg.enableClosingConfirmation();         // Показувати діалог при закритті
tg.disableClosingConfirmation();
tg.enableVerticalSwipes();              // Bot API 7.7+
tg.disableVerticalSwipes();
tg.hideKeyboard();                      // Bot API 9.1+ — сховати клавіатуру
tg.close();                             // Закрити застосунок
tg.ready();                             // Сигнал готовності (приховує placeholder)
```

### 4.5 Методи комунікації

```typescript
// Надіслати дані боту (тільки для Keyboard Button Mini Apps)
tg.sendData('{"action":"buy","item_id":42}');

// Відкрити посилання зовні
tg.openLink('https://example.com', { try_instant_view: true });
tg.openTelegramLink('https://t.me/username'); // Не закриває застосунок

// Відкрити інвойс
tg.openInvoice('https://t.me/$invoice', (status) => {
  // status: 'paid' | 'cancelled' | 'failed' | 'pending'
});

// Інлайн-запит після завершення
tg.switchInlineQuery('', ['users', 'bots', 'groups', 'channels']);

// Поділитися медіа (Bot API 8.0+)
tg.shareToStory('https://cdn.example.com/image.jpg', {
  text: 'Опис до 200 символів',
  widget_link: { url: 'https://t.me/mybot', name: 'Відкрити' }
});

// Поділитися повідомленням (Bot API 8.0+, потребує PreparedInlineMessage)
tg.shareMessage(msgId, (success) => { console.log(success); });

// Завантажити файл (Bot API 8.0+)
tg.downloadFile({
  url: 'https://example.com/file.pdf',
  file_name: 'document.pdf'
}, (accepted) => { console.log(accepted); });
```

### 4.6 Методи попапів

```typescript
// Нативний попап
tg.showPopup({
  title: 'Заголовок',
  message: 'Текст повідомлення (до 256 символів)',
  buttons: [
    { id: 'ok', type: 'ok' },
    { id: 'cancel', type: 'cancel' },
    { id: 'delete', type: 'destructive', text: 'Видалити' },
  ]
}, (buttonId) => {
  if (buttonId === 'ok') { /* ... */ }
});

tg.showAlert('Просте повідомлення', () => { /* після закриття */ });
tg.showConfirm('Ви впевнені?', (confirmed) => { /* boolean */ });

// QR-сканер
tg.showScanQrPopup({ text: 'Скануйте QR' }, (text) => {
  console.log(text); // отриманий текст
  return true; // закрити попап
});
tg.closeScanQrPopup();
```

### 4.7 Методи дозволів

```typescript
tg.requestWriteAccess((granted) => { /* boolean */ });
tg.requestContact((shared) => { /* boolean */ });
tg.requestEmojiStatusAccess((granted) => { /* boolean */ });

// Встановити emoji-статус
tg.setEmojiStatus('5368324170671202286', { duration: 3600 }, (success) => {});

// Home Screen Shortcut (Bot API 8.0+)
tg.addToHomeScreen();
tg.checkHomeScreenStatus((status) => {
  // 'unsupported' | 'unknown' | 'added' | 'missed'
});
```

### 4.8 Об'єкт WebAppInitData

Доступний через `tg.initDataUnsafe`:

```typescript
interface WebAppInitData {
  query_id?: string;        // Для answerWebAppQuery
  user?: WebAppUser;        // Поточний користувач
  receiver?: WebAppUser;    // Партнер у приватному чаті
  chat?: WebAppChat;        // Чат (для груп/каналів)
  chat_type?: string;       // 'sender' | 'private' | 'group' | 'supergroup' | 'channel'
  chat_instance?: string;   // Унікальний ідентифікатор чату
  start_param?: string;     // Параметр з посилання (?startapp=VALUE)
  can_send_after?: number;  // Затримка перед answerWebAppQuery
  auth_date: number;        // Unix timestamp відкриття
  hash: string;             // HMAC-SHA-256 для валідації
  signature: string;        // Ed25519 підпис для third-party валідації
}

interface WebAppUser {
  id: number;
  is_bot?: boolean;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;   // IETF (наприклад 'uk', 'en')
  is_premium?: true;
  added_to_attachment_menu?: true;
  allows_write_to_pm?: true;
  photo_url?: string;       // .jpeg або .svg
}

interface WebAppChat {
  id: number;
  type: 'group' | 'supergroup' | 'channel';
  title: string;
  username?: string;
  photo_url?: string;
}
```

---

## 5. ThemeParams — тема оформлення

Всі кольори у форматі `#RRGGBB`. Доступні також через CSS-змінні.

| Поле | CSS-змінна | Опис |
|------|-----------|------|
| `bg_color` | `--tg-theme-bg-color` | Основний фон |
| `secondary_bg_color` | `--tg-theme-secondary-bg-color` | Вторинний фон |
| `text_color` | `--tg-theme-text-color` | Основний текст |
| `hint_color` | `--tg-theme-hint-color` | Підказки/плейсхолдери |
| `link_color` | `--tg-theme-link-color` | Посилання |
| `button_color` | `--tg-theme-button-color` | Фон кнопок |
| `button_text_color` | `--tg-theme-button-text-color` | Текст кнопок |
| `header_bg_color` | `--tg-theme-header-bg-color` | Фон хедера |
| `bottom_bar_bg_color` | `--tg-theme-bottom-bar-bg-color` | Нижній бар |
| `accent_text_color` | `--tg-theme-accent-text-color` | Акцентний текст |
| `section_bg_color` | `--tg-theme-section-bg-color` | Фон секцій |
| `section_header_text_color` | `--tg-theme-section-header-text-color` | Заголовки секцій |
| `section_separator_color` | `--tg-theme-section-separator-color` | Роздільники секцій |
| `subtitle_text_color` | `--tg-theme-subtitle-text-color` | Підзаголовки |
| `destructive_text_color` | `--tg-theme-destructive-text-color` | Деструктивні дії |

**Інші CSS-змінні:**
```css
var(--tg-color-scheme)              /* 'light' або 'dark' */
var(--tg-viewport-height)           /* Висота viewport */
var(--tg-viewport-stable-height)    /* Стабільна висота viewport */
var(--tg-safe-area-inset-top)       /* Верхній відступ безпечної зони */
var(--tg-safe-area-inset-bottom)
var(--tg-safe-area-inset-left)
var(--tg-safe-area-inset-right)
var(--tg-content-safe-area-inset-top)    /* Відступ від Telegram UI зверху */
var(--tg-content-safe-area-inset-bottom)
var(--tg-content-safe-area-inset-left)
var(--tg-content-safe-area-inset-right)
```

### Підписка на зміни теми
```typescript
tg.onEvent('themeChanged', () => {
  document.body.style.backgroundColor = tg.themeParams.bg_color;
});
```

---

## 6. Кнопки інтерфейсу

### 6.1 BackButton (кнопка "Назад" у хедері)

```typescript
const back = tg.BackButton;

back.show();
back.onClick(() => {
  router.back();
  back.hide();
});

// Всі методи повертають об'єкт для chaining
back.show().onClick(handler);
```

| Поле/Метод | Опис |
|------------|------|
| `isVisible` | Чи видима |
| `show()` | Показати |
| `hide()` | Сховати |
| `onClick(cb)` | Обробник натискання |
| `offClick(cb)` | Видалити обробник |

### 6.2 BottomButton (MainButton / SecondaryButton)

```typescript
const main = tg.MainButton;
const secondary = tg.SecondaryButton;

// Налаштування головної кнопки
main.setParams({
  text: 'Оформити замовлення',
  color: '#2563eb',
  text_color: '#ffffff',
  is_active: true,
  is_visible: true,
  has_shine_effect: true,   // Bot API 7.10+
});

main.onClick(async () => {
  main.showProgress();      // Показати лоадер
  await processOrder();
  main.hideProgress();
  main.hide();
});

// Вторинна кнопка (Bot API 7.10+)
secondary.setParams({
  text: 'Скасувати',
  position: 'left',         // 'left' | 'right' | 'top' | 'bottom'
});
secondary.show();
```

| Поле/Метод | Опис |
|------------|------|
| `type` | `'main'` або `'secondary'` (readonly) |
| `text` | Поточний текст |
| `color` | Колір фону |
| `textColor` | Колір тексту |
| `isVisible` | Чи видима |
| `isActive` | Чи активна (клікабельна) |
| `hasShineEffect` | *Bot API 7.10+* Ефект блиску |
| `position` | Тільки для secondary: `'left'|'right'|'top'|'bottom'` |
| `isProgressVisible` | Чи показується лоадер (readonly) |
| `iconCustomEmojiId` | *Bot API 9.5+* Emoji перед текстом |
| `setText(text)` | Встановити текст |
| `show() / hide()` | Показати/сховати |
| `enable() / disable()` | Активувати/деактивувати |
| `showProgress(leaveActive?)` | Показати лоадер |
| `hideProgress()` | Сховати лоадер |
| `onClick(cb) / offClick(cb)` | Обробник |
| `setParams(params)` | Масове оновлення параметрів |

### 6.3 SettingsButton

```typescript
tg.SettingsButton.show();
tg.SettingsButton.onClick(() => {
  router.push('/settings');
});
```

### 6.4 HapticFeedback (тактильний відгук)

```typescript
const haptic = tg.HapticFeedback;

// При зіткненні UI-елементів
haptic.impactOccurred('light');    // 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'

// При завершенні дії
haptic.notificationOccurred('success');   // 'success' | 'error' | 'warning'

// При зміні вибору (списки, свайпери)
haptic.selectionChanged();
```

---

## 7. Апаратні можливості пристрою

### 7.1 Геолокація (Bot API 8.0+)

```typescript
const loc = tg.LocationManager;

loc.init(() => {
  if (!loc.isLocationAvailable) return;
  
  loc.getLocation((data) => {
    if (!data) {
      // Доступ не надано
      loc.openSettings(); // Відкрити налаштування
      return;
    }
    console.log(data.latitude, data.longitude);
    // data.altitude, data.course, data.speed
    // data.horizontal_accuracy, data.vertical_accuracy
  });
});
```

### 7.2 Акселерометр (Bot API 8.0+)

```typescript
const acc = tg.Accelerometer;

acc.start({ refresh_rate: 100 }, (started) => {
  if (!started) return;
});

tg.onEvent('accelerometerChanged', () => {
  console.log(acc.x, acc.y, acc.z); // м/с²
});

tg.onEvent('accelerometerFailed', (e) => {
  // e.error: 'UNSUPPORTED'
});

// Зупинити
acc.stop();
```

### 7.3 Орієнтація пристрою (Bot API 8.0+)

```typescript
const orient = tg.DeviceOrientation;

orient.start({
  refresh_rate: 50,
  need_absolute: true    // true = відносно магнітного Північ (для компасу)
}, (started) => {});

tg.onEvent('deviceOrientationChanged', () => {
  console.log(orient.alpha, orient.beta, orient.gamma); // радіани
  console.log(orient.absolute); // чи абсолютні дані
});
```

### 7.4 Гіроскоп (Bot API 8.0+)

```typescript
const gyro = tg.Gyroscope;

gyro.start({ refresh_rate: 100 }, (started) => {});

tg.onEvent('gyroscopeChanged', () => {
  console.log(gyro.x, gyro.y, gyro.z); // рад/с
});
```

### 7.5 Біометрія

```typescript
const bio = tg.BiometricManager;

bio.init(() => {
  if (!bio.isBiometricAvailable) return;
  // bio.biometricType: 'finger' | 'face' | 'unknown'
  
  bio.requestAccess({ reason: 'Для входу в акаунт' }, (granted) => {
    if (!granted) return;
    
    bio.authenticate({ reason: 'Підтвердіть особу' }, (success, token) => {
      if (success) {
        // Зберегти токен
        bio.updateBiometricToken('my_secret_token');
      }
    });
  });
});
```

### 7.6 Повноекранний режим (Bot API 8.0+)

```typescript
// Запит fullscreen
tg.requestFullscreen();

// Відслідковування
tg.onEvent('fullscreenChanged', () => {
  console.log('Fullscreen:', tg.isFullscreen);
  // Використовуйте safeAreaInset та contentSafeAreaInset
});

tg.onEvent('fullscreenFailed', (e) => {
  // e.error: 'UNSUPPORTED' | 'ALREADY_FULLSCREEN'
});

// Безпечні зони у fullscreen
const { top, bottom } = tg.contentSafeAreaInset;
// Або через CSS: var(--tg-content-safe-area-inset-top)
```

---

## 8. Зберігання даних

### 8.1 CloudStorage (хмарне, синхронізується між пристроями)

- Ліміт: **1024 ключі** на користувача
- Ключі: A-Z, a-z, 0-9, `_`, `-` (1–128 символів)
- Значення: до 4096 символів

```typescript
const cloud = tg.CloudStorage;

// Запис
cloud.setItem('cart', JSON.stringify(cartData), (err, saved) => {
  if (err) console.error(err);
});

// Читання
cloud.getItem('cart', (err, value) => {
  if (!err && value) {
    const cart = JSON.parse(value);
  }
});

// Читання кількох ключів одразу
cloud.getItems(['cart', 'wishlist'], (err, values) => {
  // values: { cart: '...', wishlist: '...' }
});

// Список всіх ключів
cloud.getKeys((err, keys) => {
  console.log(keys); // ['cart', 'wishlist', ...]
});

// Видалення
cloud.removeItem('cart');
cloud.removeItems(['cart', 'wishlist']);
```

### 8.2 DeviceStorage (локальне сховище пристрою, Bot API 9.0+)

- Ліміт: **5 MB** на бота на пристрій
- Аналог `localStorage`, але в Telegram-клієнті

```typescript
const ds = tg.DeviceStorage;

ds.setItem('theme', 'dark', (err, saved) => {});
ds.getItem('theme', (err, value) => { console.log(value); });
ds.removeItem('theme');
ds.clear(); // Видалити всі дані бота
```

### 8.3 SecureStorage (захищене сховище, Bot API 9.0+)

- iOS: **Keychain**, Android: **Keystore**
- Ліміт: **10 елементів** на бота на користувача
- Для токенів, секретів, стану авторизації

```typescript
const secure = tg.SecureStorage;

// Запис чутливих даних
secure.setItem('auth_token', 'eyJ...', (err, saved) => {});

// Читання
secure.getItem('auth_token', (err, value, canRestore) => {
  if (!value && canRestore) {
    // Значення було, але недоступне — можна відновити
    secure.restoreItem('auth_token', (err, restoredValue) => {});
  }
});

// Видалення
secure.removeItem('auth_token');
secure.clear();
```

---

## 9. Події (Events)

Підписка: `tg.onEvent(eventType, handler)`  
Відписка: `tg.offEvent(eventType, handler)`

### 9.1 Системні події

| Подія | Коли | Параметри |
|-------|------|-----------|
| `themeChanged` | Зміна теми (день/ніч) | — |
| `viewportChanged` | Зміна розміру | `{ isStateStable: boolean }` |
| `activated` | *8.0+* Застосунок активовано | — |
| `deactivated` | *8.0+* Застосунок мінімізовано | — |
| `safeAreaChanged` | *8.0+* Зміна safe area | — |
| `contentSafeAreaChanged` | *8.0+* Зміна content safe area | — |
| `fullscreenChanged` | *8.0+* Fullscreen вкл/викл | — |
| `fullscreenFailed` | *8.0+* Помилка fullscreen | `{ error: string }` |

### 9.2 Події кнопок

| Подія | Коли |
|-------|------|
| `mainButtonClicked` | Натиснута головна кнопка |
| `secondaryButtonClicked` | *7.10+* Натиснута вторинна кнопка |
| `backButtonClicked` | Натиснута кнопка "Назад" |
| `settingsButtonClicked` | Натиснуто "Налаштування" у меню |

### 9.3 Події діалогів

| Подія | Параметри |
|-------|-----------|
| `popupClosed` | `{ button_id: string \| null }` |
| `invoiceClosed` | `{ url: string, status: 'paid'\|'cancelled'\|'failed'\|'pending' }` |
| `qrTextReceived` | `{ data: string }` |
| `scanQrPopupClosed` | — |
| `clipboardTextReceived` | `{ data: string \| null }` |

### 9.4 Події дозволів

| Подія | Параметри |
|-------|-----------|
| `writeAccessRequested` | `{ status: 'allowed'\|'cancelled' }` |
| `contactRequested` | `{ status: 'sent'\|'cancelled' }` |
| `emojiStatusSet` | — |
| `emojiStatusFailed` | `{ error: string }` |
| `emojiStatusAccessRequested` | `{ status: 'allowed'\|'cancelled' }` |

### 9.5 Події медіа

| Подія | Параметри |
|-------|-----------|
| `shareMessageSent` | *8.0+* — |
| `shareMessageFailed` | *8.0+* `{ error: string }` |
| `fileDownloadRequested` | *8.0+* `{ status: 'downloading'\|'cancelled' }` |
| `homeScreenAdded` | *8.0+* — |
| `homeScreenChecked` | *8.0+* `{ status: string }` |

### 9.6 події апаратури (Bot API 8.0+)

```
accelerometerStarted / accelerometerStopped / accelerometerChanged / accelerometerFailed
deviceOrientationStarted / deviceOrientationStopped / deviceOrientationChanged / deviceOrientationFailed
gyroscopeStarted / gyroscopeStopped / gyroscopeChanged / gyroscopeFailed
locationManagerUpdated / locationRequested
biometricManagerUpdated / biometricAuthRequested / biometricTokenUpdated
```

---

## 10. Безпека та валідація даних

### 10.1 Валідація на сервері бота

**Ніколи не довіряйте `initDataUnsafe` без перевірки!**

```typescript
// На сервері (Node.js приклад)
import crypto from 'crypto';

function validateTelegramData(initData: string, botToken: string): boolean {
  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  params.delete('hash');
  
  // Сортуємо поля алфавітно та з'єднуємо через \n
  const dataCheckString = [...params.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join('\n');
  
  const secretKey = crypto
    .createHmac('sha256', 'WebAppData')
    .update(botToken)
    .digest();
  
  const expectedHash = crypto
    .createHmac('sha256', secretKey)
    .update(dataCheckString)
    .digest('hex');
  
  return expectedHash === hash;
}

// Також перевіряємо актуальність даних
const authDate = parseInt(params.get('auth_date') || '0');
const isExpired = Date.now() / 1000 - authDate > 3600; // старіші 1 год
```

### 10.2 Валідація для third-party (без токену бота)

Використовується підпис Ed25519. Third-party отримує `initData` та `bot_id`:

```
data_check_string = "{bot_id}:WebAppData\n{поля відсортовані алфавітно}"
```

Публічні ключі Telegram (hex):
- **Production:** `e7bf03a2fa4602af4580703d88dda5bb59f32ed8b02a56c187fe7d34caed242d`
- **Test:** `40055058a4ee38156a06562e52eece92a771bcd8346a8c4615cb7376eddf72ec`

### 10.3 Надсилання initData на сервер

```typescript
// На клієнті
const response = await fetch('/api/auth', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    initData: window.Telegram.WebApp.initData
  })
});
```

---

## 11. Налагодження (Debug)

### iOS
1. Telegram → Налаштування (10 натискань) → увімкнути "Allow Web View Inspection"
2. Підключити iPhone до Mac через USB
3. Safari → Develop → [Ім'я пристрою] → Mini App

### Android
1. Увімкнути USB Debugging на пристрої
2. Telegram Settings → прокрутити вниз → утримати номер версії двічі
3. Enable WebView Debug
4. Chrome: `chrome://inspect/#devices`

### Telegram Desktop (Windows/Linux)
1. Завантажити Beta версію
2. Settings → Advanced → Experimental → Enable webview inspection
3. ПКМ у WebView → Inspect

### Telegram macOS
1. Beta версія
2. 5 кліків на іконку Settings → Debug Menu → "Debug Mini Apps"
3. ПКМ → Inspect Element

### Тестовий сервер Telegram
- iOS: Settings (10 тап) → Accounts → Login to another account → Test
- Desktop: ☰ Settings → Shift+Alt+ПКМ "Add Account" → Test Server
- API endpoint: `https://api.telegram.org/bot<token>/test/METHOD_NAME`
- У тестовому середовищі **дозволені HTTP** посилання (без TLS)

---

## 12. Дизайн-гайдлайни

### Обов'язкові вимоги
- **Mobile-first:** всі елементи адаптивні, розроблені для мобільного
- **Тема:** завжди використовувати кольори з `themeParams` та CSS-змінні `--tg-theme-*`
- **Safe Area:** враховувати `safeAreaInset` та `contentSafeAreaInset` в fullscreen
- **Анімації:** 60fps, плавні; на Android Low-performance пристроях — мінімізувати

### Рекомендації
- Нативні UI-компоненти Telegram (кнопки, попапи) замість кастомних де можливо
- Тактильний відгук (`HapticFeedback`) для підтвердження дій
- `tg.ready()` викликати якомога раніше
- Використовувати `viewportStableHeight` для позиціонування елементів внизу екрану (не `viewportHeight`)

### Повноекранний режим
```css
/* Паддінг під системний UI */
.app-container {
  padding-top: var(--tg-content-safe-area-inset-top);
  padding-bottom: var(--tg-content-safe-area-inset-bottom);
}
```

### Оптимізація для Android
Перевіряти `User-Agent` для адаптації:
```
Telegram-Android/11.3.3 (Google Pixel 8; Android 14; SDK 34; HIGH)
```
Performance class: `LOW` | `AVERAGE` | `HIGH`

```javascript
const ua = navigator.userAgent;
const perfMatch = ua.match(/SDK \d+; (LOW|AVERAGE|HIGH)/);
const perfClass = perfMatch?.[1] ?? 'HIGH';

if (perfClass === 'LOW') {
  // Вимкнути важкі анімації
}
```

---

## 13. Практичні патерни для розробника

### 13.1 Хук для React/Next.js

```typescript
// hooks/useTelegram.ts
import { useEffect, useState } from 'react';

interface TelegramWebApp {
  ready: () => void;
  expand: () => void;
  close: () => void;
  initDataUnsafe: {
    user?: {
      id: number;
      first_name: string;
      last_name?: string;
      username?: string;
      language_code?: string;
      photo_url?: string;
    };
    start_param?: string;
  };
  themeParams: Record<string, string>;
  colorScheme: 'light' | 'dark';
  MainButton: any;
  BackButton: any;
  HapticFeedback: any;
  onEvent: (event: string, handler: Function) => void;
  offEvent: (event: string, handler: Function) => void;
  isVersionAtLeast: (version: string) => boolean;
}

export function useTelegram() {
  const [tg, setTg] = useState<TelegramWebApp | null>(null);
  
  useEffect(() => {
    const webapp = (window as any).Telegram?.WebApp as TelegramWebApp;
    if (webapp) {
      webapp.ready();
      webapp.expand();
      setTg(webapp);
    }
  }, []);
  
  return {
    tg,
    user: tg?.initDataUnsafe?.user,
    colorScheme: tg?.colorScheme ?? 'light',
    isDark: tg?.colorScheme === 'dark',
  };
}
```

### 13.2 Головна кнопка з автоматичним станом

```typescript
// hooks/useMainButton.ts
import { useEffect } from 'react';

export function useMainButton(
  text: string,
  onClick: () => void | Promise<void>,
  enabled = true
) {
  const tg = (window as any).Telegram?.WebApp;
  
  useEffect(() => {
    if (!tg?.MainButton) return;
    const btn = tg.MainButton;
    
    btn.setText(text);
    enabled ? btn.enable() : btn.disable();
    btn.show();
    
    const handler = async () => {
      btn.showProgress();
      try { await onClick(); } finally { btn.hideProgress(); }
    };
    
    btn.onClick(handler);
    return () => {
      btn.offClick(handler);
      btn.hide();
    };
  }, [text, enabled]);
}
```

### 13.3 Адаптивна тема

```typescript
// providers/TelegramThemeProvider.tsx
import { useEffect } from 'react';

export function TelegramThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp;
    if (!tg) return;
    
    const applyTheme = () => {
      const root = document.documentElement;
      const p = tg.themeParams;
      
      // Застосувати всі Telegram-кольори як CSS-змінні
      Object.entries(p).forEach(([key, val]) => {
        root.style.setProperty(`--tg-${key.replace(/_/g, '-')}`, val as string);
      });
      
      root.setAttribute('data-theme', tg.colorScheme);
    };
    
    applyTheme();
    tg.onEvent('themeChanged', applyTheme);
    return () => tg.offEvent('themeChanged', applyTheme);
  }, []);
  
  return <>{children}</>;
}
```

### 13.4 Безпечна зона у fullscreen

```typescript
// hooks/useSafeArea.ts
import { useEffect, useState } from 'react';

export function useSafeArea() {
  const [insets, setInsets] = useState({ top: 0, bottom: 0, left: 0, right: 0 });
  
  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp;
    if (!tg?.isVersionAtLeast('8.0')) return;
    
    const update = () => {
      const c = tg.contentSafeAreaInset;
      setInsets({ top: c.top, bottom: c.bottom, left: c.left, right: c.right });
    };
    
    update();
    tg.onEvent('contentSafeAreaChanged', update);
    return () => tg.offEvent('contentSafeAreaChanged', update);
  }, []);
  
  return insets;
}
```

### 13.5 Сховище з fallback

```typescript
// lib/storage.ts
const tg = () => (window as any).Telegram?.WebApp;

export const storage = {
  async get(key: string): Promise<string | null> {
    return new Promise((resolve) => {
      const cloud = tg()?.CloudStorage;
      if (cloud) {
        cloud.getItem(key, (err: any, val: string) => resolve(err ? null : val));
      } else {
        resolve(localStorage.getItem(key));
      }
    });
  },
  
  async set(key: string, value: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const cloud = tg()?.CloudStorage;
      if (cloud) {
        cloud.setItem(key, value, (err: any) => err ? reject(err) : resolve());
      } else {
        localStorage.setItem(key, value);
        resolve();
      }
    });
  }
};
```

### 13.6 Верифікація initData (Next.js API route)

```typescript
// app/api/auth/route.ts
import crypto from 'crypto';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  const { initData } = await req.json();
  
  if (!initData) {
    return NextResponse.json({ error: 'No initData' }, { status: 400 });
  }
  
  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  params.delete('hash');
  
  const dataCheckString = [...params.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join('\n');
  
  const secretKey = crypto
    .createHmac('sha256', 'WebAppData')
    .update(process.env.BOT_TOKEN!)
    .digest();
  
  const expectedHash = crypto
    .createHmac('sha256', secretKey)
    .update(dataCheckString)
    .digest('hex');
  
  if (expectedHash !== hash) {
    return NextResponse.json({ error: 'Invalid data' }, { status: 403 });
  }
  
  // Перевірка актуальності (не старіше 24 годин)
  const authDate = parseInt(params.get('auth_date') || '0');
  if (Date.now() / 1000 - authDate > 86400) {
    return NextResponse.json({ error: 'Data expired' }, { status: 403 });
  }
  
  const user = JSON.parse(params.get('user') || '{}');
  return NextResponse.json({ user, valid: true });
}
```

---

## Підсумок версій API

| Версія | Ключові нові можливості |
|--------|------------------------|
| 6.1 | BackButton, HapticFeedback, openLink, setHeaderColor |
| 6.2 | showPopup/Alert/Confirm, closingConfirmation |
| 6.4 | QR-сканер, clipboard |
| 6.7 | switchInlineQuery, Direct Link Mini Apps |
| 6.9 | CloudStorage, requestWriteAccess, requestContact |
| 7.0 | SettingsButton, нові кольори теми |
| 7.2 | BiometricManager |
| 7.6 | section_separator_color, Direct Link = fullscreen за замовчуванням |
| 7.7 | enableVerticalSwipes/disableVerticalSwipes |
| 7.8 | shareToStory, Main Mini App |
| 7.10 | SecondaryButton, bottomBarColor, shine effect |
| **8.0** | Fullscreen, safe areas, геолокація, гіроскоп/акселерометр/орієнтація, завантаження файлів, emoji статус, shareMessage, homeScreen shortcuts |
| 9.0 | DeviceStorage (5MB), SecureStorage (Keychain/Keystore) |
| 9.1 | hideKeyboard() |
| **9.5** | iconCustomEmojiId для BottomButton |

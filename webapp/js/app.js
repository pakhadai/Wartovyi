async function wartovyiRunBrowserLanding() {
    let meta = {};
    try {
        const mr = await fetch('/api/meta');
        if (mr.ok) meta = await mr.json();
    } catch (e) { /* noop */ }
    const botUrl = meta.bot_url || 'https://t.me/WartovyiBot';
    const addGroupUrl = meta.add_bot_to_group_url || 'https://t.me/WartovyiBot?startgroup';
    const lo = document.getElementById('landing-open-bot');
    const la = document.getElementById('landing-add-group');
    if (lo) lo.href = botUrl;
    if (la) la.href = addGroupUrl;

    async function applyLandingTranslations(lang) {
        let primary = {};
        let fallback = {};
        try {
            const r = await fetch(`/api/translations/${lang}`);
            if (r.ok) primary = await r.json();
            const fr = await fetch('/api/translations/en');
            if (fr.ok) fallback = await fr.json();
        } catch (e) { /* noop */ }
        const tr = { ...fallback, ...primary };
        document.querySelectorAll('#browser-landing [data-translate]').forEach((el) => {
            const key = el.dataset.translate;
            el.innerHTML = tr[key] || key;
        });
    }

    document.querySelectorAll('.landing-lang-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const lang = btn.dataset.lang || 'uk';
            localStorage.setItem('landing_lang', lang);
            applyLandingTranslations(lang);
        });
    });

    const saved = localStorage.getItem('landing_lang') || 'uk';
    await applyLandingTranslations(saved);
}

document.addEventListener('DOMContentLoaded', async () => {
    const isTelegramMiniApp = document.documentElement.classList.contains('wartovyi-telegram');
    if (!isTelegramMiniApp) {
        await wartovyiRunBrowserLanding();
        return;
    }

    const twa = window.Telegram?.WebApp;
    if (!twa) {
        await wartovyiRunBrowserLanding();
        return;
    }

    const tg = twa;
    tg.ready();
    tg.expand();

    try {
        if (tg.isVersionAtLeast?.('7.7')) tg.disableVerticalSwipes();
    } catch (e) { /* noop */ }
    try {
        tg.enableClosingConfirmation();
    } catch (e) { /* noop */ }

    function applyTelegramContentInsets() {
        let top = 0;
        let bottom = 0;
        if (tg.isVersionAtLeast?.('8.0')) {
            top = tg.contentSafeAreaInset?.top || 0;
            bottom = tg.contentSafeAreaInset?.bottom || 0;
        } else {
            const p = (tg.platform || '').toLowerCase();
            if (p === 'ios' || p === 'android') top = 52;
        }
        document.documentElement.style.setProperty('--tg-content-inset-top', `${top}px`);
        document.documentElement.style.setProperty('--tg-content-inset-bottom', `${bottom}px`);
    }
    applyTelegramContentInsets();
    try {
        tg.onEvent('safeAreaChanged', applyTelegramContentInsets);
        tg.onEvent('contentSafeAreaChanged', applyTelegramContentInsets);
    } catch (e) { /* noop */ }

    // 2. Глобальні змінні та безпечна ідентифікація користувача
    let translations = {};
    const userLang = tg.initDataUnsafe?.user?.language_code || 'en';
    let selectedChatId = null;
    let chatsLoaded = false;
    let managedGroupCount = 0;

    const hasSignedInit = !!(tg.initData && String(tg.initData).trim());
    let userData = null;
    try {
        if (tg.initDataUnsafe?.user && Object.keys(tg.initDataUnsafe.user).length > 0) {
            userData = JSON.stringify(tg.initDataUnsafe.user);
        }
    } catch (e) {
        tg.showAlert('Критична помилка: не вдалося обробити дані користувача.');
        return;
    }

    if (!userData && !hasSignedInit) {
        tg.showAlert('Помилка: не вдалося ідентифікувати користувача. Перезапустіть Web App.');
        return;
    }
    if (!userData) {
        userData = JSON.stringify(tg.initDataUnsafe?.user || { id: 0, first_name: '' });
    }

    const encodedUserData = btoa(unescape(encodeURIComponent(userData || '{}')));

    function getApiHeaders() {
        const h = { 'Content-Type': 'application/json' };
        const idt = tg.initData && String(tg.initData).trim();
        if (idt) h['X-Telegram-Init-Data'] = idt;
        h['X-User-Data'] = encodedUserData;
        return h;
    }
    // 3. Пошук основних елементів на сторінці (DOM)
    const pages = document.querySelectorAll('.page');
    const navButtons = document.querySelectorAll('.nav-btn');
    const chatSelector = document.getElementById('chat-selector');
    const settingsOnboarding = document.getElementById('settings-onboarding');
    const settingsContent = document.getElementById('settings-content');
    const settingsContainer = document.getElementById('settings-container');
    const settingsLoader = document.getElementById('settings-loader');
    const toastElement = document.getElementById('toast-notification');
    let toastTimeout;
    const themeToggleButton = document.getElementById('theme-toggle');

    // 4. Мультимовність та сповіщення
    async function loadTranslations(lang) {
        let primaryTranslations = {};
        let fallbackTranslations = {};
        try {
            const response = await fetch(`/api/translations/${lang}`);
            if(response.ok) primaryTranslations = await response.json();

            const fallbackResponse = await fetch(`/api/translations/en`);
            if(fallbackResponse.ok) fallbackTranslations = await fallbackResponse.json();

        } catch (error) {
            console.error("Failed to load translations:", error);
        } finally {
            translations = { ...fallbackTranslations, ...primaryTranslations };
            applyTranslations();
        }
    }

    function t(key) {
        return translations[key] || `[${key}]`;
    }

    function applyTranslations() {
        document.querySelectorAll('[data-translate]').forEach(el => {
            const key = el.dataset.translate;
            const target = el.placeholder ? 'placeholder' : 'innerHTML';
            el[target] = t(key);
        });
    }

    function showToast(message, isError = false) {
        clearTimeout(toastTimeout);
        toastElement.textContent = message;
        toastElement.className = 'toast show';
        if (isError) toastElement.classList.add('error');
        toastTimeout = setTimeout(() => { toastElement.className = 'toast'; }, 2500);
    }

    const THEME_MODES = ['telegram', 'dark', 'light'];
    let themeChangedBound = null;

    function detachTelegramThemeListener() {
        if (themeChangedBound) {
            try { tg.offEvent('themeChanged', themeChangedBound); } catch (e) { /* noop */ }
            themeChangedBound = null;
        }
    }

    function clearTelegramCssVariables() {
        const root = document.documentElement;
        ['--bg', '--surface', '--surface-2', '--text', '--text-dim', '--accent', '--border'].forEach((k) => {
            root.style.removeProperty(k);
        });
    }

    function injectTelegramThemeParams() {
        const tp = tg.themeParams || {};
        const root = document.documentElement;
        const set = (prop, val) => {
            if (val) root.style.setProperty(prop, val);
        };
        set('--bg', tp.bg_color);
        set('--surface', tp.secondary_bg_color);
        set('--surface-2', tp.section_bg_color || tp.secondary_bg_color);
        set('--text', tp.text_color);
        set('--text-dim', tp.hint_color || tp.subtitle_text_color);
        set('--accent', tp.button_color || tp.link_color);
        if (tp.section_separator_color) set('--border', tp.section_separator_color);
        root.setAttribute('data-color-scheme', tg.colorScheme || '');
    }

    function syncTelegramChromeColors() {
        try {
            tg.setHeaderColor('secondary_bg_color');
            tg.setBackgroundColor('bg_color');
            if (tg.isVersionAtLeast?.('7.10') && tg.themeParams?.bottom_bar_bg_color) {
                tg.setBottomBarColor(tg.themeParams.bottom_bar_bg_color);
            }
        } catch (e) { /* noop */ }
    }

    function applyCustomChromeFromCss() {
        setTimeout(() => {
            const styles = getComputedStyle(document.body);
            const header = styles.getPropertyValue('--surface').trim() || '#18181b';
            const bg = styles.getPropertyValue('--bg').trim() || '#09090b';
            try {
                tg.setHeaderColor(header);
                tg.setBackgroundColor(bg);
            } catch (e) { /* noop */ }
        }, 50);
    }

    function applyThemeMode(mode) {
        const meta = document.querySelector('meta[name="theme-color"]');
        if (mode === 'telegram') {
            document.body.classList.add('telegram-theme-active');
            detachTelegramThemeListener();
            injectTelegramThemeParams();
            syncTelegramChromeColors();
            themeChangedBound = () => {
                injectTelegramThemeParams();
                syncTelegramChromeColors();
            };
            tg.onEvent('themeChanged', themeChangedBound);
            if (meta) meta.setAttribute('content', tg.themeParams?.bg_color || '#09090b');
            return;
        }
        document.body.classList.remove('telegram-theme-active');
        detachTelegramThemeListener();
        clearTelegramCssVariables();
        document.body.classList.toggle('light-theme', mode === 'light');
        if (meta) meta.setAttribute('content', mode === 'light' ? '#f4f4f5' : '#09090b');
        applyCustomChromeFromCss();
    }

    function getThemeMode() {
        return localStorage.getItem('wartovyiTheme') || 'telegram';
    }

    function setThemeMode(mode) {
        localStorage.setItem('wartovyiTheme', mode);
    }

    if (!localStorage.getItem('wartovyiTheme') && localStorage.getItem('theme')) {
        setThemeMode(localStorage.getItem('theme') === 'light' ? 'light' : 'dark');
    }

    themeToggleButton.addEventListener('click', () => {
        const order = THEME_MODES;
        let i = order.indexOf(getThemeMode());
        if (i < 0) i = 0;
        const next = order[(i + 1) % order.length];
        setThemeMode(next);
        applyThemeMode(next);
    });

    // === КЕРУВАННЯ МОВОЮ (НОВА ВЕРСІЯ) ===
    const langToggleButton = document.getElementById('lang-toggle');
    const langOptions = document.querySelectorAll('.lang-option');
    const availableLangs = Array.from(langOptions).map(opt => opt.dataset.lang);

    function setLanguage(langCode) {
        // Переконуємось, що переданий код мови є валідним
        const validLang = availableLangs.includes(langCode) ? langCode : availableLangs[0];

        langOptions.forEach(opt => {
            opt.classList.toggle('hidden', opt.dataset.lang !== validLang);
        });
        localStorage.setItem('language', validLang);
        // Повертаємо Promise, щоб можна було продовжити ланцюжок
        return loadTranslations(validLang);
    }

    langToggleButton.addEventListener('click', () => {
        const currentLangEl = langToggleButton.querySelector('.lang-option:not(.hidden)');
        const currentLang = currentLangEl ? currentLangEl.dataset.lang : availableLangs[0];
        const currentIndex = availableLangs.indexOf(currentLang);
        const nextIndex = (currentIndex + 1) % availableLangs.length;
        const newLang = availableLangs[nextIndex];

        try { tg.HapticFeedback?.impactOccurred('light'); } catch (e) { /* noop */ }
        setLanguage(newLang);
    });

    // 5. Навігація між сторінками
    function showPage(pageId) {
        pages.forEach(page => page.classList.toggle('active', page.id === pageId));
        navButtons.forEach(btn => btn.classList.toggle('active', btn.dataset.page === pageId));

        if (pageId === 'settings-page' && !chatsLoaded) {
            loadUserChats();
        }
        if (pageId === 'stats-page' && window.statsModule && !window.statsModule.chatsLoaded) {
            window.statsModule.loadChats();
        }
    }

    // 6. Логіка сторінки "Налаштування"
    async function loadUserChats() {
        let meta = {};
        try {
            const mr = await fetch('/api/meta');
            if (mr.ok) meta = await mr.json();
        } catch (e) { /* noop */ }
        const obLink = document.getElementById('onboarding-add-bot-link');
        if (obLink && meta.add_bot_to_group_url) obLink.href = meta.add_bot_to_group_url;

        chatSelector.innerHTML = `<option value="">${t('loading_chats')}</option>`;
        settingsContent.classList.add('hidden');
        if (settingsOnboarding) settingsOnboarding.classList.add('hidden');
        try {
            const response = await fetch('/api/my-chats', { headers: getApiHeaders() });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const chats = await response.json();
            chatsLoaded = true;
            managedGroupCount = chats.length;

            chatSelector.innerHTML = `<option value="">-- ${t('select_chat_placeholder')} --</option>`;

            let canGlobal = false;
            try {
                const gr = await fetch('/api/settings/global', { headers: getApiHeaders() });
                canGlobal = gr.ok;
            } catch (e) {
                canGlobal = false;
            }
            if (canGlobal) {
                const defaultOption = document.createElement('option');
                defaultOption.value = 'global';
                defaultOption.textContent = `⚙️ ${t('default_settings')}`;
                chatSelector.appendChild(defaultOption);
            }

            if (chats.length > 0) {
                chats.forEach(chat => {
                    const option = document.createElement('option');
                    option.value = chat.id;
                    option.textContent = chat.name;
                    chatSelector.appendChild(option);
                });
                if (settingsOnboarding) settingsOnboarding.classList.add('hidden');
            } else {
                if (settingsOnboarding) settingsOnboarding.classList.remove('hidden');
                if (chatSelector.options.length === 1) {
                    chatSelector.innerHTML = `<option value="">-- ${t('no_managed_chats')} --</option>`;
                }
            }
        } catch (error) {
            console.error('Failed to load user chats:', error);
            tg.showAlert(`Помилка завантаження чатів: ${error.message}`);
            chatSelector.innerHTML = `<option value="">-- Помилка завантаження --</option>`;
        }
    }

    async function loadChatSettings(chatId) {
        if (!chatId) return;

        settingsLoader.classList.remove('hidden');
        settingsContainer.classList.add('hidden');
        document.getElementById('punishments-container').parentElement.classList.add('hidden'); // Ховаємо блок покарань

        const isGlobal = chatId === 'global';
        document.querySelectorAll('#settings-content .manage-list-btn').forEach(btn => btn.style.display = isGlobal ? 'none' : 'block');
        // Глобальні налаштування не мають гнучких покарань
        document.getElementById('punishments-container').parentElement.style.display = isGlobal ? 'none' : 'block';


        try {
            // Завантажуємо основні налаштування
            const settingsResponse = await fetch(`/api/settings/${chatId}`, { headers: getApiHeaders() });
            if (!settingsResponse.ok) throw new Error('Не вдалося завантажити налаштування.');
            const settings = await settingsResponse.json();

            document.getElementById('captcha-toggle').checked = settings.captcha_enabled;
            document.getElementById('spamfilter-toggle').checked = settings.spam_filter_enabled;
            document.getElementById('use-global-list-toggle').checked = settings.use_global_list;
            document.getElementById('use-custom-list-toggle').checked = settings.use_custom_list;
            document.getElementById('spam-threshold').value = settings.spam_threshold;
            document.getElementById('antiflood-toggle').checked = settings.antiflood_enabled;
            document.getElementById('antiflood-sensitivity').value = settings.antiflood_sensitivity;

            // Завантажуємо налаштування покарань, якщо це не глобальні налаштування
            if (!isGlobal) {
                const punishmentsResponse = await fetch(`/api/punishments/${chatId}`, { headers: getApiHeaders() });
                if (!punishmentsResponse.ok) throw new Error('Не вдалося завантажити правила покарань.');
                const punishments = await punishmentsResponse.json();

                for (const level in punishments) {
                    const rule = punishments[level];
                    const actionSelector = document.querySelector(`.action-selector[data-level='${level}']`);
                    const durationInput = document.querySelector(`.duration-input[data-level='${level}']`);

                    if (actionSelector) actionSelector.value = rule.action;
                    if (durationInput) {
                        durationInput.value = rule.duration;
                        durationInput.disabled = rule.action === 'ban'; // Робимо поле неактивним, якщо дія - бан
                    }
                }
            }

        } catch (error) {
            tg.showAlert(error.message);
        } finally {
            settingsLoader.classList.add('hidden');
            settingsContainer.classList.remove('hidden');
            if (chatId !== 'global') {
                 document.getElementById('punishments-container').parentElement.classList.remove('hidden');
            }
        }
    }

    async function handleSettingUpdate(key, value) {
        if (!selectedChatId) return;
        try {
            const response = await fetch(`/api/settings/${selectedChatId}`, {
                method: 'POST',
                headers: getApiHeaders(),
                body: JSON.stringify({ key, value })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || 'Не вдалося зберегти.');
            try { tg.HapticFeedback?.notificationOccurred('success'); } catch (e) { /* noop */ }
            showToast(`✅ ${t('changes_saved') || 'Зміни збережено'}`);
        } catch (e) {
            try { tg.HapticFeedback?.notificationOccurred('error'); } catch (err) { /* noop */ }
            showToast(`❌ ${t('error_saving') || 'Помилка збереження'}: ${e.message}`, true);
            loadChatSettings(selectedChatId);
        }
    }

    async function handlePunishmentUpdate(level, action, duration) {
        if (!selectedChatId) return;
        try {
            const response = await fetch(`/api/punishments/${selectedChatId}`, {
                method: 'POST',
                headers: getApiHeaders(),
                body: JSON.stringify({ level, action, duration })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || 'Не вдалося зберегти.');
            try { tg.HapticFeedback?.notificationOccurred('success'); } catch (e) { /* noop */ }
            showToast(`✅ ${t('changes_saved') || 'Зміни збережено'}`);
        } catch (e) {
            try { tg.HapticFeedback?.notificationOccurred('error'); } catch (err) { /* noop */ }
            showToast(`❌ ${t('error_saving') || 'Помилка збереження'}: ${e.message}`, true);
            loadChatSettings(selectedChatId); // Перезавантажуємо налаштування у випадку помилки
        }
    }

    // === МОДУЛЬ КЕРУВАННЯ СТОРІНКОЮ СПИСКІВ СЛІВ ===
    const wordListPageModule = {
        page: document.getElementById('word-list-page'),
        title: document.getElementById('word-list-title'),
        listUl: document.getElementById('word-list-ul'),
        currentListType: null,

        init() {
            document.getElementById('back-to-settings-btn').addEventListener('click', () => this.hide());
            document.getElementById('manage-blocklist-btn').addEventListener('click', () => this.show('blocklist'));
            document.getElementById('manage-whitelist-btn').addEventListener('click', () => this.show('whitelist'));
            document.getElementById('add-blocklist-btn').addEventListener('click', () => this.addWord());
            document.getElementById('add-whitelist-btn').addEventListener('click', () => this.addWord());
        },

        show(listType) {
            if (!selectedChatId || selectedChatId === 'global') {
                showToast('Спочатку виберіть групу', true);
                return;
            }
            this.currentListType = listType;
            const isBlocklist = listType === 'blocklist';

            // Оновлюємо заголовок
            this.title.innerText = isBlocklist ? t('blocklist_title') : t('whitelist_title');

            // Показуємо правильну картку
            const blocklistCard = document.getElementById('blocklist-add-card');
            const whitelistCard = document.getElementById('whitelist-add-card');

            if (blocklistCard) {
                blocklistCard.style.display = isBlocklist ? 'block' : 'none';
            }
            if (whitelistCard) {
                whitelistCard.style.display = isBlocklist ? 'none' : 'block';
            }

            // Показуємо сторінку
            this.page.classList.remove('hidden');
            tg.BackButton.show();
            tg.onEvent('backButtonClicked', this.hide.bind(this));
            this.loadList();
        },

        hide() {
            this.page.classList.add('hidden');
            tg.BackButton.hide();
            tg.offEvent('backButtonClicked', this.hide.bind(this));
        },

        async loadList() {
            this.listUl.innerHTML = `<li>${t('loading_chats')}</li>`;
            try {
                const endpoint = this.currentListType === 'blocklist' ? `/api/spam-words/${selectedChatId}` : `/api/whitelist/${selectedChatId}`;
                const response = await fetch(endpoint, { headers: getApiHeaders() });
                if (!response.ok) throw new Error('Failed to load list');
                const data = await response.json();

                this.listUl.innerHTML = '';
                if (this.currentListType === 'blocklist') {
                    if (Object.keys(data).length === 0) this.listUl.innerHTML = `<li>${t('spam_words_empty')}</li>`;
                    for (const [word, score] of Object.entries(data)) { this.renderItem(word, score); }
                } else {
                    if (data.length === 0) this.listUl.innerHTML = `<li>${t('spam_words_empty')}</li>`;
                    data.forEach(word => this.renderItem(word));
                }
            } catch (error) { this.listUl.innerHTML = `<li>Помилка завантаження</li>`; }
        },

        renderItem(word, score = null) {
            const li = document.createElement('li');
            li.dataset.word = word;
            let content = `<span class="word-text">${word}</span>`;
            if (score) {
                content = `<div>${content}<span class="word-score">${score}</span></div>`;
            }
            li.innerHTML = `${content}<button class="delete-btn">×</button>`;
            li.querySelector('.delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteWord(word);
            });
            this.listUl.appendChild(li);
        },

        async addWord() {
            const type = this.currentListType;
            const wordInput = document.getElementById(`new-${type}-word`);
            const word = wordInput.value.trim().toLowerCase();
            if (!word) return;

            let endpoint, body;
            let score = null;
            if (type === 'blocklist') {
                score = parseInt(document.getElementById('new-blocklist-score').value);
                endpoint = `/api/spam-words/${selectedChatId}`;
                body = JSON.stringify({ trigger: word, score });
            } else {
                endpoint = `/api/whitelist/${selectedChatId}`;
                body = JSON.stringify({ word });
            }

            try {
                const response = await fetch(endpoint, { method: 'POST', headers: getApiHeaders(), body });
                if (!response.ok) throw new Error((await response.json()).detail || 'Failed to add word');
                showToast(t('changes_saved'));
                wordInput.value = '';
                if (this.listUl.querySelector('li')?.innerText === t('spam_words_empty')) {
                    this.listUl.innerHTML = '';
                }
                this.renderItem(word, score);
            } catch (error) { showToast(`${t('error_saving')}: ${error.message}`, true); }
        },

        async deleteWord(word) {
            if (!confirm(`${t('confirm_delete_word')} "${word}"?`)) return;
            try {
                const type = this.currentListType;
               const endpoint = type === 'blocklist' ? `/api/spam-words/${selectedChatId}` : `/api/whitelist/${selectedChatId}`;
                const body = JSON.stringify(type === 'blocklist' ? { trigger: word } : { word: word });

                const response = await fetch(endpoint, { method: 'DELETE', headers: getApiHeaders(), body });
                if (!response.ok) throw new Error('Failed to delete word');

                showToast(t('word_deleted'));
                document.querySelector(`#word-list-ul li[data-word="${word}"]`)?.remove();
                if (this.listUl.children.length === 0) {
                    this.listUl.innerHTML = `<li>${t('spam_words_empty')}</li>`;
                }
            } catch (error) { showToast(t('error_saving'), true); }
        }
    };
    // === МОДУЛЬ СТАТИСТИКИ ===
    window.statsModule = {
        currentChatId: null,
        currentPeriod: 7,
        charts: {},
        chatsLoaded: false,

        init() {
            const statsChatSelector = document.getElementById('stats-chat-selector');
            if (statsChatSelector) {
                statsChatSelector.addEventListener('change', (e) => {
                    this.currentChatId = e.target.value;
                    if (this.currentChatId) this.loadStats();
                    else document.getElementById('stats-container').classList.add('hidden');
                });
            }
            document.querySelectorAll('.period-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const el = e.currentTarget;
                    document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
                    el.classList.add('active');
                    this.currentPeriod = parseInt(el.dataset.days, 10);
                    if (this.currentChatId) this.loadStats();
                });
            });
            const exportBtn = document.getElementById('export-stats-btn');
            if (exportBtn) {
                exportBtn.addEventListener('click', () => this.exportStats());
            }
        },

        async loadChats() {
            const selector = document.getElementById('stats-chat-selector');
            const hint = document.getElementById('stats-onboarding-hint');
            selector.innerHTML = `<option value="">${t('loading_chats')}</option>`;
            if (hint) hint.classList.add('hidden');
            try {
                const response = await fetch('/api/my-chats', { headers: getApiHeaders() });
                if (!response.ok) throw new Error('Failed to load chats');
                const chats = await response.json();
                this.chatsLoaded = true;
                selector.innerHTML = `<option value="">-- ${t('select_chat_placeholder')} --</option>`;
                chats.forEach(chat => {
                    const option = document.createElement('option');
                    option.value = chat.id;
                    option.textContent = chat.name;
                    selector.appendChild(option);
                });
                if (hint) {
                    if (chats.length === 0) hint.classList.remove('hidden');
                    else hint.classList.add('hidden');
                }
            } catch (error) {
                console.error('Error loading chats for stats:', error);
                selector.innerHTML = `<option value="">Error loading chats</option>`;
            }
        },

        async loadStats() {
            const container = document.getElementById('stats-container');
            const noDataContainer = document.getElementById('no-stats-data');
            container.classList.add('hidden');
            noDataContainer.classList.add('hidden');
            try {
                const response = await fetch(`/api/stats/${this.currentChatId}?days=${this.currentPeriod}`, { headers: getApiHeaders() });
                if (!response.ok) throw new Error('Failed to load stats');
                const data = await response.json();
                this.renderStats(data);
                container.classList.remove('hidden');
            } catch (error) {
                console.error('Error loading stats:', error);
                noDataContainer.classList.remove('hidden');
            }
        },

        renderStats(data) {
            const { historical, current } = data;
            const totals = historical.totals || {};
            document.getElementById('total-messages').textContent = this.formatNumber(totals.total_messages || 0);
            document.getElementById('spam-blocked').textContent = this.formatNumber(totals.total_deleted || 0);
            const userGrowth = (totals.total_joined || 0) - (totals.total_left || 0);
            document.getElementById('user-growth').textContent = (userGrowth >= 0 ? '+' : '') + userGrowth;
            const captchaTotal = (totals.total_captcha_passed || 0) + (totals.total_captcha_failed || 0);
            const captchaRate = captchaTotal > 0 ? Math.round((totals.total_captcha_passed / captchaTotal) * 100) : 0;
            document.getElementById('captcha-success').textContent = captchaRate + '%';
            this.drawActivityChart(historical.daily || []);
            this.drawHourlyChart(historical.hourly_activity || []);
            this.renderViolators(historical.top_violators || []);
            this.renderCurrentStatus(current);
        },

        drawActivityChart(dailyData) {
            const canvas = document.getElementById('activity-chart');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const labels = dailyData.map(d => this.formatDate(d.date));
            const messagesData = dailyData.map(d => d.messages_total || 0);
            const deletedData = dailyData.map(d => d.messages_deleted || 0);

            this.drawSimpleLineChart(ctx, labels, [
                { data: messagesData, color: '#6366f1', label: t('stat_messages') },
                { data: deletedData, color: '#f87171', label: t('stat_chart_deleted') }
            ]);
        },

        drawHourlyChart(hourlyData) {
            const canvas = document.getElementById('hourly-chart');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const hours = Array.from({length: 24}, (_, i) => i);
            const data = new Array(24).fill(0);

            hourlyData.forEach(item => {
                const hour = parseInt(item.hour);
                data[hour] = item.count;
            });

            this.drawSimpleBarChart(ctx, hours.map(h => `${h}:00`), data, '#6366f1');
        },

        drawSimpleLineChart(ctx, labels, datasets) {
            const canvas = ctx.canvas;
            const width = canvas.width = canvas.offsetWidth * 2;
            const height = canvas.height = 300;
            const padding = 40;

            ctx.clearRect(0, 0, width, height);
            ctx.scale(2, 2);

            let maxValue = 0;
            datasets.forEach(dataset => {
                maxValue = Math.max(maxValue, ...dataset.data);
            });
            maxValue = maxValue || 1;

            const chartWidth = width/2 - padding * 2;
            const chartHeight = height/2 - padding * 2;
            const stepX = chartWidth / (labels.length - 1 || 1);

            ctx.strokeStyle = '#e0e0e0';
            ctx.lineWidth = 0.5;
            for (let i = 0; i <= 5; i++) {
                const y = padding + (chartHeight * i / 5);
                ctx.beginPath();
                ctx.moveTo(padding, y);
                ctx.lineTo(padding + chartWidth, y);
                ctx.stroke();
            }

            datasets.forEach(dataset => {
                ctx.strokeStyle = dataset.color;
                ctx.lineWidth = 2;
                ctx.beginPath();

                dataset.data.forEach((value, index) => {
                    const x = padding + index * stepX;
                    const y = padding + chartHeight - (value / maxValue * chartHeight);

                    if (index === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                });

                ctx.stroke();

                ctx.fillStyle = dataset.color;
                dataset.data.forEach((value, index) => {
                    const x = padding + index * stepX;
                    const y = padding + chartHeight - (value / maxValue * chartHeight);
                    ctx.beginPath();
                    ctx.arc(x, y, 3, 0, Math.PI * 2);
                    ctx.fill();
                });
            });

            ctx.fillStyle = '#666';
            ctx.font = '10px Inter';
            labels.forEach((label, index) => {
                if (index % Math.ceil(labels.length / 7) === 0) {
                    const x = padding + index * stepX;
                    ctx.fillText(label, x - 15, height/2 - 10);
                }
            });
        },

        drawSimpleBarChart(ctx, labels, data, color) {
            const canvas = ctx.canvas;
            const width = canvas.width = canvas.offsetWidth * 2;
            const height = canvas.height = 200;
            const padding = 20;

            ctx.clearRect(0, 0, width, height);
            ctx.scale(2, 2);

            const maxValue = Math.max(...data) || 1;
            const barWidth = (width/2 - padding * 2) / labels.length;
            const chartHeight = height/2 - padding * 2;

            ctx.fillStyle = color;

            data.forEach((value, index) => {
                const x = padding + index * barWidth;
                const barHeight = (value / maxValue) * chartHeight;
                const y = height/2 - padding - barHeight;

                ctx.globalAlpha = 0.8;
                ctx.fillRect(x + barWidth * 0.1, y, barWidth * 0.8, barHeight);
            });

            ctx.globalAlpha = 1;
        },

        renderViolators(violators) {
            const container = document.getElementById('top-violators');
            if (violators.length === 0) {
                container.innerHTML = `<div class="loading-placeholder">${t('no_violators')}</div>`;
                return;
            }
            container.innerHTML = violators.map(v => {
                // Використовуємо ім'я, якщо воно є, інакше показуємо ID
                const displayName = v.user_name || `ID: ${v.user_id}`;
                return `
                    <div class="violator-item">
                        <span class="violator-name">${displayName}</span>
                        <span class="violator-count">${t('violations_count').replace('{count}', v.violation_count)}</span>
                    </div>
                `;
            }).join('');
        },

        renderCurrentStatus(current) {
            const settings = current.settings || {};
            const warnings = current.warnings || {};
            const statusEnabled = t('status_enabled');
            const statusDisabled = t('status_disabled');
            const captchaStatus = document.getElementById('captcha-status');
            if (captchaStatus) {
                captchaStatus.textContent = settings.captcha_enabled ? statusEnabled : statusDisabled;
                captchaStatus.className = settings.captcha_enabled ? 'status-value enabled' : 'status-value disabled';
            }
            const spamStatus = document.getElementById('spam-filter-status');
            if (spamStatus) {
                spamStatus.textContent = settings.spam_filter_enabled ? statusEnabled : statusDisabled;
                spamStatus.className = settings.spam_filter_enabled ? 'status-value enabled' : 'status-value disabled';
            }
            const thEl = document.getElementById('spam-threshold-status');
            if (thEl) thEl.textContent = settings.spam_threshold ?? '-';
            const warnedText = t('warned_users_format').replace('{users}', warnings.users_with_warnings || 0).replace('{warnings}', warnings.total_warnings || 0);
            const wu = document.getElementById('warned-users');
            if (wu) wu.textContent = warnedText;
            const bl = document.getElementById('blocklist-size');
            if (bl) bl.textContent = current.blocklist_count || 0;
            const wl = document.getElementById('whitelist-size');
            if (wl) wl.textContent = current.whitelist_count || 0;
        },

        async exportStats() {
            if (!this.currentChatId) {
                tg.showAlert('Спочатку виберіть групу');
                return;
            }

            try {
                const response = await fetch(
                    `/api/stats/${this.currentChatId}/export?format=csv`,
                    { headers: getApiHeaders() }
                );

                if (!response.ok) throw new Error('Failed to export');

                const data = await response.json();
                const blob = new Blob([data.csv], { type: 'text/csv' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `stats_${this.currentChatId}_${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                showToast('✅ Статистику експортовано');

            } catch (error) {
                console.error('Export error:', error);
                tg.showAlert('Помилка експорту даних');
            }
        },
        formatNumber(num) {
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num.toString();
        },
        formatDate(dateStr) {
            const date = new Date(dateStr);
            return `${date.getDate()}.${date.getMonth() + 1}`;
        }
    };

    // 7. Обробники подій
    navButtons.forEach(button => button.addEventListener('click', () => {
        showPage(button.dataset.page);
    }));

    chatSelector.addEventListener('change', (e) => {
        selectedChatId = e.target.value;
        const shouldShowSettings = selectedChatId && selectedChatId !== '';

        if (shouldShowSettings) {
            settingsContent.classList.remove('hidden');
            if (settingsOnboarding) settingsOnboarding.classList.add('hidden');
            loadChatSettings(selectedChatId);
        } else {
            settingsContent.classList.add('hidden');
            if (settingsOnboarding && managedGroupCount === 0) {
                settingsOnboarding.classList.remove('hidden');
            }
        }
    });

    document.getElementById('captcha-toggle').addEventListener('change', (e) => handleSettingUpdate('captcha_enabled', e.target.checked));
    document.getElementById('spamfilter-toggle').addEventListener('change', (e) => handleSettingUpdate('spam_filter_enabled', e.target.checked));
    document.getElementById('use-global-list-toggle').addEventListener('change', (e) => handleSettingUpdate('use_global_list', e.target.checked));
    document.getElementById('use-custom-list-toggle').addEventListener('change', (e) => handleSettingUpdate('use_custom_list', e.target.checked));
    document.getElementById('spam-threshold').addEventListener('change', (e) => {
        const value = parseInt(e.target.value);
        if (value >= 5 && value <= 50) handleSettingUpdate('spam_threshold', value);
    });

    document.getElementById('antiflood-toggle').addEventListener('change', (e) => handleSettingUpdate('antiflood_enabled', e.target.checked));
    document.getElementById('antiflood-sensitivity').addEventListener('change', (e) => {
        const value = parseInt(e.target.value);
        if (value >= 3 && value <= 15) handleSettingUpdate('antiflood_sensitivity', value);
    });

    // Обробники для гнучких покарань
    document.querySelectorAll('.action-selector').forEach(selector => {
        selector.addEventListener('change', (e) => {
            const level = parseInt(e.target.dataset.level);
            const action = e.target.value;
            const durationInput = document.querySelector(`.duration-input[data-level='${level}']`);
            durationInput.disabled = action === 'ban';
            const duration = action === 'ban' ? 0 : parseInt(durationInput.value);
            handlePunishmentUpdate(level, action, duration);
        });
    });

    document.querySelectorAll('.duration-input').forEach(input => {
        input.addEventListener('change', (e) => {
            const level = parseInt(e.target.dataset.level);
            const action = document.querySelector(`.action-selector[data-level='${level}']`).value;
            const duration = parseInt(e.target.value);
            if (action === 'mute') {
                handlePunishmentUpdate(level, action, duration);
            }
        });
    });

    // === 8. ІНІЦІАЛІЗАЦІЯ ===
    applyThemeMode(getThemeMode());

    // Визначаємо початкову мову користувача
    const savedLang = localStorage.getItem('language');
    const initialLang = savedLang || (tg.initDataUnsafe?.user?.language_code || 'uk').split('-')[0];

    // Встановлюємо мову та чекаємо завантаження перекладів перед тим, як ініціалізувати модулі.
    // Це виправлення гарантує, що statsModule та wordListPageModule завжди будуть запущені.
    setLanguage(initialLang).then(() => {
        showPage('home-page');
        window.statsModule.init();
        wordListPageModule.init();
    });
});
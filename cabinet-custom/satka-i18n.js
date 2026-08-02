(function (global) {
  'use strict';

  var STORAGE_KEY = 'i18nextLng';
  var listeners = [];

  var AUTH_STRINGS = {
    ru: {
      'auth.login': 'Войти',
      'auth.register': 'Регистрация',
      'auth.email': 'Email',
      'auth.password': 'Пароль',
      'auth.confirmPassword': 'Подтвердите пароль',
      'auth.firstName': 'Имя',
      'auth.firstNamePlaceholder': 'Ваше имя',
      'auth.loginWithTelegram': 'Войти через Telegram',
      'auth.loginWithEmail': 'Войти по email',
      'auth.forgotPassword': 'Забыли пароль?',
      'auth.forgotPasswordHint': 'Укажите email — отправим ссылку для сброса пароля.',
      'auth.sendResetLink': 'Отправить ссылку',
      'auth.passwordResetSent': 'Ссылка для сброса отправлена на почту',
      'auth.telegramWidgetBlocked':
        'Виджет входа через Telegram недоступен. Войдите через бота:',
      'auth.scanQrToLogin': 'Отсканируйте QR-код камерой телефона',
      'auth.openBotToLogin': 'Открыть бота для входа',
      'auth.orSendCommand': 'Или отправьте боту команду:',
      'auth.commandCopied': 'Команда скопирована ✓',
      'auth.or': 'или',
      'auth.orOpenInApp': 'или откройте в приложении Telegram',
      'auth.waitingForConfirmation': 'Ожидаем подтверждение в боте…',
      'auth.authenticating': 'Входим…',
      'auth.loginSuccess': 'Вход выполнен',
      'auth.loginFailed': 'Не удалось войти',
      'auth.invalidCredentials': 'Неверный email или пароль',
      'auth.invalidEmail': 'Некорректный email',
      'auth.emailAlreadyRegistered': 'Этот email уже зарегистрирован',
      'auth.emailNotVerified': 'Email не подтверждён',
      'auth.passwordMismatch': 'Пароли не совпадают',
      'auth.passwordTooShort': 'Пароль слишком короткий',
      'auth.tooManyAttempts': 'Слишком много попыток. Подождите немного.',
      'auth.tryAgain': 'Попробовать снова',
      'auth.backToLogin': 'Вернуться ко входу',
      'auth.checkEmail': 'Проверьте почту',
      'auth.clickLinkToVerify': 'Перейдите по ссылке в письме для подтверждения',
      'auth.verificationSent': 'Письмо с подтверждением отправлено',
      'auth.verificationEmailNotice': 'Мы отправили письмо для подтверждения email',
      'auth.deepLinkExpired': 'Ссылка для входа истекла. Обновите страницу.',
      'auth.oauthError': 'Ошибка авторизации',
      'auth.telegramNotConfigured': 'Вход через Telegram временно недоступен',
      'auth.telegramRequired': 'Требуется Telegram',
      'auth.telegramReopenHint': 'Откройте бота и подтвердите вход',
      'auth.referralInvite': 'Вас пригласили — зарегистрируйтесь или войдите',
    },
    en: {
      'auth.login': 'Sign in',
      'auth.register': 'Register',
      'auth.email': 'Email',
      'auth.password': 'Password',
      'auth.confirmPassword': 'Confirm password',
      'auth.firstName': 'First name',
      'auth.firstNamePlaceholder': 'Your name',
      'auth.loginWithTelegram': 'Sign in with Telegram',
      'auth.loginWithEmail': 'Sign in with email',
      'auth.forgotPassword': 'Forgot password?',
      'auth.forgotPasswordHint': 'Enter your email and we will send a reset link.',
      'auth.sendResetLink': 'Send reset link',
      'auth.passwordResetSent': 'Password reset link sent',
      'auth.telegramWidgetBlocked': 'Telegram login widget is unavailable. Sign in via the bot:',
      'auth.scanQrToLogin': 'Scan the QR code with your phone camera',
      'auth.openBotToLogin': 'Open bot to sign in',
      'auth.orSendCommand': 'Or send this command to the bot:',
      'auth.commandCopied': 'Command copied ✓',
      'auth.or': 'or',
      'auth.orOpenInApp': 'or open in the Telegram app',
      'auth.waitingForConfirmation': 'Waiting for confirmation in the bot…',
      'auth.authenticating': 'Signing in…',
      'auth.loginSuccess': 'Signed in successfully',
      'auth.loginFailed': 'Sign in failed',
      'auth.invalidCredentials': 'Invalid email or password',
      'auth.invalidEmail': 'Invalid email',
      'auth.emailAlreadyRegistered': 'This email is already registered',
      'auth.emailNotVerified': 'Email not verified',
      'auth.passwordMismatch': 'Passwords do not match',
      'auth.passwordTooShort': 'Password is too short',
      'auth.tooManyAttempts': 'Too many attempts. Please wait.',
      'auth.tryAgain': 'Try again',
      'auth.backToLogin': 'Back to sign in',
      'auth.checkEmail': 'Check your email',
      'auth.clickLinkToVerify': 'Click the link in the email to verify',
      'auth.verificationSent': 'Verification email sent',
      'auth.verificationEmailNotice': 'We sent a verification email',
      'auth.deepLinkExpired': 'Login link expired. Refresh the page.',
      'auth.oauthError': 'Authorization error',
      'auth.telegramNotConfigured': 'Telegram sign-in is temporarily unavailable',
      'auth.telegramRequired': 'Telegram required',
      'auth.telegramReopenHint': 'Open the bot and confirm sign-in',
      'auth.referralInvite': 'You were invited — register or sign in',
    },
  };

  var STRINGS = {
  ru: {
    'home.tag': 'Личный кабинет',
    'home.title': 'Подписка и подключение',
    'home.subtitle': 'Тарифы, оплата с баланса и ссылки для приложения Happ.',
    'home.link.subscription': '📋 Тарифы и подписка',
    'home.link.balance': '💳 Баланс и оплата',
    'home.link.support': '🛠 Техподдержка',
    'home.link.channel': '📰 Наш канал',
    'home.link.site': '🌐 Тарифы на сайте',
    'feature.security.title': 'Безопасность',
    'feature.security.text': 'Шифрование трафика в Wi‑Fi и мобильной сети.',
    'feature.speed.title': 'Скорость',
    'feature.speed.text': 'Серверы в Европе, Азии и США — стабильный пинг.',
    'feature.connection.title': 'Подключение',
    'feature.connection.text': 'Стабильный доступ через приложение Happ.',
    'feature.support.title': 'Поддержка 24/7',
    'feature.support.text': 'Помощь в @satkavpnsupport в любое время.',
    'support.presets.label': 'Быстрый выбор темы',
    'support.toast.created': 'Обращение создано — обновляем список…',
    'support.toast.createFail': 'Не удалось создать обращение. Проверьте тему (от 3 символов) и текст (от 10).',
    'support.toast.subjectShort': 'Тема: минимум 3 символа',
    'support.toast.messageShort': 'Сообщение: минимум 10 символов — допишите детали или выберите шаблон выше',
    'support.preset.subscription': 'Не работает подписка',
    'support.preset.subscription.msg': 'Подписка не активируется или не открывается в Happ. Устройство: ___. Что уже пробовал(а): перезапуск приложения, обновление подписки.',
    'support.preset.payment': 'Не оплачивается',
    'support.preset.payment.msg': 'Не проходит оплата (карта/СБП/крипто). Способ оплаты: ___. Сумма: ___ ₽. Скрин или текст ошибки приложу при ответе.',
    'support.preset.urgent': 'Нужна быстрая помощь',
    'support.preset.urgent.msg': 'Нужна срочная помощь с подключением. Telegram: @___. Кратко: что не работает прямо сейчас.',
    'support.preset.ping': 'Сервера не пингуются',
    'support.preset.ping.msg': 'Серверы не отвечают / высокий пинг / таймаут. Локация: ___. Оператор: ___. В Happ статус: offline/timeout.',
    'support.preset.key': 'Ключ сломался',
    'support.preset.key.msg': 'Ключ/ссылка подписки перестала работать или выдаёт ошибку. Приложение: Happ. Текст ошибки: ___.',
    'support.preset.happ': 'Не подключается Happ',
    'support.preset.happ.msg': 'Happ не подключается после импорта подписки. Модель телефона/ОС: ___. Версия Happ: ___.',
    'support.preset.speed': 'Медленная скорость',
    'support.preset.speed.msg': 'Низкая скорость через VPN. Локация: ___. Скорость без VPN / с VPN (примерно): ___ / ___ Мбит/с.',
    'support.preset.balance': 'Не пришла оплата на баланс',
    'support.preset.balance.msg': 'Оплатил(а), но баланс в кабинете не изменился. Сумма: ___ ₽. Время оплаты: ___. ID платежа (если есть): ___.',
    'wheel.title': 'Реферальное колесо',
    'wheel.heading': 'Реферальное колесо',
    'wheel.lead': 'Один прокрут за каждого друга по вашей ссылке. Призы на баланс и подписку.',
    'wheel.spinBtn': 'Крутить',
    'wheel.invited': 'Приглашено',
    'wheel.used': 'Использовано',
    'wheel.available': 'Доступно',
    'wheel.spinning': 'Крутим…',
    'wheel.spin': 'Крутить · осталось {{n}}',
    'wheel.invite': 'Пригласите друга для крутки',
    'wheel.prize': 'Приз',
    'wheel.sessionExpired': 'Сессия истекла — обновите страницу и войдите снова.',
    'wheel.noSpins': 'Нет круток — пригласите друга по реферальной ссылке.',
    'wheel.spinFail': 'Не удалось крутить. Попробуйте позже.',
    'wheel.loginRequired': 'Войдите в кабинет (Telegram или email), чтобы крутить колесо.',
    'wheel.loadFail': 'Не удалось загрузить колесо.',
    'wheel.spinsUnit': 'круток',
    'login.title': 'Вход через Telegram',
    'login.hint': 'Откройте бота и подтвердите вход — виджет на сайте не нужен.',
    'login.open': 'Открыть @{{bot}}',
    'login.or': 'или отправьте команду в боте:',
    'login.copy': 'Копировать',
    'login.copied': 'Скопировано ✓',
    'login.wait': 'Ожидаем подтверждение в боте…',
    'login.expired': 'Ссылка истекла. Обновите страницу.',
    'register.success.title': 'Регистрация успешна!',
    'register.success.message': 'Аккаунт создан. Перейдите во вкладку «Войти» и войдите с email и паролем.',
    'register.success.verifyTitle': 'Регистрация успешна!',
    'register.success.verifyMessage':
      'Не забудьте верифицировать почту — письмо со ссылкой уже отправлено. Если во «Входящих» нет — проверьте папку «Спам».',
    'register.success.btn': 'Понятно',
    'theme.label': 'Тема',
    'theme.dark': 'Тёмная',
    'theme.light': 'Светлая',
    'theme.midnight': 'Полночь',
    'theme.aurora': 'Аврора',
    'theme.rose': 'Розовая',
    'theme.liquid-glass': 'Жидкое стекло',
  },
  en: {
    'home.tag': 'Personal account',
    'home.title': 'Subscription & connection',
    'home.subtitle': 'Plans, balance payments, and Happ app links.',
    'home.link.subscription': '📋 Plans & subscription',
    'home.link.balance': '💳 Balance & payment',
    'home.link.support': '🛠 Support',
    'home.link.channel': '📰 Our channel',
    'home.link.site': '🌐 Plans on website',
    'feature.security.title': 'Security',
    'feature.security.text': 'Encrypted traffic on Wi‑Fi and mobile networks.',
    'feature.speed.title': 'Speed',
    'feature.speed.text': 'Servers in Europe, Asia & USA — stable ping.',
    'feature.connection.title': 'Connection',
    'feature.connection.text': 'Stable access via the Happ app.',
    'feature.support.title': '24/7 Support',
    'feature.support.text': 'Help at @satkavpnsupport anytime.',
    'support.presets.label': 'Quick topic',
    'support.toast.created': 'Ticket created — refreshing list…',
    'support.toast.createFail': 'Could not create ticket. Subject needs 3+ chars, message 10+ chars.',
    'support.toast.subjectShort': 'Subject: at least 3 characters',
    'support.toast.messageShort': 'Message: at least 10 characters — add details or pick a template above',
    'support.preset.subscription': 'Subscription not working',
    'support.preset.subscription.msg': 'Subscription does not activate or open in Happ. Device: ___. Tried: app restart, subscription refresh.',
    'support.preset.payment': 'Payment failed',
    'support.preset.payment.msg': 'Payment failed (card/SBP/crypto). Method: ___. Amount: ___ ₽. Will attach screenshot or error text.',
    'support.preset.urgent': 'Need urgent help',
    'support.preset.urgent.msg': 'Urgent help with connection. Telegram: @___. Briefly: what is broken right now.',
    'support.preset.ping': 'Servers not pinging',
    'support.preset.ping.msg': 'Servers timeout / high ping. Location: ___. ISP: ___. Happ status: offline/timeout.',
    'support.preset.key': 'Broken key',
    'support.preset.key.msg': 'Subscription key/link stopped working or shows an error. App: Happ. Error text: ___.',
    'support.preset.happ': 'Happ won\'t connect',
    'support.preset.happ.msg': 'Happ won\'t connect after importing subscription. Phone/OS: ___. Happ version: ___.',
    'support.preset.speed': 'Slow speed',
    'support.preset.speed.msg': 'Low VPN speed. Location: ___. Speed without / with VPN: ___ / ___ Mbps.',
    'support.preset.balance': 'Balance not credited',
    'support.preset.balance.msg': 'Paid but balance did not update. Amount: ___ ₽. Payment time: ___. Payment ID (if any): ___.',
    'wheel.title': 'Referral wheel',
    'wheel.heading': 'Referral wheel',
    'wheel.lead': 'One spin for each friend via your link. Prizes include balance and subscription time.',
    'wheel.spinBtn': 'Spin',
    'wheel.invited': 'Invited',
    'wheel.used': 'Used',
    'wheel.available': 'Available',
    'wheel.spinning': 'Spinning…',
    'wheel.spin': 'Spin · {{n}} left',
    'wheel.invite': 'Invite a friend for a spin',
    'wheel.prize': 'Prize',
    'wheel.sessionExpired': 'Session expired — refresh and log in again.',
    'wheel.noSpins': 'No spins left — invite a friend via your referral link.',
    'wheel.spinFail': 'Could not spin. Try again later.',
    'wheel.loginRequired': 'Log in (Telegram or email) to spin the wheel.',
    'wheel.loadFail': 'Could not load the wheel.',
    'wheel.spinsUnit': 'spins',
    'login.title': 'Sign in via Telegram',
    'login.hint': 'Open the bot and confirm login — no website widget needed.',
    'login.open': 'Open @{{bot}}',
    'login.or': 'or send this command to the bot:',
    'login.copy': 'Copy',
    'login.copied': 'Copied ✓',
    'login.wait': 'Waiting for confirmation in the bot…',
    'login.expired': 'Link expired. Refresh the page.',
    'register.success.title': 'Registration successful!',
    'register.success.message': 'Account created. Switch to the “Sign in” tab and log in with your email and password.',
    'register.success.verifyTitle': 'Registration successful!',
    'register.success.verifyMessage':
      "Don't forget to verify your email — we sent a confirmation link. If it's not in Inbox, check your Spam folder.",
    'register.success.btn': 'Got it',
    'theme.label': 'Theme',
    'theme.dark': 'Dark',
    'theme.light': 'Light',
    'theme.midnight': 'Midnight',
    'theme.aurora': 'Aurora',
    'theme.rose': 'Rose',
    'theme.liquid-glass': 'Liquid Glass',
  },
  };

  function normalizeLang(code) {
    var c = (code || 'ru').toLowerCase();
    if (c.indexOf('-') !== -1) c = c.split('-')[0];
    return STRINGS[c] ? c : 'ru';
  }

  function getLang() {
    try {
      return normalizeLang(localStorage.getItem(STORAGE_KEY) || 'ru');
    } catch (e) {
      return 'ru';
    }
  }

  function t(key, params) {
    var lang = getLang();
    var authTable = AUTH_STRINGS[lang] || AUTH_STRINGS.ru;
    if (key.indexOf('auth.') === 0 && authTable[key]) {
      var authValue = authTable[key];
      if (params) {
        Object.keys(params).forEach(function (k) {
          authValue = authValue.replace(new RegExp('{{' + k + '}}', 'g'), String(params[k]));
        });
      }
      return authValue;
    }
    var table = STRINGS[lang] || STRINGS.ru;
    var value = table[key] || STRINGS.ru[key] || authTable[key] || AUTH_STRINGS.ru[key] || key;
    if (params) {
      Object.keys(params).forEach(function (k) {
        value = value.replace(new RegExp('{{' + k + '}}', 'g'), String(params[k]));
      });
    }
    return value;
  }

  function onChange(cb) {
    listeners.push(cb);
    return function () {
      listeners = listeners.filter(function (x) { return x !== cb; });
    };
  }

  function notify() {
    listeners.forEach(function (cb) {
      try { cb(getLang()); } catch (e) {}
    });
    try {
      window.dispatchEvent(new CustomEvent('satka-language-changed', { detail: { lang: getLang() } }));
    } catch (e2) {}
  }

  function patchI18nResources() {
    var i18n = global.i18next;
    if (!i18n || !i18n.addResourceBundle) return false;
    ['ru', 'en'].forEach(function (lang) {
      var bundle = Object.assign({}, AUTH_STRINGS[lang] || {}, STRINGS[lang] || {});
      i18n.addResourceBundle(lang, 'translation', bundle, true, true);
    });
    return true;
  }

  function fixAuthKeyNodes() {
    var re = /^auth\.[a-zA-Z.]+$/;
    document.querySelectorAll('button, a, label, p, span, h1, h2, h3, div').forEach(function (el) {
      if (el.children.length > 2) return;
      var txt = (el.textContent || '').trim();
      if (!re.test(txt)) return;
      var fixed = t(txt);
      if (fixed && fixed !== txt) el.textContent = fixed;
    });
  }

  function hookI18n() {
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      var i18n = global.i18next;
      if (i18n && i18n.on) {
        clearInterval(timer);
        patchI18nResources();
        i18n.on('languageChanged', function () {
          patchI18nResources();
          notify();
          fixAuthKeyNodes();
        });
        notify();
        fixAuthKeyNodes();
        return;
      }
      if (tries > 120) clearInterval(timer);
    }, 200);
  }

  if (global.SatkaRoute && global.SatkaRoute.onTick) {
    global.SatkaRoute.onTick(fixAuthKeyNodes);
  } else {
    setInterval(fixAuthKeyNodes, 800);
  }

  window.addEventListener('storage', function (e) {
    if (e.key === STORAGE_KEY) notify();
  });

  hookI18n();

  global.SatkaI18n = { getLang: getLang, t: t, onChange: onChange, notify: notify };
})(window);

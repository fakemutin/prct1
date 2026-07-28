(function () {
  'use strict';

  var STORAGE_KEY = 'satka-cabinet-theme-preset';
  var CABINET_THEME_KEY = 'cabinet-theme';
  var PALETTE_ICON =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18c1.5 0 2.5-3 2.5-6s-1-6-2.5-6Z"/></svg>';
  var THEMES = [
    { id: 'dark', swatch: '#030303' },
    { id: 'light', swatch: '#f5f5f7' },
    { id: 'midnight', swatch: '#60a5fa' },
    { id: 'aurora', swatch: '#2dd4bf' },
    { id: 'rose', swatch: '#fb7185' },
  ];
  var CHROME_COLORS = {
    dark: '#030303',
    light: '#f4f4f6',
    midnight: '#080d18',
    aurora: '#061210',
    rose: '#10080c',
  };
  var mounted = false;
  var isTelegram =
    document.documentElement.classList.contains('satka-in-telegram') ||
    !!window.TelegramWebviewProxy;

  function t(key) {
    return window.SatkaI18n ? window.SatkaI18n.t(key) : key;
  }

  function getTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'dark';
    } catch (e) {
      return 'dark';
    }
  }

  function syncTelegramChrome(theme) {
    var tg = window.Telegram && window.Telegram.WebApp;
    if (!tg) return;
    var color = CHROME_COLORS[theme] || CHROME_COLORS.dark;
    try {
      if (typeof tg.setHeaderColor === 'function') tg.setHeaderColor(color);
      if (typeof tg.setBackgroundColor === 'function') tg.setBackgroundColor(color);
    } catch (e) {}
  }

  function applyTheme(id, silent) {
    var theme = THEMES.some(function (x) {
      return x.id === id;
    })
      ? id
      : 'dark';
    var html = document.documentElement;
    html.setAttribute('data-satka-theme', theme);
    html.classList.toggle('dark', theme !== 'light');
    html.classList.toggle('light', theme === 'light');
    html.style.colorScheme = theme === 'light' ? 'light' : 'dark';
    document.body.style.backgroundColor = CHROME_COLORS[theme] || CHROME_COLORS.dark;

    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', CHROME_COLORS[theme] || CHROME_COLORS.dark);

    try {
      localStorage.setItem(STORAGE_KEY, theme);
      localStorage.setItem(CABINET_THEME_KEY, theme === 'light' ? 'light' : 'dark');
      localStorage.setItem('cabinet-enabled-themes', JSON.stringify({ dark: true, light: true }));
    } catch (e) {}

    syncTelegramChrome(theme);

    if (!silent) {
      try {
        window.dispatchEvent(
          new CustomEvent('themeChanged', { detail: theme === 'light' ? 'light' : 'dark' }),
        );
      } catch (e2) {}
    }

    document.querySelectorAll('.satka-theme-switcher .satka-theme-menu button').forEach(function (btn) {
      btn.classList.toggle('is-active', btn.dataset.theme === theme);
    });
    var current = document.querySelector('.satka-theme-switcher [data-current-theme]');
    if (current) current.textContent = t('theme.' + theme);
  }

  function buildSwitcher() {
    var wrap = document.createElement('div');
    wrap.className = 'satka-theme-switcher';
    wrap.innerHTML =
      '<button type="button" aria-label="' +
      t('theme.label') +
      '">' +
      PALETTE_ICON +
      '<span data-current-theme>' +
      t('theme.' + getTheme()) +
      '</span></button>' +
      '<div class="satka-theme-menu" hidden></div>';
    var menu = wrap.querySelector('.satka-theme-menu');
    THEMES.forEach(function (item) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.dataset.theme = item.id;
      btn.innerHTML =
        '<span class="satka-theme-swatch" style="background:' +
        item.swatch +
        '"></span>' +
        '<span>' +
        t('theme.' + item.id) +
        '</span>';
      btn.addEventListener('click', function () {
        applyTheme(item.id);
        menu.hidden = true;
      });
      menu.appendChild(btn);
    });
    var toggle = wrap.querySelector('button');
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      menu.hidden = !menu.hidden;
    });
    document.addEventListener('mousedown', function (e) {
      if (!wrap.contains(e.target)) menu.hidden = true;
    });
    return wrap;
  }

  function mountSwitcher() {
    if (isTelegram || mounted) return;
    if (document.querySelector('.satka-theme-switcher')) {
      mounted = true;
      return;
    }
    var langBtn = document.querySelector('button[aria-label="Change language"]');
    if (!langBtn || !langBtn.parentElement) return;
    langBtn.parentElement.insertBefore(buildSwitcher(), langBtn);
    mounted = true;
    applyTheme(getTheme(), true);
  }

  function remountForLanguage() {
    var sw = document.querySelector('.satka-theme-switcher');
    if (sw) sw.remove();
    mounted = false;
    mountSwitcher();
  }

  applyTheme(getTheme(), true);

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) applyTheme(getTheme(), true);
  });

  if (window.SatkaI18n) {
    window.SatkaI18n.onChange(remountForLanguage);
  }

  if (window.SatkaRoute) {
    window.SatkaRoute.whenRootReady(mountSwitcher);
    window.SatkaRoute.onChange(function () {
      applyTheme(getTheme(), true);
      mountSwitcher();
    });
  } else {
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      mountSwitcher();
      if (mounted || tries > 40) clearInterval(timer);
    }, 400);
  }

  window.SatkaTheme = {
    apply: applyTheme,
    get: getTheme,
    enforce: function () {
      applyTheme(getTheme(), true);
    },
  };
})();

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
    { id: 'liquid-glass', swatch: 'linear-gradient(135deg,#8cb4ff,#c49cff,#64e8d2)' },
  ];
  var CHROME_COLORS = {
    dark: '#030303',
    light: '#f4f4f6',
    midnight: '#080d18',
    aurora: '#061210',
    rose: '#10080c',
    'liquid-glass': '#070b14',
  };
  var isTelegram =
    document.documentElement.classList.contains('satka-in-telegram') ||
    !!window.TelegramWebviewProxy;
  var menuCloseBound = false;
  var activeMenu = null;

  function t(key) {
    return window.SatkaI18n ? window.SatkaI18n.t(key) : key;
  }

  function getTheme() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved && THEMES.some(function (x) { return x.id === saved; })) return saved;
    } catch (e) {}
    return 'dark';
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
    var theme = THEMES.some(function (x) { return x.id === id; }) ? id : 'dark';
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
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: theme }));
      } catch (e2) {}
    }

    document.querySelectorAll('.satka-theme-switcher .satka-theme-menu button').forEach(function (btn) {
      btn.classList.toggle('is-active', btn.dataset.theme === theme);
    });
    var current = document.querySelector('.satka-theme-switcher [data-current-theme]');
    if (current) current.textContent = t('theme.' + theme);
  }

  function bindMenuClose() {
    if (menuCloseBound) return;
    menuCloseBound = true;
    document.addEventListener('mousedown', function (e) {
      if (!activeMenu || activeMenu.hidden) return;
      var wrap = activeMenu.closest('.satka-theme-switcher');
      if (wrap && !wrap.contains(e.target)) activeMenu.hidden = true;
    });
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
    activeMenu = menu;
    bindMenuClose();

    THEMES.forEach(function (item) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.dataset.theme = item.id;
      var swatchStyle =
        item.swatch.indexOf('gradient') !== -1
          ? 'background:' + item.swatch
          : 'background:' + item.swatch;
      btn.innerHTML =
        '<span class="satka-theme-swatch" style="' +
        swatchStyle +
        '"></span><span>' +
        t('theme.' + item.id) +
        '</span>';
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        applyTheme(item.id);
        menu.hidden = true;
      });
      menu.appendChild(btn);
    });

    wrap.querySelector('button').addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      menu.hidden = !menu.hidden;
    });
    return wrap;
  }

  function mountSwitcher() {
    if (isTelegram) return;
    var langBtn = document.querySelector('button[aria-label="Change language"]');
    if (!langBtn || !langBtn.parentElement) return;

    var parent = langBtn.parentElement;
    var existing = parent.querySelector('.satka-theme-switcher');
    if (existing && document.body.contains(existing)) {
      applyTheme(getTheme(), true);
      return;
    }

    document.querySelectorAll('.satka-theme-switcher').forEach(function (el) {
      el.remove();
    });

    parent.classList.add('satka-header-prefs');
    parent.insertBefore(buildSwitcher(), langBtn);
    applyTheme(getTheme(), true);
  }

  function remountForLanguage() {
    document.querySelectorAll('.satka-theme-switcher').forEach(function (el) {
      el.remove();
    });
    mountSwitcher();
  }

  function enforceTheme() {
    var saved = getTheme();
    if (document.documentElement.getAttribute('data-satka-theme') !== saved) {
      applyTheme(saved, true);
    }
  }

  function boot() {
    enforceTheme();
    mountSwitcher();
  }

  applyTheme(getTheme(), true);

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) boot();
  });

  if (window.SatkaI18n) {
    window.SatkaI18n.onChange(remountForLanguage);
  }

  if (window.SatkaRoute) {
    window.SatkaRoute.onTick(boot);
    window.SatkaRoute.onChange(boot);
    window.SatkaRoute.whenReady(boot);
  } else {
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      boot();
      if (document.querySelector('.satka-theme-switcher') || tries > 60) clearInterval(timer);
    }, 350);
  }

  setInterval(enforceTheme, 1500);

  window.SatkaTheme = {
    apply: applyTheme,
    get: getTheme,
    enforce: enforceTheme,
  };
})();

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
  var applying = false;

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

  function hideNativeThemeToggle() {
    var langBtn = document.querySelector('button[aria-label="Change language"]');
    if (langBtn && langBtn.parentElement) {
      langBtn.parentElement.querySelectorAll('button').forEach(function (btn) {
        if (btn === langBtn || btn.closest('.satka-theme-switcher')) return;
        var label = (btn.getAttribute('aria-label') || '').toLowerCase();
        var onlyIcon = btn.querySelector('svg') && !(btn.textContent || '').trim();
        if (onlyIcon || label.indexOf('theme') >= 0 || label.indexOf('тема') >= 0 || label.indexOf('mode') >= 0) {
          btn.remove();
          return;
        }
      });
    }
    document.querySelectorAll('#root button').forEach(function (btn) {
      if (btn.closest('.satka-theme-switcher')) return;
      var path = btn.querySelector('svg path');
      if (!path) return;
      var d = path.getAttribute('d') || '';
      if (
        d.indexOf('233.54,142.23') !== -1 ||
        d.indexOf('188.9,190.34') !== -1 ||
        d.indexOf('M233.54') !== -1 ||
        d.indexOf('M128,56a72') !== -1 ||
        d.indexOf('M128,40') !== -1
      ) {
        btn.remove();
      }
    });
  }

  function applyTheme(id, silent) {
    var theme = THEMES.some(function (x) { return x.id === id; }) ? id : 'dark';
    var html = document.documentElement;
    var already =
      html.getAttribute('data-satka-theme') === theme &&
      html.classList.contains(theme === 'light' ? 'light' : 'dark');
    if (already && silent) return;

    applying = true;
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
    hideNativeThemeToggle();

    if (!silent) {
      try {
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: theme === 'light' ? 'light' : 'dark' }));
      } catch (e2) {}
    }

    document.querySelectorAll('.satka-theme-switcher .satka-theme-menu button').forEach(function (btn) {
      btn.classList.toggle('is-active', btn.dataset.theme === theme);
    });
    var current = document.querySelector('.satka-theme-switcher [data-current-theme]');
    if (current) current.textContent = t('theme.' + theme);
    applying = false;
  }

  function enforceTheme() {
    if (applying) return;
    applyTheme(getTheme(), true);
  }

  function hookNavigation() {
    var navTimer = null;
    function onNav() {
      clearTimeout(navTimer);
      navTimer = setTimeout(function () {
        enforceTheme();
        hideNativeThemeToggle();
      }, 120);
    }
    window.addEventListener('popstate', onNav);
    var _push = history.pushState;
    var _replace = history.replaceState;
    history.pushState = function () {
      var r = _push.apply(history, arguments);
      onNav();
      return r;
    };
    history.replaceState = function () {
      var r = _replace.apply(history, arguments);
      onNav();
      return r;
    };
  }

  function buildSwitcher() {
    var wrap = document.createElement('div');
    wrap.className = 'satka-theme-switcher';
    wrap.innerHTML =
      '<button type="button" aria-label="' + t('theme.label') + '">' +
      PALETTE_ICON +
      '<span data-current-theme>' + t('theme.' + getTheme()) + '</span></button>' +
      '<div class="satka-theme-menu" hidden></div>';
    var menu = wrap.querySelector('.satka-theme-menu');
    THEMES.forEach(function (item) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.dataset.theme = item.id;
      btn.innerHTML =
        '<span class="satka-theme-swatch" style="background:' + item.swatch + '"></span>' +
        '<span>' + t('theme.' + item.id) + '</span>';
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

  function mountNearLanguage() {
    hideNativeThemeToggle();
    if (document.querySelector('.satka-theme-switcher')) return true;
    var langBtn = document.querySelector('button[aria-label="Change language"]');
    if (!langBtn) return false;
    var parent = langBtn.parentElement;
    if (!parent) return false;
    var bar = parent.closest('.satka-pref-bar');
    if (!bar) {
      bar = document.createElement('div');
      bar.className = 'satka-pref-bar';
      parent.parentNode.insertBefore(bar, parent);
      bar.appendChild(buildSwitcher());
      bar.appendChild(parent);
    } else if (!bar.querySelector('.satka-theme-switcher')) {
      bar.insertBefore(buildSwitcher(), bar.firstChild);
    }
    enforceTheme();
    return true;
  }

  applyTheme(getTheme(), true);
  hookNavigation();
  hideNativeThemeToggle();

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) enforceTheme();
  });

  if (window.SatkaI18n) {
    window.SatkaI18n.onChange(function () {
      var sw = document.querySelector('.satka-theme-switcher');
      if (sw) sw.remove();
      mountNearLanguage();
    });
  }

  var tries = 0;
  var timer = setInterval(function () {
    tries += 1;
    hideNativeThemeToggle();
    if (mountNearLanguage() || tries > 80) clearInterval(timer);
  }, 500);

  var root = document.getElementById('root');
  if (root && 'MutationObserver' in window) {
    var hideTimer = null;
    new MutationObserver(function () {
      clearTimeout(hideTimer);
      hideTimer = setTimeout(hideNativeThemeToggle, 200);
    }).observe(root, { childList: true, subtree: true });
  }

  window.SatkaTheme = { apply: applyTheme, get: getTheme, enforce: enforceTheme };
})();

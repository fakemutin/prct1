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

  function applyTheme(id, silent) {
    var theme = THEMES.some(function (x) { return x.id === id; }) ? id : 'dark';
    document.documentElement.setAttribute('data-satka-theme', theme);
    document.documentElement.classList.toggle('dark', theme !== 'light');
    document.documentElement.classList.toggle('light', theme === 'light');
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      var colors = { dark: '#030303', light: '#f4f4f6', midnight: '#080d18', aurora: '#061210', rose: '#10080c' };
      meta.setAttribute('content', colors[theme] || '#030303');
    }
    try {
      localStorage.setItem(STORAGE_KEY, theme);
      localStorage.setItem(CABINET_THEME_KEY, theme === 'light' ? 'light' : 'dark');
      localStorage.setItem('cabinet-enabled-themes', JSON.stringify({ dark: true, light: true }));
    } catch (e) {}
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
    applyTheme(getTheme(), true);
    return true;
  }

  applyTheme(getTheme(), true);

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
    if (mountNearLanguage() || tries > 120) clearInterval(timer);
  }, 500);

  window.addEventListener('popstate', function () {
    setTimeout(mountNearLanguage, 300);
  });
})();

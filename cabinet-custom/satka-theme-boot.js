(function () {
  'use strict';

  var STORAGE_KEY = 'satka-cabinet-theme-preset';
  var VALID = {
    dark: 1,
    light: 1,
    midnight: 1,
    aurora: 1,
    rose: 1,
    'liquid-glass': 1,
  };
  var CHROME = {
    dark: '#030303',
    light: '#f4f4f6',
    midnight: '#080d18',
    aurora: '#061210',
    rose: '#10080c',
    'liquid-glass': '#050a12',
  };

  function getTheme() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved && VALID[saved]) return saved;
    } catch (e) {}
    return 'dark';
  }

  function applyTheme(theme) {
    var html = document.documentElement;
    var body = document.body;
    html.setAttribute('data-satka-theme', theme);
    html.classList.toggle('dark', theme !== 'light');
    html.classList.toggle('light', theme === 'light');
    html.classList.toggle('satka-lg-active', theme === 'liquid-glass');
    html.style.colorScheme = theme === 'light' ? 'light' : 'dark';
    if (body) body.style.backgroundColor = CHROME[theme] || CHROME.dark;
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', CHROME[theme] || CHROME.dark);
  }

  function enforce() {
    applyTheme(getTheme());
  }

  enforce();

  if (typeof MutationObserver !== 'undefined') {
    var pending = false;
    new MutationObserver(function () {
      if (pending) return;
      pending = true;
      requestAnimationFrame(function () {
        pending = false;
        if (document.documentElement.getAttribute('data-satka-theme') !== getTheme()) {
          enforce();
        }
      });
    }).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-satka-theme', 'class'],
    });
  }

  window.addEventListener('storage', function (e) {
    if (e.key === STORAGE_KEY) enforce();
  });

  window.SatkaThemeBoot = { enforce: enforce, get: getTheme, apply: applyTheme };
})();

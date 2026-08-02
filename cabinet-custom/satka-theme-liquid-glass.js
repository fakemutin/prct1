(function () {
  'use strict';

  var THEME = 'liquid-glass';
  var pointerBound = false;

  function isActive() {
    return document.documentElement.getAttribute('data-satka-theme') === THEME;
  }

  function ensureGlow() {
    var shell = document.querySelector('.satka-shell');
    if (!shell) return;
    if (!shell.querySelector('.satka-lg-glow')) {
      var glow = document.createElement('div');
      glow.className = 'satka-lg-glow';
      glow.setAttribute('aria-hidden', 'true');
      shell.appendChild(glow);
    }
  }

  function tagGlassPanels() {
    if (!isActive()) return;
    var root = document.getElementById('root');
    if (!root) return;
    root.querySelectorAll('.bento-card, [class*="rounded-linear"]').forEach(function (el) {
      if (el.closest('header, nav, .satka-theme-switcher')) return;
      el.classList.add('satka-lg-glass', 'satka-lg-shine');
    });
  }

  function bindPointer() {
    if (pointerBound || !window.matchMedia('(pointer: fine)').matches) return;
    pointerBound = true;
    var ticking = false;
    window.addEventListener(
      'pointermove',
      function (e) {
        if (!isActive()) return;
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(function () {
          document.documentElement.style.setProperty('--satka-lg-x', e.clientX + 'px');
          document.documentElement.style.setProperty('--satka-lg-y', e.clientY + 'px');
          ticking = false;
        });
      },
      { passive: true },
    );
  }

  function boot() {
    if (isActive()) {
      document.documentElement.classList.add('satka-lg-ready');
      ensureGlow();
      tagGlassPanels();
      bindPointer();
    } else {
      document.documentElement.classList.remove('satka-lg-ready');
    }
  }

  boot();
  window.addEventListener('themeChanged', boot);

  if (window.SatkaRoute) {
    window.SatkaRoute.onTick(function () {
      if (isActive()) tagGlassPanels();
    });
  }

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) boot();
  });
})();

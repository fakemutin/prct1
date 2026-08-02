(function () {
  'use strict';

  var THEME = 'liquid-glass';

  function isActive() {
    return document.documentElement.getAttribute('data-satka-theme') === THEME;
  }

  function shouldRun() {
    return (
      isActive() &&
      !document.documentElement.classList.contains('satka-low-perf') &&
      !document.documentElement.classList.contains('satka-mobile') &&
      window.matchMedia('(pointer: fine)').matches
    );
  }

  function ensureGlow() {
    var shell = document.querySelector('.satka-shell');
    if (!shell || shell.querySelector('.satka-lg-glow')) return;
    var glow = document.createElement('div');
    glow.className = 'satka-lg-glow';
    glow.setAttribute('aria-hidden', 'true');
    shell.appendChild(glow);
  }

  function bindPointer() {
    if (!shouldRun()) return;
    ensureGlow();
    document.documentElement.classList.add('satka-lg-ready');

    var ticking = false;
    function onMove(e) {
      if (!shouldRun()) return;
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        document.documentElement.style.setProperty('--satka-lg-x', e.clientX + 'px');
        document.documentElement.style.setProperty('--satka-lg-y', e.clientY + 'px');
        ticking = false;
      });
    }

    window.addEventListener('pointermove', onMove, { passive: true });
  }

  function boot() {
    if (isActive()) {
      bindPointer();
    } else {
      document.documentElement.classList.remove('satka-lg-ready');
    }
  }

  boot();

  window.addEventListener('themeChanged', boot);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) boot();
  });

  if (window.SatkaTheme) {
    var orig = window.SatkaTheme.apply;
    window.SatkaTheme.apply = function (id) {
      orig.apply(this, arguments);
      boot();
    };
  }
})();

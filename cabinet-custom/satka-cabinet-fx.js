(function () {
  'use strict';

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  document.documentElement.classList.add('satka-fx-on');

  var root = document.getElementById('root');
  if (!root) return;

  function revealInjected() {
    document.querySelectorAll('.satka-reveal:not(.visible)').forEach(function (el) {
      el.classList.add('visible');
    });
  }

  function pulseCards() {
    root.querySelectorAll('[class*="card"], [class*="Card"], article').forEach(function (el, i) {
      if (el.closest('.satka-cabinet-wheel-block')) return;
      if (el.dataset.satkaFx) return;
      el.dataset.satkaFx = '1';
      el.classList.add('satka-fx-card');
      el.style.animationDelay = (i % 7) * 0.08 + 's';
    });
  }

  function shimmerHeadings() {
    root.querySelectorAll('h1, h2').forEach(function (h) {
      if (h.dataset.satkaFxH) return;
      h.dataset.satkaFxH = '1';
      h.classList.add('satka-fx-heading');
    });
  }

  function tick() {
    revealInjected();
    pulseCards();
    shimmerHeadings();
  }

  tick();

  if (window.SatkaRoute) {
    window.SatkaRoute.onChange(tick);
    window.SatkaRoute.whenRootReady(tick);
  }
})();

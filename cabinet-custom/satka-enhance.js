(function () {
  'use strict';

  var isMobile = window.matchMedia('(max-width: 768px)').matches;
  if (isMobile) return;

  function t(key) {
    return window.SatkaI18n ? window.SatkaI18n.t(key) : key;
  }

  function links() {
    return [
      { href: '/subscription', label: t('home.link.subscription'), accent: true },
      { href: '/balance', label: t('home.link.balance'), accent: true },
      { href: 'https://t.me/satkavpnsupport', label: t('home.link.support') },
      { href: 'https://t.me/satkavpn', label: t('home.link.channel') },
      { href: 'https://satkaconnect.xyz/#tariffs', label: t('home.link.site') },
    ];
  }

  var injected = false;

  function el(tag, className, html) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (html != null) node.innerHTML = html;
    return node;
  }

  function isHomePath() {
    var path = window.location.pathname.replace(/\/+$/, '') || '/';
    return path === '' || path === '/' || /\/home$/i.test(path);
  }

  function buildQuickLinks() {
    var wrap = el('div', 'satka-quick-links satka-reveal visible');
    links().forEach(function (item) {
      var a = el('a', 'satka-quick-link' + (item.accent ? ' accent' : ''));
      a.href = item.href;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.textContent = item.label;
      wrap.appendChild(a);
    });
    return wrap;
  }

  function buildHomeBlock() {
    var home = el('section', 'satka-home');
    home.setAttribute('data-satka-home', '1');
    var hero = el('div', 'satka-hero satka-reveal visible');
    hero.innerHTML =
      '<p class="satka-tag">' + t('home.tag') + '</p>' +
      '<h2>' + t('home.title') + '</h2>' +
      '<p>' + t('home.subtitle') + '</p>';
    home.appendChild(hero);
    home.appendChild(buildQuickLinks());
    return home;
  }

  function tryInject() {
    if (injected || !isHomePath()) return true;
    if (document.documentElement.classList.contains('satka-dock-right')) {
      injected = true;
      return true;
    }
    if (document.querySelector('[data-satka-home]')) {
      injected = true;
      return true;
    }
    var root = document.getElementById('root');
    if (!root || !root.children.length) return false;
    var main = root.querySelector('main') || root.querySelector('[role="main"]') || root.firstElementChild;
    if (!main) return false;
    var block = buildHomeBlock();
    if (main.firstChild) main.insertBefore(block, main.firstChild);
    else main.appendChild(block);
    injected = true;
    return true;
  }

  function resetInject() {
    injected = false;
    var old = document.querySelector('[data-satka-home]');
    if (old) old.remove();
    tryInject();
  }

  function watchApp() {
    tryInject();
  }

  if (window.SatkaRoute) {
    window.SatkaRoute.whenReady(watchApp);
    window.SatkaRoute.onChange(resetInject);
  } else {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchApp);
    else watchApp();
    window.addEventListener('popstate', resetInject);
  }
  window.addEventListener('satka-language-changed', resetInject);
  if (window.SatkaI18n) window.SatkaI18n.onChange(resetInject);
})();

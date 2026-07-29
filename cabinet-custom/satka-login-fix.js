(function () {
  'use strict';

  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) return;

  function t(key, params) {
    return window.SatkaI18n ? window.SatkaI18n.t(key, params) : key;
  }

  var API = '/api/cabinet/auth/deeplink';
  var POLL_MS = 2000;

  function isLoginPage() {
    return /\/login\/?$/i.test(window.location.pathname);
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      return Promise.resolve();
    } catch (e) {
      return Promise.reject(e);
    } finally {
      document.body.removeChild(ta);
    }
  }

  function hideTelegramWidget() {
    document.querySelectorAll('script[data-telegram-login]').forEach(function (s) {
      s.style.display = 'none';
    });
    document.querySelectorAll('iframe[src*="oauth.telegram.org"], iframe[src*="telegram.org"]').forEach(function (f) {
      f.style.display = 'none';
      f.style.visibility = 'hidden';
      f.style.width = '0';
      f.style.height = '0';
    });
  }

  function buildBlock(data) {
    var cmd = '/start webauth_' + data.token;
    var link = 'https://t.me/' + data.bot_username + '?start=webauth_' + data.token;
    var root = document.createElement('div');
    root.className = 'satka-deeplink-login';
    root.innerHTML =
      '<p class="satka-deeplink-title">' +
      t('login.title') +
      '</p>' +
      '<p class="satka-deeplink-hint">' +
      t('login.hint') +
      '</p>' +
      '<a class="satka-deeplink-open" href="' +
      link +
      '" target="_blank" rel="noopener noreferrer">' +
      t('login.open', { bot: data.bot_username }) +
      '</a>' +
      '<p class="satka-deeplink-or">' +
      t('login.or') +
      '</p>' +
      '<button type="button" class="satka-deeplink-cmd" data-cmd="' +
      cmd.replace(/"/g, '&quot;') +
      '"><code>' +
      cmd +
      '</code><span class="satka-deeplink-copy">' +
      t('login.copy') +
      '</span></button>' +
      '<p class="satka-deeplink-wait" hidden>' +
      t('login.wait') +
      '</p>';
    root.querySelector('.satka-deeplink-cmd').addEventListener('click', function () {
      var btn = this;
      copyText(cmd)
        .then(function () {
          btn.querySelector('.satka-deeplink-copy').textContent = t('login.copied');
          setTimeout(function () {
            btn.querySelector('.satka-deeplink-copy').textContent = t('login.copy');
          }, 2000);
        })
        .catch(function () {});
    });
    return root;
  }

  function pollLogin(token, waitEl, onSuccess) {
    var stopped = false;
    function tick() {
      if (stopped) return;
      fetch(API + '/poll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token }),
      })
        .then(function (res) {
          if (res.status === 200) {
            return res.json().then(function (body) {
              stopped = true;
              onSuccess(body);
            });
          }
          if (res.status === 202) {
            waitEl.hidden = false;
            setTimeout(tick, POLL_MS);
            return;
          }
          if (res.status === 410) {
            waitEl.textContent = t('login.expired');
            return;
          }
          setTimeout(tick, POLL_MS);
        })
        .catch(function () {
          setTimeout(tick, POLL_MS);
        });
    }
    tick();
    return function () {
      stopped = true;
    };
  }

  function applyTokens(auth) {
    if (!auth || !auth.access_token) return;
    try {
      sessionStorage.setItem('access_token', auth.access_token);
      if (auth.refresh_token) localStorage.setItem('refresh_token', auth.refresh_token);
    } catch (e) {}
    window.location.href = '/';
  }

  function mount() {
    if (!isLoginPage()) return;
    if (document.querySelector('.satka-deeplink-login')) return;

    var appRoot = document.getElementById('root');
    if (!appRoot || !appRoot.children.length) return;

    var main = appRoot.querySelector('main') || appRoot.querySelector('[role="main"]') || appRoot.firstElementChild;
    if (!main) return;

    var target = main.querySelector('.card') || main.querySelector('form');
    if (!target || !target.parentNode) return;

    hideTelegramWidget();

    fetch(API + '/request', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.token || !data.bot_username) return;
        if (document.querySelector('.satka-deeplink-login')) return;
        var block = buildBlock(data);
        target.parentNode.insertBefore(block, target);
        hideTelegramWidget();
        pollLogin(data.token, block.querySelector('.satka-deeplink-wait'), applyTokens);
      })
      .catch(function () {});
  }

  function tick() {
    if (!isLoginPage()) {
      document.querySelectorAll('.satka-deeplink-login').forEach(function (el) {
        el.remove();
      });
      return;
    }
    hideTelegramWidget();
    mount();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', tick);
  else tick();

  if (window.SatkaRoute) {
    window.SatkaRoute.onTick(tick);
    window.SatkaRoute.onChange(tick);
  } else {
    setInterval(tick, 500);
  }

  window.addEventListener('satka-language-changed', tick);
  if (window.SatkaI18n) window.SatkaI18n.onChange(tick);
})();

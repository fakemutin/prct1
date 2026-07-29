(function () {
  'use strict';

  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) return;

  function t(key, params) {
    return window.SatkaI18n ? window.SatkaI18n.t(key, params) : key;
  }

  var API = '/api/cabinet/auth/deeplink';
  var POLL_MS = 2000;
  var mounted = false;

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
      var box = s.parentElement;
      if (box) box.style.display = 'none';
    });
    document.querySelectorAll('iframe[src*="oauth.telegram.org"], iframe[src*="telegram.org"]').forEach(function (f) {
      var box = f.closest('div');
      if (box) box.style.display = 'none';
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
    if (mounted || !isLoginPage()) return true;
    var appRoot = document.getElementById('root');
    if (!appRoot || !appRoot.children.length) return false;
    mounted = true;
    hideTelegramWidget();
    fetch(API + '/request', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.token || !data.bot_username) return;
        var block = buildBlock(data);
        var main =
          appRoot.querySelector('main') || appRoot.querySelector('[role="main"]') || appRoot.firstElementChild;
        if (!main) return;
        var card = main.querySelector('form') || main.querySelector('.rounded-linear') || main.firstElementChild;
        if (card && card.parentNode) card.parentNode.insertBefore(block, card);
        else main.insertBefore(block, main.firstChild);
        hideTelegramWidget();
        setInterval(hideTelegramWidget, 800);
        pollLogin(data.token, block.querySelector('.satka-deeplink-wait'), applyTokens);
      })
      .catch(function () {});
    return true;
  }

  function remount() {
    mounted = false;
    document.querySelectorAll('.satka-deeplink-login').forEach(function (el) {
      el.remove();
    });
    mount();
  }

  function watch() {
    if (!isLoginPage()) return;
    if (mount()) return;
    var obs = new MutationObserver(function () {
      if (mount()) obs.disconnect();
    });
    var root = document.getElementById('root');
    if (root) obs.observe(root, { childList: true, subtree: true });
    setTimeout(function () {
      obs.disconnect();
      mount();
    }, 15000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watch);
  else watch();

  window.addEventListener('satka-language-changed', remount);
  if (window.SatkaI18n) window.SatkaI18n.onChange(remount);
})();

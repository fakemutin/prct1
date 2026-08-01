(function () {
  'use strict';

  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) return;

  function t(key, params) {
    return window.SatkaI18n ? window.SatkaI18n.t(key, params) : key;
  }

  var API = '/api/cabinet/auth/deeplink';
  var POLL_MS = 2000;
  var state = {
    token: null,
    pollStop: null,
    requestAbort: null,
    mountTimer: null,
    hideTimer: null,
    mounting: false,
  };

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
      if (box) {
        box.style.display = 'none';
        box.setAttribute('data-satka-hidden-widget', '1');
      }
    });
    document.querySelectorAll('iframe[src*="oauth.telegram.org"], iframe[src*="telegram.org"]').forEach(function (f) {
      var box = f.closest('div') || f.parentElement;
      if (box) {
        box.style.display = 'none';
        box.setAttribute('data-satka-hidden-widget', '1');
      }
    });
    document.querySelectorAll('[class*="telegram-login"], .telegram-login-button').forEach(function (el) {
      el.style.display = 'none';
    });
  }

  function isReactDeeplinkBlock(el) {
    if (!el || el.classList.contains('satka-deeplink-login')) return false;
    var text = (el.textContent || '').trim();
    if (text.indexOf('/start webauth_') !== -1) return true;
    if (el.querySelector('canvas, img[alt*="QR"], svg')) return true;
    var p = el.querySelector('p');
    if (!p) return false;
    var pt = (p.textContent || '').trim();
    return (
      pt === 'auth.telegramWidgetBlocked' ||
      pt.indexOf('Виджет входа') !== -1 ||
      pt.indexOf('widget') !== -1 ||
      pt.indexOf('Bot Domain') !== -1
    );
  }

  function hideReactDeeplinkFallback() {
    hideTelegramWidget();
    document.querySelectorAll('main .flex.flex-col.items-center, main [class*="space-y"]').forEach(function (el) {
      if (isReactDeeplinkBlock(el)) {
        el.style.display = 'none';
        el.setAttribute('data-satka-hidden-dup', '1');
      }
    });
    document.querySelectorAll('body *').forEach(function (el) {
      if (el.children.length > 20) return;
      var txt = (el.textContent || '').trim();
      if (txt === 'Bot Domain Invalid' || txt.indexOf('Bot Domain Invalid') === 0) {
        var box = el.closest('div');
        if (box) {
          box.style.display = 'none';
          box.setAttribute('data-satka-hidden-widget', '1');
        }
      }
    });
  }

  function scheduleHide() {
    hideReactDeeplinkFallback();
    if (state.hideTimer) return;
    var n = 0;
    state.hideTimer = setInterval(function () {
      hideReactDeeplinkFallback();
      n += 1;
      if (n > 40) {
        clearInterval(state.hideTimer);
        state.hideTimer = null;
      }
    }, 250);
  }

  function buildBlock(data) {
    var cmd = '/start webauth_' + data.token;
    var link = 'https://t.me/' + data.bot_username + '?start=webauth_' + data.token;
    var root = document.createElement('div');
    root.className = 'satka-deeplink-login';
    root.setAttribute('data-satka-deeplink', '1');
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
            if (waitEl) waitEl.hidden = false;
            setTimeout(tick, POLL_MS);
            return;
          }
          if (res.status === 410) {
            if (waitEl) waitEl.textContent = t('login.expired');
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

  function cleanup() {
    if (state.pollStop) {
      state.pollStop();
      state.pollStop = null;
    }
    if (state.requestAbort) {
      try {
        state.requestAbort.abort();
      } catch (e) {}
      state.requestAbort = null;
    }
    if (state.mountTimer) {
      clearTimeout(state.mountTimer);
      state.mountTimer = null;
    }
    document.querySelectorAll('.satka-deeplink-login').forEach(function (el) {
      el.remove();
    });
    state.token = null;
    state.mounting = false;
  }

  function insertBlock(block) {
    var appRoot = document.getElementById('root');
    if (!appRoot) return false;
    var main =
      appRoot.querySelector('main') || appRoot.querySelector('[role="main"]') || appRoot.firstElementChild;
    if (!main) return false;
    if (main.querySelector('.satka-deeplink-login')) return true;
    var card = main.querySelector('form') || main.querySelector('.rounded-linear') || main.firstElementChild;
    if (card && card.parentNode) card.parentNode.insertBefore(block, card);
    else main.insertBefore(block, main.firstChild);
    return true;
  }

  function doMount() {
    if (!isLoginPage()) {
      cleanup();
      return;
    }
    if (state.mounting) return;
    if (document.querySelector('.satka-deeplink-login') && state.token) {
      scheduleHide();
      return;
    }

    var appRoot = document.getElementById('root');
    if (!appRoot || !appRoot.children.length) return;

    scheduleHide();
    cleanup();
    state.mounting = true;

    var ac = new AbortController();
    state.requestAbort = ac;

    fetch(API + '/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: ac.signal,
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        state.mounting = false;
        if (!isLoginPage()) return;
        if (!data || !data.token || !data.bot_username) return;
        if (state.token === data.token && document.querySelector('.satka-deeplink-login')) return;

        document.querySelectorAll('.satka-deeplink-login').forEach(function (el) {
          el.remove();
        });

        state.token = data.token;
        var block = buildBlock(data);
        if (!insertBlock(block)) return;
        scheduleHide();
        if (state.pollStop) state.pollStop();
        state.pollStop = pollLogin(data.token, block.querySelector('.satka-deeplink-wait'), applyTokens);
      })
      .catch(function (err) {
        state.mounting = false;
        if (err && err.name === 'AbortError') return;
      });
  }

  function scheduleMount() {
    if (!isLoginPage()) {
      cleanup();
      return;
    }
    scheduleHide();
    if (state.mountTimer) clearTimeout(state.mountTimer);
    state.mountTimer = setTimeout(doMount, 150);
  }

  function remount() {
    if (!isLoginPage()) return;
    var block = document.querySelector('.satka-deeplink-login');
    if (block && state.token) {
      block.querySelector('.satka-deeplink-title').textContent = t('login.title');
      block.querySelector('.satka-deeplink-hint').textContent = t('login.hint');
      scheduleHide();
      return;
    }
    scheduleMount();
  }

  function init() {
    if (!isLoginPage()) return;
    scheduleHide();
    scheduleMount();

    if (window.SatkaRoute) {
      window.SatkaRoute.onChange(function (path) {
        if (!/\/login\/?$/i.test(path)) cleanup();
        else scheduleMount();
      });
      window.SatkaRoute.onTick(function () {
        if (isLoginPage()) scheduleHide();
      });
    } else {
      var obs = new MutationObserver(function () {
        if (isLoginPage()) {
          scheduleHide();
          scheduleMount();
        }
      });
      var root = document.getElementById('root');
      if (root) obs.observe(root, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.addEventListener('satka-language-changed', remount);
  if (window.SatkaI18n) window.SatkaI18n.onChange(remount);

  window.SatkaLoginFix = { remount: remount, cleanup: cleanup };
})();

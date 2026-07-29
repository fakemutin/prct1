(function () {
  'use strict';

  var API_LOGIN = '/api/cabinet/auth/email/login';
  var API_REGISTER = '/cabinet/auth/email/register/standalone';
  var CSRF_COOKIE = 'csrf_token';
  var CSRF_HEADER = 'X-CSRF-Token';

  function parseJson(text) {
    try {
      return JSON.parse(text);
    } catch (e) {
      return null;
    }
  }

  function ensureCsrfToken() {
    var match = document.cookie.match(new RegExp('(^| )' + CSRF_COOKIE + '=([^;]+)'));
    var token = match ? decodeURIComponent(match[2]) : null;
    if (token) return token;
    if (!crypto || !crypto.getRandomValues) return null;
    var array = new Uint8Array(32);
    crypto.getRandomValues(array);
    token = Array.from(array, function (b) {
      return b.toString(16).padStart(2, '0');
    }).join('');
    document.cookie = CSRF_COOKIE + '=' + token + '; path=/; SameSite=Strict; Secure';
    return token;
  }

  function setTokens(auth) {
    if (!auth || !auth.access_token) return false;
    try {
      sessionStorage.setItem('access_token', auth.access_token);
      if (auth.refresh_token) localStorage.setItem('refresh_token', auth.refresh_token);
      if (auth.user) sessionStorage.setItem('user', JSON.stringify(auth.user));
    } catch (e) {
      return false;
    }
    return true;
  }

  function isCheckEmailCard(card) {
    if (!card || !card.classList || !card.classList.contains('text-center')) return false;
    var h2 = card.querySelector('h2');
    if (!h2) return false;
    var t = (h2.textContent || '').toLowerCase();
    return t.indexOf('проверьте') !== -1 || t.indexOf('check your email') !== -1;
  }

  function hideCheckEmailCard() {
    var root = document.getElementById('root');
    if (!root) return;
    root.querySelectorAll('.card.text-center').forEach(function (card) {
      if (isCheckEmailCard(card)) card.style.setProperty('display', 'none', 'important');
    });
  }

  function autoLogin(email, password) {
    var headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
    var csrf = ensureCsrfToken();
    if (csrf) headers[CSRF_HEADER] = csrf;
    return fetch(API_LOGIN, {
      method: 'POST',
      credentials: 'include',
      headers: headers,
      body: JSON.stringify({ email: email, password: password }),
    }).then(function (res) {
      return res.ok ? res.json() : null;
    }).catch(function () {
      return null;
    });
  }

  function afterRegister(credentials) {
    if (!credentials || !credentials.email || !credentials.password) return;
    hideCheckEmailCard();
    autoLogin(credentials.email, credentials.password).then(function (auth) {
      if (setTokens(auth)) window.location.replace('/');
    });
  }

  function hookXHR() {
    if (window.__satkaAuthXhrHook) return;
    window.__satkaAuthXhrHook = true;
    var origOpen = XMLHttpRequest.prototype.open;
    var origSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function (method, url) {
      this._satkaMethod = method;
      this._satkaUrl = String(url || '');
      return origOpen.apply(this, arguments);
    };

    XMLHttpRequest.prototype.send = function (body) {
      var xhr = this;
      var url = xhr._satkaUrl || '';
      var isRegister =
        url.indexOf(API_REGISTER) !== -1 && String(xhr._satkaMethod || 'GET').toUpperCase() === 'POST';
      var credentials = isRegister && body ? parseJson(body) : null;

      if (isRegister) {
        xhr.addEventListener('load', function () {
          if (xhr.status < 200 || xhr.status >= 300) return;
          var res = parseJson(xhr.responseText);
          if (!res || res.requires_verification === true) return;
          afterRegister(credentials);
        });
      }
      return origSend.apply(this, arguments);
    };
  }

  function hookFetch() {
    if (window.__satkaAuthFetchHook || !window.fetch) return;
    window.__satkaAuthFetchHook = true;
    var orig = window.fetch;
    window.fetch = function (input, init) {
      var url = typeof input === 'string' ? input : input && input.url;
      var isRegister = url && url.indexOf(API_REGISTER) !== -1;
      var credentials =
        isRegister && init && init.body && typeof init.body === 'string' ? parseJson(init.body) : null;
      return orig.apply(this, arguments).then(function (res) {
        if (!isRegister || !res.ok) return res;
        return res.clone().json().then(function (body) {
          if (body && body.requires_verification !== true) afterRegister(credentials);
          return res;
        }).catch(function () {
          return res;
        });
      });
    };
  }

  function watchVerifyCard() {
    hideCheckEmailCard();
    var root = document.getElementById('root');
    if (!root || window.__satkaAuthCardObserver) return;
    window.__satkaAuthCardObserver = new MutationObserver(hideCheckEmailCard);
    window.__satkaAuthCardObserver.observe(root, { childList: true, subtree: true });
  }

  document.documentElement.classList.add('satka-no-email-verify');
  hookXHR();
  hookFetch();
  watchVerifyCard();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watchVerifyCard);
  }
})();

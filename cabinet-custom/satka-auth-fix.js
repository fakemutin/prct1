(function () {
  'use strict';

  var API_LOGIN = '/api/cabinet/auth/email/login';
  var API_REGISTER = '/cabinet/auth/email/register/standalone';
  var CSRF_COOKIE = 'csrf_token';
  var CSRF_HEADER = 'X-CSRF-Token';
  var STORE_KEY = 'satka_pending_register';
  var loginInFlight = false;

  function parseJson(text) {
    try {
      return JSON.parse(text);
    } catch (e) {
      return null;
    }
  }

  function saveCredentials(credentials) {
    if (!credentials || !credentials.email || !credentials.password) return;
    try {
      sessionStorage.setItem(STORE_KEY, JSON.stringify({ email: credentials.email, password: credentials.password }));
    } catch (e) {}
  }

  function loadCredentials() {
    try {
      return JSON.parse(sessionStorage.getItem(STORE_KEY) || 'null');
    } catch (e) {
      return null;
    }
  }

  function clearCredentials() {
    try {
      sessionStorage.removeItem(STORE_KEY);
    } catch (e) {}
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

  function autoLogin(email, password) {
    var headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
    var csrf = ensureCsrfToken();
    if (csrf) headers[CSRF_HEADER] = csrf;
    return fetch(API_LOGIN, {
      method: 'POST',
      credentials: 'include',
      headers: headers,
      body: JSON.stringify({ email: email, password: password }),
    })
      .then(function (res) {
        return res.ok ? res.json() : null;
      })
      .catch(function () {
        return null;
      });
  }

  function findCheckEmailCard() {
    var root = document.getElementById('root');
    if (!root) return null;
    var cards = root.querySelectorAll('.card.text-center');
    for (var i = 0; i < cards.length; i++) {
      var h2 = cards[i].querySelector('h2');
      if (!h2) continue;
      var t = (h2.textContent || '').toLowerCase();
      if (t.indexOf('проверьте') !== -1 || t.indexOf('check your email') !== -1) return cards[i];
    }
    return null;
  }

  function resetToLoginForm() {
    var card = findCheckEmailCard();
    if (!card) return;
    var btn = card.querySelector('button');
    if (btn) btn.click();
  }

  function completeLogin(credentials) {
    if (!credentials || loginInFlight) return;
    loginInFlight = true;

    function attempt(n) {
      autoLogin(credentials.email, credentials.password).then(function (auth) {
        if (setTokens(auth)) {
          clearCredentials();
          window.location.replace('/');
          return;
        }
        if (n < 5) {
          setTimeout(function () {
            attempt(n + 1);
          }, 350);
          return;
        }
        loginInFlight = false;
        resetToLoginForm();
      });
    }

    attempt(0);
  }

  function afterRegister(credentials) {
    credentials = credentials || loadCredentials();
    if (!credentials) return;
    saveCredentials(credentials);
    completeLogin(credentials);
  }

  function recoverCheckEmailScreen() {
    if (!findCheckEmailCard()) return;
    var creds = loadCredentials();
    if (creds) completeLogin(creds);
    else resetToLoginForm();
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
      var credentials = isRegister && typeof body === 'string' ? parseJson(body) : null;
      if (credentials) saveCredentials(credentials);

      if (isRegister) {
        xhr.addEventListener('load', function () {
          if (xhr.status < 200 || xhr.status >= 300) return;
          var res = parseJson(xhr.responseText);
          if (!res || res.requires_verification === true) return;
          afterRegister(credentials || loadCredentials());
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
      if (credentials) saveCredentials(credentials);
      return orig.apply(this, arguments).then(function (res) {
        if (!isRegister || !res.ok) return res;
        return res
          .clone()
          .json()
          .then(function (body) {
            if (body && body.requires_verification !== true) afterRegister(credentials || loadCredentials());
            return res;
          })
          .catch(function () {
            return res;
          });
      });
    };
  }

  function watchCheckEmailScreen() {
    recoverCheckEmailScreen();
    var root = document.getElementById('root');
    if (!root || window.__satkaAuthVerifyObserver) return;
    window.__satkaAuthVerifyObserver = new MutationObserver(function () {
      recoverCheckEmailScreen();
    });
    window.__satkaAuthVerifyObserver.observe(root, { childList: true, subtree: true });
  }

  document.documentElement.classList.add('satka-no-email-verify');
  hookXHR();
  hookFetch();
  watchCheckEmailScreen();
  setInterval(recoverCheckEmailScreen, 400);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watchCheckEmailScreen);
  }
})();

(function () {
  'use strict';

  var API_LOGIN = '/api/cabinet/auth/email/login';
  var API_REGISTER = '/cabinet/auth/email/register/standalone';
  var API_EMAIL_AUTH = '/api/cabinet/branding/email-auth';
  var CSRF_COOKIE = 'csrf_token';
  var CSRF_HEADER = 'X-CSRF-Token';
  var STORE_KEY = 'satka_pending_register';
  var verificationDisabled = true;
  var loginInFlight = false;

  function isLoginPage() {
    return /\/login\/?$/i.test(window.location.pathname);
  }

  function applyUi() {
    document.documentElement.classList.add('satka-no-email-verify');
    if (isLoginPage()) document.documentElement.classList.add('satka-on-login');
  }

  function setPending(on) {
    document.documentElement.classList.toggle('satka-register-pending', !!on);
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
    if (typeof document === 'undefined') return null;
    var match = document.cookie.match(new RegExp('(^| )' + CSRF_COOKIE + '=([^;]+)'));
    var token = match ? decodeURIComponent(match[2]) : null;
    if (token) return token;
    if (typeof crypto === 'undefined' || !crypto.getRandomValues) return null;
    var array = new Uint8Array(32);
    crypto.getRandomValues(array);
    token = Array.from(array, function (b) {
      return b.toString(16).padStart(2, '0');
    }).join('');
    document.cookie = CSRF_COOKIE + '=' + token + '; path=/; SameSite=Strict; Secure';
    return token;
  }

  function parseJson(text) {
    try {
      return JSON.parse(text);
    } catch (e) {
      return null;
    }
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

  function shouldSkipVerification(body) {
    if (verificationDisabled) return true;
    if (body && body.requires_verification === false) return true;
    return false;
  }

  function autoLogin(email, password) {
    var headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
    var csrf = ensureCsrfToken();
    if (csrf) headers[CSRF_HEADER] = csrf;

    return fetch(API_LOGIN, {
      method: 'POST',
      credentials: 'include',
      headers: headers,
      body: JSON.stringify({ email: email, password: password }),
    })
      .then(function (res) {
        if (!res.ok) return null;
        return res.json();
      })
      .catch(function () {
        return null;
      });
  }

  function completeLogin(credentials) {
    if (!credentials || loginInFlight) return;
    loginInFlight = true;
    setPending(true);
    applyUi();

    function attempt(n) {
      autoLogin(credentials.email, credentials.password).then(function (auth) {
        if (setTokens(auth)) {
          clearCredentials();
          window.location.replace('/');
          return;
        }
        if (n < 4) {
          setTimeout(function () {
            attempt(n + 1);
          }, 400);
          return;
        }
        loginInFlight = false;
        setPending(false);
      });
    }

    attempt(0);
  }

  function afterRegister(body, credentials) {
    credentials = credentials || loadCredentials();
    if (!credentials || !credentials.email || !credentials.password) return;
    if (!shouldSkipVerification(body)) return;
    saveCredentials(credentials);
    completeLogin(credentials);
  }

  function onRegisterRequest(body) {
    var credentials = typeof body === 'string' ? parseJson(body) : body;
    if (credentials) saveCredentials(credentials);
    setPending(true);
    applyUi();
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
      var credentials = null;

      if (isRegister && body) {
        onRegisterRequest(body);
        credentials = typeof body === 'string' ? parseJson(body) : null;
      }

      if (isRegister) {
        xhr.addEventListener('load', function () {
          if (xhr.status < 200 || xhr.status >= 300) {
            setPending(false);
            return;
          }
          var res = parseJson(xhr.responseText);
          if (res) afterRegister(res, credentials || loadCredentials());
        });
      }

      return origSend.apply(this, arguments);
    };
  }

  function hookFetch() {
    if (window.__satkaAuthFetchHook) return;
    window.__satkaAuthFetchHook = true;
    if (!window.fetch) return;

    var orig = window.fetch;
    window.fetch = function (input, init) {
      var url = typeof input === 'string' ? input : input && input.url;
      var isRegister = url && url.indexOf(API_REGISTER) !== -1;
      var credentials = null;

      if (isRegister && init && init.body) {
        onRegisterRequest(init.body);
        credentials = typeof init.body === 'string' ? parseJson(init.body) : null;
      }

      return orig.apply(this, arguments).then(function (res) {
        if (!isRegister) return res;
        if (!res.ok) {
          setPending(false);
          return res;
        }
        return res
          .clone()
          .json()
          .then(function (body) {
            afterRegister(body, credentials || loadCredentials());
            return res;
          })
          .catch(function () {
            return res;
          });
      });
    };
  }

  function isVerifyHeading(text) {
    var t = String(text || '').toLowerCase();
    return (
      t.indexOf('проверьте') !== -1 ||
      t.indexOf('почт') !== -1 ||
      t.indexOf('check your email') !== -1 ||
      t.indexOf('verification') !== -1
    );
  }

  function hideVerifyScreen() {
    if (!isLoginPage()) return false;
    var root = document.getElementById('root');
    if (!root) return false;
    var hidden = false;

    root.querySelectorAll('h2, h1, p').forEach(function (el) {
      if (!isVerifyHeading(el.textContent)) return;
      var card = el.closest ? el.closest('.card') : null;
      if (card) {
        card.style.setProperty('display', 'none', 'important');
        hidden = true;
      }
    });

    root.querySelectorAll('.card.text-center').forEach(function (card) {
      var heading = card.querySelector('h2, h1');
      if (heading && isVerifyHeading(heading.textContent)) {
        card.style.setProperty('display', 'none', 'important');
        hidden = true;
      }
    });

    if (hidden) {
      var creds = loadCredentials();
      if (creds) completeLogin(creds);
    }
    return hidden;
  }

  function watchForm() {
    if (!isLoginPage()) return;
    document.querySelectorAll('form').forEach(function (form) {
      if (form.__satkaAuthBound) return;
      form.__satkaAuthBound = true;
      form.addEventListener(
        'submit',
        function () {
          var email = form.querySelector('input[type="email"], input[name="email"], input[autocomplete="email"]');
          var pass = form.querySelector('input[type="password"], input[name="password"]');
          if (email && pass && email.value && pass.value) {
            saveCredentials({ email: email.value, password: pass.value });
            setPending(true);
          }
        },
        true
      );
    });
  }

  function tick() {
    applyUi();
    if (isLoginPage()) {
      hideVerifyScreen();
      watchForm();
    } else {
      document.documentElement.classList.remove('satka-on-login', 'satka-register-pending');
    }
  }

  function loadConfig() {
    fetch(API_EMAIL_AUTH, { credentials: 'include', headers: { Accept: 'application/json' } })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        verificationDisabled = !(data && data.verification_enabled);
        if (verificationDisabled) applyUi();
      })
      .catch(function () {
        verificationDisabled = true;
        applyUi();
      });
  }

  applyUi();
  hookXHR();
  hookFetch();
  loadConfig();
  tick();

  setInterval(tick, 200);

  if (window.SatkaRoute) {
    window.SatkaRoute.onChange(tick);
    window.SatkaRoute.onTick(tick);
  } else {
    window.addEventListener('popstate', tick);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tick);
  }
})();

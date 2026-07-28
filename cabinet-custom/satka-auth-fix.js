(function () {
  'use strict';

  var API_LOGIN = '/api/cabinet/auth/email/login';
  var API_REGISTER = '/cabinet/auth/email/register/standalone';
  var API_EMAIL_AUTH = '/api/cabinet/branding/email-auth';
  var CSRF_COOKIE = 'csrf_token';
  var CSRF_HEADER = 'X-CSRF-Token';
  var verificationDisabled = false;
  var lastCredentials = null;
  var pendingAutoLogin = false;

  function isLoginPage() {
    return /\/login\/?$/i.test(window.location.pathname);
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

  function setTokens(auth) {
    if (!auth || !auth.access_token) return false;
    try {
      sessionStorage.setItem('access_token', auth.access_token);
      if (auth.refresh_token) localStorage.setItem('refresh_token', auth.refresh_token);
    } catch (e) {
      return false;
    }
    return true;
  }

  function parseJson(text) {
    try {
      return JSON.parse(text);
    } catch (e) {
      return null;
    }
  }

  function applyNoVerifyUi() {
    document.documentElement.classList.add('satka-no-email-verify');
    if (isLoginPage()) document.documentElement.classList.add('satka-on-login');
  }

  function showRegisterPending() {
    pendingAutoLogin = true;
    document.documentElement.classList.add('satka-register-pending');
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

  function afterRegister(body, credentials) {
    if (!credentials || !credentials.email || !credentials.password) return;
    if (!shouldSkipVerification(body)) return;

    showRegisterPending();
    autoLogin(credentials.email, credentials.password).then(function (auth) {
      if (setTokens(auth)) {
        window.location.replace('/');
        return;
      }
      document.documentElement.classList.remove('satka-register-pending');
      pendingAutoLogin = false;
    });
  }

  function onRegisterRequest(body) {
    var credentials = typeof body === 'string' ? parseJson(body) : null;
    if (credentials) lastCredentials = credentials;
    if (shouldSkipVerification({ requires_verification: false })) showRegisterPending();
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
        credentials = parseJson(body);
      }

      if (isRegister) {
        xhr.addEventListener('load', function () {
          if (xhr.status < 200 || xhr.status >= 300) {
            document.documentElement.classList.remove('satka-register-pending');
            pendingAutoLogin = false;
            return;
          }
          var res = parseJson(xhr.responseText);
          if (res) afterRegister(res, credentials || lastCredentials);
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
          document.documentElement.classList.remove('satka-register-pending');
          pendingAutoLogin = false;
          return res;
        }
        return res
          .clone()
          .json()
          .then(function (body) {
            afterRegister(body, credentials || lastCredentials);
            return res;
          })
          .catch(function () {
            return res;
          });
      });
    };
  }

  function hideCheckEmailCard(node) {
    if (!node || node.nodeType !== 1) return false;
    var card = node.closest ? node.closest('.card.text-center') : null;
    if (!card) return false;
    var heading = card.querySelector('h2');
    if (!heading) return false;
    var text = (heading.textContent || '').toLowerCase();
    if (
      text.indexOf('почт') !== -1 ||
      text.indexOf('email') !== -1 ||
      text.indexOf('mail') !== -1
    ) {
      card.style.display = 'none';
      return true;
    }
    return false;
  }

  function watchVerificationCard() {
    if (!verificationDisabled || !isLoginPage()) return;
    var root = document.getElementById('root');
    if (!root) return;

    function scan() {
      if (!verificationDisabled || pendingAutoLogin) return;
      root.querySelectorAll('.card.text-center h2').forEach(function (h2) {
        hideCheckEmailCard(h2);
      });
    }

    scan();
    if (window.__satkaAuthCardObserver) return;
    window.__satkaAuthCardObserver = new MutationObserver(scan);
    window.__satkaAuthCardObserver.observe(root, { childList: true, subtree: true });
  }

  function syncLoginClass() {
    if (isLoginPage()) {
      document.documentElement.classList.add('satka-on-login');
      watchVerificationCard();
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
        if (data && data.verification_enabled === false) {
          verificationDisabled = true;
          applyNoVerifyUi();
          watchVerificationCard();
        } else if (data && data.verification_enabled) {
          verificationDisabled = false;
          document.documentElement.classList.remove('satka-no-email-verify', 'satka-register-pending');
        }
      })
      .catch(function () {
        verificationDisabled = true;
        applyNoVerifyUi();
        watchVerificationCard();
      });
  }

  if (isLoginPage()) {
    verificationDisabled = true;
    applyNoVerifyUi();
  }
  syncLoginClass();
  hookXHR();
  hookFetch();
  loadConfig();

  if (window.SatkaRoute) {
    window.SatkaRoute.onChange(syncLoginClass);
    window.SatkaRoute.onTick(syncLoginClass);
  } else {
    window.addEventListener('popstate', syncLoginClass);
    setInterval(syncLoginClass, 500);
  }
})();

(function () {
  'use strict';

  var API_LOGIN = '/api/cabinet/auth/email/login';
  var API_REGISTER = '/cabinet/auth/email/register/standalone';
  var API_EMAIL_AUTH = '/api/cabinet/branding/email-auth';
  var verificationDisabled = false;
  var lastCredentials = null;

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

  function autoLogin(email, password) {
    return new Promise(function (resolve) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', API_LOGIN, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.withCredentials = true;
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(parseJson(xhr.responseText));
        } else {
          resolve(null);
        }
      };
      xhr.onerror = function () {
        resolve(null);
      };
      xhr.send(JSON.stringify({ email: email, password: password }));
    });
  }

  function afterRegister(body, credentials) {
    if (!credentials || !credentials.email || !credentials.password) return;
    if (!verificationDisabled && body && body.requires_verification !== false) return;

    autoLogin(credentials.email, credentials.password).then(function (auth) {
      if (setTokens(auth)) {
        window.location.replace('/');
      }
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
      var credentials = null;

      if (isRegister && body) {
        credentials = parseJson(body);
        if (credentials) lastCredentials = credentials;
      }

      if (isRegister) {
        xhr.addEventListener('load', function () {
          if (xhr.status < 200 || xhr.status >= 300) return;
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
        credentials = typeof init.body === 'string' ? parseJson(init.body) : null;
        if (credentials) lastCredentials = credentials;
      }

      return orig.apply(this, arguments).then(function (res) {
        if (!isRegister || !res.ok) return res;
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

  function applyNoVerifyUi() {
    document.documentElement.classList.add('satka-no-email-verify');
    if (/\/login/i.test(window.location.pathname)) {
      document.documentElement.classList.add('satka-on-login');
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
        }
      })
      .catch(function () {
        verificationDisabled = true;
        applyNoVerifyUi();
      });
  }

  hookXHR();
  hookFetch();
  loadConfig();

  if (window.SatkaRoute) {
    window.SatkaRoute.onChange(function () {
      if (/\/login/i.test(window.location.pathname)) {
        document.documentElement.classList.add('satka-on-login');
      } else {
        document.documentElement.classList.remove('satka-on-login');
      }
    });
  }
})();

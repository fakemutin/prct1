(function (global) {
  'use strict';

  var CSRF_COOKIE = 'csrf_token';
  var CSRF_HEADER = 'X-CSRF-Token';

  function getAccessToken() {
    try {
      return sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
    } catch (e) {
      return null;
    }
  }

  function getRefreshToken() {
    try {
      return localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
    } catch (e) {
      return null;
    }
  }

  function getCsrfToken() {
    if (typeof document === 'undefined') return null;
    var match = document.cookie.match(new RegExp('(^| )' + CSRF_COOKIE + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
  }

  function ensureCsrfToken() {
    var token = getCsrfToken();
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

  function parseErrorBody(body, status) {
    if (!body) return status === 401 ? 'Требуется авторизация' : 'Ошибка запроса';
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map(function (d) {
          return d.msg || d.message || JSON.stringify(d);
        })
        .join('; ');
    }
    if (body.error) return String(body.error);
    return 'Ошибка запроса';
  }

  function refreshAccessToken() {
    var refresh = getRefreshToken();
    if (!refresh) return Promise.resolve(null);
    var csrf = ensureCsrfToken();
    var headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
    if (csrf) headers[CSRF_HEADER] = csrf;
    return fetch('/api/cabinet/auth/refresh', {
      method: 'POST',
      credentials: 'include',
      headers: headers,
      body: JSON.stringify({ refresh_token: refresh }),
    })
      .then(function (res) {
        return res.json().catch(function () {
          return {};
        });
      })
      .then(function (data) {
        if (data.access_token) {
          try {
            sessionStorage.setItem('access_token', data.access_token);
          } catch (e) {}
          return data.access_token;
        }
        return null;
      })
      .catch(function () {
        return null;
      });
  }

  function apiFetch(url, options, retry) {
    options = options || {};
    var headers = Object.assign({ Accept: 'application/json' }, options.headers || {});
    if (options.body && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
    var token = getAccessToken();
    if (token) headers.Authorization = 'Bearer ' + token;
    var csrf = ensureCsrfToken();
    if (csrf) headers[CSRF_HEADER] = csrf;

    return fetch(url, {
      method: options.method || 'GET',
      credentials: 'include',
      headers: headers,
      body: options.body,
    }).then(function (res) {
      if (res.status === 401 && !retry) {
        return refreshAccessToken().then(function (newToken) {
          if (!newToken) {
            var err = new Error('Требуется авторизация');
            err.status = 401;
            throw err;
          }
          return apiFetch(url, options, true);
        });
      }
      if (!res.ok) {
        return res
          .json()
          .catch(function () {
            return {};
          })
          .then(function (body) {
            var err = new Error(parseErrorBody(body, res.status));
            err.status = res.status;
            err.body = body;
            throw err;
          });
      }
      if (res.status === 204) return null;
      return res.json();
    });
  }

  global.SatkaCabinetApi = {
    getAccessToken: getAccessToken,
    apiFetch: apiFetch,
    refreshAccessToken: refreshAccessToken,
  };
})(window);

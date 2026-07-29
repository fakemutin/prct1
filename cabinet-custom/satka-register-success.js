(function () {
  'use strict';

  var REGISTER_RE = /\/api\/cabinet\/auth\/email\/register(?:\/standalone)?(?:\?|$)/i;
  var overlay;
  var hideTimer;
  var hooked;
  var verificationEnabled = null;

  function t(key) {
    return window.SatkaI18n ? window.SatkaI18n.t(key) : key;
  }

  function isLoginPage() {
    return /\/login\/?$/i.test(window.location.pathname);
  }

  function isRegisterRequest(url, method) {
    if (!url || String(method || 'GET').toUpperCase() !== 'POST') return false;
    try {
      var path = url.indexOf('http') === 0 ? new URL(url, window.location.origin).pathname : url;
      return REGISTER_RE.test(path);
    } catch (e) {
      return REGISTER_RE.test(String(url));
    }
  }

  function loadVerificationFlag() {
    if (verificationEnabled !== null) return Promise.resolve(verificationEnabled);
    return fetch('/api/cabinet/branding/email-auth', { credentials: 'same-origin' })
      .then(function (res) {
        return res.ok ? res.json() : null;
      })
      .then(function (data) {
        verificationEnabled = !!(data && data.verification_enabled);
        return verificationEnabled;
      })
      .catch(function () {
        verificationEnabled = false;
        return false;
      });
  }

  function playSuccessSound() {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = new Ctx();
      var now = ctx.currentTime;
      var master = ctx.createGain();
      master.gain.setValueAtTime(0.0001, now);
      master.gain.exponentialRampToValueAtTime(0.28, now + 0.02);
      master.gain.exponentialRampToValueAtTime(0.0001, now + 1.1);
      master.connect(ctx.destination);

      var notes = [
        { f: 523.25, t: 0, d: 0.22 },
        { f: 659.25, t: 0.09, d: 0.24 },
        { f: 783.99, t: 0.18, d: 0.28 },
        { f: 1046.5, t: 0.3, d: 0.55 },
      ];

      notes.forEach(function (note) {
        var start = now + note.t;
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(note.f, start);
        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.exponentialRampToValueAtTime(0.55, start + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + note.d);
        osc.connect(gain);
        gain.connect(master);
        osc.start(start);
        osc.stop(start + note.d + 0.05);
      });

      setTimeout(function () {
        ctx.close().catch(function () {});
      }, 1400);
    } catch (e) {}
  }

  function ensureOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.className = 'satka-reg-success-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.innerHTML =
      '<div class="satka-reg-success-card">' +
      '<div class="satka-reg-success-icon" aria-hidden="true">' +
      '<svg viewBox="0 0 24 24"><path d="M5 13l4 4L19 7"/></svg>' +
      '</div>' +
      '<h2 class="satka-reg-success-title"></h2>' +
      '<p class="satka-reg-success-text"></p>' +
      '<button type="button" class="satka-reg-success-btn"></button>' +
      '</div>';
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) hide();
    });
    overlay.querySelector('.satka-reg-success-btn').addEventListener('click', hide);
    document.body.appendChild(overlay);
    return overlay;
  }

  function refreshText(verifyMode) {
    if (!overlay) return;
    overlay.querySelector('.satka-reg-success-title').textContent = verifyMode
      ? t('register.success.verifyTitle')
      : t('register.success.title');
    overlay.querySelector('.satka-reg-success-text').textContent = verifyMode
      ? t('register.success.verifyMessage')
      : t('register.success.message');
    overlay.querySelector('.satka-reg-success-btn').textContent = t('register.success.btn');
  }

  function hide() {
    if (!overlay) return;
    overlay.classList.remove('is-visible');
    clearTimeout(hideTimer);
  }

  function show(verifyMode) {
    if (!isLoginPage()) return;
    ensureOverlay();
    refreshText(verifyMode);
    overlay.classList.add('is-visible');
    playSuccessSound();
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hide, verifyMode ? 12000 : 8000);
  }

  function onRegisterSuccess(res) {
    if (!isLoginPage()) return;
    var chain = Promise.resolve(verificationEnabled);
    if (verificationEnabled === null) {
      chain = loadVerificationFlag();
    }
    chain.then(function (enabled) {
      if (enabled && res && res.clone) {
        return res
          .clone()
          .json()
          .then(function (body) {
            var needsVerify = body && (body.requires_verification === true || body.requires_verification === undefined);
            setTimeout(function () {
              show(needsVerify);
            }, 120);
          })
          .catch(function () {
            setTimeout(function () {
              show(true);
            }, 120);
          });
      }
      setTimeout(function () {
        show(!!enabled);
      }, 120);
    });
  }

  function hookFetch() {
    if (!window.fetch || window.fetch.__satkaRegisterHook) return;
    var orig = window.fetch;
    function wrapped(input, init) {
      var url = typeof input === 'string' ? input : input && input.url;
      var method = (init && init.method) || (input && input.method) || 'GET';
      var track = isRegisterRequest(url, method);
      return orig.apply(this, arguments).then(function (res) {
        if (track && res.ok) onRegisterSuccess(res);
        return res;
      });
    }
    wrapped.__satkaRegisterHook = true;
    window.fetch = wrapped;
  }

  function hookXHR() {
    if (hooked || !window.XMLHttpRequest) return;
    hooked = true;
    var open = XMLHttpRequest.prototype.open;
    var send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (method, url) {
      this.__satkaRegMethod = method;
      this.__satkaRegUrl = url;
      return open.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function () {
      var xhr = this;
      if (isRegisterRequest(xhr.__satkaRegUrl, xhr.__satkaRegMethod)) {
        xhr.addEventListener('load', function () {
          if (xhr.status >= 200 && xhr.status < 300) {
            loadVerificationFlag().then(function (enabled) {
              show(enabled);
            });
          }
        });
      }
      return send.apply(this, arguments);
    };
  }

  function init() {
    loadVerificationFlag();
    hookFetch();
    hookXHR();
    if (window.SatkaI18n) {
      window.SatkaI18n.onChange(function () {
        if (overlay && overlay.classList.contains('is-visible')) {
          refreshText(verificationEnabled);
        }
      });
    }
    window.addEventListener('satka-language-changed', function () {
      if (overlay && overlay.classList.contains('is-visible')) {
        refreshText(verificationEnabled);
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.SatkaRegisterSuccess = { show: show, hide: hide };
})();

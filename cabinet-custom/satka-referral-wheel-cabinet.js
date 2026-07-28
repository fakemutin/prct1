(function () {
  'use strict';

  function t(key, params) {
    return window.SatkaI18n ? window.SatkaI18n.t(key, params) : key;
  }

  var API_BASE = '/api/cabinet/satka/referral-wheel';
  var SPIN_MS = 4800;
  var rotation = 0;
  var spinning = false;
  var injected = false;
  var state = null;
  var segmentsCache = [];

  var ICONS = {
    balance: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v10M9 10h4.5a2 2 0 1 0 0-4H10a2 2 0 0 0 0 4h4.5a2 2 0 1 1 0 4H9"/></svg>',
    days: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>',
    gift: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="13" rx="1"/><path d="M12 8v13M3 12h18M12 8c-2-3-5-3-5 0s3 3 5 0 5-3 5 0-3 3-5 0"/></svg>',
    percent: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="7.5" cy="7.5" r="3.5"/><circle cx="16.5" cy="16.5" r="3.5"/><path d="M19 5 5 19"/></svg>',
    traffic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m8 11 4 4 4-4"/><path d="M4 21h16"/></svg>',
    star: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    target: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    spark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5z"/><path d="M19 15l.8 2.8L22 18.5l-2.2.7L19 22l-.8-2.8L16 18.5l2.2-.7z"/></svg>'
  };

  function icon(name, cls) {
    return '<span class="satka-wheel-icon ' + (cls || '') + '" aria-hidden="true">' + (ICONS[name] || ICONS.star) + '</span>';
  }

  function segIconName(seg) {
    if (!seg) return 'star';
    var type = String(seg.prize_type || seg.type || '').toLowerCase();
    var title = String(seg.title || seg.short || '').toLowerCase();
    if (type.indexOf('balance') >= 0 || title.indexOf('₽') >= 0 || title.indexOf('руб') >= 0) return 'balance';
    if (type.indexOf('day') >= 0 || title.indexOf('дн') >= 0 || title.indexOf('day') >= 0) return 'days';
    if (type.indexOf('gift') >= 0 || type.indexOf('promo') >= 0) return 'gift';
    if (type.indexOf('percent') >= 0 || type.indexOf('discount') >= 0 || title.indexOf('%') >= 0) return 'percent';
    if (type.indexOf('traffic') >= 0 || title.indexOf('gb') >= 0) return 'traffic';
    return 'star';
  }

  function isReferralPath() {
    return /\/referral/i.test(window.location.pathname);
  }

  function isTelegramMiniApp() {
    var tg = window.Telegram && window.Telegram.WebApp;
    return !!(tg && tg.initData) || document.documentElement.classList.contains('satka-in-telegram');
  }

  function easeOutQuart(t) {
    return 1 - Math.pow(1 - t, 4);
  }

  function applyRotorDeg(rotor, deg) {
    rotor.style.transform = 'rotate(' + deg + 'deg)';
  }

  function animateRotationJs(rotor, fromDeg, toDeg, duration) {
    return new Promise(function (resolve) {
      var startTs = null;
      rotor.style.transition = 'none';
      applyRotorDeg(rotor, fromDeg);
      function frame(ts) {
        if (startTs === null) startTs = ts;
        var p = Math.min(1, (ts - startTs) / duration);
        var deg = fromDeg + (toDeg - fromDeg) * easeOutQuart(p);
        applyRotorDeg(rotor, deg);
        if (p < 1) requestAnimationFrame(frame);
        else resolve();
      }
      requestAnimationFrame(frame);
    });
  }

  function api(path, options) {
    var apiMod = window.SatkaCabinetApi;
    if (!apiMod || !apiMod.apiFetch) {
      return Promise.reject(new Error('API module not loaded'));
    }
    return apiMod.apiFetch(API_BASE + (path || ''), {
      method: (options && options.method) || 'GET',
      body: options && options.body ? JSON.stringify(options.body) : undefined,
    });
  }

  function shortLabel(seg) {
    var label = (seg.short || seg.title || '').trim();
    if (label.length <= 8) return label;
    return label.slice(0, 7) + '…';
  }

  function labelFontSize(label, n) {
    var len = label.length;
    if (n > 10) return len > 7 ? 9 : 10;
    if (n > 8) return len > 7 ? 9.5 : 10.5;
    return len > 7 ? 10 : 11.5;
  }

  function polar(cx, cy, r, deg) {
    var rad = (deg * Math.PI) / 180;
    return { x: cx + Math.cos(rad) * r, y: cy + Math.sin(rad) * r };
  }

  function segIconSvg(seg, dark) {
    var color = dark ? '#ffffff' : '#0a0a0a';
    var raw = ICONS[segIconName(seg)];
    return raw.replace(/currentColor/g, color);
  }

  function buildSvgWheel(segments) {
    var n = Math.max(segments.length, 1);
    var size = 420;
    var cx = size / 2;
    var cy = size / 2;
    var outer = size * 0.48;
    var inner = size * 0.14;
    var step = 360 / n;
    var start = -90;
    var parts = [];
    var labels = [];

    for (var i = 0; i < n; i++) {
      var a0 = start + i * step;
      var a1 = start + (i + 1) * step;
      var p0 = polar(cx, cy, outer, a0);
      var p1 = polar(cx, cy, outer, a1);
      var large = step > 180 ? 1 : 0;
      var dark = i % 2 === 0;
      var fill = dark ? '#111111' : '#f7f7f7';
      var stroke = dark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)';
      var d =
        'M ' + cx + ' ' + cy +
        ' L ' + p0.x + ' ' + p0.y +
        ' A ' + outer + ' ' + outer + ' 0 ' + large + ' 1 ' + p1.x + ' ' + p1.y + ' Z';
      parts.push(
        '<path class="satka-wheel-seg" data-seg-index="' + i + '" d="' + d +
        '" fill="' + fill + '" stroke="' + stroke + '" stroke-width="1.2"/>'
      );

      var mid = a0 + step / 2;
      var iconPos = polar(cx, cy, outer * 0.58, mid);
      var labelPos = polar(cx, cy, outer * 0.8, mid);
      var label = shortLabel(segments[i]);
      var fs = labelFontSize(label, n);
      var pillBg = dark ? '#ffffff' : '#111111';
      var pillText = dark ? '#111111' : '#ffffff';
      var iconColor = dark ? '#ffffff' : '#111111';
      var pillW = Math.min(Math.max(label.length * 6.2 + 10, 28), 56);
      var pillH = 15;
      var icInner = segIconSvg(segments[i], dark)
        .replace(/currentColor/g, iconColor)
        .replace(/<svg[^>]*>/, '')
        .replace(/<\/svg>/, '');

      labels.push(
        '<g class="satka-wheel-seg-content" transform="rotate(' + (mid + 90) + ' ' + labelPos.x + ' ' + labelPos.y + ')">' +
        '<g class="satka-wheel-seg-icon" transform="translate(' + (iconPos.x - 13) + ',' + (iconPos.y - 28) + ') scale(1.15)">' + icInner + '</g>' +
        '<rect class="satka-wheel-seg-pill" x="' + (labelPos.x - pillW / 2) + '" y="' + (labelPos.y - 4) +
        '" width="' + pillW + '" height="' + pillH + '" rx="5" fill="' + pillBg + '" opacity="0.96"/>' +
        '<text class="satka-wheel-seg-label" x="' + labelPos.x + '" y="' + (labelPos.y + 7) +
        '" text-anchor="middle" fill="' + pillText + '" font-size="' + fs +
        '" font-weight="800" font-family="Inter,system-ui,sans-serif">' +
        escapeXml(label) + '</text></g>'
      );
    }

    return (
      '<svg class="satka-wheel-svg" viewBox="0 0 ' + size + ' ' + size + '" role="img" aria-label="' + t('wheel.heading') + '">' +
      '<defs><filter id="satkaWheelGlow"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + (outer + 3) +
      '" fill="none" class="satka-wheel-outer-ring" stroke="rgba(255,255,255,0.2)" stroke-width="2.5"/>' +
      parts.join('') +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + inner + '" fill="var(--satka-wheel-hub, #0a0a0a)" stroke="rgba(255,255,255,0.5)" stroke-width="2.5"/>' +
      labels.join('') + '</svg>'
    );
  }

  function escapeXml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function buildBlock() {
    var wrap = document.createElement('div');
    wrap.className = 'satka-cabinet-wheel-block';
    wrap.dataset.satkaWheel = '1';
    wrap.innerHTML =
      '<h3>' + icon('spark', 'satka-wheel-title-icon') + '<span>' + t('wheel.heading') + '</span></h3>' +
      '<p class="satka-cabinet-wheel-lead">' + t('wheel.lead') + '</p>' +
      '<div class="satka-cabinet-wheel-stats" data-wheel-stats></div>' +
      '<div class="satka-cabinet-wheel-stage">' +
      '<div class="satka-cabinet-wheel-glow"></div>' +
      '<div class="satka-cabinet-wheel-pointer" aria-hidden="true"></div>' +
      '<div class="satka-cabinet-wheel-rotor">' +
      '<div class="satka-cabinet-wheel-disc"></div>' +
      '</div>' +
      '<div class="satka-cabinet-wheel-hub"><img src="/logo.svg" alt="" /></div>' +
      '</div>' +
      '<div class="satka-cabinet-wheel-legend" data-wheel-legend></div>' +
      '<div class="satka-cabinet-wheel-actions">' +
      '<button type="button" class="satka-cabinet-wheel-btn" data-cabinet-wheel-spin disabled>' +
      '<span class="satka-wheel-btn-shine"></span>' +
      '<span data-wheel-btn-text>' + t('wheel.spinBtn') + '</span></button>' +
      '</div>' +
      '<p class="satka-cabinet-wheel-result" aria-live="polite"></p>';

    wrap.querySelector('[data-cabinet-wheel-spin]').addEventListener('click', onSpin);
    return wrap;
  }

  function renderLegend(wrap, segments) {
    var el = wrap.querySelector('[data-wheel-legend]');
    if (!el) return;
    el.innerHTML = segments
      .map(function (s, i) {
        return (
          '<span class="satka-wheel-legend-item" data-leg="' + i + '">' +
          icon(segIconName(s), 'satka-wheel-legend-icon') +
          '<span class="satka-wheel-legend-text">' + escapeXml(s.title || s.short || '') + '</span></span>'
        );
      })
      .join('');
  }

  function renderStats(wrap) {
    var el = wrap.querySelector('[data-wheel-stats]');
    if (!el || !state) return;
    el.innerHTML =
      '<span class="satka-wheel-stat" title="' + t('wheel.invited') + '">' +
      icon('users') + '<span>' + state.invited + '</span></span>' +
      '<span class="satka-wheel-stat" title="' + t('wheel.used') + '">' +
      icon('target') + '<span>' + state.used + '</span></span>' +
      '<span class="satka-wheel-stat satka-wheel-stat-hot" title="' + t('wheel.available') + '">' +
      icon('spark') + '<span>' + state.available + ' ' + t('wheel.spinsUnit') + '</span></span>';
    updateSpinButton(wrap);
  }

  function updateSpinButton(wrap) {
    var btn = wrap.querySelector('[data-cabinet-wheel-spin]');
    var text = wrap.querySelector('[data-wheel-btn-text]');
    if (!btn) return;
    var avail = state && state.available > 0;
    btn.disabled = spinning || !avail;
    btn.classList.toggle('is-ready', avail && !spinning);
    if (text) {
      if (spinning) text.textContent = t('wheel.spinning');
      else if (avail) text.textContent = t('wheel.spin', { n: state.available });
      else text.textContent = t('wheel.invite');
    }
  }

  function applyWheel(wrap, segments) {
    segmentsCache = segments.length ? segments : [{ id: 'x', title: t('wheel.prize'), short: t('wheel.prize') }];
    var disc = wrap.querySelector('.satka-cabinet-wheel-disc');
    if (!disc) return;
    disc.innerHTML = buildSvgWheel(segmentsCache);
    disc.classList.add('satka-wheel-disc-live');
    renderLegend(wrap, segmentsCache);
  }

  function highlightWinner(wrap, index) {
    wrap.querySelectorAll('.satka-wheel-seg').forEach(function (path) {
      var i = parseInt(path.getAttribute('data-seg-index'), 10);
      path.classList.toggle('is-winner', i === index);
    });
    wrap.querySelectorAll('.satka-wheel-legend-item').forEach(function (el) {
      var i = parseInt(el.getAttribute('data-leg'), 10);
      el.classList.toggle('is-winner', i === index);
    });
  }

  function spinTo(wrap, data) {
    var rotor = wrap.querySelector('.satka-cabinet-wheel-rotor');
    if (!rotor) return Promise.resolve();

    var n = segmentsCache.length || 8;
    var idx = typeof data.segment_index === 'number' ? data.segment_index : 0;
    var step = 360 / n;
    var extra = data.rotation_degrees || 360 * 6 + idx * step;
    if (extra < 360 * 4) {
      extra = 360 * 5 + (n - idx) * step + step / 2;
    }
    var fromDeg = rotation;
    rotation += extra;
    var toDeg = rotation;

    var useJsAnim =
      isTelegramMiniApp() ||
      document.documentElement.classList.contains('satka-low-perf') ||
      document.documentElement.classList.contains('satka-mobile');

    function done() {
      highlightWinner(wrap, idx);
    }

    if (useJsAnim) {
      return animateRotationJs(rotor, fromDeg, toDeg, SPIN_MS).then(done);
    }

    rotor.style.transition = 'transform 4.8s cubic-bezier(0.2, 0.85, 0.22, 1)';
    applyRotorDeg(rotor, fromDeg);
    void rotor.offsetWidth;
    applyRotorDeg(rotor, toDeg);

    return new Promise(function (resolve) {
      var finished = false;
      function finish() {
        if (finished) return;
        finished = true;
        rotor.removeEventListener('transitionend', onEnd);
        clearTimeout(fallback);
        done();
        resolve();
      }
      function onEnd(e) {
        if (e.target === rotor && e.propertyName === 'transform') finish();
      }
      rotor.addEventListener('transitionend', onEnd);
      var fallback = setTimeout(finish, SPIN_MS + 200);
    });
  }

  function finishSpin(wrap, data) {
    var resEl = wrap.querySelector('.satka-cabinet-wheel-result');
    var iconName = segIconName(data);
    var msg =
      (data.title || t('wheel.prize')) +
      (data.detail ? ' — ' + data.detail : '');
    if (resEl) {
      resEl.innerHTML =
        '<span class="satka-wheel-win-banner">' +
        icon(iconName, 'satka-wheel-win-icon') +
        '<span>' + escapeXml(msg) + '</span></span>';
    }
    return api().then(function (fresh) {
      if (fresh) {
        state = fresh;
        renderStats(wrap);
      }
      spinning = false;
      wrap.classList.remove('satka-wheel-spinning');
      updateSpinButton(wrap);
    });
  }

  function onSpin() {
    if (spinning || !state || state.available <= 0) return;
    var wrap = document.querySelector('[data-satka-wheel]');
    if (!wrap) return;
    var resEl = wrap.querySelector('.satka-cabinet-wheel-result');
    spinning = true;
    updateSpinButton(wrap);
    if (resEl) resEl.textContent = '';
    wrap.classList.add('satka-wheel-spinning');
    wrap.querySelectorAll('.satka-wheel-seg').forEach(function (p) {
      p.classList.remove('is-winner');
    });

    api('/spin', { method: 'POST' })
      .then(function (data) {
        return spinTo(wrap, data).then(function () {
          return data;
        });
      })
      .then(function (data) {
        return finishSpin(wrap, data);
      })
      .catch(function (err) {
        spinning = false;
        wrap.classList.remove('satka-wheel-spinning');
        updateSpinButton(wrap);
        if (resEl) {
          if (err.status === 401) {
            resEl.textContent = t('wheel.sessionExpired');
          } else if (err.message === 'no_spins' || /прокрут/i.test(String(err.message))) {
            resEl.textContent = t('wheel.noSpins');
          } else {
            resEl.textContent = err.message || t('wheel.spinFail');
          }
        }
      });
  }

  function loadState(wrap) {
    return api()
      .then(function (data) {
        state = data;
        applyWheel(wrap, data.segments || []);
        renderStats(wrap);
      })
      .catch(function (err) {
        var resEl = wrap.querySelector('.satka-cabinet-wheel-result');
        if (resEl) {
          if (err.status === 401) {
            resEl.textContent = t('wheel.loginRequired');
          } else {
            resEl.textContent = err.message || t('wheel.loadFail');
          }
        }
      });
  }

  function tryInject() {
    if (!isReferralPath()) {
      injected = false;
      document.querySelectorAll('[data-satka-wheel]').forEach(function (el) {
        el.remove();
      });
      return;
    }
    if (injected || document.querySelector('[data-satka-wheel]')) return;

    var root = document.getElementById('root');
    if (!root) return;
    var main = root.querySelector('main') || root.querySelector('[role="main"]') || root.firstElementChild;
    if (!main || !main.children.length) return;

    var block = buildBlock();
    if (main.firstChild) main.insertBefore(block, main.firstChild);
    else main.appendChild(block);
    injected = true;
    loadState(block);
    if (isTelegramMiniApp()) {
      setTimeout(function () {
        try {
          block.scrollIntoView({ block: 'center', behavior: 'smooth' });
        } catch (e) {
          block.scrollIntoView(true);
        }
      }, 400);
    }
  }

  function tick() {
    tryInject();
  }

  tick();
  window.addEventListener('popstate', tick);
  setInterval(tick, 600);
  window.addEventListener('satka-language-changed', function () {
    injected = false;
    document.querySelectorAll('[data-satka-wheel]').forEach(function (el) {
      el.remove();
    });
    tick();
  });
  if (window.SatkaI18n) {
    window.SatkaI18n.onChange(function () {
      injected = false;
      document.querySelectorAll('[data-satka-wheel]').forEach(function (el) {
        el.remove();
      });
      tick();
    });
  }

  var root = document.getElementById('root');
  if (root && 'MutationObserver' in window) {
    new MutationObserver(tick).observe(root, { childList: true, subtree: true });
  }
})();

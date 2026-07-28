(function () {
  'use strict';

  function t(key, params) {
    return window.SatkaI18n ? window.SatkaI18n.t(key, params) : key;
  }

  var API_BASE = '/api/cabinet/satka/referral-wheel';
  var SPIN_MS = 5200;
  var rotation = 0;
  var spinning = false;
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

  function easeOutQuint(t) {
    return 1 - Math.pow(1 - t, 5);
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
        applyRotorDeg(rotor, fromDeg + (toDeg - fromDeg) * easeOutQuint(p));
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

  function compactLabel(seg) {
    var text = (seg.short || seg.title || '').trim();
    var m;
    m = text.match(/(\+\s*)?(\d+)\s*₽/);
    if (m) return (m[1] ? '+' : '') + m[2] + '₽';
    m = text.match(/(\d+)\s*%/);
    if (m) return m[1] + '%';
    m = text.match(/(\d+)\s*(дн|д\.|day)/i);
    if (m) return m[1] + 'д';
    m = text.match(/(\d+)\s*gb/i);
    if (m) return m[1] + ' GB';
    if (/скидк/i.test(text)) return 'Скидка';
    if (/баланс|рубл/i.test(text)) return 'Баланс';
    if (/подписк/i.test(text)) return 'Дни';
    if (text.length <= 8) return text;
    return text.split(/\s+/)[0].slice(0, 7);
  }

  function iconPaths(name) {
    var s = ' stroke="currentColor" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"';
    var map = {
      balance: '<circle cx="12" cy="12" r="9"' + s + '/><path d="M12 7v10M9 10h4.5a2 2 0 1 0 0-4H10a2 2 0 0 0 0 4h4.5a2 2 0 1 1 0 4H9"' + s + '/>',
      days: '<rect x="3" y="5" width="18" height="16" rx="2"' + s + '/><path d="M8 3v4M16 3v4M3 10h18"' + s + '/>',
      gift: '<rect x="3" y="8" width="18" height="13" rx="1"' + s + '/><path d="M12 8v13M3 12h18"' + s + '/>',
      percent: '<circle cx="7.5" cy="7.5" r="3.5"' + s + '/><circle cx="16.5" cy="16.5" r="3.5"' + s + '/><path d="M19 5 5 19"' + s + '/>',
      traffic: '<path d="M12 3v12M8 11l4 4 4-4M4 21h16"' + s + '/>',
      star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"' + s + '/>',
    };
    return map[name] || map.star;
  }

  function labelFontSize(label, n) {
    if (n > 10) return label.length > 5 ? 9 : 10;
    if (n > 8) return label.length > 5 ? 9.5 : 11;
    return label.length > 6 ? 10 : 12;
  }

  function polar(cx, cy, r, deg) {
    var rad = (deg * Math.PI) / 180;
    return { x: cx + Math.cos(rad) * r, y: cy + Math.sin(rad) * r };
  }

  function resolveSegmentIndex(data) {
    if (typeof data.segment_index === 'number' && data.segment_index >= 0) {
      return Math.min(data.segment_index, segmentsCache.length - 1);
    }
    var prize = data.prize || data;
    var id = data.id || data.prize_id || prize.id;
    if (id != null) {
      for (var i = 0; i < segmentsCache.length; i++) {
        if (String(segmentsCache[i].id) === String(id)) return i;
      }
    }
    var title = String(data.title || data.short || prize.title || prize.short || '');
    if (title) {
      for (var j = 0; j < segmentsCache.length; j++) {
        var seg = segmentsCache[j];
        if (seg.title === title || seg.short === title) return j;
        if (title && (String(seg.title || '').indexOf(title) >= 0 || title.indexOf(String(seg.title || '')) >= 0)) {
          return j;
        }
      }
    }
    return 0;
  }

  function calcSpinDelta(idx, n, currentRotation) {
    var step = 360 / n;
    var mid = -90 + idx * step + step / 2;
    var targetMod = ((-90 - mid) % 360 + 360) % 360;
    var currentMod = ((currentRotation % 360) + 360) % 360;
    var delta = (targetMod - currentMod + 360) % 360;
    if (delta < 45) delta += 360;
    var fullSpins = 5 + Math.floor(Math.random() * 2);
    return fullSpins * 360 + delta;
  }

  function buildSvgWheel(segments) {
    var n = Math.max(segments.length, 1);
    var size = 440;
    var cx = size / 2;
    var cy = size / 2;
    var outer = size * 0.445;
    var inner = size * 0.155;
    var rimOuter = outer + 10;
    var step = 360 / n;
    var start = -90;
    var parts = [];
    var labels = [];
    var dividers = [];
    var teeth = [];

    for (var i = 0; i < n; i++) {
      var a0 = start + i * step;
      var a1 = start + (i + 1) * step;
      var p0 = polar(cx, cy, outer, a0);
      var p1 = polar(cx, cy, outer, a1);
      var pi0 = polar(cx, cy, inner, a0);
      var pi1 = polar(cx, cy, inner, a1);
      var large = step > 180 ? 1 : 0;
      var dark = i % 2 === 0;
      var fill = dark ? 'var(--satka-wheel-seg-a, #111)' : 'var(--satka-wheel-seg-b, #f4f4f4)';
      var d =
        'M ' + pi0.x + ' ' + pi0.y +
        ' L ' + p0.x + ' ' + p0.y +
        ' A ' + outer + ' ' + outer + ' 0 ' + large + ' 1 ' + p1.x + ' ' + p1.y +
        ' L ' + pi1.x + ' ' + pi1.y +
        ' A ' + inner + ' ' + inner + ' 0 ' + large + ' 0 ' + pi0.x + ' ' + pi0.y + ' Z';
      parts.push(
        '<path class="satka-wheel-seg" data-seg-index="' + i + '" d="' + d +
        '" fill="' + fill + '" stroke="var(--satka-wheel-divider, rgba(255,255,255,0.12))" stroke-width="0.8"/>'
      );

      var divEnd = polar(cx, cy, outer, a1);
      dividers.push(
        '<line x1="' + cx + '" y1="' + cy + '" x2="' + divEnd.x + '" y2="' + divEnd.y +
        '" stroke="var(--satka-wheel-divider, rgba(255,255,255,0.15))" stroke-width="1"/>'
      );

      var toothA = a1;
      var t0 = polar(cx, cy, outer - 1, toothA - step * 0.08);
      var t1 = polar(cx, cy, rimOuter + 2, toothA);
      var t2 = polar(cx, cy, outer - 1, toothA + step * 0.08);
      teeth.push('<polygon points="' + t0.x + ',' + t0.y + ' ' + t1.x + ',' + t1.y + ' ' + t2.x + ',' + t2.y +
        '" fill="var(--satka-wheel-rim, #fff)" opacity="0.9"/>');

      var mid = a0 + step / 2;
      var lp = polar(cx, cy, (outer + inner) / 2 + 10, mid);
      var label = compactLabel(segments[i]);
      var fs = labelFontSize(label, n);
      var tone = dark ? 'dark' : 'light';
      var rot = mid + 90;

      labels.push(
        '<g class="satka-wheel-seg-content satka-wheel-tone-' + tone + '" transform="translate(' + lp.x.toFixed(2) + ',' + lp.y.toFixed(2) + ') rotate(' + rot.toFixed(2) + ')">' +
        '<g class="satka-wheel-seg-icon-wrap" transform="translate(-12,-22)"><svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">' +
        iconPaths(segIconName(segments[i])) +
        '</svg></g>' +
        '<text class="satka-wheel-seg-label" x="0" y="10" text-anchor="middle" fill="currentColor" font-size="' + fs +
        '" font-weight="800" font-family="Inter,system-ui,sans-serif" paint-order="stroke" stroke="rgba(0,0,0,0.35)" stroke-width="0.6">' +
        escapeXml(label) + '</text></g>'
      );
    }

    return (
      '<svg class="satka-wheel-svg" viewBox="0 0 ' + size + ' ' + size + '" role="img" aria-label="' + t('wheel.heading') + '">' +
      '<defs>' +
      '<filter id="satkaWheelGlow"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' +
      '<radialGradient id="satkaWheelShine" cx="40%" cy="35%" r="65%">' +
      '<stop offset="0%" stop-color="rgba(255,255,255,0.14)"/><stop offset="100%" stop-color="rgba(255,255,255,0)"/>' +
      '</radialGradient></defs>' +
      '<circle class="satka-wheel-rim-bg" cx="' + cx + '" cy="' + cy + '" r="' + (rimOuter + 4) +
      '" fill="none" stroke="var(--satka-wheel-rim, #fff)" stroke-width="5" opacity="0.25"/>' +
      teeth.join('') +
      parts.join('') +
      dividers.join('') +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + outer + '" fill="url(#satkaWheelShine)" pointer-events="none"/>' +
      labels.join('') +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + (inner + 2) +
      '" fill="none" stroke="var(--satka-wheel-rim, #fff)" stroke-width="2.5" opacity="0.5"/>' +
      '</svg>'
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
      '<div class="satka-wheel-lights" aria-hidden="true"></div>' +
      '<h3>' + icon('spark', 'satka-wheel-title-icon') + '<span>' + t('wheel.heading') + '</span></h3>' +
      '<p class="satka-cabinet-wheel-lead">' + t('wheel.lead') + '</p>' +
      '<div class="satka-cabinet-wheel-stats" data-wheel-stats></div>' +
      '<div class="satka-cabinet-wheel-frame">' +
      '<div class="satka-cabinet-wheel-stage">' +
      '<div class="satka-cabinet-wheel-pointer" aria-hidden="true"></div>' +
      '<div class="satka-cabinet-wheel-rotor">' +
      '<div class="satka-cabinet-wheel-disc"></div>' +
      '</div>' +
      '<div class="satka-cabinet-wheel-hub"><img src="/logo.svg" alt="" /></div>' +
      '</div></div>' +
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

  function launchConfetti(wrap) {
    var stage = wrap.querySelector('.satka-cabinet-wheel-stage');
    if (!stage) return;
    var old = stage.querySelector('.satka-wheel-confetti');
    if (old) old.remove();
    var box = document.createElement('div');
    box.className = 'satka-wheel-confetti';
    box.setAttribute('aria-hidden', 'true');
    for (var i = 0; i < 18; i++) {
      var p = document.createElement('span');
      p.style.setProperty('--satka-confetti-i', String(i));
      box.appendChild(p);
    }
    stage.appendChild(box);
    setTimeout(function () { if (box.parentNode) box.remove(); }, 2200);
  }

  function spinTo(wrap, data) {
    var rotor = wrap.querySelector('.satka-cabinet-wheel-rotor');
    if (!rotor) return Promise.resolve();

    var n = segmentsCache.length || 8;
    var idx = resolveSegmentIndex(data);
    var fromDeg = rotation;
    var extra = calcSpinDelta(idx, n, fromDeg);
    rotation = fromDeg + extra;
    var toDeg = rotation;
    var duration = SPIN_MS / 1000;
    var useJsAnim = isTelegramMiniApp() || document.documentElement.classList.contains('satka-mobile');

    function done() {
      highlightWinner(wrap, idx);
      launchConfetti(wrap);
    }

    if (useJsAnim) {
      return animateRotationJs(rotor, fromDeg, toDeg, SPIN_MS).then(done);
    }

    rotor.style.transition = 'none';
    applyRotorDeg(rotor, fromDeg);
    void rotor.offsetWidth;
    rotor.style.transition = 'transform ' + duration + 's cubic-bezier(0.15, 0.85, 0.2, 1)';
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
      var fallback = setTimeout(finish, SPIN_MS + 350);
    });
  }

  function finishSpin(wrap, data) {
    var resEl = wrap.querySelector('.satka-cabinet-wheel-result');
    var iconName = segIconName(data);
    var msg = (data.title || t('wheel.prize')) + (data.detail ? ' — ' + data.detail : '');
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
      var existing = document.querySelector('[data-satka-wheel]');
      if (existing) existing.remove();
      document.documentElement.classList.remove('satka-on-referral');
      return;
    }
    document.documentElement.classList.add('satka-on-referral');
    if (document.querySelector('[data-satka-wheel]')) return;

    var root = document.getElementById('root');
    if (!root) return;
    var main = root.querySelector('main') || root.querySelector('[role="main"]') || root.firstElementChild;
    if (!main || !main.children.length) return;

    var block = buildBlock();
    if (main.firstChild) main.insertBefore(block, main.firstChild);
    else main.appendChild(block);
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

  function resetWheel() {
    var old = document.querySelector('[data-satka-wheel]');
    if (old) old.remove();
    tryInject();
  }

  function boot() {
    tryInject();
  }

  window.addEventListener('satka-language-changed', resetWheel);
  if (window.SatkaI18n) window.SatkaI18n.onChange(resetWheel);

  if (window.SatkaRoute) {
    window.SatkaRoute.onTick(boot);
    window.SatkaRoute.onChange(boot);
    window.SatkaRoute.whenReady(boot);
  } else {
    boot();
    window.addEventListener('popstate', boot);
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      boot();
      if (document.querySelector('[data-satka-wheel]') || tries > 60) clearInterval(timer);
    }, 400);
  }
})();

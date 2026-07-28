(function () {
  'use strict';

  function t(key) {
    return window.SatkaI18n ? window.SatkaI18n.t(key) : key;
  }

  function presets() {
    return [
      { title: t('support.preset.subscription'), message: t('support.preset.subscription.msg') },
      { title: t('support.preset.payment'), message: t('support.preset.payment.msg') },
      { title: t('support.preset.urgent'), message: t('support.preset.urgent.msg') },
      { title: t('support.preset.ping'), message: t('support.preset.ping.msg') },
      { title: t('support.preset.key'), message: t('support.preset.key.msg') },
      { title: t('support.preset.happ'), message: t('support.preset.happ.msg') },
      { title: t('support.preset.speed'), message: t('support.preset.speed.msg') },
      { title: t('support.preset.balance'), message: t('support.preset.balance.msg') },
    ];
  }

  function isSupportPath() {
    return /\/support/i.test(window.location.pathname);
  }

  function showToast(text, kind) {
    var el = document.querySelector('.satka-cabinet-toast');
    if (!el) {
      el = document.createElement('div');
      el.className = 'satka-cabinet-toast';
      el.setAttribute('role', 'status');
      document.body.appendChild(el);
    }
    el.className = 'satka-cabinet-toast' + (kind === 'error' ? ' is-error' : kind === 'ok' ? ' is-ok' : '');
    el.textContent = text;
    el.classList.add('is-visible');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(function () {
      el.classList.remove('is-visible');
    }, 5200);
  }

  function setInputValue(input, value) {
    if (!input) return;
    var proto = input.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    var setter = Object.getOwnPropertyDescriptor(proto, 'value');
    if (setter && setter.set) setter.set.call(input, value);
    else input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function findCreateForm() {
    var subject = document.getElementById('support-subject');
    var message = document.getElementById('support-message');
    if (subject && message) return { subject: subject, message: message };
    return null;
  }

  function removePresets() {
    document.querySelectorAll('[data-satka-presets]').forEach(function (el) {
      el.remove();
    });
  }

  function injectPresets() {
    var form = findCreateForm();
    if (!form) return;
    removePresets();
    var wrap = document.createElement('div');
    wrap.className = 'satka-ticket-presets';
    wrap.dataset.satkaPresets = '1';
    wrap.innerHTML =
      '<p class="satka-ticket-presets-label">' +
      t('support.presets.label') +
      '</p><div class="satka-ticket-presets-chips"></div>';
    var chips = wrap.querySelector('.satka-ticket-presets-chips');
    presets().forEach(function (p) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'satka-ticket-preset-chip';
      btn.textContent = p.title;
      btn.addEventListener('click', function () {
        setInputValue(form.subject, p.title);
        setInputValue(form.message, p.message);
        chips.querySelectorAll('.satka-ticket-preset-chip').forEach(function (c) {
          c.classList.toggle('is-active', c === btn);
        });
      });
      chips.appendChild(btn);
    });
    form.subject.closest('form').insertBefore(wrap, form.subject.parentElement);
  }

  function markSendButtons() {
    document.querySelectorAll('form button[type="submit"], button[type="submit"]').forEach(function (btn) {
      var txt = (btn.textContent || '').replace(/\s+/g, ' ').trim();
      if (/отправ/i.test(txt) || /send/i.test(txt)) btn.classList.add('satka-send-ticket-btn');
    });
  }

  function hookFetch() {
    if (window.__satkaTicketFetchHook) return;
    window.__satkaTicketFetchHook = true;
    var orig = window.fetch;
    window.fetch = function (input, init) {
      var url = typeof input === 'string' ? input : input && input.url;
      var isTicketCreate =
        url && /\/cabinet\/tickets\b/i.test(url) && (!init || (init.method || 'GET').toUpperCase() === 'POST');
      return orig.apply(this, arguments).then(function (res) {
        if (isTicketCreate && isSupportPath()) {
          if (res.ok) showToast(t('support.toast.created'), 'ok');
          else {
            res
              .clone()
              .json()
              .catch(function () {
                return {};
              })
              .then(function (body) {
                var msg = (body && (body.detail || body.message)) || t('support.toast.createFail');
                if (typeof msg !== 'string') msg = JSON.stringify(msg);
                showToast(msg, 'error');
              });
          }
        }
        return res;
      });
    };
  }

  function validateFormHint() {
    var form = findCreateForm();
    if (!form) return;
    var submit = form.subject.closest('form').querySelector('button[type="submit"]');
    if (!submit || submit.dataset.satkaValidate) return;
    submit.dataset.satkaValidate = '1';
    submit.addEventListener(
      'click',
      function () {
        var title = (form.subject.value || '').trim();
        var msg = (form.message.value || '').trim();
        if (title.length < 3) showToast(t('support.toast.subjectShort'), 'error');
        else if (msg.length < 10) showToast(t('support.toast.messageShort'), 'error');
      },
      true,
    );
  }

  function update() {
    var on = isSupportPath();
    document.documentElement.classList.toggle('satka-on-support', on);
    if (!on) return;
    injectPresets();
    markSendButtons();
    validateFormHint();
  }

  hookFetch();
  update();
  setInterval(update, 700);
  window.addEventListener('popstate', update);
  window.addEventListener('satka-language-changed', update);
  if (window.SatkaI18n) window.SatkaI18n.onChange(update);

  var root = document.getElementById('root');
  if (root && 'MutationObserver' in window) {
    new MutationObserver(update).observe(root, { childList: true, subtree: true });
  }
})();

(function () {
  'use strict';

  var API = '/api/cabinet/satka/admin/email-users';
  var ROUTE = '/admin/email-users';
  var state = {
    page: 1,
    pageSize: 25,
    search: '',
    verified: null,
    items: [],
    total: 0,
    pages: 1,
    stats: null,
    selected: {},
    loading: false,
  };

  function api(path, options) {
    var mod = window.SatkaCabinetApi;
    if (!mod || !mod.apiFetch) return Promise.reject(new Error('API недоступен'));
    return mod.apiFetch(API + (path || ''), {
      method: (options && options.method) || 'GET',
      body: options && options.body ? JSON.stringify(options.body) : undefined,
    });
  }

  function showToast(text, kind) {
    var el = document.querySelector('.satka-email-toast');
    if (!el) {
      el = document.createElement('div');
      el.className = 'satka-email-toast';
      document.body.appendChild(el);
    }
    el.className = 'satka-email-toast' + (kind === 'error' ? ' is-error' : kind === 'ok' ? ' is-ok' : '');
    el.textContent = text;
    el.classList.add('is-visible');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(function () {
      el.classList.remove('is-visible');
    }, 4500);
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return iso;
    }
  }

  function isEmailUsersRoute() {
    return window.location.pathname === ROUTE || window.location.pathname === ROUTE + '/';
  }

  function isAdminHub() {
    var p = window.location.pathname.replace(/\/$/, '');
    return p === '/admin';
  }

  function navigate(path) {
    window.history.pushState({}, '', path);
    onRoute();
  }

  function statusBadge(status) {
    if (status === 'blocked') return '<span class="satka-email-badge satka-email-badge-block">заблок.</span>';
    if (status === 'active') return '<span class="satka-email-badge satka-email-badge-ok">активен</span>';
    return '<span class="satka-email-badge satka-email-badge-warn">' + esc(status) + '</span>';
  }

  function loadStats() {
    return api('/stats').then(function (data) {
      state.stats = data;
      return data;
    });
  }

  function loadUsers() {
    state.loading = true;
    var q = '?page=' + state.page + '&page_size=' + state.pageSize;
    if (state.search) q += '&search=' + encodeURIComponent(state.search);
    if (state.verified !== null) q += '&verified=' + state.verified;
    return api(q)
      .then(function (data) {
        state.items = data.items || [];
        state.total = data.total || 0;
        state.pages = data.pages || 1;
        state.loading = false;
        return data;
      })
      .catch(function (err) {
        state.loading = false;
        throw err;
      });
  }

  function openModal(html) {
    closeModal();
    var backdrop = document.createElement('div');
    backdrop.className = 'satka-email-modal-backdrop';
    backdrop.dataset.satkaEmailModal = '1';
    backdrop.innerHTML = html;
    backdrop.addEventListener('click', function (e) {
      if (e.target === backdrop) closeModal();
    });
    document.body.appendChild(backdrop);
  }

  function closeModal() {
    document.querySelectorAll('[data-satka-email-modal]').forEach(function (el) {
      el.remove();
    });
  }

  function act(path, method, body) {
    return api(path, { method: method || 'POST', body: body }).then(function (res) {
      showToast(res.message || 'Готово', 'ok');
      return loadUsers().then(function () {
        renderPage();
      });
    }).catch(function (err) {
      showToast(err.message || 'Ошибка', 'error');
    });
  }

  function openPasswordModal(user) {
    openModal(
      '<div class="satka-email-modal">' +
        '<h2>Сменить пароль</h2>' +
        '<p style="opacity:0.7;font-size:0.85rem;margin:0 0 12px">' + esc(user.email) + '</p>' +
        '<label>Новый пароль (мин. 8 символов)</label>' +
        '<input type="password" id="satka-email-pwd" autocomplete="new-password" />' +
        '<div class="satka-email-modal-actions">' +
        '<button type="button" class="satka-email-btn" data-close>Отмена</button>' +
        '<button type="button" class="satka-email-btn satka-email-btn-primary" data-save-pwd data-id="' + user.id + '">Сохранить</button>' +
        '</div></div>'
    );
    bindModalActions();
  }

  function openEmailModal(user) {
    openModal(
      '<div class="satka-email-modal">' +
        '<h2>Отправить письмо</h2>' +
        '<p style="opacity:0.7;font-size:0.85rem;margin:0 0 12px">' + esc(user.email) + '</p>' +
        '<label>Тема</label><input type="text" id="satka-email-subj" />' +
        '<label>Текст (HTML)</label><textarea id="satka-email-body"></textarea>' +
        '<div class="satka-email-modal-actions">' +
        '<button type="button" class="satka-email-btn" data-close>Отмена</button>' +
        '<button type="button" class="satka-email-btn satka-email-btn-primary" data-send-email data-id="' + user.id + '">Отправить</button>' +
        '</div></div>'
    );
    bindModalActions();
  }

  function openBroadcastModal() {
    var ids = Object.keys(state.selected).filter(function (k) {
      return state.selected[k];
    });
    openModal(
      '<div class="satka-email-modal">' +
        '<h2>Рассылка на почту</h2>' +
        '<p style="opacity:0.7;font-size:0.85rem;margin:0 0 12px">' +
        (ids.length ? 'Выбрано: ' + ids.length : 'Всем подтверждённым email-пользователям') +
        '</p>' +
        '<label>Тема</label><input type="text" id="satka-email-subj" />' +
        '<label>Текст (HTML)</label><textarea id="satka-email-body"></textarea>' +
        '<label><input type="checkbox" id="satka-email-only-verified" checked /> Только с подтверждённым email</label>' +
        '<div class="satka-email-modal-actions">' +
        '<button type="button" class="satka-email-btn" data-close>Отмена</button>' +
        '<button type="button" class="satka-email-btn satka-email-btn-primary" data-broadcast>Отправить рассылку</button>' +
        '</div></div>'
    );
    bindModalActions();
  }

  function bindModalActions() {
    var backdrop = document.querySelector('[data-satka-email-modal]');
    if (!backdrop) return;

    backdrop.querySelector('[data-close]')?.addEventListener('click', closeModal);

    backdrop.querySelector('[data-save-pwd]')?.addEventListener('click', function () {
      var id = this.getAttribute('data-id');
      var pwd = document.getElementById('satka-email-pwd')?.value || '';
      if (pwd.length < 8) {
        showToast('Пароль минимум 8 символов', 'error');
        return;
      }
      closeModal();
      act('/' + id + '/set-password', 'POST', { password: pwd });
    });

    backdrop.querySelector('[data-send-email]')?.addEventListener('click', function () {
      var id = this.getAttribute('data-id');
      var subject = document.getElementById('satka-email-subj')?.value || '';
      var body = document.getElementById('satka-email-body')?.value || '';
      if (!subject || !body) {
        showToast('Заполните тему и текст', 'error');
        return;
      }
      closeModal();
      act('/' + id + '/send-email', 'POST', { subject: subject, body_html: body });
    });

    backdrop.querySelector('[data-broadcast]')?.addEventListener('click', function () {
      var subject = document.getElementById('satka-email-subj')?.value || '';
      var body = document.getElementById('satka-email-body')?.value || '';
      var onlyVerified = document.getElementById('satka-email-only-verified')?.checked !== false;
      var ids = Object.keys(state.selected).filter(function (k) {
        return state.selected[k];
      }).map(Number);
      if (!subject || !body) {
        showToast('Заполните тему и текст', 'error');
        return;
      }
      closeModal();
      api('/broadcast', {
        method: 'POST',
        body: { subject: subject, body_html: body, user_ids: ids.length ? ids : null, only_verified: onlyVerified },
      })
        .then(function (res) {
          showToast('Отправлено: ' + res.sent + ', ошибок: ' + res.failed, 'ok');
        })
        .catch(function (err) {
          showToast(err.message || 'Ошибка рассылки', 'error');
        });
    });
  }

  function renderStats() {
    var s = state.stats;
    if (!s) return '<div class="satka-email-loading">Загрузка статистики…</div>';
    return (
      '<div class="satka-email-stats">' +
      statCard(s.total, 'Всего почтовиков') +
      statCard(s.verified, 'Подтверждённых') +
      statCard(s.unverified, 'Без подтверждения') +
      statCard(s.with_active_subscription, 'С подпиской') +
      statCard(s.registered_today, 'Сегодня') +
      statCard(s.registered_week, 'За неделю') +
      '</div>'
    );
  }

  function statCard(val, label) {
    return (
      '<div class="satka-email-stat"><div class="satka-email-stat-value">' +
      esc(val) +
      '</div><div class="satka-email-stat-label">' +
      esc(label) +
      '</div></div>'
    );
  }

  function renderTable() {
    if (state.loading) return '<div class="satka-email-loading">Загрузка…</div>';
    if (!state.items.length) return '<div class="satka-email-loading">Пользователи не найдены</div>';

    var rows = state.items
      .map(function (u) {
        var verified = u.email_verified
          ? '<span class="satka-email-badge satka-email-badge-ok">да</span>'
          : '<span class="satka-email-badge satka-email-badge-warn">нет</span>';
        var checked = state.selected[u.id] ? ' checked' : '';
        return (
          '<tr data-user-id="' +
          u.id +
          '">' +
          '<td><input type="checkbox" data-select="' +
          u.id +
          '"' +
          checked +
          ' /></td>' +
          '<td>' +
          esc(u.email) +
          '</td>' +
          '<td>' +
          verified +
          '</td>' +
          '<td>' +
          statusBadge(u.status) +
          '</td>' +
          '<td>' +
          (u.balance_rubles != null ? u.balance_rubles.toFixed(0) + ' ₽' : '—') +
          '</td>' +
          '<td>' +
          (u.has_subscription ? esc(u.subscription_status || 'да') : '—') +
          '</td>' +
          '<td>' +
          fmtDate(u.created_at) +
          '</td>' +
          '<td><div class="satka-email-row-actions">' +
          '<button type="button" data-act="pwd" data-id="' +
          u.id +
          '">Пароль</button>' +
          '<button type="button" data-act="mail" data-id="' +
          u.id +
          '">Письмо</button>' +
          (u.email_verified
            ? ''
            : '<button type="button" data-act="verify" data-id="' + u.id + '">Подтв.</button>') +
          (u.email_verified
            ? ''
            : '<button type="button" data-act="resend" data-id="' + u.id + '">Повтор</button>') +
          (u.status === 'blocked'
            ? '<button type="button" data-act="unblock" data-id="' + u.id + '">Разблок.</button>'
            : '<button type="button" data-act="block" data-id="' + u.id + '">Блок</button>') +
          '</div></td></tr>'
        );
      })
      .join('');

    return (
      '<div class="satka-email-table-wrap"><table class="satka-email-table">' +
      '<thead><tr><th></th><th>Email</th><th>Подтв.</th><th>Статус</th><th>Баланс</th><th>Подписка</th><th>Регистрация</th><th>Действия</th></tr></thead>' +
      '<tbody>' +
      rows +
      '</tbody></table></div>' +
      '<div class="satka-email-pagination">' +
      '<button type="button" class="satka-email-btn" data-page="prev"' +
      (state.page <= 1 ? ' disabled' : '') +
      '>← Назад</button>' +
      '<span>Стр. ' +
      state.page +
      ' / ' +
      state.pages +
      ' (' +
      state.total +
      ')</span>' +
      '<button type="button" class="satka-email-btn" data-page="next"' +
      (state.page >= state.pages ? ' disabled' : '') +
      '>Вперёд →</button></div>'
    );
  }

  function renderPage() {
    var root = document.getElementById('satka-email-admin-root');
    if (!root) return;
    root.innerHTML =
      '<div class="satka-email-admin">' +
      '<header class="satka-email-admin-header">' +
      '<button type="button" class="satka-email-admin-back" data-back-admin">← Админка</button>' +
      '<h1>📧 Почтовики</h1>' +
      '</header>' +
      '<div class="satka-email-admin-body">' +
      renderStats() +
      '<div class="satka-email-toolbar">' +
      '<input class="satka-email-search" type="search" placeholder="Поиск по email…" value="' +
      esc(state.search) +
      '" data-search />' +
      '<select class="satka-email-filter" data-filter-verified>' +
      '<option value="">Все</option>' +
      '<option value="true"' +
      (state.verified === true ? ' selected' : '') +
      '>Подтверждённые</option>' +
      '<option value="false"' +
      (state.verified === false ? ' selected' : '') +
      '>Без подтверждения</option>' +
      '</select>' +
      '<button type="button" class="satka-email-btn satka-email-btn-primary" data-broadcast-open>📨 Рассылка</button>' +
      '<button type="button" class="satka-email-btn" data-refresh>↻ Обновить</button>' +
      '</div>' +
      renderTable() +
      '</div></div>';

    bindPageEvents(root);
  }

  function bindPageEvents(root) {
    root.querySelector('[data-back-admin]')?.addEventListener('click', function () {
      navigate('/admin');
    });

    var searchInput = root.querySelector('[data-search]');
    var searchTimer;
    searchInput?.addEventListener('input', function () {
      clearTimeout(searchTimer);
      var val = this.value;
      searchTimer = setTimeout(function () {
        state.search = val;
        state.page = 1;
        refresh();
      }, 350);
    });

    root.querySelector('[data-filter-verified]')?.addEventListener('change', function () {
      var v = this.value;
      state.verified = v === '' ? null : v === 'true';
      state.page = 1;
      refresh();
    });

    root.querySelector('[data-broadcast-open]')?.addEventListener('click', openBroadcastModal);
    root.querySelector('[data-refresh]')?.addEventListener('click', refresh);

    root.querySelector('[data-page="prev"]')?.addEventListener('click', function () {
      if (state.page > 1) {
        state.page--;
        refresh();
      }
    });
    root.querySelector('[data-page="next"]')?.addEventListener('click', function () {
      if (state.page < state.pages) {
        state.page++;
        refresh();
      }
    });

    root.querySelectorAll('[data-select]').forEach(function (cb) {
      cb.addEventListener('change', function () {
        state.selected[this.getAttribute('data-select')] = this.checked;
      });
    });

    root.querySelectorAll('[data-act]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var actName = this.getAttribute('data-act');
        var id = Number(this.getAttribute('data-id'));
        var user = state.items.find(function (u) {
          return u.id === id;
        });
        if (!user) return;
        if (actName === 'pwd') openPasswordModal(user);
        else if (actName === 'mail') openEmailModal(user);
        else if (actName === 'verify') act('/' + id + '/verify', 'POST');
        else if (actName === 'resend') act('/' + id + '/resend-verification', 'POST');
        else if (actName === 'block') {
          var reason = window.prompt('Причина блокировки (необязательно):');
          act('/' + id + '/block' + (reason ? '?reason=' + encodeURIComponent(reason) : ''), 'POST');
        } else if (actName === 'unblock') act('/' + id + '/unblock', 'POST');
      });
    });
  }

  function refresh() {
    Promise.all([loadStats(), loadUsers()])
      .then(function () {
        renderPage();
      })
      .catch(function (err) {
        showToast(err.message || 'Ошибка загрузки', 'error');
      });
  }

  function mountEmailUsersPage() {
    var existing = document.getElementById('satka-email-admin-root');
    if (!existing) {
      existing = document.createElement('div');
      existing.id = 'satka-email-admin-root';
      document.body.appendChild(existing);
    }
    existing.style.display = 'block';
    var appRoot = document.getElementById('root');
    if (appRoot) appRoot.style.display = 'none';
    refresh();
  }

  function unmountEmailUsersPage() {
    var el = document.getElementById('satka-email-admin-root');
    if (el) {
      el.style.display = 'none';
      el.innerHTML = '';
    }
    var appRoot = document.getElementById('root');
    if (appRoot) appRoot.style.display = '';
    closeModal();
  }

  function injectAdminCard() {
    if (!isAdminHub()) {
      document.querySelectorAll('[data-satka-email-card]').forEach(function (el) {
        el.remove();
      });
      return;
    }
    if (document.querySelector('[data-satka-email-card]')) return;

    var main =
      document.querySelector('#root main') ||
      document.querySelector('#root [role="main"]') ||
      document.querySelector('#root');
    if (!main) return;

    var card = document.createElement('div');
    card.className = 'satka-email-admin-card';
    card.dataset.satkaEmailCard = '1';
    card.innerHTML =
      '<span class="satka-email-admin-card-icon">📧</span>' +
      '<div><div class="satka-email-admin-card-title">Почтовики</div>' +
      '<div class="satka-email-admin-card-desc">Email-регистрации: пароли, рассылки, подтверждение</div></div>';
    card.addEventListener('click', function () {
      navigate(ROUTE);
    });

    var grid = main.querySelector('.grid, [class*="grid"]');
    if (grid && grid.children.length) {
      grid.insertBefore(card, grid.children[0]);
    } else {
      main.insertBefore(card, main.firstChild);
    }
  }

  function onRoute() {
    if (isEmailUsersRoute()) {
      mountEmailUsersPage();
    } else {
      unmountEmailUsersPage();
      if (isAdminHub()) injectAdminCard();
    }
  }

  function init() {
    if (window.SatkaRoute) {
      window.SatkaRoute.onChange(onRoute);
      window.SatkaRoute.whenReady(onRoute);
    } else {
      window.addEventListener('popstate', onRoute);
      document.addEventListener('DOMContentLoaded', onRoute);
      setTimeout(onRoute, 800);
    }
    onRoute();
  }

  init();
})();

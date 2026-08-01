(function () {
  'use strict';

  var API = '/api/cabinet/satka/admin/email-users';
  var PANEL = 'email-users';
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
    loaded: false,
    open: false,
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
      return new Date(iso).toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (e) {
      return iso;
    }
  }

  function isAdminHub() {
    var p = window.location.pathname.replace(/\/$/, '');
    return p === '/admin';
  }

  function isPanelOpen() {
    if (!isAdminHub()) return false;
    try {
      return new URLSearchParams(window.location.search).get('panel') === PANEL;
    } catch (e) {
      return false;
    }
  }

  function setPanelOpen(open) {
    var url = new URL(window.location.href);
    url.pathname = '/admin';
    if (open) url.searchParams.set('panel', PANEL);
    else url.searchParams.delete('panel');
    var next = url.pathname + (url.searchParams.toString() ? '?' + url.searchParams.toString() : '');
    if (next !== window.location.pathname + window.location.search) {
      window.history.pushState({}, '', next);
    }
    onRoute(true);
  }

  function statusBadge(st) {
    if (st === 'blocked') return '<span class="satka-email-badge satka-email-badge-block">заблок.</span>';
    if (st === 'active') return '<span class="satka-email-badge satka-email-badge-ok">активен</span>';
    return '<span class="satka-email-badge satka-email-badge-warn">' + esc(st) + '</span>';
  }

  function loadStats() {
    return api('/stats').then(function (data) {
      state.stats = data;
      return data;
    });
  }

  function loadUsers() {
    state.loading = true;
    updateTableArea();
    var q = '?page=' + state.page + '&page_size=' + state.pageSize;
    if (state.search) q += '&search=' + encodeURIComponent(state.search);
    if (state.verified !== null) q += '&verified=' + state.verified;
    return api(q)
      .then(function (data) {
        state.items = data.items || [];
        state.total = data.total || 0;
        state.pages = data.pages || 1;
        state.loading = false;
        state.loaded = true;
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
    bindModalActions();
  }

  function closeModal() {
    document.querySelectorAll('[data-satka-email-modal]').forEach(function (el) {
      el.remove();
    });
  }

  function act(path, method, body) {
    return api(path, { method: method || 'POST', body: body })
      .then(function (res) {
        showToast(res.message || 'Готово', 'ok');
        return loadUsers().then(updateTableArea);
      })
      .catch(function (err) {
        showToast(err.message || 'Ошибка', 'error');
      });
  }

  function openPasswordModal(user) {
    openModal(
      '<div class="satka-email-modal"><h2>Сменить пароль</h2>' +
        '<p style="opacity:0.7;font-size:0.85rem;margin:0 0 12px">' +
        esc(user.email) +
        '</p><label>Новый пароль (мин. 8 символов)</label>' +
        '<input type="password" id="satka-email-pwd" autocomplete="new-password" />' +
        '<div class="satka-email-modal-actions">' +
        '<button type="button" class="satka-email-btn" data-close>Отмена</button>' +
        '<button type="button" class="satka-email-btn satka-email-btn-primary" data-save-pwd data-id="' +
        user.id +
        '">Сохранить</button></div></div>'
    );
  }

  function openEmailModal(user) {
    openModal(
      '<div class="satka-email-modal"><h2>Отправить письмо</h2>' +
        '<p style="opacity:0.7;font-size:0.85rem;margin:0 0 12px">' +
        esc(user.email) +
        '</p><label>Тема</label><input type="text" id="satka-email-subj" />' +
        '<label>Текст (HTML)</label><textarea id="satka-email-body"></textarea>' +
        '<div class="satka-email-modal-actions">' +
        '<button type="button" class="satka-email-btn" data-close>Отмена</button>' +
        '<button type="button" class="satka-email-btn satka-email-btn-primary" data-send-email data-id="' +
        user.id +
        '">Отправить</button></div></div>'
    );
  }

  function openBroadcastModal() {
    var ids = Object.keys(state.selected).filter(function (k) {
      return state.selected[k];
    });
    openModal(
      '<div class="satka-email-modal"><h2>Рассылка на почту</h2>' +
        '<p style="opacity:0.7;font-size:0.85rem;margin:0 0 12px">' +
        (ids.length ? 'Выбрано: ' + ids.length : 'Всем подтверждённым email-пользователям') +
        '</p><label>Тема</label><input type="text" id="satka-email-subj" />' +
        '<label>Текст (HTML)</label><textarea id="satka-email-body"></textarea>' +
        '<label><input type="checkbox" id="satka-email-only-verified" checked /> Только с подтверждённым email</label>' +
        '<div class="satka-email-modal-actions">' +
        '<button type="button" class="satka-email-btn" data-close>Отмена</button>' +
        '<button type="button" class="satka-email-btn satka-email-btn-primary" data-broadcast>Отправить рассылку</button>' +
        '</div></div>'
    );
  }

  function bindModalActions() {
    var backdrop = document.querySelector('[data-satka-email-modal]');
    if (!backdrop) return;
    var closeBtn = backdrop.querySelector('[data-close]');
    if (closeBtn) closeBtn.addEventListener('click', closeModal);

    var savePwd = backdrop.querySelector('[data-save-pwd]');
    if (savePwd) {
      savePwd.addEventListener('click', function () {
        var id = this.getAttribute('data-id');
        var pwd = (document.getElementById('satka-email-pwd') || {}).value || '';
        if (pwd.length < 8) {
          showToast('Пароль минимум 8 символов', 'error');
          return;
        }
        closeModal();
        act('/' + id + '/set-password', 'POST', { password: pwd });
      });
    }

    var sendEmail = backdrop.querySelector('[data-send-email]');
    if (sendEmail) {
      sendEmail.addEventListener('click', function () {
        var id = this.getAttribute('data-id');
        var subject = (document.getElementById('satka-email-subj') || {}).value || '';
        var body = (document.getElementById('satka-email-body') || {}).value || '';
        if (!subject || !body) {
          showToast('Заполните тему и текст', 'error');
          return;
        }
        closeModal();
        act('/' + id + '/send-email', 'POST', { subject: subject, body_html: body });
      });
    }

    var broadcast = backdrop.querySelector('[data-broadcast]');
    if (broadcast) {
      broadcast.addEventListener('click', function () {
        var subject = (document.getElementById('satka-email-subj') || {}).value || '';
        var body = (document.getElementById('satka-email-body') || {}).value || '';
        var onlyVerified = document.getElementById('satka-email-only-verified')
          ? document.getElementById('satka-email-only-verified').checked !== false
          : true;
        var ids = Object.keys(state.selected)
          .filter(function (k) {
            return state.selected[k];
          })
          .map(Number);
        if (!subject || !body) {
          showToast('Заполните тему и текст', 'error');
          return;
        }
        closeModal();
        api('/broadcast', {
          method: 'POST',
          body: {
            subject: subject,
            body_html: body,
            user_ids: ids.length ? ids : null,
            only_verified: onlyVerified,
          },
        })
          .then(function (res) {
            showToast('Отправлено: ' + res.sent + ', ошибок: ' + res.failed, 'ok');
          })
          .catch(function (err) {
            showToast(err.message || 'Ошибка рассылки', 'error');
          });
      });
    }
  }

  function renderStatsHtml() {
    var s = state.stats;
    if (!s) return '<div class="satka-email-loading">Загрузка статистики…</div>';
    function card(val, label) {
      return (
        '<div class="satka-email-stat"><div class="satka-email-stat-value">' +
        esc(val) +
        '</div><div class="satka-email-stat-label">' +
        esc(label) +
        '</div></div>'
      );
    }
    return (
      '<div class="satka-email-stats">' +
      card(s.total, 'Всего почтовиков') +
      card(s.verified, 'Подтверждённых') +
      card(s.unverified, 'Без подтверждения') +
      card(s.with_active_subscription, 'С подпиской') +
      card(s.registered_today, 'Сегодня') +
      card(s.registered_week, 'За неделю') +
      '</div>'
    );
  }

  function renderTableHtml() {
    if (state.loading && !state.items.length) {
      return '<div class="satka-email-loading" id="satka-email-table-area">Загрузка…</div>';
    }
    if (!state.items.length) {
      return '<div class="satka-email-loading" id="satka-email-table-area">Пользователи не найдены</div>';
    }
    var rows = state.items
      .map(function (u) {
        var verified = u.email_verified
          ? '<span class="satka-email-badge satka-email-badge-ok">да</span>'
          : '<span class="satka-email-badge satka-email-badge-warn">нет</span>';
        var checked = state.selected[u.id] ? ' checked' : '';
        return (
          '<tr><td><input type="checkbox" data-select="' +
          u.id +
          '"' +
          checked +
          ' /></td><td>' +
          esc(u.email) +
          '</td><td>' +
          verified +
          '</td><td>' +
          statusBadge(u.status) +
          '</td><td>' +
          (u.balance_rubles != null ? u.balance_rubles.toFixed(0) + ' ₽' : '—') +
          '</td><td>' +
          (u.has_subscription ? esc(u.subscription_status || 'да') : '—') +
          '</td><td>' +
          fmtDate(u.created_at) +
          '</td><td><div class="satka-email-row-actions">' +
          '<button type="button" data-act="pwd" data-id="' +
          u.id +
          '">Пароль</button>' +
          '<button type="button" data-act="mail" data-id="' +
          u.id +
          '">Письмо</button>' +
          (u.email_verified ? '' : '<button type="button" data-act="verify" data-id="' + u.id + '">Подтв.</button>') +
          (u.email_verified ? '' : '<button type="button" data-act="resend" data-id="' + u.id + '">Повтор</button>') +
          (u.status === 'blocked'
            ? '<button type="button" data-act="unblock" data-id="' + u.id + '">Разблок.</button>'
            : '<button type="button" data-act="block" data-id="' + u.id + '">Блок</button>') +
          '</div></td></tr>'
        );
      })
      .join('');
    return (
      '<div class="satka-email-table-wrap" id="satka-email-table-area"><table class="satka-email-table">' +
      '<thead><tr><th></th><th>Email</th><th>Подтв.</th><th>Статус</th><th>Баланс</th><th>Подписка</th><th>Регистрация</th><th>Действия</th></tr></thead>' +
      '<tbody>' +
      rows +
      '</tbody></table></div>' +
      '<div class="satka-email-pagination">' +
      '<button type="button" class="satka-email-btn" data-page="prev"' +
      (state.page <= 1 ? ' disabled' : '') +
      '>← Назад</button><span>Стр. ' +
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

  function updateTableArea() {
    var area = document.getElementById('satka-email-table-area');
    var wrap = document.getElementById('satka-email-table-wrap');
    var parent = wrap || (area && area.parentElement);
    if (!parent) return;
    var pagination = parent.querySelector('.satka-email-pagination');
    if (pagination) pagination.remove();
    var old = document.getElementById('satka-email-table-area');
    if (old) old.outerHTML = renderTableHtml();
    else parent.insertAdjacentHTML('beforeend', renderTableHtml());
    bindTableEvents(document.getElementById('satka-email-admin-root'));
  }

  function bindTableEvents(root) {
    if (!root) return;
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
    root.querySelector('[data-page="prev"]')?.addEventListener('click', function () {
      if (state.page > 1) {
        state.page--;
        loadUsers().then(updateTableArea).catch(function (err) {
          showToast(err.message || 'Ошибка', 'error');
        });
      }
    });
    root.querySelector('[data-page="next"]')?.addEventListener('click', function () {
      if (state.page < state.pages) {
        state.page++;
        loadUsers().then(updateTableArea).catch(function (err) {
          showToast(err.message || 'Ошибка', 'error');
        });
      }
    });
  }

  function bindPanelEvents(root) {
    root.querySelector('[data-back-admin]')?.addEventListener('click', function () {
      setPanelOpen(false);
    });
    var searchInput = root.querySelector('[data-search]');
    if (searchInput) {
      var searchTimer;
      searchInput.addEventListener('input', function () {
        clearTimeout(searchTimer);
        var val = this.value;
        searchTimer = setTimeout(function () {
          state.search = val;
          state.page = 1;
          loadUsers().then(updateTableArea).catch(function (err) {
            showToast(err.message || 'Ошибка', 'error');
          });
        }, 400);
      });
    }
    root.querySelector('[data-filter-verified]')?.addEventListener('change', function () {
      var v = this.value;
      state.verified = v === '' ? null : v === 'true';
      state.page = 1;
      loadUsers().then(updateTableArea).catch(function (err) {
        showToast(err.message || 'Ошибка', 'error');
      });
    });
    root.querySelector('[data-broadcast-open]')?.addEventListener('click', openBroadcastModal);
    root.querySelector('[data-refresh]')?.addEventListener('click', function () {
      Promise.all([loadStats(), loadUsers()])
        .then(function () {
          var statsEl = document.getElementById('satka-email-stats-area');
          if (statsEl) statsEl.innerHTML = renderStatsHtml();
          updateTableArea();
        })
        .catch(function (err) {
          showToast(err.message || 'Ошибка', 'error');
        });
    });
    bindTableEvents(root);
  }

  function ensurePanelShell() {
    var root = document.getElementById('satka-email-admin-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'satka-email-admin-root';
      document.body.appendChild(root);
    }
    if (!root.querySelector('.satka-email-admin')) {
      root.innerHTML =
        '<div class="satka-email-admin">' +
        '<header class="satka-email-admin-header">' +
        '<button type="button" class="satka-email-admin-back" data-back-admin>← Админка</button>' +
        '<h1>📧 Почтовики</h1></header>' +
        '<div class="satka-email-admin-body">' +
        '<div id="satka-email-stats-area"></div>' +
        '<div class="satka-email-toolbar">' +
        '<input class="satka-email-search" type="search" placeholder="Поиск по email…" data-search />' +
        '<select class="satka-email-filter" data-filter-verified>' +
        '<option value="">Все</option><option value="true">Подтверждённые</option><option value="false">Без подтверждения</option>' +
        '</select>' +
        '<button type="button" class="satka-email-btn satka-email-btn-primary" data-broadcast-open>📨 Рассылка</button>' +
        '<button type="button" class="satka-email-btn" data-refresh>↻ Обновить</button>' +
        '</div>' +
        '<div id="satka-email-table-wrap">' +
        renderTableHtml() +
        '</div></div></div>';
      bindPanelEvents(root);
    }
    return root;
  }

  function openPanel() {
    var root = ensurePanelShell();
    root.style.display = 'block';
    state.open = true;
    document.documentElement.classList.add('satka-email-panel-open');
    if (!state.loaded) {
      Promise.all([loadStats(), loadUsers()])
        .then(function () {
          var statsEl = document.getElementById('satka-email-stats-area');
          if (statsEl) statsEl.innerHTML = renderStatsHtml();
          updateTableArea();
        })
        .catch(function (err) {
          showToast(err.message || 'Ошибка загрузки', 'error');
        });
    }
  }

  function closePanel() {
    var root = document.getElementById('satka-email-admin-root');
    if (root) root.style.display = 'none';
    state.open = false;
    document.documentElement.classList.remove('satka-email-panel-open');
    closeModal();
  }

  function findAdminCardsGrid() {
    var main = document.querySelector('#root main');
    if (!main) return null;
    var links = Array.from(main.querySelectorAll('a[href^="/admin/"]')).filter(function (a) {
      return a.href.indexOf('panel=') === -1;
    });
    if (!links.length) return null;
    var best = null;
    var bestCount = 0;
    links.forEach(function (link) {
      var node = link.parentElement;
      var depth = 0;
      while (node && node !== main && depth < 8) {
        var count = node.querySelectorAll('a[href^="/admin/"]').length;
        if (count > bestCount) {
          bestCount = count;
          best = node;
        }
        node = node.parentElement;
        depth++;
      }
    });
    return best;
  }

  function injectAdminCard() {
    if (!isAdminHub() || isPanelOpen()) {
      document.querySelectorAll('[data-satka-email-card]').forEach(function (el) {
        el.remove();
      });
      return;
    }
    if (document.querySelector('[data-satka-email-card]')) return;

    var grid = findAdminCardsGrid();
    var links = grid ? Array.from(grid.querySelectorAll('a[href^="/admin/"]')) : [];
    var template = links[0];
    if (!template) return;

    var card = template.cloneNode(true);
    card.setAttribute('data-satka-email-card', '1');
    card.setAttribute('href', '/admin?panel=' + PANEL);
    card.removeAttribute('data-discover');

    var texts = card.querySelectorAll('p, h3, h4, span, div');
    var titleSet = false;
    texts.forEach(function (el) {
      if (titleSet) return;
      var t = (el.textContent || '').trim();
      if (t.length > 2 && t.length < 80 && el.children.length < 3) {
        el.textContent = 'Почтовики';
        titleSet = true;
      }
    });
    if (!titleSet && card.textContent) {
      card.textContent = 'Почтовики';
    }

    card.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      setPanelOpen(true);
    });

    if (grid) grid.appendChild(card);
  }

  var lastRouteKey = '';
  function onRoute(force) {
    var key = window.location.pathname + window.location.search;
    if (!force && key === lastRouteKey) return;
    lastRouteKey = key;

    if (isPanelOpen()) {
      openPanel();
    } else {
      closePanel();
      if (isAdminHub()) injectAdminCard();
      else document.querySelectorAll('[data-satka-email-card]').forEach(function (el) { el.remove(); });
    }
  }

  function init() {
    if (window.SatkaRoute) {
      window.SatkaRoute.onChange(function () {
        onRoute(false);
      });
    }
    window.addEventListener('popstate', function () {
      onRoute(true);
    });
    setTimeout(function () {
      onRoute(true);
    }, 400);
    var cardTimer = setInterval(function () {
      if (!isAdminHub() || isPanelOpen()) {
        clearInterval(cardTimer);
        return;
      }
      if (!document.querySelector('[data-satka-email-card]')) injectAdminCard();
      if (document.querySelector('[data-satka-email-card]')) clearInterval(cardTimer);
    }, 500);
    setTimeout(function () {
      clearInterval(cardTimer);
    }, 15000);
  }

  init();
})();

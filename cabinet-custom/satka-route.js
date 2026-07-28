(function (global) {
  'use strict';

  var routeListeners = [];
  var readyListeners = [];
  var lastPath = '';
  var observer = null;

  function currentPath() {
    return global.location.pathname || '/';
  }

  function isAppReady() {
    var root = document.getElementById('root');
    if (!root || !root.children.length) return false;
    return !!(
      root.querySelector('main') ||
      root.querySelector('[role="main"]') ||
      root.querySelector('header') ||
      root.querySelector('nav')
    );
  }

  function flushReady() {
    if (!isAppReady()) return;
    readyListeners.forEach(function (fn) {
      try {
        fn();
      } catch (e) {}
    });
  }

  function scheduleReady() {
    clearTimeout(scheduleReady._t);
    scheduleReady._t = setTimeout(flushReady, 100);
  }

  function ensureObserver() {
    if (observer) return;
    var root = document.getElementById('root');
    if (!root) return;
    observer = new MutationObserver(function () {
      if (isAppReady()) scheduleReady();
    });
    observer.observe(root, { childList: true, subtree: true });
    setTimeout(function () {
      if (observer) {
        observer.disconnect();
        observer = null;
      }
    }, 30000);
  }

  function whenReady(fn) {
    if (typeof fn !== 'function') return;
    readyListeners.push(fn);
    if (isAppReady()) scheduleReady();
    else ensureObserver();
  }

  function emitRoute() {
    var path = currentPath();
    if (path === lastPath && lastPath) return;
    lastPath = path;
    routeListeners.forEach(function (fn) {
      try {
        fn(path);
      } catch (e) {}
    });
    scheduleReady();
  }

  function onChange(fn) {
    if (typeof fn === 'function') routeListeners.push(fn);
  }

  function hookHistory() {
    var _push = global.history.pushState;
    var _replace = global.history.replaceState;
    global.history.pushState = function () {
      var r = _push.apply(global.history, arguments);
      emitRoute();
      return r;
    };
    global.history.replaceState = function () {
      var r = _replace.apply(global.history, arguments);
      emitRoute();
      return r;
    };
    global.addEventListener('popstate', emitRoute);
  }

  hookHistory();
  lastPath = currentPath();
  ensureObserver();
  scheduleReady();

  global.SatkaRoute = {
    onChange: onChange,
    whenReady: whenReady,
    whenRootReady: whenReady,
    path: currentPath,
    refresh: function () {
      lastPath = '';
      emitRoute();
    },
  };
})(window);

(function (global) {
  'use strict';

  var listeners = [];
  var lastPath = '';

  function currentPath() {
    return global.location.pathname || '/';
  }

  function emit() {
    var path = currentPath();
    if (path === lastPath && lastPath) return;
    lastPath = path;
    listeners.forEach(function (fn) {
      try {
        fn(path);
      } catch (e) {}
    });
  }

  function onRoute(fn) {
    if (typeof fn === 'function') listeners.push(fn);
    return function () {
      listeners = listeners.filter(function (x) {
        return x !== fn;
      });
    };
  }

  function hookHistory() {
    var _push = global.history.pushState;
    var _replace = global.history.replaceState;
    global.history.pushState = function () {
      var r = _push.apply(global.history, arguments);
      emit();
      return r;
    };
    global.history.replaceState = function () {
      var r = _replace.apply(global.history, arguments);
      emit();
      return r;
    };
    global.addEventListener('popstate', emit);
  }

  function whenRootReady(fn, maxMs) {
    var deadline = Date.now() + (maxMs || 12000);
    function tick() {
      var root = document.getElementById('root');
      if (root && root.children.length) {
        fn(root);
        return;
      }
      if (Date.now() < deadline) requestAnimationFrame(tick);
    }
    tick();
  }

  hookHistory();
  lastPath = currentPath();

  global.SatkaRoute = {
    onChange: onRoute,
    path: currentPath,
    refresh: emit,
    whenRootReady: whenRootReady,
  };
})(window);

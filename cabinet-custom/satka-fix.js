(function (global) {
  'use strict';

  var ONBOARD_KEY = 'onboarding_completed';

  try {
    localStorage.setItem(ONBOARD_KEY, 'true');
  } catch (e) {}

  function removeOnboardingOverlay() {
    document.querySelectorAll('.onboarding-overlay, .onboarding-spotlight, .onboarding-tooltip').forEach(function (el) {
      el.remove();
    });
  }

  function onRouteChange() {
    removeOnboardingOverlay();
    try {
      localStorage.setItem(ONBOARD_KEY, 'true');
    } catch (e) {}
  }

  removeOnboardingOverlay();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', removeOnboardingOverlay);
  }

  /* ── SatkaRoute: app-ready + navigation hooks ── */
  if (!global.SatkaRoute) {
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

    function hookHistory() {
      var _push = global.history.pushState;
      var _replace = global.history.replaceState;
      global.history.pushState = function () {
        var r = _push.apply(global.history, arguments);
        emitRoute();
        onRouteChange();
        return r;
      };
      global.history.replaceState = function () {
        var r = _replace.apply(global.history, arguments);
        emitRoute();
        onRouteChange();
        return r;
      };
      global.addEventListener('popstate', function () {
        emitRoute();
        onRouteChange();
      });
    }

    hookHistory();
    lastPath = currentPath();
    ensureObserver();
    scheduleReady();

    global.SatkaRoute = {
      onChange: function (fn) {
        if (typeof fn === 'function') routeListeners.push(fn);
      },
      whenReady: whenReady,
      whenRootReady: whenReady,
      path: currentPath,
      refresh: function () {
        lastPath = '';
        emitRoute();
      },
    };
  } else if (global.SatkaRoute) {
    global.SatkaRoute.onChange(onRouteChange);
  }
})(window);

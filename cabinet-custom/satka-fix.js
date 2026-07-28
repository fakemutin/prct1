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

  function removeInjectedHome() {
    document.querySelectorAll('[data-satka-home]').forEach(function (el) {
      el.remove();
    });
  }

  function onRouteChange() {
    removeOnboardingOverlay();
    removeInjectedHome();
    try {
      localStorage.setItem(ONBOARD_KEY, 'true');
    } catch (e) {}
  }

  removeOnboardingOverlay();
  removeInjectedHome();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      removeOnboardingOverlay();
      removeInjectedHome();
    });
  }

  /* ── SatkaRoute: navigation + reliable mount ticks ── */
  if (!global.SatkaRoute) {
    var routeListeners = [];
    var readyListeners = [];
    var tickListeners = [];
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

    function runTicks() {
      if (document.hidden || !isAppReady()) return;
      tickListeners.forEach(function (fn) {
        try {
          fn();
        } catch (e) {}
      });
    }

    function flushReady() {
      if (!isAppReady()) return;
      readyListeners.forEach(function (fn) {
        try {
          fn();
        } catch (e) {}
      });
      runTicks();
    }

    function scheduleReady() {
      clearTimeout(scheduleReady._t);
      scheduleReady._t = setTimeout(flushReady, 80);
    }

    function ensureObserver() {
      if (observer) return;
      var root = document.getElementById('root');
      if (!root) return;
      observer = new MutationObserver(function () {
        scheduleReady();
      });
      observer.observe(root, { childList: true, subtree: true });
    }

    function whenReady(fn) {
      if (typeof fn !== 'function') return;
      readyListeners.push(fn);
      if (isAppReady()) scheduleReady();
      else ensureObserver();
    }

    function onTick(fn) {
      if (typeof fn !== 'function') return;
      tickListeners.push(fn);
      scheduleReady();
      ensureObserver();
    }

    function emitRoute() {
      var path = currentPath();
      var changed = path !== lastPath;
      lastPath = path;
      if (changed) {
        routeListeners.forEach(function (fn) {
          try {
            fn(path);
          } catch (e) {}
        });
      }
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
      global.addEventListener('pageshow', function () {
        lastPath = '';
        emitRoute();
      });
    }

    hookHistory();
    lastPath = currentPath();
    ensureObserver();
    scheduleReady();
    setInterval(runTicks, 500);

    global.SatkaRoute = {
      onChange: function (fn) {
        if (typeof fn === 'function') routeListeners.push(fn);
      },
      whenReady: whenReady,
      whenRootReady: whenReady,
      onTick: onTick,
      path: currentPath,
      refresh: function () {
        lastPath = '';
        emitRoute();
      },
    };
  } else if (global.SatkaRoute && !global.SatkaRoute.onTick) {
    var legacyTicks = [];
    global.SatkaRoute.onTick = function (fn) {
      if (typeof fn === 'function') legacyTicks.push(fn);
      try {
        fn();
      } catch (e) {}
    };
    setInterval(function () {
      if (document.hidden) return;
      legacyTicks.forEach(function (fn) {
        try {
          fn();
        } catch (e) {}
      });
    }, 500);
    global.SatkaRoute.onChange(onRouteChange);
  } else if (global.SatkaRoute) {
    global.SatkaRoute.onChange(onRouteChange);
  }
})(window);

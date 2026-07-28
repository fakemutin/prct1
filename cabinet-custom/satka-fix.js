(function () {
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

  if (window.SatkaRoute) {
    window.SatkaRoute.onChange(onRouteChange);
  } else {
    window.addEventListener('popstate', onRouteChange);
  }
})();

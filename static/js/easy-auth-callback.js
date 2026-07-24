/* PeerSlate Entra External ID callback hardening.
   Easy Auth can return to an already-open document by changing only its
   fragment. Fragments never reach Flask, so discard the opaque callback value
   and force one clean request that includes the secure Easy Auth cookie. */
(function (root, factory) {
  'use strict';

  var api = factory();
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  if (root && root.window === root) {
    root.PeerSlateEasyAuthCallback = api;
    api.install(root);
  }
})(typeof window !== 'undefined' ? window :
  (typeof globalThis !== 'undefined' ? globalThis : this), function () {
  'use strict';

  var TOKEN_FRAGMENT_PREFIX = '#token=';

  function clearCallbackAndReload(windowRef) {
    var locationRef = windowRef && windowRef.location;
    if (!locationRef || typeof locationRef.hash !== 'string' ||
        locationRef.hash.indexOf(TOKEN_FRAGMENT_PREFIX) !== 0) {
      return false;
    }

    var cleanPath = (locationRef.pathname || '/') + (locationRef.search || '');
    try {
      windowRef.history.replaceState(null, '', cleanPath);
      locationRef.reload();
    } catch (error) {
      // Modern supported browsers provide replaceState. The fallback still
      // removes the fragment and replaces, rather than extends, browser history.
      locationRef.replace(cleanPath);
    }
    return true;
  }

  function install(windowRef) {
    function checkForCallback() {
      return clearCallbackAndReload(windowRef);
    }

    checkForCallback();
    if (windowRef && typeof windowRef.addEventListener === 'function') {
      windowRef.addEventListener('hashchange', checkForCallback);
      windowRef.addEventListener('pageshow', checkForCallback);
    }
    return checkForCallback;
  }

  return {
    clearCallbackAndReload: clearCallbackAndReload,
    install: install
  };
});

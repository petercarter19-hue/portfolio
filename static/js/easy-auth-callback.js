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
    var privateBfcacheReloaded = false;

    function checkForCallback() {
      return clearCallbackAndReload(windowRef);
    }

    // PS-SIGNIN-MEMBER-ARRIVAL-001. Keep in step with
    // safe_return.PROTECTED_DESTINATIONS; tests/test_signin_member_arrival.py
    // fails if these two lists drift apart. This guard was written when /app
    // was the only private namespace and was never extended as Community,
    // Interview Studio and the Opportunity Slate room moved behind sign-in —
    // so those pages could restore a signed-in body under a signed-out header
    // after a Back press in any browser that revives a no-store document.
    var PRIVATE_PREFIXES = ['/app', '/the-slate', '/interview-studio', '/opportunity-slate'];

    function isPrivatePath() {
      var pathname = windowRef && windowRef.location && windowRef.location.pathname;
      if (typeof pathname !== 'string') {
        return false;
      }
      if (pathname.indexOf('/auth/') === 0) {
        return true;
      }
      for (var index = 0; index < PRIVATE_PREFIXES.length; index += 1) {
        var prefix = PRIVATE_PREFIXES[index];
        if (pathname === prefix || pathname.indexOf(prefix + '/') === 0) {
          return true;
        }
      }
      return false;
    }

    checkForCallback();
    if (windowRef && typeof windowRef.addEventListener === 'function') {
      windowRef.addEventListener('hashchange', checkForCallback);
      windowRef.addEventListener('pageshow', function (event) {
        if (checkForCallback()) {
          return;
        }
        // A private document restored from bfcache can otherwise show the
        // previous server-authorized shell after sign-out. This is kept here
        // because the guard already loads on every private route; the boolean
        // lives only in this document, never in browser storage.
        if (
          event && event.persisted && isPrivatePath() && !privateBfcacheReloaded
          && windowRef.location && typeof windowRef.location.reload === 'function'
        ) {
          privateBfcacheReloaded = true;
          windowRef.location.reload();
        }
      });
    }
    return checkForCallback;
  }

  return {
    clearCallbackAndReload: clearCallbackAndReload,
    install: install
  };
});

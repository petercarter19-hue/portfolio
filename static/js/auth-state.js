/* PeerSlate account-control reconciliation.
 *
 * The server renders every possible account control. This optional script
 * only chooses among those existing controls after a same-origin,
 * principal-only session check. It never handles tokens, claims, cookies, or
 * browser storage, and it intentionally preserves the server-rendered state
 * whenever the check is unavailable or ambiguous.
 */
(function (root, factory) {
  'use strict';

  var api = factory();
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  if (root && root.window === root) {
    root.PeerSlateAuthState = api;
    api.install(root);
  }
})(typeof window !== 'undefined' ? window :
  (typeof globalThis !== 'undefined' ? globalThis : this), function () {
  'use strict';

  var SESSION_PATH = '/auth/session';
  var VISIBILITY_RECHECK_MS = 15000;
  var DISPLAYABLE_STATES = {
    authenticated: true,
    signed_out: true,
    invalid_session: true
  };
  var CONTROL_STATE = {
    authenticated: 'authenticated',
    signed_out: 'signed_out',
    invalid_session: 'account_issue'
  };

  function isSafeSameOriginPath(value) {
    return typeof value === 'string'
      && value.indexOf('/') === 0
      && value.indexOf('//') !== 0
      && value.indexOf('\\') === -1
      && !/[\x00-\x1f\x7f]/.test(value);
  }

  function sessionUrl(windowRef) {
    if (!windowRef || !windowRef.location || !isSafeSameOriginPath(SESSION_PATH)) {
      return null;
    }
    try {
      var url = new URL(SESSION_PATH, windowRef.location.origin);
      return url.origin === windowRef.location.origin ? url.toString() : null;
    } catch (error) {
      return null;
    }
  }

  function showKnownState(documentRef, state) {
    if (!DISPLAYABLE_STATES[state] || !documentRef || !documentRef.querySelectorAll) {
      return false;
    }
    var controlState = CONTROL_STATE[state];
    var controls = documentRef.querySelectorAll('[data-ps-auth-control]');
    for (var index = 0; index < controls.length; index += 1) {
      controls[index].hidden = controls[index].getAttribute('data-ps-auth-control') !== controlState;
    }
    var container = documentRef.querySelector('[data-ps-auth-controls]');
    if (container) {
      container.setAttribute('data-ps-auth-state', state);
    }
    return true;
  }

  function reconcile(windowRef, documentRef) {
    var fetchRef = windowRef && windowRef.fetch;
    var target = sessionUrl(windowRef);
    if (!fetchRef || !target) {
      return Promise.resolve(false);
    }
    return fetchRef(target, {
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Accept: 'application/json' }
    }).then(function (response) {
      // A 503 represents an unavailable auth boundary. Preserve the visible
      // controls rather than turning an authenticated UI into "Sign In".
      if (!response || response.status === 503 || (response.status !== 200 && response.status !== 401)) {
        return false;
      }
      return response.json().then(function (payload) {
        if (!payload || typeof payload !== 'object' || !DISPLAYABLE_STATES[payload.state]) {
          return false;
        }
        return showKnownState(documentRef, payload.state);
      }, function () {
        return false;
      });
    }, function () {
      return false;
    });
  }

  function install(windowRef) {
    var documentRef = windowRef && windowRef.document;
    if (!documentRef || !windowRef.addEventListener) {
      return;
    }

    var lastVisibilityCheck = 0;

    windowRef.addEventListener('pageshow', function () {
      reconcile(windowRef, documentRef);
    });

    if (documentRef.addEventListener) {
      documentRef.addEventListener('visibilitychange', function () {
        if (documentRef.visibilityState !== 'visible') {
          return;
        }
        var now = Date.now();
        if (now - lastVisibilityCheck < VISIBILITY_RECHECK_MS) {
          return;
        }
        lastVisibilityCheck = now;
        reconcile(windowRef, documentRef);
      });
    }
  }

  return {
    isSafeSameOriginPath: isSafeSameOriginPath,
    showKnownState: showKnownState,
    reconcile: reconcile,
    install: install
  };
});

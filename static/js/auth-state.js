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

  // The private namespaces, kept identical to safe_return.py's registered
  // destinations and to easy-auth-callback.js's own list.  A parity test in
  // tests/test_signin_member_arrival.py fails if the three ever disagree,
  // because a namespace that is private on the server but unknown here is
  // exactly the producer/consumer mismatch this package exists to remove.
  var PRIVATE_PREFIXES = ['/app', '/the-slate', '/interview-studio', '/opportunity-slate'];

  // One reload attempt per document, held in a WeakSet keyed on the window so
  // the flag never reaches browser storage and a genuinely new document may
  // try again.  WeakSet is no newer than the fetch, Promise and URL support
  // reconcile() already requires.
  var reloadedWindows = new WeakSet();

  // Deliberately NOT the same predicate as easy-auth-callback.js's
  // isPrivatePath: that one answers true for /auth/ because a callback
  // fragment must be cleared there.  Here /auth/ must answer false — the
  // sign-in surfaces are exactly where reloading on a signed-out session
  // would loop.
  function isPrivateDocumentPath(windowRef) {
    var pathname = windowRef && windowRef.location && windowRef.location.pathname;
    if (typeof pathname !== 'string' || pathname.indexOf('/auth/') === 0) {
      return false;
    }
    for (var index = 0; index < PRIVATE_PREFIXES.length; index += 1) {
      var prefix = PRIVATE_PREFIXES[index];
      if (pathname === prefix || pathname.indexOf(prefix + '/') === 0) {
        return true;
      }
    }
    return false;
  }

  // What the SERVER said about this document when it rendered it.  Every shell
  // branch declares this, including the owner shell, so a document is never
  // identified by the ABSENCE of a node.
  function serverRenderedAuthState(documentRef) {
    if (!documentRef || !documentRef.querySelector) {
      return null;
    }
    var marked = documentRef.querySelector('[data-ps-auth-state]');
    if (!marked || typeof marked.getAttribute !== 'function') {
      return null;
    }
    return marked.getAttribute('data-ps-auth-state');
  }

  // Being under a private prefix does not make a document private.  Three of
  // the four namespaces are gated by configuration, and /app/workshop is a
  // deliberately public preview served to signed-out visitors in production
  // today — on the owner shell, which renders no account controls at all.  An
  // earlier revision inferred "private" from a missing controls container and
  // would have reloaded that public page on every tab return.
  //
  // So: reload only when the server says it rendered this document for a
  // signed-IN member.  Anything else — signed_out, auth_unavailable,
  // account_issue, or no declared state at all — is left alone.  Failing to
  // reload is inert; reloading a page that is behaving correctly is not.
  function renderIsStaleForSignedOut(documentRef) {
    return serverRenderedAuthState(documentRef) === 'authenticated';
  }

  function reloadPrivateDocumentOnce(windowRef) {
    var location = windowRef && windowRef.location;
    if (!location || typeof location.reload !== 'function') {
      return false;
    }
    if (reloadedWindows.has(windowRef)) {
      return false;
    }
    reloadedWindows.add(windowRef);
    location.reload();
    return true;
  }

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
        // Swapping header controls is not enough on a private document: the
        // owner workspace renders no data-ps-auth-control elements at all
        // (templates/base.html gates them on `not is_owner_app_path`), so a
        // member who signed out in another tab would keep a fully usable
        // private page under an unchanged header.  Reload and let the server
        // re-authorize instead — it answers with the sign-in redirect, so the
        // private content leaves the screen rather than sitting beneath a
        // Sign In button.
        if (
          payload.state === 'signed_out'
          && isPrivateDocumentPath(windowRef)
          && renderIsStaleForSignedOut(documentRef)
        ) {
          return reloadPrivateDocumentOnce(windowRef);
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
      // A private document was authorized by the server for this very render,
      // so asking again on load is redundant — and it would add a request to
      // every workspace page load. easy-auth-callback.js already reloads a
      // private document restored from bfcache, and the case this reconcile
      // exists for is a *return* to an already-open tab, which
      // visibilitychange below covers. Public documents are unchanged: their
      // header is the only thing that can be stale on arrival.
      if (isPrivateDocumentPath(windowRef)) {
        return;
      }
      reconcile(windowRef, documentRef);
    });

    // Shared by both triggers below, so returning to a tab cannot cost more
    // than one session check per VISIBILITY_RECHECK_MS however you got there.
    function recheck() {
      var now = Date.now();
      if (now - lastVisibilityCheck < VISIBILITY_RECHECK_MS) {
        return;
      }
      lastVisibilityCheck = now;
      reconcile(windowRef, documentRef);
    }

    if (documentRef.addEventListener) {
      documentRef.addEventListener('visibilitychange', function () {
        if (documentRef.visibilityState !== 'visible') {
          return;
        }
        recheck();
      });
    }

    // visibilitychange alone does not cover two windows side by side: both stay
    // visibilityState 'visible', so clicking between them fires nothing and the
    // claim that signing out in one window reaches the other would be false.
    // Independent review named this gap; window focus closes it.
    windowRef.addEventListener('focus', function () {
      if (documentRef.visibilityState && documentRef.visibilityState !== 'visible') {
        return;
      }
      recheck();
    });
  }

  return {
    PRIVATE_PREFIXES: PRIVATE_PREFIXES,
    isPrivateDocumentPath: isPrivateDocumentPath,
    serverRenderedAuthState: serverRenderedAuthState,
    isSafeSameOriginPath: isSafeSameOriginPath,
    showKnownState: showKnownState,
    reconcile: reconcile,
    install: install
  };
});

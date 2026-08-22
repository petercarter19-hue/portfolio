'use strict';

const assert = require('node:assert/strict');
const authState = require('../static/js/auth-state.js');

function element(state, hidden) {
  return {
    hidden: !!hidden,
    getAttribute(name) { return name === 'data-ps-auth-control' ? state : null; }
  };
}

function harness(pathname) {
  const controls = [
    element('authenticated', false),
    element('authenticated', false),
    element('workspace_waking', true),
    element('account_issue', true),
    element('signed_out', true)
  ];
  const container = {
    // Seeded with what the server rendered for a signed-IN member, which is
    // the state the private-document reload is meant to correct.
    attributes: { 'data-ps-auth-state': 'authenticated' },
    setAttribute(name, value) { this.attributes[name] = value; },
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(this.attributes, name)
        ? this.attributes[name] : null;
    }
  };
  const documentEvents = {};
  const windowEvents = {};
  const calls = { fetch: [], reload: 0 };
  const documentRef = {
    body: {
      getAttribute() { return null; },
      setAttribute() {}
    },
    visibilityState: 'visible',
    querySelectorAll(selector) {
      return selector === '[data-ps-auth-control]' ? controls : [];
    },
    querySelector(selector) {
      if (selector === '[data-ps-auth-controls]') { return container; }
      // Every shell branch declares the state it rendered, including the owner
      // shell, which has no controls container at all.
      if (selector === '[data-ps-auth-state]') { return container; }
      return null;
    },
    addEventListener(name, handler) { documentEvents[name] = handler; }
  };
  const windowRef = {
    document: documentRef,
    location: {
      origin: 'https://peerslate.com',
      // Public by default, so every pre-existing assertion below still
      // describes a public document. A private-path test sets this.
      pathname: pathname,
      reload() { calls.reload += 1; }
    },
    addEventListener(name, handler) { windowEvents[name] = handler; },
    fetch(url, options) {
      calls.fetch.push({ url, options });
      return Promise.resolve({ status: 200, json: () => Promise.resolve({ state: 'signed_out' }) });
    }
  };
  return { calls, container, controls, documentEvents, windowEvents, windowRef };
}

function visibleControls(harnessRef) {
  return harnessRef.controls
    .filter((control) => !control.hidden)
    .map((control) => control.getAttribute('data-ps-auth-control'));
}

function testOnlyKnownStatesChangeExistingControls() {
  const h = harness();
  assert.equal(authState.showKnownState(h.windowRef.document, 'invalid_session'), true);
  assert.deepEqual(visibleControls(h), ['account_issue']);
  assert.equal(h.container.attributes['data-ps-auth-state'], 'invalid_session');

  assert.equal(authState.showKnownState(h.windowRef.document, 'workspace_waking'), false);
  assert.deepEqual(visibleControls(h), ['account_issue']);
}

async function testUnavailableAndInvalidPayloadsNeverDowngradeTheUi() {
  const h = harness();
  h.windowRef.fetch = () => Promise.resolve({ status: 503, json: () => Promise.resolve({ state: 'signed_out' }) });
  await authState.reconcile(h.windowRef, h.windowRef.document);
  assert.deepEqual(visibleControls(h), ['authenticated', 'authenticated']);

  h.windowRef.fetch = () => Promise.resolve({ status: 200, json: () => Promise.resolve({ state: 'unknown' }) });
  await authState.reconcile(h.windowRef, h.windowRef.document);
  assert.deepEqual(visibleControls(h), ['authenticated', 'authenticated']);
}

async function testPublicReconciliationUsesOnlyTheFixedSameOriginEndpoint() {
  const h = harness();
  authState.install(h.windowRef);
  h.windowEvents.pageshow({ persisted: false });
  await Promise.resolve();
  await Promise.resolve();

  assert.equal(h.calls.fetch.length, 1);
  assert.equal(h.calls.fetch[0].url, 'https://peerslate.com/auth/session');
  assert.equal(h.calls.fetch[0].options.credentials, 'same-origin');
  assert.equal(h.calls.fetch[0].options.cache, 'no-store');
  assert.deepEqual(visibleControls(h), ['signed_out']);
}

function testPathsCannotBecomeCrossOriginOrInjected() {
  assert.equal(authState.isSafeSameOriginPath('/auth/session'), true);
  assert.equal(authState.isSafeSameOriginPath('//attacker.example'), false);
  assert.equal(authState.isSafeSameOriginPath('/auth\\session'), false);
  assert.equal(authState.isSafeSameOriginPath('/auth\x00session'), false);
}

// PS-SIGNIN-MEMBER-ARRIVAL-001. A member who signs out in one tab kept a
// fully usable private page in another: /app renders no data-ps-auth-control
// elements at all, so swapping header controls there changes nothing. These
// cover the reload that replaces it, and the three cases that must NOT reload.
async function testSignedOutPrivateDocumentReloadsInsteadOfSwappingControls() {
  const h = harness('/app');
  await authState.reconcile(h.windowRef, h.windowRef.document);
  assert.equal(h.calls.reload, 1);
  // The server, not the client, decides what a signed-out member may see.
  assert.deepEqual(visibleControls(h), ['authenticated', 'authenticated']);

  // Every registered private namespace behaves the same way, including a
  // path beneath one.
  for (const path of ['/the-slate', '/interview-studio', '/opportunity-slate', '/app/settings']) {
    const each = harness(path);
    await authState.reconcile(each.windowRef, each.windowRef.document);
    assert.equal(each.calls.reload, 1, path);
  }
}

async function testTheReloadIsAttemptedOnlyOncePerDocument() {
  const h = harness('/app');
  await authState.reconcile(h.windowRef, h.windowRef.document);
  await authState.reconcile(h.windowRef, h.windowRef.document);
  await authState.reconcile(h.windowRef, h.windowRef.document);
  assert.equal(h.calls.reload, 1);
}

async function testAuthAndPublicSurfacesNeverReload() {
  // Reloading a sign-in page on a signed-out session is a loop.
  for (const path of ['/auth/sign-in', '/auth/complete', '/', '/resume', '/appointments']) {
    const h = harness(path);
    await authState.reconcile(h.windowRef, h.windowRef.document);
    assert.equal(h.calls.reload, 0, path);
  }
  // '/appointments' also proves the prefix match is exact rather than a bare
  // string prefix of '/app'.
}

async function testAnUnavailableSessionCheckNeverReloadsAPrivateDocument() {
  for (const response of [
    { status: 503, json: () => Promise.resolve({ state: 'signed_out' }) },
    { status: 200, json: () => Promise.resolve({ state: 'unknown' }) },
    { status: 200, json: () => Promise.reject(new Error('bad json')) }
  ]) {
    const h = harness('/app');
    h.windowRef.fetch = () => Promise.resolve(response);
    await authState.reconcile(h.windowRef, h.windowRef.document);
    assert.equal(h.calls.reload, 0);
    assert.deepEqual(visibleControls(h), ['authenticated', 'authenticated']);
  }

  const rejected = harness('/app');
  rejected.windowRef.fetch = () => Promise.reject(new Error('offline'));
  await authState.reconcile(rejected.windowRef, rejected.windowRef.document);
  assert.equal(rejected.calls.reload, 0);
}

// A private document is authorized by the server for the render it just did,
// so reconciling on load is redundant. It is also not free: it put a request
// on every workspace page load, which is what made 16 Journal browser tests
// time out waiting for network idle. The case this exists for is returning to
// an already-open tab.
async function testAPrivateDocumentDoesNotReconcileOnLoad() {
  const h = harness('/app');
  authState.install(h.windowRef);
  h.windowEvents.pageshow({ persisted: false });
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(h.calls.fetch.length, 0);
  assert.equal(h.calls.reload, 0);
}

async function testAPrivateDocumentStillReconcilesWhenTheTabIsReturnedTo() {
  const h = harness('/app');
  authState.install(h.windowRef);
  h.documentEvents.visibilitychange();
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(h.calls.fetch.length, 1);
  assert.equal(h.calls.fetch[0].url, 'https://peerslate.com/auth/session');
  assert.equal(h.calls.reload, 1);
}

// Several PRIVATE_PREFIXES namespaces are flag-gated: with the flag off the
// same path serves an ordinary public page to a signed-out visitor. That
// render already says signed_out and is not stale. Reloading it would bounce
// the visitor every time they returned to the tab — a defect found by review
// before this shipped, not by a failing test.
async function testAPublicRenderOnAPrivatePathIsNeverReloaded() {
  for (const rendered of ['signed_out', 'auth_unavailable', 'account_issue']) {
    const h = harness('/interview-studio');
    h.container.attributes['data-ps-auth-state'] = rendered;
    await authState.reconcile(h.windowRef, h.windowRef.document);
    assert.equal(h.calls.reload, 0, rendered);
  }
}

// REJECTED_WITH_NAMED_DEFECTS, independent review 2026-08-21 (DEFECT-1/2).
// An earlier revision inferred "private document" from a MISSING controls
// container and asserted that a null state must reload. That was the defect
// written down as a test. /app/workshop is a deliberately public preview,
// served 200 to signed-out visitors in production today, on the owner shell —
// which renders no controls container. It would have been reloaded on every
// tab return.
//
// The rule is now: reload only what the server DECLARED it rendered for a
// signed-in member. An undeclared document is never reloaded.
async function testAnUndeclaredDocumentIsNeverReloaded() {
  const h = harness('/app');
  h.windowRef.document.querySelector = () => null;
  assert.equal(authState.serverRenderedAuthState(h.windowRef.document), null);
  await authState.reconcile(h.windowRef, h.windowRef.document);
  assert.equal(h.calls.reload, 0);
}

// The owner shell carries no account controls, so these two documents are
// distinguishable ONLY by the declared state. Both must be handled correctly.
async function testTheOwnerShellIsJudgedByItsDeclaredStateNotByMissingControls() {
  // A public Workshop preview: signed-out visitor, nothing stale, no reload.
  const publicPreview = harness('/app/workshop');
  publicPreview.container.attributes['data-ps-auth-state'] = 'signed_out';
  publicPreview.windowRef.document.querySelectorAll = () => [];
  await authState.reconcile(publicPreview.windowRef, publicPreview.windowRef.document);
  assert.equal(publicPreview.calls.reload, 0);

  // The same path rendered for a signed-in member IS a private library, and
  // must reload once the session has ended elsewhere.
  const signedIn = harness('/app/workshop');
  signedIn.container.attributes['data-ps-auth-state'] = 'authenticated';
  signedIn.windowRef.document.querySelectorAll = () => [];
  await authState.reconcile(signedIn.windowRef, signedIn.windowRef.document);
  assert.equal(signedIn.calls.reload, 1);
}

// Two windows side by side both stay visibilityState 'visible', so clicking
// between them fires no visibilitychange. Without a focus trigger, "signing out
// in one window reaches the other" would simply be false for that arrangement.
// Named by independent review as a gap in the claim, not a ship-blocker.
async function testReturningToASideBySideWindowStillReconciles() {
  const h = harness('/app');
  authState.install(h.windowRef);
  h.windowEvents.focus();
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(h.calls.fetch.length, 1);
  assert.equal(h.calls.reload, 1);
}

async function testTheTwoTriggersShareOneThrottle() {
  // Otherwise returning to a tab could cost two session checks instead of one.
  const h = harness('/app');
  authState.install(h.windowRef);
  h.documentEvents.visibilitychange();
  await Promise.resolve();
  h.windowEvents.focus();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(h.calls.fetch.length, 1);
}

async function testAHiddenWindowFocusEventIsIgnored() {
  const h = harness('/app');
  h.windowRef.document.visibilityState = 'hidden';
  authState.install(h.windowRef);
  h.windowEvents.focus();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(h.calls.fetch.length, 0);
}

function testPrivatePrefixesAreExactlyTheRegisteredPrivateNamespaces() {
  assert.deepEqual(
    authState.PRIVATE_PREFIXES,
    ['/app', '/the-slate', '/interview-studio', '/opportunity-slate']
  );
  assert.equal(authState.isPrivateDocumentPath({ location: { pathname: '/app' } }), true);
  assert.equal(authState.isPrivateDocumentPath({ location: { pathname: '/app/settings' } }), true);
  assert.equal(authState.isPrivateDocumentPath({ location: { pathname: '/appointments' } }), false);
  assert.equal(authState.isPrivateDocumentPath({ location: { pathname: '/auth/sign-in' } }), false);
  assert.equal(authState.isPrivateDocumentPath({ location: {} }), false);
  assert.equal(authState.isPrivateDocumentPath(null), false);
}

async function main() {
  testOnlyKnownStatesChangeExistingControls();
  await testSignedOutPrivateDocumentReloadsInsteadOfSwappingControls();
  await testTheReloadIsAttemptedOnlyOncePerDocument();
  await testAuthAndPublicSurfacesNeverReload();
  await testAnUnavailableSessionCheckNeverReloadsAPrivateDocument();
  await testAPublicRenderOnAPrivatePathIsNeverReloaded();
  await testAnUndeclaredDocumentIsNeverReloaded();
  await testTheOwnerShellIsJudgedByItsDeclaredStateNotByMissingControls();
  await testAPrivateDocumentDoesNotReconcileOnLoad();
  await testAPrivateDocumentStillReconcilesWhenTheTabIsReturnedTo();
  await testReturningToASideBySideWindowStillReconciles();
  await testTheTwoTriggersShareOneThrottle();
  await testAHiddenWindowFocusEventIsIgnored();
  testPrivatePrefixesAreExactlyTheRegisteredPrivateNamespaces();
  await testUnavailableAndInvalidPayloadsNeverDowngradeTheUi();
  await testPublicReconciliationUsesOnlyTheFixedSameOriginEndpoint();
  testPathsCannotBecomeCrossOriginOrInjected();

  const source = require('node:fs').readFileSync('static/js/auth-state.js', 'utf8');
  assert.equal(source.includes('innerHTML'), false);
  assert.equal(source.includes('localStorage'), false);
  assert.equal(source.includes('sessionStorage'), false);
  console.log('auth state: 17 behavioral checks passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

'use strict';

const assert = require('node:assert/strict');
const authState = require('../static/js/auth-state.js');

function element(state, hidden) {
  return {
    hidden: !!hidden,
    getAttribute(name) { return name === 'data-ps-auth-control' ? state : null; }
  };
}

function harness() {
  const controls = [
    element('authenticated', false),
    element('authenticated', false),
    element('workspace_waking', true),
    element('account_issue', true),
    element('signed_out', true)
  ];
  const container = {
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; }
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
      return selector === '[data-ps-auth-controls]' ? container : null;
    },
    addEventListener(name, handler) { documentEvents[name] = handler; }
  };
  const windowRef = {
    document: documentRef,
    location: {
      origin: 'https://peerslate.com',
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

async function main() {
  testOnlyKnownStatesChangeExistingControls();
  await testUnavailableAndInvalidPayloadsNeverDowngradeTheUi();
  await testPublicReconciliationUsesOnlyTheFixedSameOriginEndpoint();
  testPathsCannotBecomeCrossOriginOrInjected();

  const source = require('node:fs').readFileSync('static/js/auth-state.js', 'utf8');
  assert.equal(source.includes('innerHTML'), false);
  assert.equal(source.includes('localStorage'), false);
  assert.equal(source.includes('sessionStorage'), false);
  console.log('auth state: 4 behavioral checks passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

'use strict';

const assert = require('node:assert/strict');
const callback = require('../static/js/easy-auth-callback.js');

function harness(hash = '') {
  const events = {};
  const calls = {
    reload: 0,
    replace: [],
    replaceState: []
  };
  const windowRef = {
    location: {
      hash,
      pathname: '/app',
      search: '?view=owner',
      reload() { calls.reload += 1; },
      replace(value) { calls.replace.push(value); }
    },
    history: {
      replaceState(state, title, value) {
        calls.replaceState.push([state, title, value]);
        windowRef.location.hash = '';
      }
    },
    addEventListener(name, listener) { events[name] = listener; }
  };
  return { calls, events, windowRef };
}

function testInitialCallbackIsDiscardedAndReloaded() {
  const h = harness('#token=opaque-value-that-must-not-be-read');

  assert.equal(callback.clearCallbackAndReload(h.windowRef), true);
  assert.deepEqual(h.calls.replaceState, [[null, '', '/app?view=owner']]);
  assert.equal(h.calls.reload, 1);
  assert.deepEqual(h.calls.replace, []);
}

function testUnrelatedFragmentsRemainUntouched() {
  const h = harness('#my-story');

  assert.equal(callback.clearCallbackAndReload(h.windowRef), false);
  assert.deepEqual(h.calls.replaceState, []);
  assert.equal(h.calls.reload, 0);
}

function testDelayedHashCallbackIsHandled() {
  const h = harness('');
  callback.install(h.windowRef);
  h.windowRef.location.hash = '#token=opaque';
  h.events.hashchange();

  assert.equal(h.calls.reload, 1);
  assert.deepEqual(h.calls.replaceState, [[null, '', '/app?view=owner']]);
}

function testBackForwardCacheReturnIsHandled() {
  const h = harness('');
  callback.install(h.windowRef);
  h.windowRef.location.hash = '#token=opaque';
  h.events.pageshow();

  assert.equal(h.calls.reload, 1);
}

function testHistoryFailureUsesCleanReplacement() {
  const h = harness('#token=opaque');
  h.windowRef.history.replaceState = () => { throw new Error('unavailable'); };

  assert.equal(callback.clearCallbackAndReload(h.windowRef), true);
  assert.deepEqual(h.calls.replace, ['/app?view=owner']);
  assert.equal(h.calls.reload, 0);
}

testInitialCallbackIsDiscardedAndReloaded();
testUnrelatedFragmentsRemainUntouched();
testDelayedHashCallbackIsHandled();
testBackForwardCacheReturnIsHandled();
testHistoryFailureUsesCleanReplacement();
console.log('easy auth callback: 5 behavioral checks passed');

/* Executable contract for the production Community Voice retry helpers.
 * Run: node tests/community_voice_retry.test.js
 */
'use strict';

const assert = require('assert');

let clock = 1000;
let nextTimerId = 1;
const timers = new Map();
const windowListeners = new Map();
const documentListeners = new Map();

class FakeElement {
  constructor(tagName) {
    this.tagName = String(tagName || 'div').toUpperCase();
    this.children = [];
    this.parentNode = null;
    this.dataset = {};
    this.attributes = {};
    this.className = '';
    this.classList = {add: (name) => {
      if (!this.className.split(/\s+/).includes(name)) this.className += (this.className ? ' ' : '') + name;
    }};
    this.hidden = false;
    this.isConnected = true;
    this.textContent = '';
    this.value = '';
    this.selectionStart = 0;
    this.listeners = new Map();
    this.focusCount = 0;
  }

  appendChild(child) {
    child.parentNode = this;
    child.isConnected = this.isConnected;
    this.children.push(child);
    return child;
  }

  replaceChildren(...children) {
    this.children.forEach((child) => {
      child.parentNode = null;
      child.isConnected = false;
    });
    this.children = [];
    children.forEach((child) => this.appendChild(child));
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  addEventListener(name, handler) {
    if (!this.listeners.has(name)) this.listeners.set(name, []);
    this.listeners.get(name).push(handler);
  }

  dispatchEvent(event) {
    (this.listeners.get(event.type) || []).forEach((handler) => handler(event));
    return true;
  }

  contains(node) {
    for (let current = node; current; current = current.parentNode) {
      if (current === this) return true;
    }
    return false;
  }

  querySelector(selector) {
    const matches = (node) => selector.startsWith('.')
      ? node.className.split(/\s+/).includes(selector.slice(1))
      : node.tagName.toLowerCase() === selector.toLowerCase();
    const visit = (node) => {
      for (const child of node.children) {
        if (matches(child)) return child;
        const nested = visit(child);
        if (nested) return nested;
      }
      return null;
    };
    return visit(this);
  }

  querySelectorAll() {
    return [];
  }

  focus() {
    if (!this.isConnected) return;
    this.focusCount += 1;
    document.activeElement = this;
  }

  remove() {
    if (this.parentNode) {
      this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
    }
    this.parentNode = null;
    this.isConnected = false;
  }

  setSelectionRange(start) {
    this.selectionStart = start;
  }
}

function addListener(store, name, handler) {
  if (!store.has(name)) store.set(name, []);
  store.get(name).push(handler);
}

function dispatchListeners(store, name) {
  (store.get(name) || []).slice().forEach((handler) => handler({type: name}));
}

const body = new FakeElement('body');
const app = new FakeElement('main');
app.dataset.owner = 'false';
app.querySelector = () => null;
app.querySelectorAll = () => [];

global.document = {
  body,
  activeElement: body,
  visibilityState: 'visible',
  querySelector: (selector) => selector === '[data-community-app]' ? app : null,
  createElement: (tag) => new FakeElement(tag),
  createElementNS: (_namespace, tag) => new FakeElement(tag),
  createComment: () => new FakeElement('#comment'),
  addEventListener: (name, handler) => addListener(documentListeners, name, handler)
};
global.window = {
  setTimeout: (handler, delay) => {
    const id = nextTimerId++;
    timers.set(id, {handler, due: clock + Math.max(0, Number(delay) || 0)});
    return id;
  },
  clearTimeout: (id) => timers.delete(id),
  setInterval: (handler, delay) => {
    const id = nextTimerId++;
    timers.set(id, {handler, due: clock + Math.max(0, Number(delay) || 0), interval: delay});
    return id;
  },
  clearInterval: (id) => timers.delete(id),
  addEventListener: (name, handler) => addListener(windowListeners, name, handler)
};
global.PeerSlateCommunityVoiceControllerTestMode = true;
const realDateNow = Date.now;
Date.now = () => clock;
const voice = require('../static/js/community-v1.js');
delete global.PeerSlateCommunityVoiceControllerTestMode;

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return {promise, resolve, reject};
}

async function flushPromises() {
  for (let index = 0; index < 20; index += 1) await Promise.resolve();
}

function resetControllerHarness() {
  voice.controllerTest.disposeControllers();
  timers.clear();
  clock = 1000;
  document.activeElement = document.body;
  document.visibilityState = 'visible';
  global.fetch = undefined;
}

function createController() {
  const form = new FakeElement('form');
  const input = new FakeElement('textarea');
  const trigger = new FakeElement('button');
  form.appendChild(input);
  form.appendChild(trigger);
  const controller = new voice.controllerTest.Controller({
    form,
    input,
    trigger,
    context: 'contribution',
    maxLength: 2000,
    noun: 'reply'
  });
  return {controller, form, input, trigger};
}

function capture(controller) {
  controller.cancelled = false;
  controller.blob = new Blob(['bounded audio'], {type: 'audio/webm'});
  controller.durationSeconds = 1.25;
  controller.retryState = voice.transitionRetryState(controller.retryState, 'captured', clock);
  assert.strictEqual(controller.claim(), true);
}

function retainAfterTransientFailure(controller) {
  const error = new Error('Timed out.');
  error.code = 'provider_timeout';
  error.retry = 'same_recording';
  error.retryable = true;
  controller.applyTranscriptionFailure(error);
  assert.strictEqual(controller.state, 'failure');
  assert.strictEqual(controller.retryState.holdsRegistry, true);
  assert.strictEqual(voice.controllerTest.registry.active, controller);
}

function buttonLabels(panel) {
  const labels = [];
  const visit = (node) => {
    if (node.tagName === 'BUTTON') labels.push(node.textContent);
    node.children.forEach(visit);
  };
  visit(panel);
  return labels;
}

function response(status, payload, contentType = 'application/json') {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {get: () => contentType},
    json: () => Promise.resolve(payload)
  };
}

async function runDueTimers(target) {
  clock = target;
  while (true) {
    const due = [...timers.entries()]
      .filter(([, timer]) => timer.due <= clock)
      .sort((left, right) => left[1].due - right[1].due);
    if (!due.length) return;
    const [id, timer] = due[0];
    timers.delete(id);
    timer.handler();
    await flushPromises();
  }
}

async function traceInFlightExpiry(lateResponse) {
  resetControllerHarness();
  const {controller, input} = createController();
  document.activeElement = input;
  capture(controller);
  retainAfterTransientFailure(controller);
  const pending = deferred();
  let requestOptions;
  global.fetch = (_url, options) => {
    requestOptions = options;
    return pending.promise;
  };
  clock += 1000;
  controller.retrySameRecording();
  await flushPromises();
  assert.strictEqual(controller.state, 'processing');
  assert.ok(requestOptions.body instanceof FormData);
  assert.ok(requestOptions.body.get('audio') instanceof Blob);
  assert.strictEqual(requestOptions.signal.aborted, false);
  const processingGeneration = controller.requestGeneration;
  const outside = new FakeElement('button');
  document.activeElement = outside;

  // Model a suspended browser: neither the 60-second request timer nor the
  // five-minute wake-up runs. Resume must apply wall-clock truth first.
  clock = controller.retryState.retainedAt + voice.RETRY_TTL_MS + 1000;
  dispatchListeners(documentListeners, 'visibilitychange');
  assert.strictEqual(requestOptions.signal.aborted, true);
  assert.strictEqual(controller.requestGeneration, processingGeneration + 1);
  assert.strictEqual(controller.abortController, null);
  assert.strictEqual(controller.requestTimer, null);
  assert.strictEqual(controller.requestTimedOut, false);
  assert.strictEqual(controller.retryTimer, null);
  assert.strictEqual(controller.stopTimer, null);
  assert.strictEqual(controller.elapsedTimer, null);
  assert.strictEqual(controller.stream, null);
  assert.strictEqual(controller.recorder, null);
  assert.deepStrictEqual(controller.chunks, []);
  assert.strictEqual(controller.blob, null);
  assert.strictEqual(controller.startedAt, null);
  assert.strictEqual(controller.durationSeconds, null);
  assert.strictEqual(controller.state, 'failure');
  assert.strictEqual(controller.retryState.retryKind, 'new_recording');
  assert.strictEqual(voice.controllerTest.registry.active, null);
  assert.deepStrictEqual(buttonLabels(controller.panel), ['Record again', 'Not now']);
  assert.strictEqual(document.activeElement, outside);
  assert.strictEqual(outside.focusCount, 0);
  assert.strictEqual(timers.size, 0);
  const terminalGeneration = controller.requestGeneration;

  pending.resolve(lateResponse);
  await flushPromises();
  assert.strictEqual(controller.requestGeneration, terminalGeneration);
  assert.strictEqual(controller.state, 'failure');
  assert.strictEqual(controller.blob, null);
  assert.strictEqual(controller.proposal, undefined);
  assert.strictEqual(voice.controllerTest.registry.active, null);
}

async function controllerLifecycleTraces() {
  await traceInFlightExpiry(response(200, {
    success: true,
    proposal: {text: 'Late success must be ignored.'}
  }));
  await traceInFlightExpiry(response(503, {
    code: 'provider_timeout',
    message: 'Late failure must be ignored.',
    retry: 'same_recording',
    retryable: true
  }));

  resetControllerHarness();
  let parts = createController();
  document.activeElement = parts.input;
  global.fetch = () => Promise.resolve(response(200, {
    success: true,
    proposal: {text: 'Reviewable transcript.'}
  }));
  capture(parts.controller);
  parts.controller.transcribe();
  await flushPromises();
  assert.strictEqual(parts.controller.state, 'preview');
  assert.strictEqual(parts.controller.blob, null);
  assert.strictEqual(parts.controller.abortController, null);
  assert.strictEqual(parts.controller.requestTimer, null);
  assert.strictEqual(voice.controllerTest.registry.active, null);
  assert.strictEqual(timers.size, 0);

  resetControllerHarness();
  parts = createController();
  document.activeElement = parts.input;
  global.fetch = () => Promise.resolve(response(422, {
    code: 'no_speech',
    message: "We couldn't hear any words in that recording.",
    retry: 'new_recording',
    retryable: false
  }));
  capture(parts.controller);
  parts.controller.transcribe();
  await flushPromises();
  assert.strictEqual(parts.controller.state, 'failure');
  assert.strictEqual(parts.controller.blob, null);
  assert.strictEqual(parts.controller.retryState.retryKind, 'new_recording');
  assert.deepStrictEqual(buttonLabels(parts.controller.panel), ['Record again', 'Not now']);
  assert.strictEqual(voice.controllerTest.registry.active, null);
  assert.strictEqual(document.activeElement, parts.input);
  assert.strictEqual(timers.size, 0);

  resetControllerHarness();
  parts = createController();
  document.activeElement = parts.input;
  const cancelled = deferred();
  let cancelOptions;
  global.fetch = (_url, options) => {
    cancelOptions = options;
    return cancelled.promise;
  };
  capture(parts.controller);
  parts.controller.transcribe();
  await flushPromises();
  parts.controller.discard(false);
  assert.strictEqual(cancelOptions.signal.aborted, true);
  assert.strictEqual(parts.controller.state, 'ready');
  assert.strictEqual(parts.controller.blob, null);
  assert.strictEqual(parts.controller.requestTimer, null);
  assert.strictEqual(voice.controllerTest.registry.active, null);
  assert.strictEqual(timers.size, 0);
  cancelled.resolve(response(200, {success: true, proposal: {text: 'Stale.'}}));
  await flushPromises();
  assert.strictEqual(parts.controller.state, 'ready');
  assert.strictEqual(parts.controller.proposal, '');

  resetControllerHarness();
  parts = createController();
  document.activeElement = parts.input;
  capture(parts.controller);
  retainAfterTransientFailure(parts.controller);
  dispatchListeners(windowListeners, 'pagehide');
  assert.strictEqual(parts.controller.panel.isConnected, false);
  assert.strictEqual(parts.controller.blob, null);
  assert.strictEqual(parts.form._communityVoiceController, null);
  assert.strictEqual(voice.controllerTest.registry.controllers.length, 0);
  assert.strictEqual(voice.controllerTest.registry.active, null);

  resetControllerHarness();
  parts = createController();
  document.activeElement = parts.input;
  capture(parts.controller);
  retainAfterTransientFailure(parts.controller);
  parts.controller.panel.isConnected = false;
  voice.controllerTest.checkRetryWindows();
  assert.strictEqual(parts.controller.blob, null);
  assert.strictEqual(parts.form._communityVoiceController, null);
  assert.strictEqual(voice.controllerTest.registry.controllers.length, 0);
  assert.strictEqual(voice.controllerTest.registry.active, null);

  resetControllerHarness();
  parts = createController();
  document.activeElement = parts.input;
  capture(parts.controller);
  retainAfterTransientFailure(parts.controller);
  const deadline = parts.controller.retryState.retainedAt + voice.RETRY_TTL_MS;
  await runDueTimers(deadline + 1);
  assert.strictEqual(parts.controller.blob, null);
  assert.strictEqual(parts.controller.state, 'failure');
  assert.strictEqual(parts.controller.retryState.retryKind, 'new_recording');
  assert.strictEqual(voice.controllerTest.registry.active, null);

  resetControllerHarness();
  parts = createController();
  document.activeElement = parts.input;
  capture(parts.controller);
  retainAfterTransientFailure(parts.controller);
  clock = parts.controller.retryState.retainedAt + voice.RETRY_TTL_MS + 5000;
  dispatchListeners(windowListeners, 'pageshow');
  assert.strictEqual(parts.controller.blob, null);
  assert.strictEqual(parts.controller.retryState.retryKind, 'new_recording');
  assert.strictEqual(voice.controllerTest.registry.active, null);
  assert.strictEqual(document.activeElement, parts.input);
}

async function run() {
  const noSpeech = voice.normalizeFailure(422, {
    code: 'no_speech',
    message: "We couldn't hear any words in that recording.",
    retry: 'new_recording',
    retryable: false
  }, 1000, null);
  assert.strictEqual(noSpeech.retryKind, 'new_recording');
  assert.strictEqual(noSpeech.retryable, false);

  const typedUnavailable = voice.normalizeFailure(503, {
    code: 'transcription_unavailable',
    message: 'Unavailable.',
    retry: 'none',
    retryable: false
  }, 1000, null);
  assert.strictEqual(typedUnavailable.retryKind, 'none');

  const oldUnavailable = voice.normalizeFailure(503, {
    code: 'transcription_unavailable', message: 'Unavailable.', retryable: true
  }, 1000, null);
  assert.strictEqual(oldUnavailable.retryKind, 'same_recording');
  assert.strictEqual(voice.normalizeFailure(429, {
    code: 'voice_rate_limited', retryable: true
  }, 1000, null).retryKind, 'none');

  assert.strictEqual(voice.normalizeFailure(0, null, 1000, null).retryKind, 'same_recording');
  assert.strictEqual(voice.normalizeFailure(401, null, 1000, null).retryKind, 'none');
  assert.strictEqual(voice.normalizeFailure(404, null, 1000, null).retryKind, 'none');
  assert.strictEqual(voice.normalizeFailure(413, null, 1000, null).retryKind, 'new_recording');
  assert.strictEqual(voice.normalizeFailure(429, null, 1000, null).retryKind, 'none');
  assert.strictEqual(voice.normalizeFailure(422, null, 1000, null).retryKind, 'none');
  assert.strictEqual(voice.normalizeFailure(503, null, 1000, null).retryKind, 'same_recording');

  [undefined, null, 0, -1, 1.5, 301, '30'].forEach((wait) => {
    const normalized = voice.normalizeFailure(429, {
      code: 'voice_rate_limited', retry: 'same_recording', retry_after_seconds: wait
    }, 1000, null);
    assert.strictEqual(normalized.retryKind, 'none');
  });
  const boundedWait = voice.normalizeFailure(429, {
    code: 'voice_rate_limited', retry: 'same_recording', retry_after_seconds: 30
  }, 1000, null);
  assert.strictEqual(boundedWait.retryKind, 'same_recording');
  assert.strictEqual(boundedWait.retryAfterSeconds, 30);
  const overRemaining = voice.normalizeFailure(429, {
    code: 'voice_rate_limited', retry: 'same_recording', retry_after_seconds: 30
  }, 280000, 0);
  assert.strictEqual(overRemaining.retryKind, 'none');
  assert.strictEqual(voice.normalizeFailure(503, {
    code: 'provider_timeout', retry: 'same_recording', retry_after_seconds: 2
  }, 1000, null).retryKind, 'none');

  let requested;
  try {
    await voice.request((url, options) => {
      requested = {url, options};
      return Promise.resolve(response(503, {
        code: 'provider_timeout',
        message: 'Timed out.',
        retry: 'same_recording',
        retryable: true
      }));
    }, '/api/v1/community/voice/transcriptions', {method: 'POST'}, 1000, null);
    assert.fail('Expected the voice wrapper to reject a failed response.');
  } catch (error) {
    assert.strictEqual(error.code, 'provider_timeout');
    assert.strictEqual(error.retry, 'same_recording');
    assert.strictEqual(error.retryable, true);
  }
  assert.strictEqual(requested.url, '/api/v1/community/voice/transcriptions');
  assert.strictEqual(requested.options.headers['X-PeerSlate-Request'], 'same-origin');

  try {
    await voice.request(
      () => Promise.resolve(response(503, null, 'text/html')),
      '/api/v1/community/voice/transcriptions',
      {method: 'POST'},
      1000,
      null
    );
    assert.fail('Expected a non-JSON 5xx response to reject.');
  } catch (error) {
    assert.strictEqual(error.code, 'transcription_unavailable');
    assert.strictEqual(error.retry, 'same_recording');
  }
  try {
    await voice.request(
      () => { throw new TypeError('offline'); },
      '/api/v1/community/voice/transcriptions',
      {method: 'POST'},
      1000,
      null
    );
    assert.fail('Expected a network failure to reject.');
  } catch (error) {
    assert.strictEqual(error.code, 'upload_network');
    assert.strictEqual(error.retry, 'same_recording');
    assert.strictEqual(String(error).includes('offline'), false);
  }

  let state = voice.emptyRetryState(false);
  state = voice.transitionRetryState(state, 'captured', 1000);
  state = voice.transitionRetryState(state, 'failure', 2000, {retryKind: 'same_recording'});
  assert.deepStrictEqual(
    {
      hasAudio: state.hasAudio,
      retryCount: state.retryCount,
      retainedAt: state.retainedAt,
      holdsRegistry: state.holdsRegistry
    },
    {hasAudio: true, retryCount: 0, retainedAt: 2000, holdsRegistry: true}
  );
  assert.strictEqual(voice.canRetrySameRecording(state, 2000), true);
  state = voice.transitionRetryState(state, 'retry', 3000);
  assert.strictEqual(state.retryCount, 1);
  assert.strictEqual(voice.canRetrySameRecording(state, 3000), false);
  state = voice.transitionRetryState(state, 'failure', 4000, {retryKind: 'same_recording'});
  assert.strictEqual(state.hasAudio, false);
  assert.strictEqual(state.retryKind, 'new_recording');
  assert.strictEqual(state.holdsRegistry, false);

  let expiring = voice.transitionRetryState(
    voice.transitionRetryState(voice.emptyRetryState(false), 'captured', 0),
    'failure',
    5000,
    {retryKind: 'same_recording'}
  );
  assert.strictEqual(voice.canRetrySameRecording(expiring, 5000 + voice.RETRY_TTL_MS - 1), true);
  expiring = voice.transitionRetryState(expiring, 'expiry', 5000 + voice.RETRY_TTL_MS);
  assert.strictEqual(expiring.hasAudio, false);
  assert.strictEqual(expiring.retryKind, 'new_recording');

  await controllerLifecycleTraces();

  console.log('community_voice_retry.test.js: all assertions passed');
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
}).finally(() => {
  Date.now = realDateNow;
});

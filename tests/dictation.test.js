/* Shared dictation module — configurable-duration regression, PS-OPPORTUNITY-
 * SLATE-001 slice OS-5.
 *
 * Executes the real static/js/dictation.js in plain Node, the same way
 * tests/workshop_voice.test.js exercises static/js/workshop-voice.js —
 * tests/test_interview_studio.py runs this file by subprocess in the same
 * way tests/test_workshop_voice.py runs tests/workshop_voice.test.js. There
 * is no npm/jest harness in this repository.
 *
 * Scope, stated honestly: this drives the module's controller through a
 * configured (non-default) silenceMs and checks the announced/displayed
 * duration text is BUILT from that value, not a hardcoded "10 seconds"
 * literal — the exact bug named in the OS-5 handoff (a host that configured
 * a different duration would previously show copy that disagreed with its
 * own behaviour). It stubs the minimal window/document/navigator/
 * SpeechRecognition surface the module touches; it does not exercise real
 * speech recognition, browser timers at their real delay, or a DOM binding,
 * all of which need a browser and are out of scope here.
 */
'use strict';

const assert = require('node:assert/strict');

/* Minimal host globals — the smallest stand-in that lets the module's own
   browser-facing code run unmodified under Node. */
global.window = global;
global.document = {
    documentElement: { lang: 'en-US' },
    addEventListener: function () { }
};
/* Node 21+ ships its own read-only `navigator` global, so a plain assignment
   throws; redefine it the way the module needs — no mediaDevices, so the
   permission handshake resolves immediately instead of prompting. */
Object.defineProperty(global, 'navigator', { value: {}, configurable: true, writable: true });

/* A controllable fake SpeechRecognition. The module constructs one on every
   start() and assigns its own onstart/onresult/onend/onerror handlers onto
   it; each test invokes those handlers directly instead of waiting on real
   audio or real timers. */
const instances = [];
function FakeRecognition() {
    this.continuous = false;
    this.interimResults = false;
    this.lang = '';
    this.onstart = null;
    this.onresult = null;
    this.onerror = null;
    this.onend = null;
    instances.push(this);
}
FakeRecognition.prototype.start = function () { };
FakeRecognition.prototype.stop = function () { };
global.SpeechRecognition = FakeRecognition;

const dictation = require('../static/js/dictation.js');

function fakeButton() {
    return {
        classList: { add: function () { }, remove: function () { } },
        setAttribute: function () { },
        removeAttribute: function () { },
        disabled: false
    };
}
function fakeField(value) {
    return {
        value: value || '',
        selectionStart: (value || '').length,
        selectionEnd: (value || '').length,
        setSelectionRange: function (start, end) { this.selectionStart = start; this.selectionEnd = end; },
        dispatchEvent: function () { return true; }
    };
}

/* dictation.js's appendTranscript builds a DOM Event; Node has had a global
   Event constructor since v15, but this stands in exactly the way
   workshop_voice.test.js already does in case that ever changes. */
global.Event = global.Event || function (type) { this.type = type; };

const results = [];
function test(name, fn) {
    return Promise.resolve()
        .then(fn)
        .then(function () { results.push([true, name]); })
        .catch(function (error) {
            results.push([false, name + '\n    ' + ((error && error.stack) || error)]);
        });
}

/* Flushes the microtask queue. startDictation's permission handshake always
   resolves a Promise (even with no navigator.mediaDevices, it is
   Promise.resolve()), so beginDictation — and the SpeechRecognition
   construction inside it — runs one tick later. setImmediate is a macrotask,
   scheduled after every pending microtask drains. */
function flush() {
    return new Promise(function (resolve) { setImmediate(resolve); });
}

function finalResult(transcript) {
    var result = [{ transcript: transcript }];
    result.isFinal = true;
    return result;
}

async function run() {
    await test('the default 10-second contract is unchanged for a host that overrides nothing', async () => {
        const statuses = [];
        const announcements = [];
        const controller = dictation.createController({
            announce: function (message) { announcements.push(message); }
        });
        controller.register('k', {
            button: fakeButton(),
            resolveTarget: function () { return fakeField(''); },
            noun: 'answer',
            setStatus: function (message) { statuses.push(message); }
        });
        controller.start('k');
        await flush();
        const instance = instances[instances.length - 1];
        instance.onstart();
        assert.ok(
            statuses.indexOf('Listening. Stops after 10 seconds of silence, or press Escape.') !== -1,
            'expected the default 10-second status, saw: ' + JSON.stringify(statuses)
        );
        assert.ok(
            announcements.some(function (message) { return message.indexOf('silent for 10 seconds.') !== -1; }),
            'expected the default 10-second announcement, saw: ' + JSON.stringify(announcements)
        );
        controller.stop('manual');
    });

    await test('a configured silenceMs changes the announced duration, not just the timer', async () => {
        const statuses = [];
        const announcements = [];
        const controller = dictation.createController({
            announce: function (message) { announcements.push(message); },
            silenceMs: 5000
        });
        controller.register('k', {
            button: fakeButton(),
            resolveTarget: function () { return fakeField(''); },
            noun: 'answer',
            setStatus: function (message) { statuses.push(message); }
        });
        controller.start('k');
        await flush();
        const instance = instances[instances.length - 1];
        instance.onstart();
        assert.ok(
            statuses.indexOf('Listening. Stops after 5 seconds of silence, or press Escape.') !== -1,
            'expected a 5-second status, saw: ' + JSON.stringify(statuses)
        );
        assert.ok(
            !statuses.some(function (message) { return message && message.indexOf('10 seconds') !== -1; }),
            'the stale 10-second literal leaked into a controller configured for 5 seconds'
        );
        assert.ok(
            announcements.some(function (message) { return message.indexOf('silent for 5 seconds.') !== -1; }),
            'expected a 5-second announcement, saw: ' + JSON.stringify(announcements)
        );
        controller.stop('manual');
    });

    await test('the silence-stop announcement also names the configured duration', async () => {
        const announcements = [];
        const controller = dictation.createController({
            announce: function (message) { announcements.push(message); },
            silenceMs: 5000
        });
        controller.register('k', {
            button: fakeButton(),
            resolveTarget: function () { return fakeField(''); },
            noun: 'answer',
            setStatus: function () { }
        });
        controller.start('k');
        await flush();
        const instance = instances[instances.length - 1];
        instance.onstart();
        /* One final result so words > 0 — with nothing captured,
           finishDictation takes the "nothing heard" branch instead of ever
           naming the stop reason, and this test would pass for the wrong
           reason. */
        instance.onresult({ resultIndex: 0, results: [finalResult('testing one two')] });
        controller.stop('silence');
        assert.ok(
            announcements.some(function (message) {
                return message.indexOf('Dictation stopped after 5 seconds of silence.') !== -1;
            }),
            'expected the 5-second stop announcement, saw: ' + JSON.stringify(announcements)
        );
    });

    const failed = results.filter(function (row) { return !row[0]; });
    results.forEach(function (row) { console.log((row[0] ? 'ok   ' : 'FAIL ') + row[1]); });
    console.log('\n' + (results.length - failed.length) + '/' + results.length + ' passed');
    if (failed.length) process.exit(1);
}

run();

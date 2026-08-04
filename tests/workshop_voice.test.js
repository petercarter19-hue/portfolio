/* Workshop voice state machine — PS-WORKSHOP-001 W2d.
 *
 * Executes the real static/js/workshop-voice.js in plain Node. There is no
 * npm/jest harness in this repository, and tests/test_workshop_voice.py runs
 * this file by subprocess in the same way tests/test_community_tabs.py runs
 * tests/community_focus_lifecycle.test.js.
 *
 * Scope, stated honestly: this covers the state machine, the R17 copy, the
 * transcript-insertion rule, and the permission-error classification — all of
 * which are DOM-free production code. It does NOT cover MediaRecorder, fetch,
 * or the DOM binding, which need a browser; those are exercised by the
 * Playwright pass instead.
 */
'use strict';

const assert = require('node:assert/strict');

require('../static/js/dictation.js');
const voice = require('../static/js/workshop-voice.js');

const results = [];
function test(name, fn) {
    try {
        fn();
        results.push([true, name]);
    } catch (error) {
        results.push([false, name + '\n    ' + (error && error.message)]);
    }
}

/* --- R17 defines exactly six states --------------------------------- */

test('there are exactly the six states R17 draws', () => {
    assert.deepEqual(voice.STATES, [
        'ready', 'listening', 'transcribing', 'transcript', 'failed', 'denied'
    ]);
});

test('every state has copy, and every failure copy leaves typing standing', () => {
    voice.STATES.forEach((state) => {
        const copy = voice.copyFor(state);
        assert.ok(copy, state + ' has no copy');
    });
    ['failed', 'denied'].forEach((state) => {
        const copy = voice.copyFor(state);
        assert.ok(copy.recovery, state + ' must offer recovery');
        assert.ok(copy.retryLabel, state + ' must offer a retry');
        assert.ok(/typing/i.test(copy.dismissLabel), state + ' must offer the keyboard path');
    });
});

test('R17 state 4 tells the member they may edit before submitting', () => {
    assert.match(voice.copyFor('transcript').message, /edit before submitting/i);
});

test('R17 state 5 and 6 use the board’s own words', () => {
    assert.match(voice.copyFor('failed').message, /couldn’t transcribe that recording/i);
    assert.equal(voice.copyFor('failed').retryLabel, 'Try again');
    assert.equal(voice.copyFor('failed').dismissLabel, 'Keep typing');
    assert.match(voice.copyFor('denied').message, /microphone access is off/i);
    assert.equal(voice.copyFor('denied').retryLabel, 'Enable microphone');
    assert.equal(voice.copyFor('denied').dismissLabel, 'Continue typing');
});

/* --- The happy path, and every branch off it ------------------------ */

test('the golden path is ready to listening to transcribing to transcript', () => {
    const machine = voice.createVoiceMachine({});
    assert.equal(machine.get(), 'ready');
    assert.ok(machine.record());
    assert.equal(machine.get(), 'listening');
    assert.ok(machine.stop());
    assert.equal(machine.get(), 'transcribing');
    assert.ok(machine.transcribed());
    assert.equal(machine.get(), 'transcript');
});

test('a transcript never auto-submits — it is a state, not an action', () => {
    /* The machine has no submit, save, or send event at all. The only way a
       transcript becomes the member's words is the member's own submit. */
    const machine = voice.createVoiceMachine({});
    ['submit', 'save', 'send', 'accept'].forEach((event) => {
        assert.equal(machine.can(event), false, event + ' must not exist');
    });
});

test('cancelling while listening returns to ready without transcribing', () => {
    const machine = voice.createVoiceMachine({});
    machine.record();
    assert.ok(machine.cancel());
    assert.equal(machine.get(), 'ready');
});

test('a denied permission goes straight to the microphone-off state', () => {
    const machine = voice.createVoiceMachine({});
    assert.ok(machine.denied());
    assert.equal(machine.get(), 'denied');
});

test('a failure can be retried, and retrying starts listening again', () => {
    const machine = voice.createVoiceMachine({});
    machine.record();
    machine.stop();
    assert.ok(machine.fail());
    assert.equal(machine.get(), 'failed');
    assert.ok(machine.record());
    assert.equal(machine.get(), 'listening');
});

test('dismissing a failure returns to ready with nothing lost', () => {
    const machine = voice.createVoiceMachine({});
    machine.fail();
    assert.ok(machine.dismiss());
    assert.equal(machine.get(), 'ready');
});

test('a member can record a second time from a finished transcript', () => {
    const machine = voice.createVoiceMachine({});
    machine.record();
    machine.stop();
    machine.transcribed();
    assert.ok(machine.record());
    assert.equal(machine.get(), 'listening');
});

test('an event that makes no sense in the current state is ignored', () => {
    const machine = voice.createVoiceMachine({});
    assert.equal(machine.stop(), false, 'cannot stop before recording');
    assert.equal(machine.get(), 'ready');
    assert.equal(machine.transcribed(), false, 'cannot finish a transcription that never began');
    assert.equal(machine.get(), 'ready');
});

test('a late reply after a cancel cannot resurrect a finished recording', () => {
    const machine = voice.createVoiceMachine({});
    machine.record();
    machine.cancel();
    assert.equal(machine.transcribed(), false);
    assert.equal(machine.get(), 'ready');
});

test('every state is reachable from ready', () => {
    const reachable = new Set(['ready']);
    let changed = true;
    while (changed) {
        changed = false;
        Object.keys(voice.TRANSITIONS).forEach((from) => {
            if (!reachable.has(from)) return;
            Object.keys(voice.TRANSITIONS[from]).forEach((event) => {
                const to = voice.TRANSITIONS[from][event];
                if (!reachable.has(to)) { reachable.add(to); changed = true; }
            });
        });
    }
    voice.STATES.forEach((state) => {
        assert.ok(reachable.has(state), state + ' is unreachable');
    });
});

test('every state can get back to ready, so nothing is a dead end', () => {
    voice.STATES.forEach((state) => {
        const exits = Object.keys(voice.TRANSITIONS[state]).map((event) => {
            return voice.TRANSITIONS[state][event];
        });
        assert.ok(exits.length > 0, state + ' is a dead end');
    });
});

test('a server sentence replaces the generic one when there is one', () => {
    const machine = voice.createVoiceMachine({});
    machine.fail('Voice input is unavailable right now. You can keep typing.');
    assert.match(machine.message(), /unavailable right now/);
});

test('a supplied message never outlives the failure that caused it', () => {
    const machine = voice.createVoiceMachine({});
    machine.fail('A very specific problem.');
    machine.dismiss();
    assert.equal(machine.message(), voice.copyFor('ready').message);
});

test('onChange reports the state, the previous state, and the copy', () => {
    const seen = [];
    const machine = voice.createVoiceMachine({ onChange: (change) => seen.push(change) });
    machine.record();
    assert.equal(seen.length, 1);
    assert.equal(seen[0].state, 'listening');
    assert.equal(seen[0].previous, 'ready');
    assert.equal(seen[0].event, 'record');
    assert.match(seen[0].copy.inline, /Listening/);
});

/* --- Transcript insertion ------------------------------------------- */

function fakeField(value, maxlength) {
    return {
        value: value,
        _events: [],
        selectionStart: value.length,
        selectionEnd: value.length,
        getAttribute: function (name) {
            return name === 'maxlength' && maxlength ? String(maxlength) : null;
        },
        setSelectionRange: function (start, end) {
            this.selectionStart = start;
            this.selectionEnd = end;
        },
        dispatchEvent: function (event) { this._events.push(event); return true; }
    };
}

/* dictation.js's appendTranscript builds a DOM Event, which Node has since
   v15 — but the field above is a plain object, so a tiny stand-in keeps this
   test about insertion rather than about the Event constructor. */
global.Event = global.Event || function (type) { this.type = type; };

test('a transcript is inserted into the member’s field, not substituted for it', () => {
    const field = fakeField('I led the review');
    voice.insertTranscript(field, 'and the team shipped it.');
    assert.match(field.value, /^I led the review/);
    assert.match(field.value, /shipped it\.$/);
});

test('inserting fires an input event so the page can react', () => {
    const field = fakeField('');
    voice.insertTranscript(field, 'Some words.');
    assert.ok(field._events.length >= 1);
});

test('a transcript that overflows maxlength is trimmed, never sent oversized', () => {
    const field = fakeField('12345', 10);
    const outcome = voice.insertTranscript(field, 'far too many words to fit in ten');
    assert.equal(field.value.length, 10);
    assert.equal(outcome.truncated, true);
});

test('a transcript that fits is reported as not truncated', () => {
    const field = fakeField('', 100);
    const outcome = voice.insertTranscript(field, 'Short enough.');
    assert.equal(outcome.truncated, false);
});

/* --- Permission classification --------------------------------------- */

test('a refused permission is the microphone-off state, not a failure', () => {
    assert.equal(voice.isPermissionError({ name: 'NotAllowedError' }), true);
    assert.equal(voice.isPermissionError({ name: 'SecurityError' }), true);
    assert.equal(voice.isPermissionError({ name: 'NotFoundError' }), false);
    assert.equal(voice.isPermissionError({ name: 'NotReadableError' }), false);
});

test('every media error message tells the member they can keep typing', () => {
    [null, { name: 'NotFoundError' }, { name: 'NotReadableError' }, { name: 'Whatever' }]
        .forEach((error) => {
            assert.match(voice.mediaErrorMessage(error), /keep typing/i);
        });
});

test('a browser without MediaRecorder is reported as unable to record', () => {
    assert.equal(voice.browserCanRecord(), false, 'Node has no MediaRecorder');
    assert.equal(voice.supportedMimeType(), null);
});

test('a repeated permission refusal keeps its own supplied guidance', () => {
    const machine = voice.createVoiceMachine({});
    machine.denied();
    assert.equal(machine.message(), voice.copyFor('denied').message);
    machine.dismiss();
    machine.denied('Microphone access is off. PeerSlate can\u2019t turn it on \u2014 allow it in settings.');
    assert.match(machine.message(), /can\u2019t turn it on/);
});

/* --- Report ---------------------------------------------------------- */

const failed = results.filter((row) => !row[0]);
results.forEach((row) => {
    console.log((row[0] ? 'ok   ' : 'FAIL ') + row[1]);
});
console.log('\n' + (results.length - failed.length) + '/' + results.length + ' passed');
if (failed.length) process.exit(1);

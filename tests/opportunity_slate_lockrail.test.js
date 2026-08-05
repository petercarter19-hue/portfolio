/* lockRail vs. a permanently-unavailable mic — PS-OPPORTUNITY-SLATE-001
 * slice OS-5 fix-up.
 *
 * opportunity-slate.js has no CommonJS export (unlike dictation.js and
 * workshop-voice.js, both written to run under Node as well as a browser):
 * it is a bare IIFE that registers real document/window listeners the
 * moment it loads, so it cannot be required() the way those two are.
 * Rather than assert about its source text alone for a fix this specific,
 * this extracts the real, unmodified lockRail function body straight out of
 * the shipped file by brace-depth counting and executes it against a
 * minimal fake DOM — genuine behavioural coverage of the production code,
 * not a reimplementation of it, without inventing a module system this
 * file was never written to use.
 *
 * The bug: disableUnsupportedMics ran once at init (no SpeechRecognition in
 * this browser), setting a mic's disabled/aria-disabled/is-unavailable
 * state — and lockRail's own unlock path then unconditionally cleared
 * aria-disabled and re-enabled every [data-os-rail-control] element,
 * including that mic, the moment a member pressed Cancel after any locking
 * request. The fix makes lockRail skip any .is-unavailable control
 * entirely, on both the locking AND the unlocking call, so its truthful
 * inert state survives every cycle, not just the render that first set it.
 */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const source = fs.readFileSync(
    path.join(__dirname, '..', 'static', 'js', 'opportunity-slate.js'),
    'utf8'
);

/* `sentinels`, when given, must each appear literally in the extracted body
   before it is ever handed to `new Function`. Without this, extracting the
   WRONG function (a stale marker string, an earlier same-named helper) or
   over/under-running the brace-depth counter past the real end of the
   intended function both tend to still produce syntactically valid
   JavaScript — `new Function` would happily construct it, and the tests
   below would either throw a confusing unrelated error deep inside a
   fake-DOM call, or (worse) silently pass or fail while exercising code
   that was never lockRail at all. A missing sentinel fails loudly, at the
   extraction site, naming exactly what is missing. */
function extractFunction(name, sentinels) {
    const marker = 'function ' + name + '(';
    const start = source.indexOf(marker);
    if (start === -1) throw new Error('could not find function ' + name);
    const paramsEnd = source.indexOf(')', start);
    const params = source
        .slice(start + marker.length, paramsEnd)
        .split(',')
        .map((each) => each.trim())
        .filter(Boolean);
    const bodyStart = source.indexOf('{', paramsEnd) + 1;
    let depth = 1;
    let i = bodyStart;
    while (depth > 0) {
        if (source[i] === '{') depth += 1;
        else if (source[i] === '}') depth -= 1;
        i += 1;
    }
    const body = source.slice(bodyStart, i - 1);
    (sentinels || []).forEach((sentinel) => {
        if (body.indexOf(sentinel) === -1) {
            throw new Error(
                'extractFunction(' + name + '): the extracted body (' +
                    body.length + ' characters) does not contain "' + sentinel +
                    '" — this looks like the wrong function was matched, or the ' +
                    'brace-depth counter ran past (or stopped short of) the real ' +
                    'end of ' + name + '(). Check the marker and re-run.'
            );
        }
    });
    // eslint-disable-next-line no-new-func
    return new Function(params.join(','), body);
}

const lockRail = extractFunction('lockRail', ['is-unavailable', 'aria-disabled']);

function fakeControl(overrides) {
    const classes = new Set((overrides && overrides.classes) || []);
    return Object.assign(
        {
            disabled: false,
            _attrs: {},
            classList: {
                contains: (name) => classes.has(name),
                add: (name) => classes.add(name),
                remove: (name) => classes.delete(name)
            },
            setAttribute(name, value) {
                this._attrs[name] = value;
            },
            getAttribute(name) {
                return Object.prototype.hasOwnProperty.call(this._attrs, name)
                    ? this._attrs[name]
                    : null;
            }
        },
        overrides || {}
    );
}

/* disableUnsupportedMics' own real effect on a mic: aria-disabled true,
   .disabled true, is-unavailable class added. Built by hand here (not by
   calling that function) because it is the STARTING state this test needs
   to hold constant across a lock/unlock cycle, not the thing under test. */
function unavailableMic() {
    const mic = fakeControl({ classes: ['os-mic', 'is-unavailable'] });
    mic.disabled = true;
    mic.setAttribute('aria-disabled', 'true');
    return mic;
}

function fakeNode(controls) {
    return {
        querySelectorAll(selector) {
            if (selector === '[data-os-rail-control]') return controls;
            return [];
        },
        querySelector() {
            return null;
        }
    };
}

const results = [];
function test(name, fn) {
    try {
        fn();
        results.push([true, name]);
    } catch (error) {
        results.push([false, name + '\n    ' + (error && error.stack)]);
    }
}

test('an unavailable mic is untouched by a lock', () => {
    const mic = unavailableMic();
    const node = fakeNode([mic]);
    lockRail(node, true);
    assert.equal(mic.disabled, true);
    assert.equal(mic.getAttribute('aria-disabled'), 'true');
});

test('an unavailable mic is untouched by an unlock — the actual bug', () => {
    const mic = unavailableMic();
    const node = fakeNode([mic]);
    lockRail(node, true);
    lockRail(node, false);
    assert.equal(
        mic.disabled,
        true,
        'lockRail(node, false) re-enabled a permanently unsupported mic'
    );
    assert.equal(
        mic.getAttribute('aria-disabled'),
        'true',
        'lockRail(node, false) cleared aria-disabled on a permanently unsupported mic'
    );
});

test('a full lock-then-unlock cycle still leaves it exactly as disableUnsupportedMics set it', () => {
    const mic = unavailableMic();
    const node = fakeNode([mic]);
    for (let cycle = 0; cycle < 3; cycle += 1) {
        lockRail(node, true);
        lockRail(node, false);
    }
    assert.equal(mic.disabled, true);
    assert.equal(mic.getAttribute('aria-disabled'), 'true');
    assert.equal(mic.classList.contains('is-unavailable'), true);
});

test('an ordinary (available) control still locks and unlocks normally', () => {
    const textarea = fakeControl();
    const node = fakeNode([textarea]);
    lockRail(node, true);
    assert.equal(textarea.disabled, true);
    assert.equal(textarea.getAttribute('aria-disabled'), 'true');
    lockRail(node, false);
    assert.equal(
        textarea.disabled,
        false,
        'the is-unavailable skip must not also freeze ordinary controls'
    );
    assert.equal(textarea.getAttribute('aria-disabled'), 'false');
});

test('a mixed rail locks/unlocks the available control and holds the unavailable one', () => {
    const mic = unavailableMic();
    const textarea = fakeControl();
    const node = fakeNode([textarea, mic]);
    lockRail(node, true);
    assert.equal(textarea.disabled, true);
    assert.equal(mic.disabled, true);
    lockRail(node, false);
    assert.equal(textarea.disabled, false, 'the available control must unlock');
    assert.equal(mic.disabled, true, 'the unavailable mic must not');
    assert.equal(mic.getAttribute('aria-disabled'), 'true');
});

const failed = results.filter((row) => !row[0]);
results.forEach((row) => { console.log((row[0] ? 'ok   ' : 'FAIL ') + row[1]); });
console.log('\n' + (results.length - failed.length) + '/' + results.length + ' passed');
if (failed.length) process.exit(1);

/* PeerSlate Workshop voice input — PS-WORKSHOP-001 W2d.
 *
 * Visual authority: R17-voice-input-state-board-facelift.png (six states).
 *
 * Strictly additive. Every Workshop flow is complete server-rendered HTML
 * before this file runs: the textarea, the submit button, and the form post
 * all work with no JavaScript, no microphone, and no permission. If this
 * module never loads, or MediaRecorder is missing, the mic simply is not
 * there — nothing else changes.
 *
 * The load-bearing trust property is state 4. A transcript is a PROPOSAL: it
 * lands in the field the member can see and correct, and becomes their words
 * only when they submit that field themselves. This module never submits a
 * form, never saves, and never makes anything canonical.
 *
 * Recording goes to PeerSlate's own endpoint, which hands it to the released
 * Azure Speech adapter and keeps the transcript only (see
 * services/workshop_voice_service.py for exactly what is and is not
 * retained). That is a different path from static/js/dictation.js, which is
 * browser-local Web Speech recognition for Interview Studio — that one
 * streams text in live and so has no "transcribing" step and no moment where
 * a finished transcript sits editable before submission. R17 requires both,
 * so Workshop records and then transcribes. The one thing borrowed from
 * dictation.js is appendTranscript, so caret and spacing behaviour is
 * identical in both rooms rather than reimplemented differently here.
 *
 * The state machine below is deliberately free of DOM, timers, and network,
 * so tests/workshop_voice.test.js executes the real production transitions
 * in plain Node rather than asserting about them through a browser mock.
 */
(function (root, factory) {
    'use strict';

    var api = factory();
    if (typeof module === 'object' && module.exports) { module.exports = api; }
    root.PeerSlateWorkshopVoice = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    /* ---------------------------------------------------------------
       The six states of R17, and nothing else.
       --------------------------------------------------------------- */

    var READY = 'ready';
    var LISTENING = 'listening';
    var TRANSCRIBING = 'transcribing';
    var TRANSCRIPT = 'transcript';
    var FAILED = 'failed';
    var DENIED = 'denied';

    var STATES = [READY, LISTENING, TRANSCRIBING, TRANSCRIPT, FAILED, DENIED];

    /* An explicit table rather than scattered conditionals: an event that is
       not listed for a state is ignored, which is what makes a late network
       reply or a double click harmless instead of a state nobody designed.

       'record' from TRANSCRIPT is how a member speaks a second time — their
       first transcript stays in the field and the new speech appends to it,
       because both are their words. */
    var TRANSITIONS = {};
    TRANSITIONS[READY] = { record: LISTENING, denied: DENIED, fail: FAILED };
    TRANSITIONS[LISTENING] = { stop: TRANSCRIBING, cancel: READY, fail: FAILED, denied: DENIED };
    TRANSITIONS[TRANSCRIBING] = { transcribed: TRANSCRIPT, fail: FAILED, cancel: READY };
    TRANSITIONS[TRANSCRIPT] = { record: LISTENING, denied: DENIED, fail: FAILED, dismiss: READY };
    TRANSITIONS[FAILED] = { record: LISTENING, dismiss: READY, denied: DENIED };
    TRANSITIONS[DENIED] = { record: LISTENING, dismiss: READY, fail: FAILED };

    function nextState(state, event) {
        var allowed = TRANSITIONS[state];
        if (!allowed) return null;
        return Object.prototype.hasOwnProperty.call(allowed, event) ? allowed[event] : null;
    }

    /* ---------------------------------------------------------------
       Copy. R17's own words, kept in one place so the six states read the
       same on every screen. Every failure sentence leaves the keyboard
       path standing, because it is always still there.
       --------------------------------------------------------------- */

    var COPY = {};
    COPY[READY] = { inline: '', message: '', recovery: false };
    COPY[LISTENING] = { inline: 'Listening…', message: 'Listening. Select stop when you have finished.', recovery: false };
    COPY[TRANSCRIBING] = { inline: 'Transcribing…', message: 'Transcribing what you said.', recovery: false };
    COPY[TRANSCRIPT] = { inline: '', message: 'You can edit before submitting.', recovery: false };
    COPY[FAILED] = {
        inline: '',
        message: 'We couldn’t transcribe that recording.',
        recovery: true,
        retryLabel: 'Try again',
        dismissLabel: 'Keep typing'
    };
    COPY[DENIED] = {
        inline: '',
        message: 'Microphone access is off.',
        recovery: true,
        retryLabel: 'Enable microphone',
        dismissLabel: 'Continue typing'
    };

    function copyFor(state) {
        return COPY[state] || COPY[READY];
    }

    /* Denied is the browser telling us the member said no, or that the site
       has no permission to ask. Everything else is a failure we describe
       plainly instead of blaming the member's microphone settings for. */
    function isPermissionError(error) {
        if (!error) return false;
        return error.name === 'NotAllowedError' || error.name === 'SecurityError';
    }

    function mediaErrorMessage(error) {
        if (!error) return 'The microphone is unavailable. You can keep typing.';
        if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
            return 'No microphone was found. You can keep typing.';
        }
        if (error.name === 'NotReadableError') {
            return 'Another application may be using the microphone. You can keep typing.';
        }
        return 'The microphone could not be started. You can keep typing.';
    }

    /* ---------------------------------------------------------------
       The machine. No DOM, no timers, no network.
       --------------------------------------------------------------- */

    function createVoiceMachine(options) {
        var settings = options || {};
        var onChange = typeof settings.onChange === 'function' ? settings.onChange : function () { };
        var state = READY;
        /* A message the caller supplied for this particular failure (an
           honest server sentence, say) rather than the generic R17 line. It
           is cleared on every transition so it can never outlive its cause. */
        var detail = '';

        function send(event, payload) {
            var target = nextState(state, event);
            if (target === null) return false;
            var previous = state;
            state = target;
            detail = (payload && payload.message) || '';
            onChange({
                state: state,
                previous: previous,
                event: event,
                message: detail || copyFor(state).message,
                copy: copyFor(state)
            });
            return true;
        }

        return {
            get: function () { return state; },
            message: function () { return detail || copyFor(state).message; },
            can: function (event) { return nextState(state, event) !== null; },
            send: send,
            record: function () { return send('record'); },
            stop: function () { return send('stop'); },
            cancel: function () { return send('cancel'); },
            transcribed: function () { return send('transcribed'); },
            fail: function (message) { return send('fail', { message: message }); },
            denied: function (message) { return send('denied', { message: message }); },
            dismiss: function () { return send('dismiss'); }
        };
    }

    /* ---------------------------------------------------------------
       Transcript insertion.
       --------------------------------------------------------------- */

    /* maxlength stops a person typing past the limit; it does NOT stop a
       script assigning past it. Inserting a transcript that overflows would
       silently hand the server more than it accepts, so the overflow is
       trimmed here and the member is told rather than discovering it at
       submit time. */
    function insertTranscript(field, transcript, append) {
        var appendFn = append || (root_appendTranscript());
        var limit = parseInt(field.getAttribute('maxlength') || '', 10);
        var before = field.value;
        appendFn(field, transcript);
        if (!(limit > 0) || field.value.length <= limit) return { truncated: false };
        field.value = field.value.slice(0, limit);
        if (typeof field.setSelectionRange === 'function') {
            field.setSelectionRange(field.value.length, field.value.length);
        }
        field.dispatchEvent(new Event('input', { bubbles: true }));
        return { truncated: true, kept: field.value.length - before.length };
    }

    function root_appendTranscript() {
        var shared = typeof globalThis !== 'undefined' ? globalThis.PeerSlateDictation : null;
        if (shared && typeof shared.appendTranscript === 'function') return shared.appendTranscript;
        /* dictation.js is loaded alongside this file on every Workshop page
           that renders a mic. Reaching here means it did not load, so rather
           than a second insertion behaviour that would drift from the shared
           one, do the simplest correct thing and let it be obviously
           different. */
        return function (field, text) {
            field.value = field.value ? field.value + ' ' + text : text;
            field.dispatchEvent(new Event('input', { bubbles: true }));
        };
    }

    /* ---------------------------------------------------------------
       DOM binding. Browser only.
       --------------------------------------------------------------- */

    var PREFERRED_TYPES = ['audio/webm', 'audio/ogg', 'audio/mp4'];

    function supportedMimeType() {
        if (typeof MediaRecorder === 'undefined') return null;
        for (var index = 0; index < PREFERRED_TYPES.length; index += 1) {
            if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(PREFERRED_TYPES[index])) {
                return PREFERRED_TYPES[index];
            }
        }
        return null;
    }

    function browserCanRecord() {
        return Boolean(
            typeof navigator !== 'undefined' &&
            navigator.mediaDevices &&
            typeof navigator.mediaDevices.getUserMedia === 'function' &&
            typeof MediaRecorder !== 'undefined' &&
            typeof FormData !== 'undefined' &&
            typeof fetch === 'function'
        );
    }

    function bind(container, document_) {
        var doc = document_ || document;
        var fieldId = container.getAttribute('data-wk-voice-for');
        var field = doc.getElementById(fieldId);
        var micButton = container.querySelector('[data-wk-voice-mic]');
        var cancelButton = container.querySelector('[data-wk-voice-cancel]');
        var inlineLabel = container.querySelector('[data-wk-voice-inline-label]');
        var statusBox = doc.querySelector('[data-wk-voice-status-for="' + fieldId + '"]');
        var messageLine = statusBox && statusBox.querySelector('[data-wk-voice-message]');
        var recovery = statusBox && statusBox.querySelector('[data-wk-voice-recovery]');
        var retryButton = statusBox && statusBox.querySelector('[data-wk-voice-retry]');
        var dismissButton = statusBox && statusBox.querySelector('[data-wk-voice-dismiss]');
        var noun = container.getAttribute('data-wk-voice-noun') || 'answer';
        var endpoint = container.getAttribute('data-wk-voice-endpoint');

        if (!field || !micButton || !endpoint) return null;

        /* No false affordance: a browser that cannot record never shows a
           control that cannot work. The field and its submit stay exactly as
           the server rendered them. */
        if (!browserCanRecord()) {
            container.hidden = true;
            if (statusBox) statusBox.hidden = true;
            return null;
        }

        var maxSeconds = parseInt(container.getAttribute('data-wk-voice-max-seconds') || '90', 10);
        var submitSelector = statusBox && statusBox.getAttribute('data-wk-voice-submit');
        var submitControl = submitSelector ? doc.querySelector(submitSelector) : null;

        var recorder = null;
        var stream = null;
        var chunks = [];
        var startedAt = 0;
        var limitTimer = null;
        var cancelled = false;
        var deniedAttempts = 0;

        var machine = createVoiceMachine({ onChange: render });

        function render(change) {
            var state = change.state;
            var copy = change.copy;
            container.setAttribute('data-wk-voice-state', state);
            if (statusBox) statusBox.setAttribute('data-wk-voice-state', state);
            if (inlineLabel) inlineLabel.textContent = copy.inline || '';
            if (messageLine) messageLine.textContent = change.message || '';
            micButton.setAttribute('aria-pressed', state === LISTENING ? 'true' : 'false');
            micButton.setAttribute(
                'aria-label',
                state === LISTENING ? 'Stop recording' : 'Speak your ' + noun
            );
            /* Nothing to press while the recording is in flight, but the
               button keeps its place in the tab order rather than vanishing
               under the member's focus.

               This assignment is also what ENABLES the mic for the first
               time: the server renders it disabled and honestly labelled,
               because a live-looking mic is a promise only the script can
               keep. bind() calls render() once at the end, so the control
               becomes real exactly when something exists to make it work. */
            micButton.disabled = state === TRANSCRIBING;
            if (state === TRANSCRIBING) {
                micButton.setAttribute('aria-disabled', 'true');
            } else {
                micButton.removeAttribute('aria-disabled');
            }
            if (cancelButton) cancelButton.hidden = state !== LISTENING;
            if (recovery) recovery.hidden = !copy.recovery;
            if (retryButton && copy.retryLabel) retryButton.textContent = copy.retryLabel;
            if (dismissButton && copy.dismissLabel) dismissButton.textContent = copy.dismissLabel;
            /* R17 state 4 emphasises the submit control once there is a
               transcript to send. Presentation only — it is the same button
               doing the same thing. */
            if (submitControl) {
                submitControl.classList.toggle('wk-voice-ready', state === TRANSCRIPT);
            }
        }

        function releaseMicrophone() {
            if (limitTimer) { clearTimeout(limitTimer); limitTimer = null; }
            if (stream) {
                stream.getTracks().forEach(function (track) { track.stop(); });
                stream = null;
            }
            recorder = null;
        }

        function failWith(message) {
            releaseMicrophone();
            machine.fail(message);
        }

        function start() {
            if (machine.get() === LISTENING) { stopRecording(); return; }
            if (!machine.can('record')) return;
            var mimeType = supportedMimeType();
            if (!mimeType) {
                machine.fail('This browser’s recording format isn’t supported. You can keep typing.');
                return;
            }
            cancelled = false;
            navigator.mediaDevices.getUserMedia({ audio: true, video: false }).then(function (granted) {
                stream = granted;
                chunks = [];
                recorder = new MediaRecorder(granted, { mimeType: mimeType });
                recorder.ondataavailable = function (event) {
                    if (event.data && event.data.size) chunks.push(event.data);
                };
                recorder.onstop = function () {
                    var seconds = Math.max(0.1, (Date.now() - startedAt) / 1000);
                    var blob = new Blob(chunks, { type: mimeType });
                    releaseMicrophone();
                    if (cancelled) return;
                    upload(blob, seconds);
                };
                recorder.onerror = function () {
                    failWith('The recording stopped unexpectedly. You can try again, or keep typing.');
                };
                startedAt = Date.now();
                recorder.start();
                machine.record();
                /* A hard client-side stop at the same ceiling the server
                   enforces, so a forgotten recording ends by itself instead
                   of being refused after the fact. */
                limitTimer = setTimeout(function () {
                    if (machine.get() === LISTENING) stopRecording();
                }, maxSeconds * 1000);
            }).catch(function (error) {
                releaseMicrophone();
                if (isPermissionError(error)) {
                    /* "Enable microphone" cannot grant permission — no page
                       can. Retrying is still right, because a member who has
                       since allowed it in site settings gets straight back
                       to work. But if the refusal repeats, saying only
                       "Microphone access is off" again would leave them
                       pressing a control that looks broken, so the second
                       time it says where the switch actually is. */
                    deniedAttempts += 1;
                    machine.denied(
                        deniedAttempts > 1
                            ? 'Microphone access is off. PeerSlate can’t turn it on — allow the ' +
                              'microphone for this site in your browser’s settings, then choose ' +
                              'Enable microphone again. Typing works either way.'
                            : ''
                    );
                    return;
                }
                machine.fail(mediaErrorMessage(error));
            });
        }

        function stopRecording() {
            if (machine.get() !== LISTENING) return;
            machine.stop();
            try {
                if (recorder && recorder.state !== 'inactive') recorder.stop();
                else releaseMicrophone();
            } catch (error) {
                failWith('The recording could not be finished. You can try again, or keep typing.');
            }
        }

        function cancelRecording() {
            if (machine.get() !== LISTENING) return;
            cancelled = true;
            try {
                if (recorder && recorder.state !== 'inactive') recorder.stop();
            } catch (error) { /* releasing below is what matters */ }
            releaseMicrophone();
            machine.cancel();
            field.focus();
        }

        function upload(blob, seconds) {
            var payload = new FormData();
            payload.append('audio', blob, 'recording');
            payload.append('duration_seconds', String(seconds));
            fetch(endpoint, {
                method: 'POST',
                body: payload,
                credentials: 'same-origin',
                headers: { 'Accept': 'application/json' }
            }).then(function (response) {
                return response.json().catch(function () { return {}; }).then(function (body) {
                    return { ok: response.ok, body: body };
                });
            }).then(function (result) {
                if (!result.ok || !result.body || !result.body.transcript) {
                    machine.fail((result.body && result.body.message) || '');
                    return;
                }
                var outcome = insertTranscript(field, String(result.body.transcript));
                machine.transcribed();
                if (outcome.truncated && messageLine) {
                    messageLine.textContent =
                        'Your ' + noun + ' reached its length limit, so the end of that recording ' +
                        'was not added. You can edit before submitting.';
                }
                /* Focus follows the work: the member's next action is to read
                   and correct their own words, which happens in the field. */
                field.focus();
            }).catch(function () {
                /* A network failure is not a transcription failure, but from
                   the member's side it is the same fact and the same two
                   choices, so it renders as R17 state 5 with its own words. */
                machine.fail('We couldn’t reach voice input just now. You can try again, or keep typing.');
            });
        }

        /* Paint the ready state once at bind time. onChange only fires on a
           TRANSITION, so without this the control keeps whatever the server
           rendered until the member's first click — which is how Cancel was
           visible in state 1. */
        render({ state: READY, previous: READY, event: 'init', message: '', copy: copyFor(READY) });

        micButton.addEventListener('click', function () {
            if (machine.get() === LISTENING) stopRecording();
            else start();
        });
        if (cancelButton) cancelButton.addEventListener('click', cancelRecording);
        if (retryButton) retryButton.addEventListener('click', start);
        if (dismissButton) {
            dismissButton.addEventListener('click', function () {
                machine.dismiss();
                field.focus();
            });
        }
        /* Escape stops a recording the way it closes anything else, without
           the member having to find the control again. */
        doc.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && machine.get() === LISTENING) cancelRecording();
        });

        return { machine: machine, field: field };
    }

    function init(doc) {
        var scope = doc || (typeof document !== 'undefined' ? document : null);
        if (!scope) return [];
        var bound = [];
        Array.prototype.forEach.call(scope.querySelectorAll('[data-wk-voice]'), function (container) {
            var binding = bind(container, scope);
            if (binding) bound.push(binding);
        });
        return bound;
    }

    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function () { init(document); });
        } else {
            init(document);
        }
    }

    return {
        STATES: STATES,
        READY: READY,
        LISTENING: LISTENING,
        TRANSCRIBING: TRANSCRIBING,
        TRANSCRIPT: TRANSCRIPT,
        FAILED: FAILED,
        DENIED: DENIED,
        TRANSITIONS: TRANSITIONS,
        nextState: nextState,
        copyFor: copyFor,
        createVoiceMachine: createVoiceMachine,
        insertTranscript: insertTranscript,
        isPermissionError: isPermissionError,
        mediaErrorMessage: mediaErrorMessage,
        supportedMimeType: supportedMimeType,
        browserCanRecord: browserCanRecord,
        init: init,
        bind: bind
    };
});

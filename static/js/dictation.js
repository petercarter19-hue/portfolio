/* PeerSlate shared browser dictation.
 *
 * One browser-local dictation path, usable by any room that puts a mic beside
 * a text field. Transcription is performed by the visitor's own browser; no
 * audio is sent to or retained by PeerSlate, and nothing here writes a
 * canonical record. This module is transcription only: it never submits,
 * confirms, analyses, saves, publishes, or navigates.
 *
 * PS-VOICE-001 private Voice Capture is a separate authenticated system and
 * must not be reimplemented here.
 *
 * Behaviour contract: click to start, keep listening, stop on a second click,
 * and auto-stop after DICTATION_SILENCE_MS of silence.
 *
 * Host-agnostic by design. The module owns recognition, permission, timers,
 * caret insertion, and button state; the host owns how its own status,
 * interim, and error elements are found and written. Markup contracts such as
 * Interview Studio's data-is-* attributes belong to the host, never here.
 *
 * The small CommonJS export keeps the same production code directly testable
 * without a browser-only test dependency.
 *
 * Extracted from static/js/interview-studio.js (PS-OPPORTUNITY-SLATE-001,
 * slice OS-5) with no behaviour change.
 */
(function (root, factory) {
    'use strict';

    var api = factory();
    if (typeof module === 'object' && module.exports) { module.exports = api; }
    root.PeerSlateDictation = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    var DICTATION_SILENCE_MS = 10000;
    var DICTATION_COUNTDOWN_MS = 4000;
    var DICTATION_RESTART_DELAY_MS = 150;
    var DICTATION_MAX_RESTARTS = 120;
    var TRANSIENT_SPEECH_ERRORS = ['aborted', 'no-speech'];

    function speechRecognitionCtor() {
        return window.SpeechRecognition || window.webkitSpeechRecognition || null;
    }
    function speechIsSupported() {
        return Boolean(speechRecognitionCtor());
    }
    function friendlySpeechError(code) {
        if (code === 'not-allowed' || code === 'service-not-allowed') return 'Microphone permission was denied. Allow microphone access in your browser’s site settings, then try again.';
        if (code === 'no-speech') return 'No speech was detected. Try again and speak clearly into your microphone.';
        if (code === 'audio-capture') return 'No microphone was found, or it is being used by another app.';
        if (code === 'network') return 'Dictation lost its network connection. Check your connection and try again.';
        return 'Dictation stopped before it captured a transcript. Try again, or keep typing.';
    }
    function defaultMediaErrorMessage(error) {
        if (!error) return 'The microphone is unavailable.';
        if (error.name === 'NotAllowedError' || error.name === 'SecurityError') return 'Microphone permission was denied. Use your browser site settings to allow access, then try again.';
        if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') return 'No usable microphone was found.';
        if (error.name === 'NotReadableError') return 'Another application may be using the microphone.';
        return 'The microphone could not be started in this browser.';
    }
    function appendTranscript(target, transcript) {
        if (!target || !transcript) return 0;
        var start = typeof target.selectionStart === 'number' ? target.selectionStart : target.value.length;
        var end = typeof target.selectionEnd === 'number' ? target.selectionEnd : start;
        var before = target.value.slice(0, start);
        var after = target.value.slice(end);
        var leadingSpace = before && !/\s$/.test(before) ? ' ' : '';
        var trailingSpace = after && !/^\s/.test(after) ? ' ' : '';
        var inserted = leadingSpace + transcript.trim() + trailingSpace;
        target.value = before + inserted + after;
        var cursor = before.length + inserted.length;
        if (typeof target.setSelectionRange === 'function') target.setSelectionRange(cursor, cursor);
        target.dispatchEvent(new Event('input', { bubbles: true }));
        return transcript.split(/\s+/).filter(Boolean).length;
    }

    function noop() { }
    function numberOption(value, fallback) {
        return typeof value === 'number' && isFinite(value) && value >= 0 ? value : fallback;
    }
    function functionOption(value, fallback) {
        return typeof value === 'function' ? value : fallback;
    }

    /* A binding is one mic surface: its button, the field it dictates into,
       and the host callbacks that write that surface's status, interim, and
       error copy. The host supplies these; the module never queries the DOM
       for them. */
    function normalizeBinding(key, binding) {
        var supplied = binding || {};
        return {
            key: key,
            button: supplied.button || null,
            resolveTarget: functionOption(supplied.resolveTarget, function () { return supplied.target || null; }),
            label: supplied.label || 'Start dictation',
            listeningLabel: supplied.listeningLabel || 'Stop dictation',
            noun: supplied.noun || 'text',
            setStatus: functionOption(supplied.setStatus, noop),
            setInterim: functionOption(supplied.setInterim, noop),
            showError: functionOption(supplied.showError, noop),
            hideError: functionOption(supplied.hideError, noop),
            setButtonLabel: functionOption(supplied.setButtonLabel, noop)
        };
    }

    function createController(options) {
        var settings = options || {};
        var announce = functionOption(settings.announce, noop);
        var mediaErrorMessage = functionOption(settings.mediaErrorMessage, defaultMediaErrorMessage);
        var silenceMs = numberOption(settings.silenceMs, DICTATION_SILENCE_MS);
        var countdownMs = numberOption(settings.countdownMs, DICTATION_COUNTDOWN_MS);
        var restartDelayMs = numberOption(settings.restartDelayMs, DICTATION_RESTART_DELAY_MS);
        var maxRestarts = numberOption(settings.maxRestarts, DICTATION_MAX_RESTARTS);
        var transientErrors = Array.isArray(settings.transientErrors)
            ? settings.transientErrors.slice()
            : TRANSIENT_SPEECH_ERRORS.slice();

        var bindings = {};
        var activeDictation = null;
        var dictationPermissionRequestId = 0;
        var pendingDictationPermission = null;
        var microphonePermissionConfirmed = false;

        function bindingFor(key) {
            return Object.prototype.hasOwnProperty.call(bindings, key) ? bindings[key] : null;
        }
        function register(key, binding) {
            bindings[key] = normalizeBinding(key, binding);
            return bindings[key];
        }
        function isActive() {
            return Boolean(activeDictation);
        }
        function clearDictationTimers(state) {
            if (state.silenceTimer) { window.clearTimeout(state.silenceTimer); state.silenceTimer = null; }
            if (state.tickTimer) { window.clearInterval(state.tickTimer); state.tickTimer = null; }
            if (state.restartTimer) { window.clearTimeout(state.restartTimer); state.restartTimer = null; }
        }
        function renderDictationCountdown(state) {
            var remaining = Math.max(0, state.silenceDeadline - Date.now());
            if (remaining > countdownMs) {
                state.binding.setStatus('Listening. Stops after 10 seconds of silence, or press Escape.');
                return;
            }
            state.binding.setStatus('Listening. Stopping in ' + Math.ceil(remaining / 1000) + 's unless you speak.');
        }
        function armDictationSilence(state) {
            if (state.silenceTimer) { window.clearTimeout(state.silenceTimer); state.silenceTimer = null; }
            state.silenceDeadline = Date.now() + silenceMs;
            state.silenceTimer = window.setTimeout(function () { stopDictation('silence'); }, silenceMs);
            renderDictationCountdown(state);
            if (state.tickTimer) return;
            state.tickTimer = window.setInterval(function () {
                if (activeDictation !== state || state.stopping) return;
                renderDictationCountdown(state);
            }, 250);
        }
        function finishDictation(state) {
            if (state.finished) return;
            state.finished = true;
            clearDictationTimers(state);
            if (activeDictation === state) activeDictation = null;
            /* Speech the visitor could see in the preview but the browser never
               finalised still belongs to them. Keep it rather than discard it. */
            if (state.interim) {
                state.words += appendTranscript(state.target, state.interim);
                state.interim = '';
            }
            state.binding.setInterim('');
            state.binding.setStatus('');
            state.button.classList.remove('is-listening');
            state.button.removeAttribute('aria-busy');
            state.button.setAttribute('aria-pressed', 'false');
            state.button.setAttribute('aria-label', state.binding.label);
            state.binding.setButtonLabel('Start dictation');

            if (state.reason === 'error') return;
            var noun = state.binding.noun;
            if (!state.words) {
                /* The Web Speech API cannot tell a dismissed permission prompt
                   apart from silence, so name it as one possible cause instead of
                   inventing a state we cannot actually observe. */
                var nothing = state.heardSomething
                    ? 'Dictation stopped before any speech could be transcribed. You can try again, or keep typing.'
                    : 'Dictation stopped without capturing any speech. If your browser asked for microphone permission and the prompt was closed, nothing was heard. You can keep typing.';
                announce(nothing);
                state.binding.showError(nothing);
                return;
            }
            var added = state.words === 1 ? '1 word was added to your ' + noun + '.' : state.words + ' words were added to your ' + noun + '.';
            if (state.reason === 'silence') announce('Dictation stopped after 10 seconds of silence. ' + added + ' You can edit it.');
            else if (state.reason === 'interrupted') announce('Dictation stopped. ' + added);
            else announce('Dictation stopped. ' + added + ' You can edit it.');
        }
        function cancelPendingDictationPermission() {
            dictationPermissionRequestId += 1;
            if (!pendingDictationPermission) return;
            var pending = pendingDictationPermission;
            pendingDictationPermission = null;
            pending.button.removeAttribute('aria-busy');
            pending.binding.setStatus('');
        }
        function stopDictation(reason) {
            cancelPendingDictationPermission();
            var state = activeDictation;
            if (!state || state.stopping || state.finished) return;
            state.stopping = true;
            state.reason = reason || 'manual';
            clearDictationTimers(state);
            /* Commit visible interim speech before the caller reads, clears, or
               hides the field. Later recognition events are ignored by the
               finished guard, so they cannot append into stale UI. */
            try { state.recognition.stop(); } catch (error) { /* finish below */ }
            finishDictation(state);
        }
        function beginDictation(binding, button) {
            var Recognition = speechRecognitionCtor();
            if (!Recognition) {
                var unsupported = 'Speech input is not supported in this browser. You can keep typing.';
                announce(unsupported);
                binding.showError(unsupported);
                return;
            }
            var target = binding.resolveTarget();
            if (!target) return;
            binding.hideError();
            var recognition = new Recognition();
            var state = {
                key: binding.key,
                binding: binding,
                button: button,
                target: target,
                recognition: recognition,
                words: 0,
                restarts: 0,
                interim: '',
                heardSomething: false,
                stopping: false,
                finished: false,
                reason: 'manual',
                silenceDeadline: 0,
                silenceTimer: null,
                tickTimer: null,
                restartTimer: null
            };
            activeDictation = state;
            recognition.lang = document.documentElement.lang || 'en-US';
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.onresult = function (event) {
                if (state.finished) return;
                armDictationSilence(state);
                var interim = '';
                var finalText = '';
                for (var index = event.resultIndex; index < event.results.length; index += 1) {
                    var result = event.results[index];
                    var chunk = result[0] && result[0].transcript ? result[0].transcript : '';
                    if (result.isFinal) finalText += (finalText ? ' ' : '') + chunk.trim();
                    else interim += chunk;
                }
                if (finalText || interim.trim()) state.heardSomething = true;
                if (finalText) {
                    state.words += appendTranscript(state.target, finalText);
                    state.interim = '';
                    state.binding.setInterim('');
                } else {
                    state.interim = interim.trim();
                    state.binding.setInterim(state.interim);
                }
            };
            recognition.onstart = function () {
                button.removeAttribute('aria-busy');
                binding.setStatus('Listening. Stops after 10 seconds of silence, or press Escape.');
            };
            recognition.onerror = function (event) {
                var code = event && event.error;
                /* Continuous sessions emit these while the visitor is simply pausing.
                   The 10-second silence deadline decides when to stop, not the browser. */
                if (transientErrors.indexOf(code) !== -1) return;
                var message = friendlySpeechError(code);
                state.stopping = true;
                state.reason = 'error';
                announce(message);
                state.binding.showError(message);
                finishDictation(state);
            };
            recognition.onend = function () {
                if (state.finished) return;
                if (state.stopping) { finishDictation(state); return; }
                if (Date.now() >= state.silenceDeadline) { state.reason = 'silence'; finishDictation(state); return; }
                if (state.restarts >= maxRestarts) { state.reason = 'manual'; finishDictation(state); return; }
                state.restarts += 1;
                state.restartTimer = window.setTimeout(function () {
                    if (state.finished || state.stopping) return;
                    try { recognition.start(); } catch (error) { finishDictation(state); }
                }, restartDelayMs);
            };
            button.classList.add('is-listening');
            button.setAttribute('aria-pressed', 'true');
            button.setAttribute('aria-label', binding.listeningLabel);
            binding.setButtonLabel('Stop dictation');
            announce('Listening. Speak your ' + binding.noun + '. Dictation keeps running until you stop it or you are silent for 10 seconds.');
            armDictationSilence(state);
            try {
                recognition.start();
            } catch (error) {
                state.reason = 'error';
                binding.showError('The microphone could not start. Close other microphone apps and try again.');
                finishDictation(state);
            }
        }
        function startDictation(key) {
            var binding = bindingFor(key);
            if (!binding || !binding.button) return;
            var button = binding.button;
            var Recognition = speechRecognitionCtor();
            if (!Recognition) {
                var unsupported = 'Speech input is not supported in this browser. You can keep typing.';
                announce(unsupported);
                binding.showError(unsupported);
                return;
            }
            if (button.disabled) return;
            var target = binding.resolveTarget();
            if (!target) return;
            var requestId = ++dictationPermissionRequestId;
            pendingDictationPermission = { key: key, binding: binding, button: button, requestId: requestId };
            binding.hideError();
            button.setAttribute('aria-busy', 'true');
            binding.setStatus(microphonePermissionConfirmed ? 'Starting the microphone…' : 'Requesting microphone access…');

            var permission = Promise.resolve();
            if (!microphonePermissionConfirmed && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                permission = navigator.mediaDevices.getUserMedia({ audio: true, video: false }).then(function (stream) {
                    var tracks = stream.getAudioTracks();
                    var ready = tracks.some(function (track) { return track.readyState === 'live'; });
                    stream.getTracks().forEach(function (track) { track.stop(); });
                    if (!ready) throw { name: 'NotFoundError' };
                    microphonePermissionConfirmed = true;
                });
            }
            permission.then(function () {
                if (requestId !== dictationPermissionRequestId) return;
                pendingDictationPermission = null;
                beginDictation(binding, button);
            }).catch(function (error) {
                if (requestId !== dictationPermissionRequestId) return;
                pendingDictationPermission = null;
                button.removeAttribute('aria-busy');
                binding.setStatus('');
                var message = mediaErrorMessage(error);
                binding.showError(message);
                announce(message);
            });
        }
        function toggleDictation(key) {
            var binding = bindingFor(key);
            if (!binding) return;
            if (pendingDictationPermission) {
                var samePendingButton = pendingDictationPermission.button === binding.button;
                cancelPendingDictationPermission();
                if (!samePendingButton) window.setTimeout(function () { startDictation(key); }, 0);
                return;
            }
            if (activeDictation) {
                var sameButton = activeDictation.button === binding.button;
                stopDictation('manual');
                if (!sameButton) window.setTimeout(function () { startDictation(key); }, 0);
                return;
            }
            startDictation(key);
        }

        return {
            register: register,
            start: startDictation,
            stop: stopDictation,
            toggle: toggleDictation,
            isActive: isActive
        };
    }

    return {
        isSupported: speechIsSupported,
        recognitionConstructor: speechRecognitionCtor,
        friendlySpeechError: friendlySpeechError,
        appendTranscript: appendTranscript,
        createController: createController,
        defaults: {
            silenceMs: DICTATION_SILENCE_MS,
            countdownMs: DICTATION_COUNTDOWN_MS,
            restartDelayMs: DICTATION_RESTART_DELAY_MS,
            maxRestarts: DICTATION_MAX_RESTARTS,
            transientErrors: TRANSIENT_SPEECH_ERRORS.slice()
        }
    };
});

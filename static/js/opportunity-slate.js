/*
 * Opportunity Slate room behaviour — PS-OPPSLATE-001, slice OS-1.
 *
 * Two jobs, and deliberately no more:
 *
 *   1. Progressive enhancement for BOTH modes — the primary action is
 *      disabled while the editor is empty (image 01), a rail action that
 *      points at a collapsed disclosure opens it instead of leaving a link
 *      that appears to do nothing, and every mic is wired to the shared
 *      static/js/dictation.js module (slice OS-5; see "Speech input"
 *      below) unless the browser has no SpeechRecognition at all, in
 *      which case it is put into a real, labelled inert state rather than
 *      left looking live and doing nothing.
 *
 *   2. The anonymous public session's transport (handoff section 18). A
 *      signed-out visitor's working state lives in a signed context token
 *      held in this browser tab's sessionStorage and posted back as a fetch
 *      JSON body. The server re-renders the room from that token and returns
 *      HTML, so there is exactly one renderer for both modes and this file
 *      never composes member-facing copy of its own.
 *
 * Signed-in members never need any of part 2: their screens are ordinary
 * server-rendered pages driven by plain HTML form posts, and the whole flow
 * works with JavaScript switched off.
 *
 * No secret, key, token name, or endpoint credential appears in this file.
 * The context token is opaque, server-signed, and only ever handed straight
 * back to the server that issued it.
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'peerslate.opportunity-slate.context.v1';
    var liveRegion = null;
    var rehydrated = false;

    function room() {
        return document.querySelector('[data-os-room]');
    }

    function isPublic(node) {
        return !!node && node.getAttribute('data-os-mode') === 'public';
    }

    /* The announcement region lives outside the swapped fragment, so a
       re-render never silently discards a message mid-announcement. */
    function announce(message) {
        if (!liveRegion) {
            liveRegion = document.createElement('p');
            liveRegion.setAttribute('role', 'status');
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.className = 'os-visually-hidden';
            document.body.appendChild(liveRegion);
        }
        liveRegion.textContent = '';
        window.setTimeout(function () {
            liveRegion.textContent = message;
        }, 60);
    }

    function readStoredToken() {
        try {
            return window.sessionStorage.getItem(STORAGE_KEY);
        } catch (error) {
            return null;
        }
    }

    function writeStoredToken(token) {
        try {
            if (token) {
                window.sessionStorage.setItem(STORAGE_KEY, token);
            } else {
                window.sessionStorage.removeItem(STORAGE_KEY);
            }
        } catch (error) {
            /* Private-mode storage refusal is not an error worth shouting
               about: the visitor simply loses the state when they navigate,
               which is exactly what the banner already promises. */
        }
    }

    function currentToken(node) {
        var rendered = node && node.getAttribute('data-os-context-token');
        return rendered || readStoredToken();
    }

    /* Image 01: the primary action stays inert until there is something to
       review. Applied as an enhancement — with JavaScript off the button is
       live and the server returns a named, text-preserving error instead. */
    function syncPrimary(node) {
        var editor = node.querySelector('[data-os-source-input]');
        var primary = node.querySelector('[data-os-primary]');
        if (!editor || !primary) {
            return;
        }
        var empty = editor.value.trim().length === 0;
        primary.disabled = empty;
        primary.setAttribute('aria-disabled', empty ? 'true' : 'false');
    }

    /* The anonymous input counter (independent review finding F5). The public
       wording review reads a tighter cap than the editor's maxlength, and the
       server enforces it at the AI call; this keeps the number on screen from
       the first keystroke so the refusal is never the first the visitor hears
       of it.

       Writes a NUMBER and toggles `hidden`. Every sentence around it is
       authored in _intake.html — no member-facing copy lives here. */
    function syncSourceCount(node) {
        var limitNote = node.querySelector('[data-os-source-limit]');
        var editor = node.querySelector('[data-os-source-input]');
        if (!limitNote || !editor) {
            return;
        }
        var limit = parseInt(limitNote.getAttribute('data-os-source-limit'), 10);
        var count = editor.value.length;
        var counter = limitNote.querySelector('[data-os-source-count]');
        if (counter) {
            counter.textContent = String(count);
        }
        var over = !isNaN(limit) && count > limit;
        var overNote = limitNote.querySelector('[data-os-source-over]');
        if (overNote) {
            overNote.hidden = !over;
        }
        limitNote.classList.toggle('os-help--over', over);
    }

    function enableJsOnlyControls(node) {
        var controls = node.querySelectorAll('[data-os-needs-js]');
        for (var index = 0; index < controls.length; index += 1) {
            controls[index].disabled = false;
            controls[index].removeAttribute('data-os-needs-js');
        }
    }

    /* Never steals focus on an ordinary page load. */
    function initRoom() {
        var node = room();
        if (!node) {
            return;
        }
        if (isPublic(node)) {
            enableJsOnlyControls(node);
        }
        syncPrimary(node);
        syncSourceCount(node);
        initDictation(node);
    }

    /* Replacing the fragment destroys whatever the visitor was focused on,
       so focus is deliberately placed again: on the failure card when there
       is one (so the reason is read first), otherwise on the new screen's
       heading. Never left on <body>. */
    function restoreFocus(node) {
        var target =
            node.querySelector('[data-os-error]') || node.querySelector('[data-os-focus]');
        if (target) {
            target.focus();
        }
    }

    /* Independent review finding F10. The stage rail's last polite message is
       stage 3, fired immediately before this swap, so a screen-reader user
       heard that the screen was being rebuilt and never heard that it had
       been. A screen that has something to say about its new state renders
       [data-os-swap-announce], and it is repeated through the persistent
       region above — a live region inserted together with its own text is not
       reliably announced. The sentence is server-authored; nothing here
       composes member-facing copy. */
    function announceSwap(node) {
        var carrier = node.querySelector('[data-os-swap-announce]');
        if (!carrier) {
            return;
        }
        var message = carrier.textContent.replace(/\s+/g, ' ').trim();
        if (message) {
            announce(message);
        }
    }

    function swapRoom(html) {
        var node = room();
        if (!node || !html) {
            return;
        }
        /* The fragment about to be replaced may hold an actively listening
           mic bound to a field that is about to be detached. Flush it into
           that field first (dictation's own stop path already commits
           visible interim speech) rather than leaving a recognition session
           running against markup nobody can see or reach any more. */
        stopActiveDictation('interrupted');
        node.outerHTML = html;
        initRoom();
        var fresh = room();
        if (fresh) {
            restoreFocus(fresh);
            announceSwap(fresh);
        }
    }

    /* ------------------------------------------------------------------
       Slice OS-5 — speech input, shared with Interview Studio via
       static/js/dictation.js (handoff sections 4 and 6). Recognition,
       microphone permission, timers, restart handling, and caret insertion
       live in that module, which this template loads first; this room only
       binds it to its own mic markup, exactly as interview-studio.js binds
       it to its own — the data-os-mic* attributes below are this room's
       binding, not the module's.

       Every mic surface renders identically in both modes (handoff section
       18): dictation never leaves the visitor's own browser and never
       touches the paste-only server boundary described there — whichever
       mode a member is in, the server only ever receives whatever text
       already sits in the field at submit time, spoken or typed, exactly
       like a member who only ever typed. So the anonymous public session
       gets the same live mic the signed-in workbench does, on every field
       that has one.

       This file still composes none of its own member-facing copy: the
       accessible label, the noun used in an announcement, and the help
       sentence beside each field are all read from what the template
       already rendered. ------------------------------------------------ */
    var dictationModule = window.PeerSlateDictation || null;
    var dictation = dictationModule
        ? dictationModule.createController({ announce: announce })
        : null;

    function stopActiveDictation(reason) {
        if (dictation && dictation.isActive()) {
            dictation.stop(reason);
        }
    }

    function dictationStatusEl(key) {
        return document.querySelector('[data-os-dictation-status="' + key + '"]');
    }
    function dictationInterimEl(key) {
        return document.querySelector('[data-os-dictation-interim="' + key + '"]');
    }
    function dictationErrorEl(key) {
        return document.querySelector('[data-os-mic-error="' + key + '"]');
    }
    function setDictationStatus(key, message) {
        var target = dictationStatusEl(key);
        if (!target) {
            return;
        }
        target.textContent = message || '';
        target.hidden = !message;
    }
    function setDictationInterim(key, value) {
        var target = dictationInterimEl(key);
        if (!target) {
            return;
        }
        var textNode = target.querySelector('[data-os-dictation-interim-text]');
        if (textNode) {
            textNode.textContent = value || '';
        }
        target.hidden = !value;
    }
    function showMicError(key, message) {
        var target = dictationErrorEl(key);
        if (!target) {
            return;
        }
        target.textContent = message;
        target.hidden = false;
    }
    function hideMicError(key) {
        var target = dictationErrorEl(key);
        if (target) {
            target.hidden = true;
        }
    }

    /* One binding per mic button on screen. A field can render more than
       one instance of the same surface at once — the response rail holds
       one panel per qualification, and the source review holds one
       correction card per flagged concern, all but the selected/relevant
       one hidden rather than absent — so the template gives each button its
       own key rather than one per surface TYPE. */
    function bindMic(button) {
        var key = button.getAttribute('data-os-mic');
        if (!key || !dictation) {
            return;
        }
        var editor = button.closest('.os-editor');
        var field = editor ? editor.querySelector('textarea') : null;
        if (!field) {
            return;
        }
        dictation.register(key, {
            button: button,
            resolveTarget: function () {
                return field;
            },
            /* The server already rendered an accurate aria-label ("Dictate
               the role", …); the module keeps it in sync as the button
               toggles. Falling back to its own default only matters if a
               future surface ever omits one. */
            label: button.getAttribute('aria-label') || undefined,
            noun: button.getAttribute('data-os-mic-noun') || 'text',
            setStatus: function (message) {
                setDictationStatus(key, message);
            },
            setInterim: function (value) {
                setDictationInterim(key, value);
            },
            showError: function (message) {
                showMicError(key, message);
            },
            hideError: function () {
                hideMicError(key);
            }
        });
        button.addEventListener('click', function () {
            dictation.toggle(key);
        });
    }

    /* Progressive enhancement (handoff section 6 rule 5): with no
       SpeechRecognition at all, every mic stays in a labelled inert state —
       distinct from the pre-OS-5 "not available yet" render, because
       dictation IS available, just not in this browser. Typing remains the
       whole path either way. */
    function disableUnsupportedMics(buttons) {
        for (var index = 0; index < buttons.length; index += 1) {
            var button = buttons[index];
            button.setAttribute('aria-disabled', 'true');
            button.disabled = true;
            button.classList.add('is-unavailable');
            setDictationStatus(
                button.getAttribute('data-os-mic'),
                'Speech input is not supported in this browser. Typing works normally.'
            );
        }
    }

    function initDictation(node) {
        var buttons = node.querySelectorAll('[data-os-mic]');
        /* Bind first, unconditionally, THEN disable if unsupported —
           interview-studio.js's exact order for its own mics. A button that
           was never registered has no click listener at all, so if
           something later re-enables it (lockRail unlocking a rail, below)
           a press does nothing and explains nothing. Binding first means
           the shared module's own startDictation still gates on
           SpeechRecognition at the moment of the click and reports an
           honest "not supported" error either way, the same backstop
           Interview Studio already relies on. */
        for (var index = 0; index < buttons.length; index += 1) {
            bindMic(buttons[index]);
        }
        if (!dictationModule || !dictationModule.isSupported()) {
            disableUnsupportedMics(buttons);
        }
    }

    /* Which anonymous actions put the correction rail into image 08's
       read-only state while they are in flight. They are the ones the member
       fires FROM that rail, or that change what it is showing: letting a
       second correction be typed into a control whose value is already on
       its way to the server is how a member loses an edit they thought they
       made. Cancel aborts and restores editing; nothing was written. */
    var RAIL_LOCKING_ACTIONS = {
        statement: true,
        confirm_requirements: true,
        resolve: true,
        /* Slice OS-3. A response is fired FROM the rail, so a second one must
           not be typed into a control whose value is already on its way. */
        respond: true
    };

    function send(payload) {
        var node = room();
        if (!node) {
            return;
        }
        var endpoint = node.getAttribute('data-os-public-url');
        payload.context_token = currentToken(node);

        var controller =
            typeof window.AbortController === 'function'
                ? new window.AbortController()
                : null;
        var locking = RAIL_LOCKING_ACTIONS[payload.action] === true;
        if (locking) {
            /* Every caller that can reach a locking action flushes dictation
               before it ever builds `payload` — the submit handler's own
               flush above `kind = form.getAttribute(...)` is what protects
               the field value this function was handed; by the time send()
               runs, that value is already final. This second flush is a
               backstop for send() as its own unit, not the fix for lost
               interim speech: it exists so a rail is never locked while a
               mic is still listening against it, the same invariant
               beginProposal's own flush keeps at its own lockRail call. */
            stopActiveDictation('interrupted');
            lockRail(node, true);
            pending = {
                controller: controller,
                restore: function () {
                    lockRail(node, false);
                    pending = null;
                }
            };
        }

        window
            .fetch(endpoint, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                signal: controller ? controller.signal : undefined,
                body: JSON.stringify(payload)
            })
            .then(function (response) {
                if (response.status === 404) {
                    /* The mode changed under us (signed in), or the room was
                       switched off. Clear the browser-held state and let the
                       server say what is true now. */
                    writeStoredToken(null);
                    window.location.reload();
                    return null;
                }
                return response.json().then(function (data) {
                    return { ok: response.ok, data: data };
                });
            })
            .then(function (result) {
                pending = null;
                if (!result) {
                    return;
                }
                var data = result.data || {};
                if (Object.prototype.hasOwnProperty.call(data, 'context_token')) {
                    writeStoredToken(data.context_token);
                }
                if (data.html) {
                    /* The replacement markup arrives unlocked, so there is
                       nothing to unlock. */
                    swapRoom(data.html);
                } else if (locking) {
                    lockRail(room() || node, false);
                }
                if (data.message) {
                    announce(data.message);
                }
            })
            .catch(function (error) {
                var restore = pending && pending.restore;
                pending = null;
                if (restore) {
                    restore();
                }
                if (error && error.name === 'AbortError') {
                    return;
                }
                /* Never discard the visitor's held state on a transient
                   failure — say so plainly and leave the screen alone. */
                announce(
                    'We could not reach PeerSlate just then. Nothing was lost — your ' +
                        'role text is still on this screen. Try that again.'
                );
            });
    }

    function rehydrate() {
        var node = room();
        if (!node || !isPublic(node) || rehydrated) {
            return;
        }
        rehydrated = true;
        if (node.getAttribute('data-os-context-token')) {
            return;
        }
        if (!readStoredToken()) {
            return;
        }
        send({ action: 'render' });
    }

    /* event.target is not guaranteed to expose closest() (document and
       text nodes do not), so every delegated lookup goes through this. */
    function closestFrom(target, selector) {
        if (!target || typeof target.closest !== 'function') {
            return null;
        }
        return target.closest(selector);
    }

    /* ------------------------------------------------------------------
       Slice OS-2 — the stage rail, statement selection, and the two AI
       requests.

       Every sentence any of this shows is authored server-side. The stage
       rail is cloned from a <template> the page already carries, the
       read-only notice and the processing Cancel control are rendered
       hidden and revealed, and the only strings this file owns are the two
       transient announcements slice OS-1 already shipped. That is not
       tidiness: copy that lives in JavaScript is copy nobody reviews.
       ------------------------------------------------------------------ */

    var pending = null;

    /* The interview-studio.js setStage idiom: exactly one step carries
       aria-current="step" at any time, kept in sync with the visual state,
       and each change is announced politely from inside the rail. */
    function setStage(rail, stage) {
        if (!rail) {
            return;
        }
        var steps = rail.querySelectorAll('[data-os-stage]');
        var note = rail.querySelector('[data-os-stage-note]');
        var live = rail.querySelector('[data-os-stage-live]');
        for (var index = 0; index < steps.length; index += 1) {
            var step = steps[index];
            var number = Number(step.getAttribute('data-os-stage'));
            var current = number === stage;
            step.classList.toggle('is-done', number < stage);
            step.classList.toggle('is-current', current);
            if (current) {
                step.setAttribute('aria-current', 'step');
                var label = step.querySelector('.os-stage__label');
                if (live && label) {
                    live.textContent = label.textContent.trim();
                }
                if (note) {
                    /* The per-stage sentence is carried on the step itself so
                       it stays server-authored. */
                    var described = step.getAttribute('data-os-stage-note');
                    if (described) {
                        note.textContent = described;
                    }
                }
            } else {
                step.removeAttribute('aria-current');
            }
        }
    }

    /* Image 08's locked rail. Visibly disabled, never hidden, so the member
       can see exactly what will come back. */
    function lockRail(node, locked) {
        var controls = node.querySelectorAll('[data-os-rail-control]');
        if (!controls.length && !node.querySelector('[data-os-statement-rail]')) {
            return;
        }
        for (var index = 0; index < controls.length; index += 1) {
            var control = controls[index];
            /* A mic marked permanently unavailable (no SpeechRecognition in
               this browser, set once by disableUnsupportedMics) is not this
               mechanism's to touch — unlocking would clear its aria-disabled
               and re-enable it, so a browser with no speech support would
               show a glowing, apparently-live mic the moment a member
               pressed Cancel. Its inert state has to survive every lock and
               unlock the rail goes through, not just the first one. */
            if (control.classList.contains('is-unavailable')) {
                continue;
            }
            control.disabled = locked;
            control.setAttribute('aria-disabled', locked ? 'true' : 'false');
        }
        var notice = node.querySelector('[data-os-rail-locked-note]');
        if (notice) {
            notice.hidden = !locked;
        }
        /* Scoped to the correction rail. The stage rail carries its own
           Cancel and is only ever on screen while a request is running, so
           hiding by this toggle would remove the one control that can stop
           it. */
        var rail = node.querySelector('[data-os-statement-rail]');
        if (!rail) {
            return;
        }
        var cancels = rail.querySelectorAll('[data-os-cancel-processing]');
        for (var i = 0; i < cancels.length; i += 1) {
            cancels[i].hidden = !locked;
        }
        var ordinary = rail.querySelectorAll('[data-os-cancel-statement]');
        for (var j = 0; j < ordinary.length; j += 1) {
            ordinary[j].hidden = locked;
        }
    }

    /* Selecting a statement moves context to the rail WITHOUT stealing focus
       (handoff section 13). The member stays where they were and can Tab into
       the rail when they want it. */
    /* Slice OS-3. Selecting a qualification moves BOTH rails to it — the
       response panel on the left and the evidence panel on the right — and
       likewise never steals focus. */
    function selectAlignment(node, key) {
        var groups = [
            '[data-os-response-panel]',
            '[data-os-evidence-panel]'
        ];
        for (var g = 0; g < groups.length; g += 1) {
            var panels = node.querySelectorAll(groups[g]);
            var attribute = groups[g].slice(1, -1);
            for (var index = 0; index < panels.length; index += 1) {
                panels[index].hidden =
                    panels[index].getAttribute(attribute) !== key;
            }
        }
        var rows = node.querySelectorAll('[data-os-align-row]');
        for (var i = 0; i < rows.length; i += 1) {
            var selected = rows[i].getAttribute('data-os-align-row') === key;
            rows[i].classList.toggle('is-selected', selected);
            var control = rows[i].querySelector('[data-os-select-align]');
            if (control) {
                if (selected) {
                    control.setAttribute('aria-current', 'true');
                } else {
                    control.removeAttribute('aria-current');
                }
            }
        }
    }

    function selectStatement(node, key) {
        var panels = node.querySelectorAll('[data-os-statement-panel]');
        for (var index = 0; index < panels.length; index += 1) {
            panels[index].hidden =
                panels[index].getAttribute('data-os-statement-panel') !== key;
        }
        var rows = node.querySelectorAll('[data-os-statement-row]');
        for (var i = 0; i < rows.length; i += 1) {
            var selected = rows[i].getAttribute('data-os-statement-row') === key;
            rows[i].classList.toggle('is-selected', selected);
            /* Independent review finding F7: the state used to be written as
               aria-selected on the <tr>, where it is unsupported outside a
               grid/treegrid and therefore announced to nobody. It moves to
               the control that performs the selection. */
            var control = rows[i].querySelector('[data-os-select-statement]');
            if (control) {
                if (selected) {
                    control.setAttribute('aria-current', 'true');
                } else {
                    control.removeAttribute('aria-current');
                }
            }
        }
    }

    function stageRailFor(node) {
        var template = node.querySelector('[data-os-stage-template]');
        if (!template || !template.content) {
            return null;
        }
        var clone = template.content.firstElementChild;
        return clone ? clone.cloneNode(true) : null;
    }

    /* Both AI requests, both modes, one shape:
         stage 1  the request is composed and about to leave
         stage 2  it is in flight
         stage 3  a response has arrived and the screen is being rebuilt
       Those are real boundaries. Nothing here reports progress the request
       has not actually made. */
    function publicFetch(node, endpointAttribute, payload, controller, token) {
        /* `token` is passed explicitly when one request has just minted a
           fresher one than the rendered DOM carries. Reading it back off the
           node would use the attribute from the PREVIOUS render, which is
           exactly stale enough to make a chained request act on the state
           before the first half of the member's action. */
        payload.context_token = token || currentToken(node);
        return window.fetch(node.getAttribute(endpointAttribute), {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            signal: controller ? controller.signal : undefined,
            body: JSON.stringify(payload)
        });
    }

    function beginProposal(node, form, publicAction) {
        var rail = stageRailFor(node);
        if (!rail) {
            return false;
        }
        /* The rail replaces the prompt card that started the request when
           there is one (images 07/08), and otherwise appears at the head of
           the workbench — the footer's "Confirm requirements and analyze" and
           "Run this again" have no card to replace. */
        var card = form.closest('.os-prompt-card');
        var anchor = card || node.querySelector('.os-workbench');
        if (!anchor) {
            return false;
        }
        var controller =
            typeof window.AbortController === 'function'
                ? new window.AbortController()
                : null;

        if (card) {
            card.parentNode.insertBefore(rail, card);
            card.hidden = true;
        } else {
            anchor.insertBefore(rail, anchor.firstChild);
        }
        setStage(rail, 1);
        /* The submit handler above already flushed before it ever read a
           field value, so by the time a proposal reaches here nothing is
           normally still listening — this is the same backstop send()
           keeps at its own lockRail call, so a mic can never be left
           running against a textarea this is about to disable, from this
           function alone regardless of what called it. */
        stopActiveDictation('interrupted');
        lockRail(node, true);
        pending = {
            controller: controller,
            restore: function () {
                if (rail.parentNode) {
                    rail.parentNode.removeChild(rail);
                }
                if (card) {
                    card.hidden = false;
                }
                lockRail(node, false);
                pending = null;
            }
        };

        /* Independent review finding F11. One member press, TWO bounded
           requests in the anonymous path — and stage 2 was set synchronously
           for both, so the stage that names the evidence check was on screen
           for the whole of the confirm round-trip, which checks none. Stage 1
           now covers the request that confirms the requirements, and stage 2
           begins when the request that actually reads the member's records is
           issued. The signed-in path is one request that does both, so its
           stage 2 already spanned the real read and is unchanged. Every stage
           NAME is server-authored in the calling template; this only decides
           when each becomes true. */
        var deferStageTwo = publicAction === 'confirm_requirements';

        var request;
        if (publicAction === 'confirm_requirements') {
            /* One member press, two bounded requests: the checkpoint on the
               ordinary session budget, then the model call on the tighter AI
               budget. The stage rail spans both, which is exactly what image
               08 draws. */
            request = publicFetch(
                node,
                'data-os-public-url',
                { action: 'confirm_requirements', step: 'requirements' },
                controller
            ).then(function (response) {
                if (!response.ok) {
                    return response;
                }
                return response.json().then(function (data) {
                    var fresh = data && data.context_token;
                    if (
                        data &&
                        Object.prototype.hasOwnProperty.call(data, 'context_token')
                    ) {
                        writeStoredToken(data.context_token);
                    }
                    /* The confirm round-trip is done and the evidence read
                       is the request about to leave (finding F11). */
                    setStage(rail, 2);
                    return publicFetch(
                        node,
                        'data-os-public-propose-url',
                        { action: 'analyze' },
                        controller,
                        fresh
                    );
                });
            });
        } else if (publicAction) {
            request = publicFetch(
                node,
                'data-os-public-propose-url',
                { action: publicAction },
                controller
            );
        } else {
            request = window.fetch(form.action, {
                method: 'POST',
                credentials: 'same-origin',
                signal: controller ? controller.signal : undefined,
                body: new window.FormData(form)
            });
        }
        if (!deferStageTwo) {
            setStage(rail, 2);
        }

        request
            .then(function (response) {
                setStage(rail, 3);
                if (!publicAction) {
                    /* The member routes answer with an ordinary redirect to
                       the room. Following it lands on the real server-rendered
                       state rather than a client-assembled one. */
                    window.location.assign(response.url || window.location.href);
                    return null;
                }
                if (response.status === 404) {
                    writeStoredToken(null);
                    window.location.reload();
                    return null;
                }
                return response.json();
            })
            .then(function (data) {
                if (!data) {
                    return;
                }
                pending = null;
                if (Object.prototype.hasOwnProperty.call(data, 'context_token')) {
                    writeStoredToken(data.context_token);
                }
                if (data.html) {
                    swapRoom(data.html);
                } else if (data.message) {
                    announce(data.message);
                }
            })
            .catch(function (error) {
                var restore = pending && pending.restore;
                pending = null;
                if (restore) {
                    restore();
                }
                if (!error || error.name !== 'AbortError') {
                    announce(
                        'We could not reach PeerSlate just then. Nothing was lost — your ' +
                            'role text is still on this screen. Try that again.'
                    );
                }
            });
        return true;
    }

    /* event.submitter is not available in every browser this site supports,
       and which button was pressed is load-bearing here: it carries the
       apply-or-dismiss decision on a concern card. Captured on the way down
       so a handler cannot have changed it first. */
    var lastSubmitter = null;
    document.addEventListener(
        'click',
        function (event) {
            var button = closestFrom(event.target, 'button[type="submit"]');
            if (button) {
                lastSubmitter = button;
            }
        },
        true
    );

    function submitterFor(event, form) {
        var candidate = event.submitter || lastSubmitter;
        return candidate && form.contains(candidate) ? candidate : null;
    }

    document.addEventListener('submit', function (event) {
        var form = closestFrom(event.target, '[data-os-form]');
        var node = room();
        if (!form || !node || !node.contains(form)) {
            return;
        }
        /* Flush BEFORE anything below reads a field's .value — matching
           Interview Studio's submitReview(), which stops dictation first and
           only then reads answer.value.trim(). Flushing any later (as this
           used to, only inside send()'s locking branch) is too late: by
           then every branch below has already copied a stale .value onto
           the outgoing payload, so an unfinalised "Heard so far" phrase the
           member can still see on screen is silently dropped from what gets
           sent, not merely left running past its use. This also covers the
           signed-in path, which never calls send() at all — an ordinary
           native form submit reads the same .value moments after this
           listener returns, so the flush has to land before that too. */
        stopActiveDictation('interrupted');
        var kind = form.getAttribute('data-os-form');

        /* The two AI requests are intercepted in BOTH modes, because both
           have a real wait worth showing a bounded stage rail for. If the
           rail template is missing for any reason, beginProposal returns
           false and the ordinary form post goes ahead — the flow degrades to
           a plain page load rather than breaking. */
        /* The three AI requests are intercepted in BOTH modes, because all
           three have a real wait worth showing a bounded stage rail for. If
           the rail template is missing for any reason, beginProposal returns
           false and the ordinary form post goes ahead — the flow degrades to
           a plain page load rather than breaking. */
        var PROPOSAL_ACTIONS = {
            review: 'review',
            interpret: 'interpret',
            analyze: 'analyze',
            /* Image 03's primary is "Confirm requirements and analyze" and
               that is one member action. A signed-in member gets both halves
               in one request; anonymously the two halves have deliberately
               different rate-limit budgets, so the confirm goes to the
               session endpoint and the analysis follows on the propose
               endpoint. Same single press, same single stage rail. */
            'confirm-requirements': 'confirm_requirements'
        };
        if (Object.prototype.hasOwnProperty.call(PROPOSAL_ACTIONS, kind)) {
            if (beginProposal(node, form, isPublic(node) ? PROPOSAL_ACTIONS[kind] : null)) {
                event.preventDefault();
                return;
            }
        }

        if (!isPublic(node)) {
            return;
        }
        event.preventDefault();

        if (kind === 'resolve') {
            var pressed = submitterFor(event, form);
            var input = form.querySelector('[data-os-concern-input]');
            send({
                action: 'resolve',
                concern_key: form.querySelector('[name="concern_key"]').value,
                decision: pressed ? pressed.value : 'applied',
                corrected_text: input ? input.value : '',
                step: 'review'
            });
            return;
        }
        if (kind === 'statement') {
            var classSelect = form.querySelector('[name="member_class"]');
            var clarification = form.querySelector('[name="member_clarification"]');
            send({
                action: 'statement',
                statement_key: form.querySelector('[name="statement_key"]').value,
                member_class: classSelect ? classSelect.value : '',
                member_clarification: clarification ? clarification.value : '',
                step: 'requirements'
            });
            return;
        }
        if (kind === 'confirm-requirements') {
            /* Only reached when the stage rail could not be built; the staged
               path above owns this action normally. */
            send({ action: 'confirm_requirements', step: 'requirements' });
            return;
        }
        if (kind === 'respond') {
            var kindField = form.querySelector('[name="response_kind"]');
            var responseField = form.querySelector('[name="response_text"]');
            var chosen = form.querySelector('[name="connected_evidence_key"]:checked');
            send({
                action: 'respond',
                statement_key: form.querySelector('[name="statement_key"]').value,
                response_kind: kindField ? kindField.value : '',
                response_text: responseField ? responseField.value : null,
                connected_evidence_key: chosen ? chosen.value : null,
                step: 'alignment'
            });
            return;
        }
        if (kind === 'source') {
            var editor = node.querySelector('[data-os-source-input]');
            send({
                action: 'source',
                source_text: editor ? editor.value : '',
                step: 'review'
            });
        } else if (kind === 'correct') {
            var correction = node.querySelector('[data-os-correction-input]');
            send({
                action: 'correct',
                corrected_text: correction ? correction.value : '',
                step: 'review'
            });
        } else if (kind === 'confirm') {
            send({ action: 'confirm', step: 'review' });
        } else if (kind === 'delete') {
            send({ action: 'discard' });
        }
    });

    document.addEventListener('click', function (event) {
        var node = room();
        if (!node) {
            return;
        }

        var next = closestFrom(event.target, '[data-os-inert-next]');
        if (next && node.contains(next)) {
            event.preventDefault();
            announce(
                'Comparing these requirements against your evidence is not built ' +
                    'yet. Your requirements are confirmed and nothing was saved.'
            );
            return;
        }

        /* Cancel while a proposal is in flight. Aborts the request and puts
           the screen back exactly as it was — nothing was written, so there
           is nothing to undo. */
        var cancelProcessing = closestFrom(event.target, '[data-os-cancel-processing]');
        if (cancelProcessing && node.contains(cancelProcessing)) {
            event.preventDefault();
            if (pending) {
                if (pending.controller) {
                    pending.controller.abort();
                }
                var restore = pending.restore;
                pending = null;
                if (restore) {
                    restore();
                }
            }
            return;
        }

        /* Selecting a statement row. A real link, so it works with
           JavaScript off; intercepted here so it does not cost a round trip. */
        var select = closestFrom(event.target, '[data-os-select-statement]');
        if (select && node.contains(select)) {
            event.preventDefault();
            /* Every statement's clarification panel — and its own mic —
               stays in the DOM, only `hidden` toggling between them
               (client-side, no round trip), so a mic left listening in the
               PREVIOUS panel would otherwise keep listening invisibly
               behind it. Same stale-context case swapRoom and send()
               already flush. */
            stopActiveDictation('interrupted');
            selectStatement(node, select.getAttribute('data-os-select-statement'));
            return;
        }

        /* The same, for the alignment workbench's two rails. */
        var selectAlign = closestFrom(event.target, '[data-os-select-align]');
        if (selectAlign && node.contains(selectAlign)) {
            event.preventDefault();
            stopActiveDictation('interrupted');
            selectAlignment(node, selectAlign.getAttribute('data-os-select-align'));
            return;
        }

        /* Slice OS-3's honestly inert primary: image 04 draws `Save
           privately` and saving is slice OS-4. */
        var inertSave = closestFrom(event.target, '[data-os-inert-save]');
        if (inertSave && node.contains(inertSave)) {
            event.preventDefault();
            announce(
                'Saving this analysis privately is not built yet. Nothing was ' +
                    'saved, and your analysis is still on this screen.'
            );
            return;
        }

        /* Cancel inside the correction rail: put the controls back to the
           values the server rendered, without a round trip and without
           touching anything else on the screen. */
        var cancelStatement = closestFrom(event.target, '[data-os-cancel-statement]');
        if (cancelStatement && node.contains(cancelStatement) && !pending) {
            var railForm = closestFrom(cancelStatement, 'form');
            if (railForm) {
                event.preventDefault();
                railForm.reset();
            }
            return;
        }

        /* A rail or footer action that points at a collapsed <details>.
           Fragment navigation alone does not open one, so the link would
           look dead. Opening it here and moving focus to its summary makes
           the action work identically for pointer and keyboard, in both
           modes — this runs before the public-only branch below. */
        var reveal = closestFrom(event.target, '[data-os-reveal]');
        if (reveal && node.contains(reveal)) {
            var disclosure = document.getElementById(
                reveal.getAttribute('data-os-reveal')
            );
            if (disclosure) {
                event.preventDefault();
                disclosure.open = true;
                var summary = disclosure.querySelector('summary');
                if (summary) {
                    summary.focus();
                }
                if (typeof disclosure.scrollIntoView === 'function') {
                    disclosure.scrollIntoView({ block: 'nearest' });
                }
                return;
            }
        }

        if (!isPublic(node)) {
            return;
        }
        /* Anchors only, and deliberately so. `data-os-step` carries two
           different meanings: on a link it is an ACTION (go to this step),
           and on the room container it is STATE (the step being shown).
           A bare '[data-os-step]' lookup walks up to that container from
           any click in the public room, so every click — including the
           "Review source" submit button — was answered with
           preventDefault() and a no-op step re-render, which discarded the
           visitor's typed text and made the anonymous flow unusable past
           intake. Every real step control is an <a>. */
        var stepLink = closestFrom(event.target, 'a[data-os-step]');
        if (stepLink && node.contains(stepLink)) {
            event.preventDefault();
            send({ action: 'step', step: stepLink.getAttribute('data-os-step') });
        }
    });

    document.addEventListener('input', function (event) {
        var node = room();
        if (
            node &&
            event.target &&
            typeof event.target.matches === 'function' &&
            event.target.matches('[data-os-source-input]')
        ) {
            syncPrimary(node);
            syncSourceCount(node);
        }
    });

    /* The dictation status line itself says "or press Escape" (shared
       module copy, handoff section 6); this is what makes that literally
       true, exactly as interview-studio.js does for its own mics. */
    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') {
            return;
        }
        stopActiveDictation('manual');
    });
    /* A visitor who switches tabs mid-dictation should not come back to a
       microphone still silently listening. */
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            stopActiveDictation('interrupted');
        }
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initRoom();
            rehydrate();
        });
    } else {
        initRoom();
        rehydrate();
    }
})();

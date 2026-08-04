/*
 * Opportunity Slate room behaviour — PS-OPPSLATE-001, slice OS-1.
 *
 * Two jobs, and deliberately no more:
 *
 *   1. Progressive enhancement for BOTH modes — the primary action is
 *      disabled while the editor is empty (image 01), the inert microphone
 *      explains itself when someone presses it, and a rail action that
 *      points at a collapsed disclosure opens it instead of leaving a link
 *      that appears to do nothing.
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

    function swapRoom(html) {
        var node = room();
        if (!node || !html) {
            return;
        }
        node.outerHTML = html;
        initRoom();
        var fresh = room();
        if (fresh) {
            restoreFocus(fresh);
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
        resolve: true
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
            controls[index].disabled = locked;
            controls[index].setAttribute('aria-disabled', locked ? 'true' : 'false');
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
    function beginProposal(node, form, publicAction) {
        var rail = stageRailFor(node);
        var card = form.closest('.os-prompt-card');
        if (!rail || !card) {
            return false;
        }
        var controller =
            typeof window.AbortController === 'function'
                ? new window.AbortController()
                : null;

        card.parentNode.insertBefore(rail, card);
        card.hidden = true;
        setStage(rail, 1);
        lockRail(node, true);
        pending = {
            controller: controller,
            restore: function () {
                if (rail.parentNode) {
                    rail.parentNode.removeChild(rail);
                }
                card.hidden = false;
                lockRail(node, false);
                pending = null;
            }
        };

        var request;
        if (publicAction) {
            request = window.fetch(node.getAttribute('data-os-public-propose-url'), {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                signal: controller ? controller.signal : undefined,
                body: JSON.stringify({
                    action: publicAction,
                    context_token: currentToken(node)
                })
            });
        } else {
            request = window.fetch(form.action, {
                method: 'POST',
                credentials: 'same-origin',
                signal: controller ? controller.signal : undefined,
                body: new window.FormData(form)
            });
        }
        setStage(rail, 2);

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
        var kind = form.getAttribute('data-os-form');

        /* The two AI requests are intercepted in BOTH modes, because both
           have a real wait worth showing a bounded stage rail for. If the
           rail template is missing for any reason, beginProposal returns
           false and the ordinary form post goes ahead — the flow degrades to
           a plain page load rather than breaking. */
        if (kind === 'review' || kind === 'interpret') {
            var action = kind === 'review' ? 'review' : 'interpret';
            if (beginProposal(node, form, isPublic(node) ? action : null)) {
                event.preventDefault();
            }
            return;
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
            send({ action: 'confirm_requirements', step: 'requirements' });
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

        var mic = closestFrom(event.target, '[data-os-inert-mic]');
        if (mic && node.contains(mic)) {
            event.preventDefault();
            announce(
                'Dictation is not available yet. Type or paste the wording instead — ' +
                    'it arrives in a later update.'
            );
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
            selectStatement(node, select.getAttribute('data-os-select-statement'));
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

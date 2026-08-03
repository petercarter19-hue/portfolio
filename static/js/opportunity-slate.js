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

    function send(payload) {
        var node = room();
        if (!node) {
            return;
        }
        var endpoint = node.getAttribute('data-os-public-url');
        payload.context_token = currentToken(node);

        window
            .fetch(endpoint, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
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
                if (!result) {
                    return;
                }
                var data = result.data || {};
                if (Object.prototype.hasOwnProperty.call(data, 'context_token')) {
                    writeStoredToken(data.context_token);
                }
                if (data.html) {
                    swapRoom(data.html);
                }
                if (data.message) {
                    announce(data.message);
                }
            })
            .catch(function () {
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

    document.addEventListener('submit', function (event) {
        var form = closestFrom(event.target, '[data-os-form]');
        var node = room();
        if (!form || !node || !node.contains(form) || !isPublic(node)) {
            return;
        }
        event.preventDefault();

        var kind = form.getAttribute('data-os-form');
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
                'Reviewing the employer requirements is not built yet. Your source ' +
                    'is confirmed and nothing was saved.'
            );
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

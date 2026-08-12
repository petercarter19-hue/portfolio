/* Opportunity Slate REPLACEMENT room — PS-OPPORTUNITY-SLATE-002, slice R1.
 *
 * Progressive enhancement only. Every form on this page is a plain HTML
 * POST and every <details> disclosure is native browser behavior, so the
 * whole room — capture, upload, import, identity, correction, confirm,
 * delete — already works with this script absent (the OS-1 rule, carried
 * forward: "the flow works with JavaScript disabled"). What this file adds:
 *
 *   1. Wires the stage-1 "Dictate" button to the shared
 *      window.PeerSlateDictation module (static/js/dictation.js, loaded
 *      first and left completely untouched).
 *   2. Keeps "Review source" visually and functionally disabled while the
 *      textarea is empty (image 04 / VISUAL_AUDIT item 04), on top of the
 *      server's own refusal of empty text — belt, not the only buckle.
 *   3. Gives upload/import truthful in-flight progress and a client-request
 *      Cancel backed by AbortController while preserving the other intake
 *      fields on failure.
 *   4. Coordinates the Stage 2 draft as one visible unit: saving one section
 *      cannot erase the other section, and confirmation stays unavailable
 *      until every visible edit matches stored state.
 *
 * No client-side routing and no AI. Every endpoint still works through a
 * plain HTML POST when this script is absent.
 */
(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    function announceRegion() {
        var region = document.querySelector('[data-os2-announce]');
        if (region) return region;
        region = document.createElement('div');
        region.setAttribute('data-os2-announce', '');
        region.setAttribute('aria-live', 'polite');
        region.className = 'os2-visually-hidden';
        document.body.appendChild(region);
        return region;
    }

    function announce(message) {
        if (!message) return;
        var region = announceRegion();
        region.textContent = '';
        // Forces a fresh announcement even if the text is identical to the
        // last one, the same "clear, then set" idiom the rest of the site
        // uses for polite live regions.
        window.setTimeout(function () { region.textContent = message; }, 30);
    }

    function initSourceReviewButton(room) {
        var textarea = room.querySelector('[data-os2-source-text]');
        var button = room.querySelector('[data-os2-review-source]');
        if (!textarea || !button) return;

        function refresh() {
            var hasText = textarea.value.trim().length > 0;
            button.setAttribute('aria-disabled', hasText ? 'false' : 'true');
        }

        textarea.addEventListener('input', refresh);
        refresh();

        button.addEventListener('click', function (event) {
            if (button.getAttribute('aria-disabled') === 'true') {
                event.preventDefault();
                textarea.focus();
            }
        });
    }

    function initDictation(room) {
        var button = room.querySelector('[data-os2-dictate-button]');
        if (!button || !window.PeerSlateDictation) return;
        var targetId = button.getAttribute('data-os2-dictate-target');
        var target = targetId ? document.getElementById(targetId) : null;
        if (!target) return;

        var statusEl = room.querySelector('[data-os2-dictate-status]');
        var errorEl = room.querySelector('[data-os2-dictate-error]');
        var labelEl = button.querySelector('[data-os2-dictate-label]');

        if (!window.PeerSlateDictation.isSupported()) {
            button.disabled = true;
            button.title = 'Speech input is not supported in this browser.';
            if (statusEl) {
                statusEl.textContent = 'Dictation is unavailable in this browser. You can paste or type the role.';
            }
            return;
        }

        var controller = window.PeerSlateDictation.createController({
            announce: announce
        });

        controller.register('source_text', {
            button: button,
            resolveTarget: function () { return target; },
            label: 'Start dictation',
            listeningLabel: 'Stop dictation',
            noun: 'role text',
            setStatus: function (text) {
                if (statusEl) statusEl.textContent = text || '';
            },
            setInterim: function () {
                /* No separate interim-preview element on this stage; the
                   shared module still calls this hook, so it must exist. */
            },
            showError: function (message) {
                if (!errorEl) return;
                errorEl.textContent = message;
                errorEl.hidden = false;
            },
            hideError: function () {
                if (!errorEl) return;
                errorEl.hidden = true;
                errorEl.textContent = '';
            },
            setButtonLabel: function (text) {
                if (labelEl) labelEl.textContent = text;
            }
        });

        button.addEventListener('click', function () {
            controller.toggle('source_text');
        });

        // Escape stops an active dictation without submitting anything,
        // mirroring the shared module's documented contract elsewhere.
        target.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && controller.isActive()) {
                controller.stop('manual');
            }
        });
    }

    function initDeferredSaveActions(room) {
        /* Stage 2: the identity/correction save buttons are undrawn in
           mockup 05 (parity F12). They stay in the DOM — explicit save is
           an invariant, and with this script absent they are always
           visible — but each is hidden until the member edits a field in
           its form, so the drawn composition holds until editing begins.
           Server-rendered error states are left untouched: if a failure
           card is present, every save action stays visible. */
        var form = room.querySelector('[data-os2-review-form]');
        if (!form) return;
        var identityFields = [
            form.querySelector('[name="employer_name"]'),
            form.querySelector('[name="role_title"]')
        ].filter(Boolean);
        var wordingField = form.querySelector('[name="corrected_text"]');
        var identityAction = form.querySelector('[data-os2-save-kind="identity"]');
        var wordingAction = form.querySelector('[data-os2-save-kind="wording"]');
        var confirm = form.querySelector('[data-os2-confirm-source]');
        var confirmHelper = form.querySelector('[data-os2-confirm-helper]');
        var keepActionsVisible = Boolean(room.querySelector('.os2-card--error'));

        function differs(field) {
            return field && field.value !== (field.getAttribute('data-os2-stored-value') || '');
        }

        function refresh() {
            var identityDirty = identityFields.some(differs);
            var wordingDirty = differs(wordingField);
            var anyDirty = identityDirty || wordingDirty;
            if (identityAction && identityAction.parentElement) {
                identityAction.parentElement.hidden = !keepActionsVisible && !identityDirty;
            }
            if (wordingAction && wordingAction.parentElement) {
                wordingAction.parentElement.hidden = !keepActionsVisible && !wordingDirty;
            }
            if (confirm) {
                confirm.setAttribute('aria-disabled', anyDirty ? 'true' : 'false');
            }
            if (confirmHelper) confirmHelper.hidden = !anyDirty;
        }

        form.addEventListener('input', refresh);
        form.addEventListener('submit', function (event) {
            var submitter = event.submitter;
            if (!submitter || !submitter.matches('[data-os2-confirm-source]')) return;
            if (submitter.getAttribute('aria-disabled') !== 'true') return;
            event.preventDefault();
            var firstDirty = identityFields.concat(wordingField || []).find(differs);
            announce('Save your visible edits before confirming this exact source.');
            if (firstDirty) firstDirty.focus();
        });
        refresh();
    }

    function initTransferRequests(room) {
        var form = room.querySelector('[data-os2-source-form]');
        if (!form || !window.AbortController || !window.fetch) return;
        var active = null;

        function setCaptureBusy(disabled) {
            room.querySelectorAll('[data-os2-review-source], [data-os2-transfer-submit]').forEach(function (control) {
                control.disabled = disabled;
            });
        }

        function transferPayload(kind, field, submitter) {
            var payload = new window.FormData();
            var sourceText = form.elements.source_text;
            var replace = form.elements.replace;
            if (sourceText) payload.set('source_text', sourceText.value);
            if (replace) payload.set('replace', replace.value);
            if (kind === 'upload') {
                payload.set('document', field.files[0], field.files[0].name);
            } else {
                payload.set('source_url', field.value.trim());
            }
            if (submitter.name) payload.set(submitter.name, submitter.value);
            return payload;
        }

        function showFailure(panel, html) {
            var target = panel.querySelector('[data-os2-transfer-error]');
            if (!target) return;
            var parsed = new window.DOMParser().parseFromString(html, 'text/html');
            var card = parsed.querySelector('.os2-card--error');
            if (card) {
                target.replaceChildren(document.importNode(card, true));
            } else {
                target.innerHTML = '<div class="os2-card os2-card--error" role="alert"><p class="os2-card__heading">We could not complete that request.</p><p class="os2-card__message">Your intake draft is still here. Try again or reload the stored version.</p></div>';
            }
        }

        form.addEventListener('submit', function (event) {
            var submitter = event.submitter;
            if (active) {
                event.preventDefault();
                announce('Wait for the current upload or import, or cancel it before starting another capture.');
                return;
            }
            if (!submitter || !submitter.matches('[data-os2-transfer-submit]')) return;
            var kind = submitter.getAttribute('data-os2-transfer-kind');
            var panel = submitter.closest('[data-os2-upload-panel], [data-os2-import-panel]');
            if (!kind || !panel) return;
            var field = kind === 'upload'
                ? room.querySelector('[name="document"]')
                : room.querySelector('[name="source_url"]');
            if (!field || (kind === 'upload' ? !field.files.length : !field.value.trim())) {
                event.preventDefault();
                field.setCustomValidity(kind === 'upload' ? 'Choose a PDF, DOCX, or TXT file.' : 'Enter a public https URL.');
                field.reportValidity();
                field.focus();
                window.setTimeout(function () { field.setCustomValidity(''); }, 0);
                return;
            }

            event.preventDefault();
            var controller = new window.AbortController();
            var state = panel.querySelector('[data-os2-transfer-state]');
            var message = panel.querySelector('[data-os2-transfer-message]');
            var cancel = panel.querySelector('[data-os2-transfer-cancel]');
            var errorTarget = panel.querySelector('[data-os2-transfer-error]');
            var label = kind === 'upload'
                ? (field.files[0].name || 'document')
                : field.value.trim();
            var payload = transferPayload(kind, field, submitter);
            active = {controller: controller, panel: panel, submitter: submitter};
            if (errorTarget) errorTarget.replaceChildren();
            if (state) state.hidden = false;
            if (message) message.textContent = (kind === 'upload' ? 'Uploading ' : 'Importing ') + label + '…';
            if (cancel) cancel.hidden = false;
            setCaptureBusy(true);
            window.fetch(submitter.formAction, {
                method: 'POST',
                body: payload,
                credentials: 'same-origin',
                headers: {'X-Requested-With': 'OpportunitySlateV2'},
                signal: controller.signal
            }).then(function (response) {
                return response.text().then(function (html) {
                    if (response.ok && response.redirected) {
                        window.location.assign(response.url);
                        return;
                    }
                    if (response.ok) {
                        var parsed = new window.DOMParser().parseFromString(html, 'text/html');
                        if (parsed.querySelector('[data-os2-stage="source_review"]')) {
                            window.location.assign(form.getAttribute('data-os2-room-url'));
                            return;
                        }
                    }
                    showFailure(panel, html);
                    var mustReload = response.status === 503;
                    if (message) {
                        message.textContent = mustReload
                            ? 'The storage outcome could not be verified. Your draft is still here; reload the stored version before retrying.'
                            : 'The request did not complete. Your intake draft is still here.';
                    }
                    if (cancel) cancel.hidden = true;
                    if (!mustReload) setCaptureBusy(false);
                    active = null;
                });
            }).catch(function (error) {
                if (error && error.name === 'AbortError') {
                    setCaptureBusy(false);
                    if (message) message.textContent = (kind === 'upload' ? 'Upload' : 'Import') + ' cancelled — nothing was captured.';
                    announce((kind === 'upload' ? 'Upload' : 'Import') + ' cancelled. Nothing was captured.');
                } else {
                    if (message) message.textContent = 'The request outcome could not be verified. Your intake draft is still here; reload the stored version before retrying.';
                    showFailure(panel, '');
                }
                if (cancel) cancel.hidden = true;
                active = null;
            });

            if (cancel) {
                cancel.onclick = function () {
                    if (active && active.controller === controller) controller.abort();
                };
            }
        });
    }

    function initDisclosures(room) {
        var disclosures = room.querySelectorAll('details.os2-alt-entry-wrap');
        disclosures.forEach(function (details) {
            details.addEventListener('toggle', function () {
                if (!details.open) return;
                var field = details.querySelector('input, textarea');
                if (field) field.focus();
            });
        });
    }

    ready(function () {
        var room = document.querySelector('[data-os2-room]');
        if (!room) return;
        initSourceReviewButton(room);
        initDictation(room);
        initDeferredSaveActions(room);
        initTransferRequests(room);
        initDisclosures(room);
    });
})();

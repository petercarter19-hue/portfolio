/* PS-ASK-PETE-AI-001: one page-memory recruiter evidence companion. */
(() => {
    'use strict';

    const REQUEST_TIMEOUT_MS = 45000;
    const SLOW_THRESHOLD_MS = 1800;
    const HIGHLIGHT_DURATION_MS = 4800;
    const MAX_MESSAGE_LENGTH = 1000;
    const VALID_ACTIONS = new Set(['recruiter_brief', 'evidence_finder', 'interview_preparation']);
    const VALID_STATES = new Set(['supported', 'partially_supported', 'not_established', 'ambiguous', 'refused', 'unavailable']);
    const VALID_KINDS = new Set(['evidence', 'interpretation', 'boundary']);
    const VALID_RECORD_ID = /^[a-z0-9-]+$/;
    const RECOVERY_PHASES = new Set(['rate_limited', 'unverifiable', 'network_error', 'timeout', 'unavailable', 'validation_error']);
    const ANSWER_FIRST_PHASES = new Set(['loading', 'slow', 'answered', ...RECOVERY_PHASES]);

    /* PS-ASK-PETE-DIRECT-001: the private question form inside the handoff
       card. It appears only when the server rendered the direct-config element
       (flag on), and it sends nothing until a person ticks the consent box and
       chooses Send. Every string below is authored here, exactly like the rest
       of the handoff card's copy; no model output is ever placed in markup by
       anything other than textContent / value. */
    const MAX_DIRECT_QUESTION_LENGTH = 2000;
    const MAX_DIRECT_CONTACT_LENGTH = 300;
    const DIRECT_HONEYPOT_FIELD = 'company_website';
    const DIRECT_COPY = {
        /* Owner direction (Pete, 2026-08-09): one compact entry point. This
           summary line is now the handoff card's whole collapsed face, so it
           carries the card's old name rather than a second, longer variant. */
        summary: 'Ask Pete directly',
        intro: 'Ask Pete answers only from information Pete approved for the public. If your question needs Pete himself, send it to him here.',
        questionLabel: 'Your question for Pete',
        contactLabel: 'How Pete can reach you (optional)',
        contactHelp: 'Whatever you want him to have - a name, a company, an email address. Leave it blank and he will have no way to reply.',
        honeypotLabel: 'Company website',
        /* Owner decision 2026-08-08 ("published always"): every sentence a
           visitor reads has to be true TODAY, not once a later leg lands. The
           closing sentence therefore describes only what actually happens -
           Pete archives, and no automated retention exists to expire or delete
           anything. It previously promised "archive after 90 days and remove
           after 180", which nothing in this package implements and which it
           could not implement, because a hard delete is outside the package.
           The claim made now is strictly weaker than that draft, so if the
           scheduled-maintenance leg ever lands this sentence can be
           strengthened to the timed promise without having misled anyone in
           the meantime. */
        consent: "What happens to this: your question, and anything you type above, are stored privately for Pete. Only Pete can read them. They are never published, never shown on this site, and never used to teach Ask Pete anything. Pete replies himself, using the contact details you chose to leave - nothing is sent back automatically, and he reads these on his own schedule. Pete manages these himself: he archives what he has read, and keeps a message for as long as he needs it - nothing here is removed on an automatic timetable.",
        agree: 'I agree to send this question, and anything I typed above, to Pete privately.',
        submit: 'Send to Pete',
        meta: 'Nothing is sent until you choose Send to Pete.',
        needQuestion: 'Not sent - write the question you want Pete to answer.',
        tooLong: `Not sent - keep the question to ${MAX_DIRECT_QUESTION_LENGTH.toLocaleString()} characters or fewer.`,
        contactTooLong: `Not sent - keep the contact details to ${MAX_DIRECT_CONTACT_LENGTH} characters or fewer.`,
        needConsent: 'Not sent - agree to the note above first.',
        sending: 'Sending your question to Pete...',
        sent: 'Sent privately to Pete. He reads these on his own schedule and replies himself if he has something useful to say.',
        alreadySent: 'That question was already sent. Pete reads these on his own schedule.',
        limited: 'Not sent - too many questions from this connection just now. You can try again later, or use the contact link above.',
        unavailable: 'Not sent - sending a question to Pete directly is unavailable right now. You can use the contact link above.',
        error: 'Not sent - the service could not be reached. You can try again, or use the contact link above.',
    };

    function directRequestKey() {
        const uuid = window.crypto && typeof window.crypto.randomUUID === 'function'
            ? window.crypto.randomUUID()
            : null;
        if (uuid) return uuid;
        /* A non-secure context (plain http, e.g. a local preview) has no
           randomUUID. Any unpredictable, per-attempt string satisfies the
           idempotency contract; it is never an identifier of anything. */
        const bytes = new Uint8Array(16);
        if (window.crypto && typeof window.crypto.getRandomValues === 'function') {
            window.crypto.getRandomValues(bytes);
        } else {
            for (let index = 0; index < bytes.length; index += 1) {
                bytes[index] = Math.floor(Math.random() * 256);
            }
        }
        return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
    }

    function isPlainObject(value) {
        return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
    }

    function makeElement(tagName, className, text) {
        const element = document.createElement(tagName);
        if (className) element.className = className;
        if (typeof text === 'string') element.textContent = text;
        return element;
    }

    function appendText(parent, tagName, className, text) {
        const element = makeElement(tagName, className, text);
        parent.appendChild(element);
        return element;
    }

    function safeText(value, fallback = '') {
        return typeof value === 'string' ? value : fallback;
    }

    function validContextKey(value) {
        return typeof value === 'string'
            && /^(profile|career_role|skill|achievement):[a-z0-9-]+$/.test(value)
            ? value
            : null;
    }

    function readablePurpose(purpose) {
        if (purpose === 'recruiter_brief') return "Pete's 60-second recruiter brief";
        if (purpose === 'evidence_finder') return "Evidence from Pete's approved public information";
        if (purpose === 'interview_preparation') return 'Useful interview questions for Pete';
        return 'Ask Pete AI answer';
    }

    function supportClass(state) {
        return `ask-pete-support-badge--${String(state || 'unavailable').replaceAll('_', '-')}`;
    }

    function supportText(state, label) {
        if (typeof label === 'string' && label.trim()) return label.trim();
        return {
            supported: 'Supported',
            partially_supported: 'Partially supported',
            not_established: 'Not established publicly',
            ambiguous: 'Needs clarification',
            refused: 'Cannot answer this request',
            unavailable: 'Temporarily unavailable',
        }[state] || 'Unavailable';
    }

    function normalizeLocator(locator) {
        if (!isPlainObject(locator)) return null;
        const recordKind = safeText(locator.record_kind);
        const recordId = safeText(locator.record_id);
        const section = safeText(locator.section);
        const anchor = safeText(locator.anchor);
        if (!VALID_RECORD_ID.test(recordId)) return null;
        const expected = {
            profile: { section: 'overview', anchor: 'resume-overview' },
            career_role: { section: 'experience', anchor: `r2-exp-card-${recordId}` },
            skill: { section: 'skills', anchor: `r2-skill-panel-${recordId}` },
            achievement: { section: 'credentials', anchor: `r2-credential-record-achievement-${recordId}` },
        }[recordKind];
        if (!expected || expected.section !== section || expected.anchor !== anchor) return null;
        return { section, anchor, recordKind, recordId, highlightKey: safeText(locator.highlight_key) };
    }

    function validateStructuredPayload(payload) {
        if (!isPlainObject(payload) || payload.schema_version !== 'ask-pete-public-answer.v1') return null;
        if (!VALID_STATES.has(payload.state) || typeof payload.summary !== 'string') return null;
        if (!Array.isArray(payload.claims) || !Array.isArray(payload.follow_up_questions) || !Array.isArray(payload.sources_used)) return null;
        if (!isPlainObject(payload.source_summary) || typeof payload.source_summary.label !== 'string') return null;
        for (const claim of payload.claims) {
            if (!isPlainObject(claim) || typeof claim.text !== 'string') return null;
            if (!VALID_STATES.has(claim.state) || !VALID_KINDS.has(claim.kind) || !Array.isArray(claim.citations)) return null;
            if (claim.limitation !== null && claim.limitation !== undefined && typeof claim.limitation !== 'string') return null;
            if (!claim.citations.every((citation) => isPlainObject(citation)
                && typeof citation.excerpt === 'string'
                && typeof citation.source_title === 'string'
                && normalizeLocator(citation.locator))) return null;
        }
        if (!payload.follow_up_questions.every((question) => typeof question === 'string')) return null;
        if (!payload.sources_used.every((source) => isPlainObject(source)
            && typeof source.title === 'string'
            && normalizeLocator(source.locator))) return null;
        if (payload.handoff !== null && payload.handoff !== undefined && !isPlainObject(payload.handoff)) return null;
        if (payload.context !== null && payload.context !== undefined) {
            if (!isPlainObject(payload.context)) return null;
            const contextKey = payload.context.context_key;
            if (contextKey !== null && contextKey !== undefined && !validContextKey(contextKey)) return null;
        }
        return payload;
    }

    document.addEventListener('DOMContentLoaded', () => {
        const page = document.querySelector('[data-ask-pete-evidence-active]');
        const companion = document.querySelector('[data-ask-pete-companion]');
        if (!page || !companion) return;

        const elements = {
            close: companion.querySelector('[data-ask-pete-close]'),
            capability: companion.querySelector('[data-ask-pete-capability]'),
            context: companion.querySelector('[data-ask-pete-context]'),
            contextLabel: companion.querySelector('[data-ask-pete-context-label]'),
            contextCount: companion.querySelector('[data-ask-pete-context-count]'),
            form: companion.querySelector('[data-ask-pete-form]'),
            input: companion.querySelector('[data-ask-pete-input]'),
            submit: companion.querySelector('[data-ask-pete-submit]'),
            cancel: companion.querySelector('[data-ask-pete-cancel]'),
            status: companion.querySelector('[data-ask-pete-status]'),
            answer: companion.querySelector('[data-ask-pete-answer]'),
            recovery: companion.querySelector('[data-ask-pete-recovery]'),
            recoveryTitle: companion.querySelector('[data-ask-pete-recovery-title]'),
            recoveryMessage: companion.querySelector('[data-ask-pete-recovery-message]'),
        };
        if (Object.values(elements).some((value) => !value)) return;

        /* PS-ASK-PETE-DIRECT-001. Deliberately NOT a member of `elements`: that
           object's all-or-nothing guard above would disable the ENTIRE
           companion whenever this optional element is absent, which is every
           deployment today. Absent config simply means no private form, and
           everything else behaves exactly as it did before. The endpoint is
           re-validated as a same-origin path here rather than trusted because
           it arrives from the DOM. */
        const directConfig = companion.querySelector('[data-ask-pete-direct-config]');
        const directEndpoint = directConfig
            && isSafeSameOriginPath(directConfig.dataset.askPeteDirectEndpoint)
            ? directConfig.dataset.askPeteDirectEndpoint
            : null;

        /* The rail's OWN scroll container (`overflow: auto`). Kept out of
           `elements` for the same reason as directConfig: the all-or-nothing
           guard above must never be able to disable the whole companion over a
           scrolling nicety. */
        const scroller = companion.querySelector('.ask-pete-evidence-companion__scroll');

        const state = {
            layout: 'wide_rail', open: false, phase: 'idle', draft: '',
            requestedAction: null, explicitContext: null, viewingSection: 'overview',
            /* `previousAnswer` retains exactly ONE prior answer, never a
               growing history - see restorePreviousAnswer below. */
            answer: null, previousAnswer: null,
            lastInvoker: null, requestSequence: 0, abortController: null,
            slowTimer: null, timeoutTimer: null, timeoutSequence: null, revealOnReturn: false,
            highlightedTargets: new Set(), highlightTimers: new Map(), selectedSourceTarget: null,
        };

        function currentLayout() {
            if (window.matchMedia('(max-width: 60rem)').matches) return 'mobile_sheet';
            if (window.matchMedia('(max-width: 90rem)').matches) return 'narrow_sheet';
            return 'wide_rail';
        }

        function isWide() { return state.layout === 'wide_rail'; }
        function hasStableContent() { return Boolean(state.answer || elements.input.value.trim() || state.explicitContext); }

        function updateOpeners() {
            document.querySelectorAll('[data-ask-pete-open], [data-ask-pete-context-action]').forEach((opener) => {
                opener.setAttribute('aria-expanded', String(isWide() || state.open));
            });
        }

        function syncLayout() {
            const previousLayout = state.layout;
            state.layout = currentLayout();
            if (previousLayout === 'wide_rail' && !isWide() && hasStableContent()) state.open = true;
            const visible = isWide() || state.open;
            companion.hidden = !visible;
            companion.inert = !visible;
            companion.classList.toggle('is-open', visible);
            companion.dataset.askPeteLayout = state.layout;
            updateOpeners();
        }

        function setStatus(message) { elements.status.textContent = message || ''; }
        function hasStableAnswer() { return Boolean(state.answer); }
        function setPhase(phase) {
            state.phase = phase;
            companion.dataset.askPetePhase = phase;
            const answerFirst = ANSWER_FIRST_PHASES.has(phase);
            elements.capability.hidden = answerFirst || phase === 'context_ready';
            companion.classList.toggle('is-answer-first', answerFirst);
            elements.answer.hidden = !hasStableAnswer();
            if (!RECOVERY_PHASES.has(phase)) elements.recovery.hidden = true;
        }

        function renderRecovery(phase, message) {
            if (!hasStableAnswer()) elements.answer.replaceChildren();
            setPhase(phase);
            elements.recoveryTitle.textContent = {
                rate_limited: 'Ask Pete needs a moment',
                unverifiable: 'Ask Pete could not verify this answer',
                network_error: 'Ask Pete could not reach the service',
                timeout: 'Ask Pete took too long to respond',
                validation_error: 'Ask Pete needs a clearer question',
                unavailable: 'Ask Pete is temporarily unavailable',
            }[phase] || 'Ask Pete needs another path';
            elements.recoveryMessage.textContent = message;
            elements.recovery.hidden = false;
            setStatus(message);
        }


        function renderContext() {
            elements.context.hidden = !state.explicitContext;
            if (state.explicitContext) {
                elements.contextLabel.textContent = state.explicitContext.label;
                const count = state.explicitContext.evidenceItemCount;
                elements.contextCount.textContent = Number.isFinite(count)
                    ? `${count} approved evidence item${count === 1 ? '' : 's'}`
                    : 'Approved public information only';
                return;
            }
            const labels = { overview: 'Overview', summary: 'Overview', impact: 'Impact', skills: 'Skills', experience: 'Experience', credentials: 'Credentials' };
            elements.contextLabel.textContent = `Viewing: ${labels[state.viewingSection] || 'Resume'}`;
            elements.contextCount.textContent = 'Answers use Pete-approved public information.';
        }

        function openCompanion(invoker, focusInput = true) {
            if (invoker instanceof HTMLElement && !companion.contains(invoker)) state.lastInvoker = invoker;
            if (!isWide()) state.open = true;
            syncLayout();
            renderContext();
            if (focusInput) window.requestAnimationFrame(() => {
                if (!companion.hidden) elements.input.focus({ preventScroll: true });
            });
        }

        function closeCompanion({ restoreFocus = true } = {}) {
            if (isWide()) return;
            state.open = false;
            syncLayout();
            const invoker = state.lastInvoker;
            if (restoreFocus && invoker && document.contains(invoker)) {
                window.requestAnimationFrame(() => invoker.focus({ preventScroll: true }));
            }
        }

        function setRequestControls(isSubmitting) {
            elements.submit.disabled = isSubmitting;
            elements.cancel.hidden = !isSubmitting;
            elements.input.setAttribute('aria-busy', String(isSubmitting));
            companion.setAttribute('aria-busy', String(isSubmitting));
        }

        function clearRequestTimers() {
            if (state.slowTimer) window.clearTimeout(state.slowTimer);
            if (state.timeoutTimer) window.clearTimeout(state.timeoutTimer);
            state.slowTimer = null;
            state.timeoutTimer = null;
            state.timeoutSequence = null;
        }

        function cancelActiveRequest({ announce = true } = {}) {
            if (state.abortController) state.abortController.abort();
            state.abortController = null;
            clearRequestTimers();
            setRequestControls(false);
            if (state.phase === 'loading' || state.phase === 'slow') {
                setPhase(state.answer ? 'answered' : (state.explicitContext ? 'context_ready' : 'idle'));
            }
            if (announce) setStatus('The request was cancelled. You can revise the question and try again.');
        }

        function completeRecovery(phase, message) {
            clearRequestTimers();
            state.abortController = null;
            setRequestControls(false);
            renderRecovery(phase, message);
        }

        function prepareNewRequest() {
            elements.recovery.hidden = true;
            clearEvidenceMarkers();
        }

        function recoveryForResponse(response, payload) {
            if (response.status === 429) {
                return {
                    phase: 'rate_limited',
                    message: 'Ask Pete needs a moment before another answer. You can keep reviewing the resume, open the PDF, or contact Pete directly.',
                };
            }
            if (response.status === 502) {
                return {
                    phase: 'unverifiable',
                    message: 'Ask Pete could not verify this answer against approved public information. You can continue reviewing the resume or contact Pete directly.',
                };
            }
            if (response.status >= 500) {
                return {
                    phase: 'unavailable',
                    message: 'Ask Pete is temporarily unavailable. You can continue reviewing the resume, open the PDF, or contact Pete directly.',
                };
            }
            return {
                phase: 'validation_error',
                message: safeText(payload && payload.error, 'Ask Pete could not use that question as written. Please revise it and try again.'),
            };
        }

        function requestAnswer(requestedAction) {
            const message = elements.input.value.trim();
            const action = VALID_ACTIONS.has(requestedAction) ? requestedAction : 'evidence_finder';
            if (!message) {
                renderRecovery('validation_error', 'Enter a question before asking Pete AI.');
                elements.input.focus();
                return;
            }
            if (message.length > MAX_MESSAGE_LENGTH) {
                renderRecovery('validation_error', 'Keep the question to 1,000 characters or fewer.');
                elements.input.focus();
                return;
            }

            cancelActiveRequest({ announce: false });
            const sequence = state.requestSequence + 1;
            state.requestSequence = sequence;
            state.requestedAction = action;
            state.draft = message;
            prepareNewRequest();
            setPhase('loading');
            setRequestControls(true);
            setStatus('Reviewing Pete-approved public information...');
            const controller = new AbortController();
            state.abortController = controller;

            state.slowTimer = window.setTimeout(() => {
                if (sequence !== state.requestSequence || controller.signal.aborted) return;
                setPhase('slow');
                setStatus('This is taking longer than expected. You can keep reviewing the resume while the answer finishes.');
            }, SLOW_THRESHOLD_MS);

            state.timeoutSequence = sequence;
            state.timeoutTimer = window.setTimeout(() => {
                if (sequence !== state.requestSequence || controller.signal.aborted) return;
                controller.abort();
                completeRecovery(
                    'timeout',
                    'Ask Pete took too long to respond. You can try again, continue reviewing the resume, open the PDF, or contact Pete directly.'
                );
            }, REQUEST_TIMEOUT_MS);

            const contextKey = state.explicitContext ? state.explicitContext.contextKey : null;
            window.fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ message, action, context_key: contextKey }),
                signal: controller.signal,
            })
                .then(async (response) => {
                    let payload = null;
                    try { payload = await response.json(); } catch (error) { payload = null; }
                    if (!response.ok) throw { kind: 'response', response, payload };
                    const validated = validateStructuredPayload(payload);
                    if (!validated) throw { kind: 'unverifiable' };
                    return validated;
                })
                .then((payload) => {
                    if (sequence !== state.requestSequence || controller.signal.aborted) return;
                    clearRequestTimers();
                    state.abortController = null;
                    if (payload.state === 'unavailable') {
                        completeRecovery(
                            'unavailable',
                            safeText(payload.summary, 'Ask Pete is temporarily unavailable. You can continue reviewing the resume, open the PDF, or contact Pete directly.')
                        );
                        return;
                    }
                    const expectedContextKey = state.explicitContext ? state.explicitContext.contextKey : null;
                    const returnedContextKey = isPlainObject(payload.context)
                        ? safeContextKey(payload.context.context_key)
                        : null;
                    if (expectedContextKey && returnedContextKey !== expectedContextKey) {
                        state.explicitContext = null;
                        elements.context.hidden = true;
                    }
                    /* Retain exactly one prior answer before replacing it, so
                       "Back to previous answer" has something to return to. */
                    if (state.answer) state.previousAnswer = state.answer;
                    state.answer = payload;
                    setPhase('answered');
                    setRequestControls(false);
                    setStatus('Answer ready. The claims and evidence behind it expand below the summary.');
                    renderAnswer(payload);
                })
                .catch((error) => {
                    if (sequence !== state.requestSequence) return;
                    if (error && error.name === 'AbortError') {
                        if (state.timeoutSequence !== sequence) return;
                        return;
                    }
                    if (error && error.kind === 'response') {
                        const recovery = recoveryForResponse(error.response, error.payload);
                        clearRequestTimers();
                        state.abortController = null;
                        setRequestControls(false);
                        renderRecovery(recovery.phase, recovery.message);
                        return;
                    }
                    if (error && error.kind === 'unverifiable') {
                        completeRecovery(
                            'unverifiable',
                            'Ask Pete could not verify this answer against approved public information. You can continue reviewing the resume, open the PDF, or contact Pete directly.'
                        );
                        return;
                    }
                    completeRecovery(
                        'network_error',
                        'Ask Pete could not reach the service. You can continue reviewing the resume, open the PDF, or contact Pete directly.'
                    );
                });
        }

        function makeSupportBadge(answerState, label) {
            return makeElement('span', `ask-pete-support-badge ${supportClass(answerState)}`, supportText(answerState, label));
        }

        function makeSourceButton(citation, className = 'ask-pete-evidence-source') {
            const locator = normalizeLocator(citation.locator);
            if (!locator) return null;
            const button = makeElement('button', className);
            button.type = 'button';
            button.dataset.askPeteSource = '';
            button.dataset.askPeteSection = locator.section;
            button.dataset.askPeteAnchor = locator.anchor;
            button.dataset.askPeteRecordKind = locator.recordKind;
            button.dataset.askPeteRecordId = locator.recordId;
            button.dataset.askPeteHighlightKey = locator.highlightKey;
            button.textContent = `Open ${safeText(citation.source_title || citation.title, 'resume evidence')} \u2192`;
            return button;
        }

        /* Owner direction (Pete, 2026-08-09), redesigning the accepted cards:
           one claim sentence per card; no badge where support is established
           ("it's clear that there's evidence") and nuanced wording ONLY where
           something is not; excerpt only on expand; one source line with ONE
           action per source, replacing the old Show evidence/Open pairs that
           named each source twice. */
        function renderClaim(claim, answerSequence, claimIndex) {
            const claimCard = makeElement('article', `ask-pete-evidence-claim ask-pete-evidence-claim--${claim.kind} ask-pete-evidence-claim--${String(claim.state).replaceAll('_', '-')}`);
            const detailId = `ask-pete-claim-${answerSequence}-${claimIndex}`;
            const hasDetail = Boolean(claim.limitation || claim.citations.length);

            const face = makeElement(hasDetail ? 'button' : 'div', 'ask-pete-evidence-claim__face');
            if (hasDetail) {
                face.type = 'button';
                face.dataset.askPeteClaimToggle = '';
                face.setAttribute('aria-expanded', 'false');
                face.setAttribute('aria-controls', detailId);
            }
            appendText(face, 'span', 'ask-pete-evidence-claim__text', claim.text);
            if (claim.state !== 'supported') {
                face.appendChild(makeSupportBadge(claim.state, claim.support_label));
            } else if (claim.kind === 'interpretation') {
                /* An interpretation is the one supported kind that still is
                   not a directly established fact, so its quiet label stays. */
                appendText(face, 'span', 'ask-pete-evidence-claim__kind', 'Interpretation');
            }
            claimCard.appendChild(face);

            if (!hasDetail) return claimCard;
            const detail = makeElement('div', 'ask-pete-evidence-claim__detail');
            detail.id = detailId;
            detail.hidden = true;
            if (claim.limitation) {
                appendText(detail, 'p', 'ask-pete-evidence-claim__limitation', claim.limitation);
            }
            claim.citations.forEach((citation) => {
                const row = makeElement('div', 'ask-pete-evidence-citation');
                appendText(row, 'p', 'ask-pete-evidence-citation__excerpt', `“${safeText(citation.excerpt)}”`);
                const button = makeSourceButton(citation);
                if (button) {
                    row.appendChild(button);
                } else {
                    appendText(row, 'span', 'ask-pete-evidence-citation__title', citation.source_title);
                }
                detail.appendChild(row);
            });
            claimCard.appendChild(detail);
            return claimCard;
        }

        function toggleClaim(face) {
            const detailId = safeText(face.getAttribute('aria-controls'));
            const detail = detailId ? document.getElementById(detailId) : null;
            if (!detail || !elements.answer.contains(detail)) return;
            const shouldExpand = face.getAttribute('aria-expanded') !== 'true';
            face.setAttribute('aria-expanded', String(shouldExpand));
            face.closest('.ask-pete-evidence-claim')?.classList.toggle('is-expanded', shouldExpand);
            detail.hidden = !shouldExpand;
        }

        /* Owner direction (Pete, 2026-08-09): the whole evidence body folds
           behind one line \u2014 "N claims \u00b7 <source summary> \u00b7 See the evidence" \u2014
           and the cards expand on tap. The claims still arrive, still render,
           and are still individually inspectable; only the default altitude
           changed. (The suggested-questions block is dropped outright by the
           same direction \u2014 the payload still carries the questions, the
           companion just no longer renders them.) */
        function renderEvidenceFold(payload, claims) {
            const section = makeElement('section', 'ask-pete-evidence-fold');
            const bar = makeElement('div', 'ask-pete-evidence-fold__bar');
            const label = `${claims.length} claim${claims.length === 1 ? '' : 's'} \u00b7 ${safeText(payload.source_summary.label)}`;
            appendText(bar, 'span', 'ask-pete-evidence-fold__label', label);
            const bodyId = `ask-pete-evidence-fold-${state.requestSequence}`;
            const toggle = makeElement('button', 'ask-pete-evidence-fold__toggle', 'See the evidence');
            toggle.type = 'button';
            toggle.dataset.askPeteFoldToggle = '';
            toggle.setAttribute('aria-expanded', 'false');
            toggle.setAttribute('aria-controls', bodyId);
            bar.appendChild(toggle);
            section.appendChild(bar);

            const body = makeElement('div', 'ask-pete-evidence-fold__body');
            body.id = bodyId;
            body.hidden = true;
            claims.forEach((claim, claimIndex) => {
                body.appendChild(renderClaim(claim, state.requestSequence, claimIndex));
            });
            if (payload.source_summary.show_all_on_resume && payload.sources_used.length) {
                const showAll = makeElement('button', 'ask-pete-evidence-show-all', 'Show all on resume \u2192');
                showAll.type = 'button';
                showAll.dataset.askPeteShowAll = '';
                body.appendChild(showAll);
            }
            section.appendChild(body);
            return section;
        }

        function toggleEvidenceFold(toggle) {
            const bodyId = safeText(toggle.getAttribute('aria-controls'));
            const body = bodyId ? document.getElementById(bodyId) : null;
            if (!body || !elements.answer.contains(body)) return;
            const shouldExpand = toggle.getAttribute('aria-expanded') !== 'true';
            toggle.setAttribute('aria-expanded', String(shouldExpand));
            toggle.textContent = shouldExpand ? 'Hide the evidence' : 'See the evidence';
            body.hidden = !shouldExpand;
        }

        function isSafeSameOriginPath(value) {
            return typeof value === 'string' && /^\/[a-z0-9/_-]*$/i.test(value);
        }

        function renderDirectQuestionForm(payload, sequence) {
            /* Rendered only when the server said the private path exists. With
               the flag off the config element is not in the document at all,
               so this returns null and the handoff card is exactly what it was
               before this package. */
            if (!directEndpoint) return null;

            const details = makeElement('details', 'ask-pete-direct');
            const summary = makeElement('summary', 'ask-pete-direct__summary', DIRECT_COPY.summary);
            details.appendChild(summary);
            appendText(details, 'p', 'ask-pete-direct__intro', DIRECT_COPY.intro);

            const form = makeElement('form', 'ask-pete-evidence-composer ask-pete-direct__form');
            form.noValidate = true;

            const questionId = `ask-pete-direct-question-${sequence}`;
            const questionLabel = appendText(form, 'label', null, DIRECT_COPY.questionLabel);
            questionLabel.htmlFor = questionId;
            const field = makeElement('div', 'ask-pete-evidence-composer__field');
            const questionInput = makeElement('textarea');
            questionInput.id = questionId;
            questionInput.rows = 3;
            questionInput.maxLength = MAX_DIRECT_QUESTION_LENGTH;
            /* The model's suggested wording, placed as a VALUE - never as
               markup - and fully editable. The person sends their own words. */
            questionInput.value = safeText(payload.handoff.question).trim();
            const submit = makeElement('button', null, DIRECT_COPY.submit);
            submit.type = 'submit';
            /* A STYLING hook, shared deliberately with the composer so this
               button is the accepted submit treatment
               (`.ask-pete-evidence-composer [data-ask-pete-submit]`) rather
               than a new one. It is not a controller hook: `elements.submit`
               is resolved once at init, before this form can exist, so the two
               never collide. Select it as
               `[data-ask-pete-form] [data-ask-pete-submit]` when you mean the
               composer's. */
            submit.dataset.askPeteSubmit = '';
            field.appendChild(questionInput);
            field.appendChild(submit);
            form.appendChild(field);

            const contactId = `ask-pete-direct-contact-${sequence}`;
            const contactHelpId = `ask-pete-direct-contact-help-${sequence}`;
            const contactLabel = appendText(form, 'label', null, DIRECT_COPY.contactLabel);
            contactLabel.htmlFor = contactId;
            const contactInput = makeElement('textarea');
            contactInput.id = contactId;
            contactInput.rows = 2;
            contactInput.maxLength = MAX_DIRECT_CONTACT_LENGTH;
            contactInput.setAttribute('aria-describedby', contactHelpId);
            form.appendChild(contactInput);
            const contactHelp = appendText(form, 'p', 'ask-pete-direct__help', DIRECT_COPY.contactHelp);
            contactHelp.id = contactHelpId;

            const honeypot = makeElement('div', 'ask-pete-direct__honeypot');
            honeypot.setAttribute('aria-hidden', 'true');
            const honeypotId = `ask-pete-direct-hp-${sequence}`;
            const honeypotLabel = appendText(honeypot, 'label', null, DIRECT_COPY.honeypotLabel);
            honeypotLabel.htmlFor = honeypotId;
            const honeypotInput = makeElement('textarea');
            honeypotInput.id = honeypotId;
            honeypotInput.rows = 1;
            honeypotInput.tabIndex = -1;
            honeypotInput.autocomplete = 'off';
            honeypot.appendChild(honeypotInput);
            form.appendChild(honeypot);

            appendText(form, 'p', 'ask-pete-direct__consent', DIRECT_COPY.consent);

            const agree = makeElement('label', 'ask-pete-direct__agree');
            const consentInput = document.createElement('input');
            consentInput.type = 'checkbox';
            agree.appendChild(consentInput);
            agree.appendChild(makeElement('span', null, DIRECT_COPY.agree));
            form.appendChild(agree);

            const meta = makeElement('div', 'ask-pete-evidence-composer__meta');
            appendText(meta, 'span', null, DIRECT_COPY.meta);
            form.appendChild(meta);

            const stateLine = makeElement('p', 'ask-pete-direct__state');
            stateLine.setAttribute('role', 'status');
            stateLine.setAttribute('aria-live', 'polite');
            stateLine.setAttribute('aria-atomic', 'true');
            form.appendChild(stateLine);

            let requestKey = null;
            let sending = false;

            function announce(message, tone) {
                stateLine.textContent = message;
                stateLine.classList.toggle('ask-pete-direct__state--sent', tone === 'sent');
                stateLine.classList.toggle('ask-pete-direct__state--problem', tone === 'problem');
                /* The companion's own live region carries it too, so the
                   announcement reaches a reader whose focus is elsewhere. */
                setStatus(message);
            }

            function setSending(isSending) {
                sending = isSending;
                submit.disabled = isSending;
                form.setAttribute('aria-busy', String(isSending));
            }

            /* Editing after an attempt is a NEW question, so it gets a new
               idempotency key. Retrying unchanged text keeps the old key, which
               is what makes a double tap or a retry after a dropped connection
               store one question rather than two. */
            const forgetKey = () => { requestKey = null; };
            questionInput.addEventListener('input', forgetKey);
            contactInput.addEventListener('input', forgetKey);

            form.addEventListener('submit', (event) => {
                event.preventDefault();
                if (sending) return;

                const question = questionInput.value.trim();
                const contact = contactInput.value.trim();
                if (!question) {
                    announce(DIRECT_COPY.needQuestion, 'problem');
                    questionInput.focus();
                    return;
                }
                if (question.length > MAX_DIRECT_QUESTION_LENGTH) {
                    announce(DIRECT_COPY.tooLong, 'problem');
                    questionInput.focus();
                    return;
                }
                if (contact.length > MAX_DIRECT_CONTACT_LENGTH) {
                    announce(DIRECT_COPY.contactTooLong, 'problem');
                    contactInput.focus();
                    return;
                }
                if (!consentInput.checked) {
                    announce(DIRECT_COPY.needConsent, 'problem');
                    consentInput.focus();
                    return;
                }

                if (!requestKey) requestKey = directRequestKey();
                setSending(true);
                announce(DIRECT_COPY.sending, null);

                const body = { question, consent: true };
                if (contact) body.contact = contact;
                if (honeypotInput.value) body[DIRECT_HONEYPOT_FIELD] = honeypotInput.value;

                window.fetch(directEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-PeerSlate-Request': 'same-origin',
                        'Idempotency-Key': requestKey,
                    },
                    body: JSON.stringify(body),
                })
                    .then(async (response) => {
                        let result = null;
                        try { result = await response.json(); } catch (error) { result = null; }
                        return { response, result };
                    })
                    .then(({ response, result }) => {
                        setSending(false);
                        if (response.ok && isPlainObject(result) && result.success === true) {
                            announce(
                                result.state === 'already_sent' ? DIRECT_COPY.alreadySent : DIRECT_COPY.sent,
                                'sent'
                            );
                            submit.disabled = true;
                            questionInput.readOnly = true;
                            contactInput.readOnly = true;
                            consentInput.disabled = true;
                            return;
                        }
                        if (response.status === 429) {
                            announce(DIRECT_COPY.limited, 'problem');
                            return;
                        }
                        if (response.status === 422 || response.status === 413) {
                            /* The server's validation sentences are authored
                               server-side for a sender to read; they are placed
                               with textContent regardless. */
                            announce(
                                isPlainObject(result) && typeof result.message === 'string'
                                    ? result.message
                                    : DIRECT_COPY.error,
                                'problem'
                            );
                            return;
                        }
                        announce(DIRECT_COPY.unavailable, 'problem');
                    })
                    .catch(() => {
                        setSending(false);
                        announce(DIRECT_COPY.error, 'problem');
                    });
            });

            details.appendChild(form);
            return details;
        }

        /* Owner direction (Pete, 2026-08-09): the old card offered "Ask Pete
           directly" AND "Contact Pete directly" AND "Send this question to
           Pete privately" — three names for one idea. Now there is exactly ONE
           compact entry point: the private-question disclosure when that path
           exists, otherwise a single contact link. The honesty line about
           nothing being sent automatically lives inside the form, next to the
           only control that could send anything. */
        function renderHandoff(payload) {
            if (!payload.handoff || payload.handoff.available !== true) return null;
            const section = makeElement('section', 'ask-pete-evidence-handoff');
            const directForm = renderDirectQuestionForm(payload, state.requestSequence);
            if (directForm) {
                section.appendChild(directForm);
                return section;
            }
            const contactUrl = companion.dataset.askPeteContactUrl;
            if (!isSafeSameOriginPath(contactUrl)) return null;
            const link = makeElement('a', null, safeText(payload.handoff.label, 'Contact Pete directly'));
            link.href = contactUrl;
            section.appendChild(link);
            return section;
        }

        /* Owner-reported defect (Pete, 2026-08-08): "the sixty second recruiter
           view is a two second recruiter view... a lot of information, sorted
           out weird."

           The DOM order was already answer-first - heading, support state,
           summary, claims, then sources, follow-ups and the handoff card. What
           was missing was any scroll management of the rail AT ALL: the two
           existing scrollIntoView calls both move the RESUME, never this
           container. So the rail kept whatever scrollTop it had, and a
           recruiter who has just typed in the composer is scrolled to the
           bottom of the rail. Inserting a tall answer above the composer left
           them looking at its tail - follow-ups and the contact card - with
           the summary scrolled off the top. That is what "sorted out weird"
           was seeing.

           The accepted authority is explicit that state 4 renders "answer
           first, followed by clearly associated claims and inspectable
           evidence" (02_BACKEND_CONTRACT_AND_VISUAL_HANDOFF), that `summary`
           is "the concise answer-first synthesis"
           (03_VISUAL_RUNTIME_ARCHITECTURE), and that the flagship desktop
           answer is "compact enough to inspect in one rail view"
           (this stylesheet, the is-answer-first block). So this is a DEFECT
           against the locked design, not a change to it.

           Only this container is scrolled. scrollIntoView is deliberately not
           used: it walks every scrollable ancestor, which would drag the
           résumé behind the rail as a side effect. */
        function revealAnswerTop() {
            if (!scroller || elements.answer.hidden) return;
            const offset = elements.answer.getBoundingClientRect().top
                - scroller.getBoundingClientRect().top;
            if (Math.abs(offset) < 2) return;
            const top = Math.max(0, scroller.scrollTop + offset);
            /* Proven live 2026-08-09: browsers suppress smooth scrolling in a
               hidden tab, so an answer that lands while the visitor is on
               another tab gets the instant jump a reduced-motion visitor
               gets - and the reveal re-runs once when the tab returns, in
               case the browser swallowed even that. */
            const instant = hasReducedMotion() || document.visibilityState === 'hidden';
            if (document.visibilityState === 'hidden') state.revealOnReturn = true;
            if (typeof scroller.scrollTo === 'function') {
                scroller.scrollTo({ top, behavior: instant ? 'auto' : 'smooth' });
                return;
            }
            scroller.scrollTop = top;
        }

        function makeBackButton() {
            const button = makeElement('button', 'ask-pete-evidence-back', 'Back to previous answer');
            button.type = 'button';
            button.dataset.askPeteBack = '';
            return button;
        }

        function renderAnswer(payload) {
            const fragment = document.createDocumentFragment();
            const heading = makeElement('h3', 'ask-pete-evidence-answer__heading', readablePurpose(payload.purpose));
            heading.id = `ask-pete-answer-heading-${state.requestSequence}`;
            elements.answer.setAttribute('aria-labelledby', heading.id);
            fragment.appendChild(heading);
            const meta = makeElement('div', 'ask-pete-evidence-answer__meta');
            /* Owner direction (Pete, 2026-08-09): one trust line at the top of
               the answer at most — this badge is it. The old machinery caption
               beside it is gone with the per-card badges it described. */
            meta.appendChild(makeSupportBadge(payload.state, payload.support_label));
            if (state.previousAnswer) meta.insertBefore(makeBackButton(), meta.firstChild);
            fragment.appendChild(meta);
            appendText(fragment, 'p', 'ask-pete-evidence-answer__summary', payload.summary);

            /* Owner direction (Pete, 2026-08-09): no boundary CARD. The server
               quality contract still requires the boundary claim, and honesty
               still requires saying it — as one quiet sentence under the
               summary rather than a boxed block. Folded visually, not
               deleted. */
            const boundaryClaims = payload.claims.filter((claim) => claim.kind === 'boundary');
            if (boundaryClaims.length) {
                appendText(
                    fragment,
                    'p',
                    'ask-pete-evidence-answer__boundary',
                    boundaryClaims.map((claim) => safeText(claim.text).trim()).filter(Boolean).join(' ')
                );
            }

            const evidenceClaims = payload.claims.filter((claim) => claim.kind !== 'boundary');
            if (evidenceClaims.length) {
                fragment.appendChild(renderEvidenceFold(payload, evidenceClaims));
            }
            const handoff = renderHandoff(payload);
            if (handoff) fragment.appendChild(handoff);
            elements.answer.replaceChildren(fragment);
            elements.answer.hidden = false;
            revealAnswerTop();
        }

        /* Owner-reported gap (Pete, 2026-08-08): "there's no way to go back."
           Asking a second question replaced the first answer outright, with
           nothing that could return to it.

           The accepted state model holds a single `answer`
           (03_VISUAL_RUNTIME_ARCHITECTURE, client state) and names
           multi-answer history as "future conversation-state work"
           (02_BACKEND_CONTRACT_AND_VISUAL_HANDOFF), so this is an
           owner-directed ADAPTATION rather than a defect fix: exactly one
           prior answer is retained, and one inline control returns to it.
           There is no history panel and no stack.

           It swaps rather than pops, so the control is truthful in both
           directions and using it can never destroy the newer answer. Two
           answers live in memory at most, and neither is ever sent back to the
           model - a follow-up stays independently grounded, exactly as the
           architecture requires. */
        function restorePreviousAnswer() {
            if (!state.previousAnswer) return;
            const restored = state.previousAnswer;
            state.previousAnswer = state.answer;
            state.answer = restored;
            clearEvidenceMarkers();
            setPhase('answered');
            renderAnswer(restored);
            setStatus('Showing the previous answer. Select it again to return to the newer one.');
        }

        function readLocatorFromElement(element) {
            return normalizeLocator({
                section: element.dataset.askPeteSection,
                anchor: element.dataset.askPeteAnchor,
                record_kind: element.dataset.askPeteRecordKind,
                record_id: element.dataset.askPeteRecordId,
                highlight_key: element.dataset.askPeteHighlightKey,
            });
        }

        function targetForLocator(locator) {
            if (!locator) return null;
            const target = document.getElementById(locator.anchor);
            if (!target) return null;
            if (locator.recordKind === 'profile') {
                return target.closest('.r2-summary') || target;
            }
            return target;
        }

        function isVisibleTarget(target) {
            return Boolean(target && !target.hidden && !target.closest('[hidden]'));
        }

        function exactRepresentativeForLocator(locator) {
            const exactTarget = targetForLocator(locator);
            if (!exactTarget) return { target: null, pendingTarget: null };
            if (isVisibleTarget(exactTarget)) return { target: exactTarget, pendingTarget: null };

            if (locator.recordKind === 'skill') {
                const skillCard = Array.from(document.querySelectorAll('[data-r2-skill-toggle]'))
                    .find((button) => button.dataset.r2SkillToggle === locator.recordId);
                return { target: skillCard || null, pendingTarget: exactTarget };
            }
            if (locator.recordKind === 'achievement') {
                const categoryButton = Array.from(document.querySelectorAll('[data-r2-credential-toggle]'))
                    .find((button) => button.dataset.r2CredentialToggle === 'recognition');
                return { target: categoryButton || null, pendingTarget: exactTarget };
            }
            return { target: null, pendingTarget: exactTarget };
        }

        function hasReducedMotion() {
            return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        }

        function clearEvidenceMarkers() {
            state.highlightTimers.forEach((timer) => window.clearTimeout(timer));
            state.highlightTimers.clear();
            state.highlightedTargets.forEach((target) => {
                target.classList.remove('ask-pete-evidence-highlight');
            });
            state.highlightedTargets.clear();
            document.querySelectorAll('[data-ask-pete-evidence-marker]').forEach((marker) => marker.remove());
            document.querySelectorAll('.ask-pete-evidence-source-selected').forEach((target) => {
                target.classList.remove('ask-pete-evidence-source-selected');
            });
            document.querySelectorAll('[data-ask-pete-pending-evidence-target]').forEach((target) => {
                target.classList.remove('ask-pete-evidence-pending-source');
                delete target.dataset.askPetePendingEvidenceTarget;
            });
            state.selectedSourceTarget = null;
        }

        function selectSourceTarget(target) {
            if (!target) return;
            if (state.selectedSourceTarget && state.selectedSourceTarget !== target) {
                state.selectedSourceTarget.classList.remove('ask-pete-evidence-source-selected');
                state.selectedSourceTarget.querySelectorAll('[data-ask-pete-evidence-marker]').forEach((marker) => marker.remove());
            }
            target.classList.add('ask-pete-evidence-source-selected');
            let marker = target.querySelector('[data-ask-pete-evidence-marker]');
            if (!marker) {
                marker = makeElement('span', 'ask-pete-evidence-selected-marker', 'Selected evidence from this Ask Pete answer');
                marker.dataset.askPeteEvidenceMarker = '';
                target.appendChild(marker);
            }
            state.selectedSourceTarget = target;
        }

        function highlightTarget(target, { scroll = false, focus = false } = {}) {
            if (!target) return;
            const existingTimer = state.highlightTimers.get(target);
            if (existingTimer) window.clearTimeout(existingTimer);
            target.classList.add('ask-pete-evidence-highlight');
            state.highlightedTargets.add(target);
            const timer = window.setTimeout(() => {
                target.classList.remove('ask-pete-evidence-highlight');
                state.highlightTimers.delete(target);
                state.highlightedTargets.delete(target);
            }, HIGHLIGHT_DURATION_MS);
            state.highlightTimers.set(target, timer);
            if (scroll) target.scrollIntoView({ behavior: hasReducedMotion() ? 'auto' : 'smooth', block: 'center', inline: 'nearest' });
            if (focus) {
                target.setAttribute('tabindex', '-1');
                window.requestAnimationFrame(() => target.focus({ preventScroll: true }));
            }
        }

        function openResumeRecord(locator, origin) {
            if (!locator) return;
            const sourceOrigin = isWide() && origin instanceof HTMLElement ? origin : null;
            if (!isWide()) closeCompanion({ restoreFocus: false });
            if (locator.recordKind === 'career_role') {
                page.dispatchEvent(new CustomEvent('r2:open-experience', { detail: { roleId: locator.recordId, origin: sourceOrigin } }));
            } else if (locator.recordKind === 'skill') {
                page.dispatchEvent(new CustomEvent('r2:open-skill', { detail: { skillId: locator.recordId, origin: sourceOrigin } }));
            } else if (locator.recordKind === 'achievement') {
                page.dispatchEvent(new CustomEvent('r2:open-credential', { detail: { categoryId: 'recognition', origin: sourceOrigin } }));
            }
            window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
                const target = targetForLocator(locator);
                if (!target) {
                    setStatus('That approved evidence is not available in this resume view.');
                    return;
                }
                selectSourceTarget(target);
                highlightTarget(target, { scroll: true, focus: true });
                setStatus(`Opened the exact public evidence for ${locator.recordKind.replaceAll('_', ' ')}.`);
            }));
        }

        function showAllOnResume() {
            if (!state.answer) return;
            if (!isWide()) closeCompanion({ restoreFocus: false });
            const locators = state.answer.sources_used
                .map((source) => normalizeLocator(source.locator))
                .filter(Boolean);
            const targets = [];
            const pendingTargets = [];
            for (const locator of locators) {
                const representation = exactRepresentativeForLocator(locator);
                if (representation.target && !targets.includes(representation.target)) {
                    highlightTarget(representation.target);
                    targets.push(representation.target);
                }
                if (representation.pendingTarget && !pendingTargets.includes(representation.pendingTarget)) {
                    pendingTargets.push(representation.pendingTarget);
                    if (representation.target) {
                        representation.target.dataset.askPetePendingEvidenceTarget = representation.pendingTarget.id;
                        representation.target.classList.add('ask-pete-evidence-pending-source');
                    }
                }
            }
            if (!targets.length && !pendingTargets.length) {
                setStatus('No matching public evidence is available in this resume view.');
                return;
            }
            if (targets.length) {
                targets[0].scrollIntoView({ behavior: hasReducedMotion() ? 'auto' : 'smooth', block: 'center', inline: 'nearest' });
            }
            const visible = targets.length;
            const pending = pendingTargets.length;
            setStatus(
                `Highlighted ${visible} exact public ${visible === 1 ? 'record or entry point' : 'records or entry points'}`
                + (pending ? `. ${pending} exact record${pending === 1 ? ' is' : 's are'} ready to open.` : '.')
            );
        }

        function handleSourceClick(button) {
            const locator = readLocatorFromElement(button);
            if (!locator) {
                setStatus('That evidence link is unavailable.');
                return;
            }
            openResumeRecord(locator, button);
        }

        function parseEvidenceCount(value) {
            if (typeof value !== 'string') return null;
            const match = value.match(/^\s*(\d+)/);
            return match ? Number.parseInt(match[1], 10) : null;
        }

        function safeContextKey(value) {
            return validContextKey(value);
        }

        function prepareContext(button) {
            cancelActiveRequest({ announce: false });
            const contextKey = safeContextKey(button.dataset.askPeteContextKey);
            state.requestedAction = VALID_ACTIONS.has(button.dataset.askPeteAction)
                ? button.dataset.askPeteAction
                : 'evidence_finder';
            const draft = safeText(button.dataset.askPeteDraft).trim();
            if (draft) elements.input.value = draft;

            if (!contextKey) {
                state.explicitContext = null;
                renderContext();
                openCompanion(button);
                setPhase(state.answer ? 'answered' : 'idle');
                setStatus("Ask Pete is ready. Ask a question about Pete's approved public information.");
                return;
            }

            state.explicitContext = {
                contextKey,
                label: safeText(button.dataset.askPeteContextLabel, 'Resume evidence'),
                evidenceItemCount: parseEvidenceCount(button.dataset.askPeteContextCount),
            };
            openCompanion(button);
            setPhase(state.answer ? 'answered' : 'context_ready');
            setStatus('Context ready. Review or edit the question, then select Ask.');
        }

        document.querySelectorAll('[data-ask-pete-open]').forEach((opener) => {
            opener.addEventListener('click', () => openCompanion(opener));
        });

        document.querySelectorAll('[data-ask-pete-context-action]').forEach((button) => {
            button.addEventListener('click', () => prepareContext(button));
        });

        companion.addEventListener('click', (event) => {
            const back = event.target.closest('[data-ask-pete-back]');
            if (back && companion.contains(back)) {
                restorePreviousAnswer();
                return;
            }
            const claimToggle = event.target.closest('[data-ask-pete-claim-toggle]');
            if (claimToggle && companion.contains(claimToggle)) {
                toggleClaim(claimToggle);
                return;
            }
            const foldToggle = event.target.closest('[data-ask-pete-fold-toggle]');
            if (foldToggle && companion.contains(foldToggle)) {
                toggleEvidenceFold(foldToggle);
                return;
            }
            const source = event.target.closest('[data-ask-pete-source]');
            if (source && companion.contains(source)) {
                handleSourceClick(source);
                return;
            }
            const showAll = event.target.closest('[data-ask-pete-show-all]');
            if (showAll && companion.contains(showAll)) {
                showAllOnResume();
                return;
            }
            const starter = event.target.closest('[data-ask-pete-starter]');
            if (starter && companion.contains(starter)) {
                const action = safeText(starter.dataset.askPeteStarter);
                const question = safeText(starter.dataset.askPeteQuestion).trim();
                if (!VALID_ACTIONS.has(action) || !question) return;
                state.explicitContext = null;
                state.requestedAction = action;
                elements.input.value = question;
                openCompanion(starter, false);
                requestAnswer(action);
            }
        });

        elements.form.addEventListener('submit', (event) => {
            event.preventDefault();
            requestAnswer(state.requestedAction || 'evidence_finder');
        });
        elements.cancel.addEventListener('click', () => cancelActiveRequest());
        elements.close.addEventListener('click', () => closeCompanion());
        elements.input.addEventListener('input', () => {
            state.draft = elements.input.value;
            if (state.phase === 'validation_error') {
                setPhase(state.answer ? 'answered' : (state.explicitContext ? 'context_ready' : 'idle'));
                setStatus('');
            }
        });

        page.addEventListener('r2:section-change', (event) => {
            const detail = isPlainObject(event.detail) ? event.detail : {};
            if (typeof detail.sectionId === 'string') state.viewingSection = detail.sectionId;
            if (!state.explicitContext) renderContext();
        });

        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState !== 'visible' || !state.revealOnReturn) return;
            state.revealOnReturn = false;
            revealAnswerTop();
        });
        document.addEventListener('keydown', (event) => {
            if (event.defaultPrevented) return;
            if (event.key === 'Escape' && !isWide() && !companion.hidden) {
                event.preventDefault();
                closeCompanion();
            }
        });
        window.addEventListener('resize', () => syncLayout());

        syncLayout();
        setPhase('idle');
        renderContext();
    });
})();

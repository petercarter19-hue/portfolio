/* INTERVIEW WORKSPACE — CONCEPT 1: Focused Coaching Workspace (2026-07-15)
   One continuous, state-driven coaching loop on a single route:

     setup -> answering -> reviewing -> reviewed -> coaching
           -> retrying -> reviewed(retry) -> completed

   THE ANSWER STAYS VISIBLE THROUGH EVERY STEP. Review never navigates,
   never opens a full-screen popup, and never mutates the scored attempt:
   submitting freezes an immutable snapshot; edits and retries are new
   drafts/attempts linked to the same question.

   AI calls:
     POST /api/interview/review — schema-validated structured coach review
     POST /api/interview/coach  — scoped workshop chat (not Ask Pete AI)
   Drafts autosave to localStorage and are restored per question. */
(function () {
    'use strict';

    var root = document.querySelector('[data-ic1]');
    if (!root) return;

    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function $(sel) { return root.querySelector(sel); }
    function $all(sel) { return Array.prototype.slice.call(root.querySelectorAll(sel)); }

    var live = $('[data-ic1-live]');
    function announce(text) { if (live) live.textContent = text; }

    /* ------------------------------------------------------------------
       Data: question bank (shared partial) + verified evidence fixture
       ------------------------------------------------------------------ */
    var bank = Array.prototype.slice.call(document.querySelectorAll('.iq-item')).map(function (btn) {
        return { text: btn.textContent.trim(), mode: btn.dataset.mode, topic: btn.dataset.topic || 'General' };
    });

    var evidence = [];
    try {
        evidence = JSON.parse(document.getElementById('ic1-evidence-data').textContent) || [];
    } catch (err) { evidence = []; }

    /* Evidence suggestions per question topic (verified items only). */
    var evidenceByTopic = {
        Leadership: ['ev-36m-cor', 'ev-19m-flight', 'ev-4-6m-nav'],
        Pressure: ['ev-70-repair', 'ev-4-6m-nav', 'ev-52-missing'],
        Initiative: ['ev-52-missing', 'ev-70-repair', 'ev-19m-flight'],
        Decisions: ['ev-4-6m-nav', 'ev-36m-cor', 'ev-cameo'],
        Communication: ['ev-36m-cor', 'ev-cameo', 'ev-4-6m-nav'],
        Teamwork: ['ev-19m-flight', 'ev-36m-cor', 'ev-70-repair'],
        Accountability: ['ev-52-missing', 'ev-36m-cor', 'ev-70-repair'],
        Adaptability: ['ev-70-repair', 'ev-4-6m-nav', 'ev-52-missing']
    };

    function suggestedEvidence(topic) {
        var ids = evidenceByTopic[topic] || ['ev-70-repair', 'ev-4-6m-nav', 'ev-36m-cor'];
        return ids.map(function (id) {
            return evidence.filter(function (e) { return e.id === id; })[0];
        }).filter(Boolean).slice(0, 3);
    }

    /* ------------------------------------------------------------------
       Elements
       ------------------------------------------------------------------ */
    var stagecard = $('[data-ic1-stagecard]');
    var setupPanel = $('[data-ic1-setup-panel]');
    var sessionPanel = $('[data-ic1-session-panel]');
    var promiseLine = $('[data-ic1-promise]');

    var questionEl = $('[data-ic1-question]');
    var qcountEl = $('[data-ic1-qcount]');
    var qtopicEl = $('[data-ic1-qtopic]');
    var qtypeEl = $('[data-ic1-qtype]');

    var composerBlock = $('[data-ic1-composer-block]');
    var answerEl = $('[data-ic1-answer]');
    var wordsEl = $('[data-ic1-words]');
    var charsEl = $('[data-ic1-chars]');
    var elapsedEl = $('[data-ic1-elapsed]');
    var autosaveEl = $('[data-ic1-autosave]');
    var reviewBtn = $('[data-ic1-review-btn]');
    var saveLaterBtn = $('[data-ic1-save-later]');

    var submittedBlock = $('[data-ic1-submitted]');
    var submittedLabel = $('[data-ic1-submitted-label]');
    var annotatedEl = $('[data-ic1-annotated]');
    var legendEl = $('[data-ic1-legend]');
    var linenoteEl = $('[data-ic1-linenote]');
    var submittedActions = $('[data-ic1-submitted-actions]');

    var scorePreview = $('[data-ic1-scorepreview]');
    var evidenceStrip = $('[data-ic1-evidence-strip]');
    var evidenceSuggestedRow = $('[data-ic1-evidence-suggested]');

    var reviewPanel = $('[data-ic1-reviewpanel]');
    var reviewDims = $all('[data-ic1-review-dims] li');
    var reviewError = $('[data-ic1-review-error]');
    var reviewErrorMsg = $('[data-ic1-review-error-msg]');

    var reviewBlock = $('[data-ic1-review]');
    var scoreRing = $('[data-ic1-scorering]');
    var scoreNum = $('[data-ic1-score-num]');
    var verdictEl = $('[data-ic1-verdict]');
    var encouragementEl = $('[data-ic1-encouragement]');
    var rubricEl = $('[data-ic1-rubric]');
    var strengthsEl = $('[data-ic1-strengths]');
    var improvementsEl = $('[data-ic1-improvements]');
    var missingCard = $('[data-ic1-missing-evidence]');
    var missingBody = $('[data-ic1-missing-evidence-body]');

    var workshopBlock = $('[data-ic1-workshop]');
    var originalEl = $('[data-ic1-original]');
    var coachDraftEl = $('[data-ic1-coach-draft]');
    var changesEl = $('[data-ic1-changes]');
    var useDraftBtn = $('[data-ic1-use-draft]');
    var useDraftNote = $('[data-ic1-use-draft-note]');
    var keepVoiceInput = $('[data-ic1-keepvoice]');
    var coachThread = $('[data-ic1-coach-thread]');
    var coachForm = $('[data-ic1-coach-form]');
    var coachInput = document.getElementById('ic1-coach-input');

    var retryCompare = $('[data-ic1-retrycompare]');
    var retryHeadline = $('[data-ic1-retry-headline]');
    var retrySub = $('[data-ic1-retry-sub]');
    var scoreFirstEl = $('[data-ic1-score-first]');
    var scoreRetryEl = $('[data-ic1-score-retry]');
    var deltasEl = $('[data-ic1-deltas]');
    var retryTakeaway = $('[data-ic1-retry-takeaway]');

    var completeBlock = $('[data-ic1-complete]');
    var completeSummary = $('[data-ic1-complete-summary]');

    var drawerVeil = $('[data-ic1-drawer-veil]');
    var evidenceDrawer = $('[data-ic1-drawer="evidence"]');

    var DIM_LABELS = {
        relevance: 'Relevance',
        structure: 'Structure',
        specificity: 'Specificity',
        evidence: 'Evidence',
        impact: 'Impact',
        delivery: 'Delivery'
    };

    /* ------------------------------------------------------------------
       Session + state
       ------------------------------------------------------------------ */
    var SESSION_LENGTH = 5;

    var session = {
        started: false,
        level: 'leadership',
        basis: 'my-history',
        type: 'practice',
        queue: [],
        index: 0,
        attempts: []            // {question, topic, text, review, attemptNumber}
    };

    var stage = 'setup';
    var elapsedTimer = null;
    var elapsedStart = null;
    var autosaveTimer = null;
    var reviewAbort = null;
    var dimCycleTimer = null;
    var lastReview = null;      // review currently shown
    var firstAttempt = null;    // first scored attempt for the active question
    var retryAttempt = null;    // retry scored attempt (if any)

    function poolFor(level) {
        if (level === 'leadership') {
            var led = bank.filter(function (q) { return q.topic === 'Leadership'; });
            if (led.length >= SESSION_LENGTH) return led;
        }
        if (level === 'management') {
            var mgmt = bank.filter(function (q) {
                return ['Leadership', 'Decisions', 'Accountability'].indexOf(q.topic) !== -1;
            });
            if (mgmt.length >= SESSION_LENGTH) return mgmt;
        }
        return bank.slice();
    }

    function buildQueue() {
        var pool = poolFor(session.level).slice();
        for (var i = pool.length - 1; i > 0; i -= 1) {
            var j = Math.floor(Math.random() * (i + 1));
            var tmp = pool[i]; pool[i] = pool[j]; pool[j] = tmp;
        }
        session.queue = pool.slice(0, SESSION_LENGTH);
        session.index = 0;
    }

    function currentQuestion() { return session.queue[session.index]; }

    /* ------------------------------------------------------------------
       Stage machine — one primary state at a time, answer always visible
       ------------------------------------------------------------------ */
    function setStage(next) {
        stage = next;
        stagecard.setAttribute('data-ic1-stage-state', next);

        var isSetup = next === 'setup';
        var isAnswering = next === 'answering' || next === 'retrying';
        var isReviewing = next === 'reviewing';
        var isReviewed = next === 'reviewed';
        var isCoaching = next === 'coaching';
        var isCompared = next === 'compared';
        var isDone = next === 'done';

        composerBlock.hidden = !(isSetup || isAnswering);
        submittedBlock.hidden = !(isReviewing || isReviewed || isCompared);
        scorePreview.hidden = !isSetup;
        evidenceStrip.hidden = !(isSetup || isAnswering);
        reviewPanel.hidden = !isReviewing;
        reviewBlock.hidden = !isReviewed;
        workshopBlock.hidden = !isCoaching;
        retryCompare.hidden = !isCompared;
        completeBlock.hidden = !isDone;
        reviewError.hidden = true;
        $('[data-ic1-qblock]').hidden = isDone;

        answerEl.disabled = isSetup;
        answerEl.readOnly = false;
        saveLaterBtn.hidden = !isAnswering;
        elapsedEl.hidden = !isAnswering;

        if (isAnswering) {
            reviewBtn.textContent = next === 'retrying' ? 'Review Retry →' : 'Review My Answer →';
            startElapsed();
            syncReviewBtn();
        } else {
            stopElapsed();
        }

        updateStepper();
    }

    var STEP_FOR_STAGE = {
        setup: 'focus',
        answering: 'answer',
        reviewing: 'review',
        reviewed: 'review',
        coaching: 'improve',
        retrying: 'retry',
        compared: 'retry',
        done: 'retry'
    };

    function updateStepper() {
        var order = ['focus', 'answer', 'review', 'improve', 'retry'];
        var active = STEP_FOR_STAGE[stage] || 'focus';
        var activeIdx = order.indexOf(active);
        $all('[data-ic1-stepper] li').forEach(function (li) {
            var idx = order.indexOf(li.getAttribute('data-ic1-step'));
            li.classList.toggle('is-active', idx === activeIdx);
            li.classList.toggle('is-done', idx < activeIdx || stage === 'done');
            var marker = li.querySelector('i');
            if (marker) marker.textContent = (idx < activeIdx || stage === 'done') ? '✓' : String(idx + 1);
        });
    }

    /* ------------------------------------------------------------------
       Question rendering + session chrome
       ------------------------------------------------------------------ */
    function renderQuestion() {
        var q = currentQuestion();
        if (!q) return;
        questionEl.textContent = q.text;
        qtopicEl.textContent = q.topic;
        qtypeEl.textContent = q.mode === 'star' ? 'STAR story' : 'Behavioral';
        qcountEl.textContent = (session.index + 1) + ' of ' + session.queue.length;
        renderSuggestedEvidence(q.topic);
        updateProgress();
    }

    function updateProgress() {
        var n = session.index + 1;
        var total = session.queue.length || SESSION_LENGTH;
        var pct = Math.round((n / total) * 100);
        var text = 'Question ' + n + ' of ' + total;
        $('[data-ic1-progress-text]').textContent = text;
        $('[data-ic1-progress-pct]').textContent = pct + '%';
        var bar = $('[data-ic1-progress-bar]');
        bar.setAttribute('aria-label', 'Session progress: question ' + n + ' of ' + total);
        bar.querySelector('i').style.setProperty('--w', pct + '%');
    }

    function renderSuggestedEvidence(topic) {
        evidenceSuggestedRow.textContent = '';
        suggestedEvidence(topic).forEach(function (item) {
            var chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'ic1-evidencechip';
            var b = document.createElement('b');
            b.textContent = item.metric;
            chip.appendChild(b);
            chip.appendChild(document.createTextNode(' ' + item.label));
            chip.addEventListener('click', openEvidenceDrawer);
            evidenceSuggestedRow.appendChild(chip);
        });
    }

    /* ------------------------------------------------------------------
       Composer: counts, timer, autosave
       ------------------------------------------------------------------ */
    function wordCount(text) {
        var words = text.trim().split(/\s+/).filter(Boolean);
        return words.length;
    }

    function syncCounts() {
        var text = answerEl.value;
        wordsEl.textContent = wordCount(text) + ' words';
        charsEl.textContent = text.length.toLocaleString() + ' / 5,000';
        syncReviewBtn();
    }

    function syncReviewBtn() {
        reviewBtn.disabled = stage === 'setup' || !answerEl.value.trim();
    }

    function startElapsed() {
        if (elapsedTimer) return;
        elapsedStart = Date.now();
        elapsedTimer = setInterval(function () {
            var s = Math.floor((Date.now() - elapsedStart) / 1000);
            var mm = String(Math.floor(s / 60)).padStart(2, '0');
            var ss = String(s % 60).padStart(2, '0');
            elapsedEl.textContent = mm + ':' + ss + ' elapsed';
        }, 1000);
    }

    function stopElapsed() {
        if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
    }

    function draftKey(questionText) { return 'ic1Draft:' + questionText.slice(0, 80); }

    function saveDraft(showStatus) {
        var q = currentQuestion();
        if (!q) return;
        try { localStorage.setItem(draftKey(q.text), answerEl.value); } catch (err) { /* private mode */ }
        if (showStatus !== false) autosaveEl.textContent = 'Draft saved just now';
    }

    function restoreDraft() {
        var q = currentQuestion();
        if (!q) return '';
        try { return localStorage.getItem(draftKey(q.text)) || ''; } catch (err) { return ''; }
    }

    answerEl.addEventListener('input', function () {
        syncCounts();
        autosaveEl.textContent = 'Saving…';
        if (autosaveTimer) clearTimeout(autosaveTimer);
        autosaveTimer = setTimeout(function () { saveDraft(); }, 850);
    });

    saveLaterBtn.addEventListener('click', function () {
        saveDraft();
        announce('Draft saved. You can come back to this question any time.');
        autosaveEl.textContent = 'Saved for later';
    });

    /* ------------------------------------------------------------------
       Setup controls
       ------------------------------------------------------------------ */
    $all('[data-ic1-level]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            session.level = btn.getAttribute('data-ic1-level');
            $all('[data-ic1-level]').forEach(function (b) {
                var on = b === btn;
                b.classList.toggle('is-active', on);
                b.setAttribute('aria-pressed', String(on));
            });
        });
    });

    $all('[data-ic1-basis]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            session.basis = btn.getAttribute('data-ic1-basis');
            $all('[data-ic1-basis]').forEach(function (b) {
                var on = b === btn;
                b.classList.toggle('is-active', on);
                b.setAttribute('aria-pressed', String(on));
            });
            var hint = $('[data-ic1-basis-hint]');
            hint.textContent = session.basis === 'my-history'
                ? 'The coach may only cite your verified slate evidence.'
                : 'Suggestions use realistic illustrative examples, clearly labeled as fictional.';
            syncYouBasisNote();
        });
    });

    function labelFor(value, map) { return map[value] || value; }

    var LEVEL_LABELS = { entry: 'Entry Level', experienced: 'Experienced', management: 'Management', leadership: 'Leadership', mixed: 'Mixed' };
    var BASIS_LABELS = { 'my-history': 'My History', 'example-candidate': 'Example Candidate' };

    $('[data-ic1-start]').addEventListener('click', function () {
        session.started = true;
        buildQueue();
        setupPanel.hidden = true;
        sessionPanel.hidden = false;
        if (promiseLine) promiseLine.hidden = true;
        $('[data-ic1-chip-level]').textContent = labelFor(session.level, LEVEL_LABELS);
        $('[data-ic1-chip-basis]').textContent = labelFor(session.basis, BASIS_LABELS);
        $('[data-ic1-chip-type]').textContent = 'Practice';
        renderQuestion();
        answerEl.value = restoreDraft();
        syncCounts();
        setStage('answering');
        announce('Practice session started. ' + currentQuestion().text);
        answerEl.focus();
    });

    $('[data-ic1-edit-setup]').addEventListener('click', function () {
        if (answerEl.value.trim() && stage === 'answering') {
            var ok = window.confirm('Change the session setup? Your draft stays saved for this question.');
            if (!ok) return;
            saveDraft(false);
        }
        sessionPanel.hidden = true;
        setupPanel.hidden = false;
        if (promiseLine) promiseLine.hidden = false;
        setStage('setup');
    });

    /* ------------------------------------------------------------------
       Review flow
       ------------------------------------------------------------------ */
    function setDimStatus(index, status) {
        reviewDims.forEach(function (li, i) {
            if (i > index && status !== 'reset') return;
            if (status === 'reset') {
                li.classList.remove('is-analyzing', 'is-complete');
                li.querySelector('b').textContent = 'Waiting';
                return;
            }
            if (i < index) {
                li.classList.remove('is-analyzing');
                li.classList.add('is-complete');
                li.querySelector('b').textContent = 'Complete';
            } else if (i === index) {
                li.classList.add('is-analyzing');
                li.classList.remove('is-complete');
                li.querySelector('b').textContent = 'Analyzing';
            }
        });
    }

    function startDimCycle() {
        setDimStatus(0, 'reset');
        var i = 0;
        setDimStatus(0);
        dimCycleTimer = setInterval(function () {
            // Advance the UI phase, but never mark the last dimension
            // complete on a timer — real completion comes from the response.
            if (i < reviewDims.length - 1) { i += 1; setDimStatus(i); }
        }, 900);
    }

    function stopDimCycle(complete) {
        if (dimCycleTimer) { clearInterval(dimCycleTimer); dimCycleTimer = null; }
        if (complete) {
            reviewDims.forEach(function (li) {
                li.classList.remove('is-analyzing');
                li.classList.add('is-complete');
                li.querySelector('b').textContent = 'Complete';
            });
        }
    }

    function requestReview(isRetry) {
        var q = currentQuestion();
        var text = answerEl.value.trim();
        if (!q || !text) return;

        // Immutable attempt snapshot: the scored attempt is exactly what
        // was submitted, even if the composer changes later.
        var attempt = {
            question: q.text,
            topic: q.topic,
            text: text,
            attemptNumber: isRetry ? 2 : 1,
            review: null
        };

        saveDraft(false);
        setStage('reviewing');
        renderSubmitted(text, null);
        submittedLabel.textContent = 'Submitted answer · ' + wordCount(text) + ' words';
        announce('Reviewing your answer. Your response stays visible.');
        startDimCycle();

        reviewAbort = typeof AbortController === 'function' ? new AbortController() : null;

        fetch('/api/interview/review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: q.text,
                topic: q.topic,
                answer: text,
                level: session.level,
                basis: session.basis,
                keep_voice: !keepVoiceInput || keepVoiceInput.checked
            }),
            signal: reviewAbort ? reviewAbort.signal : undefined
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) {
                if (!response.ok || !data.review) {
                    throw new Error(data.error || 'The coach is unavailable right now.');
                }
                return data.review;
            });
        }).then(function (review) {
            attempt.review = review;
            session.attempts.push(attempt);
            if (isRetry) { retryAttempt = attempt; } else { firstAttempt = attempt; retryAttempt = null; }
            lastReview = review;
            stopDimCycle(true);
            window.setTimeout(function () {
                if (isRetry && firstAttempt && firstAttempt.review) {
                    renderRetryComparison();
                } else {
                    renderReview(attempt);
                }
            }, reduceMotion ? 0 : 350);
        }).catch(function (err) {
            stopDimCycle(false);
            if (err && err.name === 'AbortError') {
                setStage(isRetry ? 'retrying' : 'answering');
                announce('Review canceled. Your answer is unchanged.');
                return;
            }
            setStage(isRetry ? 'retrying' : 'answering');
            // Keep the answer; explain plainly; offer recovery actions.
            reviewError.hidden = false;
            reviewErrorMsg.textContent = (err && err.message) || 'The coach is unavailable right now.';
            announce('The review failed. Your answer is safe — you can try again.');
        }).finally(function () {
            reviewAbort = null;
        });
    }

    reviewBtn.addEventListener('click', function () {
        requestReview(stage === 'retrying');
    });

    $('[data-ic1-cancel-review]').addEventListener('click', function () {
        if (reviewAbort) reviewAbort.abort();
    });

    $('[data-ic1-error-retry]').addEventListener('click', function () {
        reviewError.hidden = true;
        requestReview(stage === 'retrying');
    });

    $('[data-ic1-error-save]').addEventListener('click', function () {
        saveDraft();
        reviewError.hidden = true;
        autosaveEl.textContent = 'Saved for later';
    });

    /* ------------------------------------------------------------------
       Rendering: submitted answer + annotations
       ------------------------------------------------------------------ */
    function validAnnotations(annotations, textLength) {
        if (!Array.isArray(annotations)) return [];
        var seen = [];
        var out = [];
        annotations.slice().sort(function (a, b) { return a.start - b.start; }).forEach(function (a) {
            if (typeof a.start !== 'number' || typeof a.end !== 'number') return;
            if (a.start < 0 || a.end > textLength || a.end <= a.start) return;
            var overlaps = seen.some(function (s) { return a.start < s.end && a.end > s.start; });
            if (overlaps) return;
            if (['strong', 'needs-specificity', 'missing-evidence', 'clarity'].indexOf(a.type) === -1) return;
            seen.push(a);
            out.push(a);
        });
        return out;
    }

    function renderSubmitted(text, review) {
        annotatedEl.textContent = '';
        var annotations = review ? validAnnotations(review.annotations, text.length) : [];

        if (!annotations.length) {
            annotatedEl.textContent = text;
        } else {
            var cursor = 0;
            annotations.forEach(function (a) {
                if (a.start > cursor) {
                    annotatedEl.appendChild(document.createTextNode(text.slice(cursor, a.start)));
                }
                var mark = document.createElement('mark');
                mark.className = 'ic1-ann ic1-ann--' + a.type;
                mark.textContent = text.slice(a.start, a.end);
                mark.title = a.label + ': ' + a.explanation;
                annotatedEl.appendChild(mark);
                cursor = a.end;
            });
            if (cursor < text.length) {
                annotatedEl.appendChild(document.createTextNode(text.slice(cursor)));
            }
        }

        legendEl.hidden = !annotations.length;
        var note = annotations.filter(function (a) { return a.type !== 'strong'; })[0];
        if (review && note) {
            linenoteEl.hidden = false;
            linenoteEl.textContent = 'Line-level note: ' + note.explanation;
        } else {
            linenoteEl.hidden = true;
        }
        submittedActions.hidden = !review;
    }

    /* ------------------------------------------------------------------
       Rendering: coach review
       ------------------------------------------------------------------ */
    function renderReview(attempt) {
        var review = attempt.review;
        renderSubmitted(attempt.text, review);
        submittedLabel.textContent = 'Question ' + (session.index + 1) + ' · ' + attempt.topic + ' — your submitted answer';

        var score = review.overallScore;
        scoreRing.style.setProperty('--p', score);
        scoreRing.setAttribute('aria-label', 'Overall score ' + score + ' out of 100 — ' + review.verdict);
        scoreNum.textContent = score;
        verdictEl.textContent = review.verdict;
        encouragementEl.textContent = review.encouragement;

        rubricEl.textContent = '';
        (review.dimensions || []).forEach(function (dim) {
            var li = document.createElement('li');
            var details = document.createElement('details');
            var summary = document.createElement('summary');

            var name = document.createElement('span');
            name.textContent = DIM_LABELS[dim.key] || dim.key;
            var bar = document.createElement('span');
            bar.className = 'ic1-bar';
            var fill = document.createElement('i');
            fill.style.setProperty('--w', dim.score + '%');
            bar.appendChild(fill);
            var num = document.createElement('b');
            num.textContent = dim.score;

            summary.appendChild(name);
            summary.appendChild(bar);
            summary.appendChild(num);
            summary.setAttribute('aria-label',
                (DIM_LABELS[dim.key] || dim.key) + ': ' + dim.score + ' out of 100. Select for the rationale.');
            details.appendChild(summary);

            var why = document.createElement('div');
            why.className = 'ic1-rubric__why';
            var rationale = document.createElement('span');
            rationale.textContent = dim.rationale + ' ';
            var next = document.createElement('b');
            next.textContent = 'Next: ' + dim.nextAction;
            why.appendChild(rationale);
            why.appendChild(next);
            details.appendChild(why);

            li.appendChild(details);
            rubricEl.appendChild(li);
        });

        fillList(strengthsEl, review.strengths);
        fillList(improvementsEl, review.improvements);

        var missing = review.missingEvidence || [];
        if (missing.length) {
            missingCard.hidden = false;
            missingBody.textContent = '';
            missing.slice(0, 2).forEach(function (m) {
                var p = document.createElement('p');
                p.textContent = m.opportunity;
                missingBody.appendChild(p);
                if (m.suggestedUse) {
                    var use = document.createElement('div');
                    use.className = 'ic1-suggested';
                    use.textContent = 'Suggested use: ' + m.suggestedUse;
                    missingBody.appendChild(use);
                }
            });
        } else {
            missingCard.hidden = true;
        }

        setStage('reviewed');
        if (!reduceMotion) reviewBlock.classList.add('ic1-fadein');
        announce('Review complete. Overall score ' + score + ' out of 100. ' + review.verdict);
    }

    function fillList(el, items) {
        el.textContent = '';
        (items || []).slice(0, 4).forEach(function (item) {
            var li = document.createElement('li');
            li.textContent = item;
            el.appendChild(li);
        });
    }

    /* ------------------------------------------------------------------
       Reviewed actions
       ------------------------------------------------------------------ */
    $('[data-ic1-edit-answer]').addEventListener('click', function () {
        // Editing after review never mutates the scored attempt — the
        // composer draft starts from the submitted text as a NEW draft.
        var base = retryAttempt || firstAttempt;
        if (base) answerEl.value = base.text;
        syncCounts();
        setStage('retrying');
        announce('Editing a new draft. The scored attempt stays in history.');
        answerEl.focus();
    });

    $('[data-ic1-improve]').addEventListener('click', function () {
        openWorkshop();
    });

    $('[data-ic1-retry]').addEventListener('click', function () {
        var base = firstAttempt;
        if (base) answerEl.value = base.text;
        syncCounts();
        setStage('retrying');
        announce('Retry started. Improve your answer, then review it again.');
        answerEl.focus();
    });

    $('[data-ic1-next]').addEventListener('click', nextQuestion);
    $('[data-ic1-next-2]').addEventListener('click', nextQuestion);

    function nextQuestion() {
        if (session.index + 1 >= session.queue.length) {
            finishSession();
            return;
        }
        session.index += 1;
        firstAttempt = null;
        retryAttempt = null;
        lastReview = null;
        renderQuestion();
        answerEl.value = restoreDraft();
        autosaveEl.textContent = '';
        syncCounts();
        setStage('answering');
        announce('Next question. ' + currentQuestion().text);
        answerEl.focus();
    }

    function finishSession() {
        var scored = session.attempts.filter(function (a) { return a.review; });
        var firsts = scored.filter(function (a) { return a.attemptNumber === 1; });
        var avg = firsts.length
            ? Math.round(firsts.reduce(function (sum, a) { return sum + a.review.overallScore; }, 0) / firsts.length)
            : null;
        completeSummary.textContent = scored.length
            ? 'You answered ' + firsts.length + ' question' + (firsts.length === 1 ? '' : 's') +
              (avg !== null ? ' with an average first-attempt score of ' + avg + '/100.' : '.') +
              ' Every attempt, score, and review from this session stays on this page until you leave.'
            : 'No answers were scored this session.';
        setStage('done');
        announce('Session complete.');
    }

    $('[data-ic1-new-session]').addEventListener('click', function () {
        session.attempts = [];
        firstAttempt = null;
        retryAttempt = null;
        sessionPanel.hidden = true;
        setupPanel.hidden = false;
        if (promiseLine) promiseLine.hidden = false;
        answerEl.value = '';
        syncCounts();
        setStage('setup');
        renderQuestion();
    });

    /* ------------------------------------------------------------------
       Workshop (coaching)
       ------------------------------------------------------------------ */
    function openWorkshop() {
        var attempt = retryAttempt || firstAttempt;
        if (!attempt || !attempt.review) return;
        originalEl.textContent = attempt.text;
        coachDraftEl.textContent = attempt.review.improvedAnswer || 'The coach did not return an improved draft this time.';
        changesEl.textContent = '';
        (attempt.review.changesExplained || []).slice(0, 6).forEach(function (c) {
            var li = document.createElement('li');
            li.textContent = c;
            changesEl.appendChild(li);
        });
        useDraftBtn.textContent = 'Use Draft';
        useDraftBtn.dataset.confirming = '';
        useDraftNote.hidden = true;
        if (!coachThread.children.length) {
            addCoachMsg('coach', 'I’m your interview coach for this question. Ask me why you scored the way you did, or how to make the draft stronger — I’ll keep it in your voice.');
        }
        setStage('coaching');
        announce('Answer workshop open. Your original answer and the coach-assisted draft are side by side.');
    }

    /* Use Draft is a two-step, explicit confirmation — the coach never
       silently replaces the user's words. */
    useDraftBtn.addEventListener('click', function () {
        var attempt = retryAttempt || firstAttempt;
        if (!attempt || !attempt.review || !attempt.review.improvedAnswer) return;
        if (!useDraftBtn.dataset.confirming) {
            useDraftBtn.dataset.confirming = '1';
            useDraftBtn.textContent = 'Replace my draft? Confirm';
            useDraftNote.hidden = false;
            return;
        }
        answerEl.value = attempt.review.improvedAnswer;
        syncCounts();
        saveDraft(false);
        setStage('retrying');
        announce('Coach draft copied into your editable draft. The original scored attempt is unchanged. Review the retry when ready.');
        answerEl.focus();
    });

    $('[data-ic1-workshop-edit]').addEventListener('click', function () {
        var attempt = retryAttempt || firstAttempt;
        if (attempt) answerEl.value = attempt.text;
        syncCounts();
        setStage('retrying');
        answerEl.focus();
    });

    $('[data-ic1-back-review]').addEventListener('click', function () {
        var attempt = retryAttempt || firstAttempt;
        if (attempt) renderReview(attempt);
    });

    /* Scoped Interview Coach chat (NOT the general Ask Pete assistant). */
    function addCoachMsg(role, text, pending) {
        var div = document.createElement('div');
        div.className = 'ic1-msg ic1-msg--' + (role === 'user' ? 'user' : 'coach') + (pending ? ' ic1-msg--pending' : '');
        div.textContent = text;
        coachThread.appendChild(div);
        coachThread.scrollTop = coachThread.scrollHeight;
        return div;
    }

    function askCoach(message) {
        var attempt = retryAttempt || firstAttempt;
        if (!attempt || !message.trim()) return;
        addCoachMsg('user', message);
        var pending = addCoachMsg('coach', 'Thinking…', true);

        fetch('/api/interview/coach', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: attempt.question,
                answer: attempt.text,
                message: message,
                basis: session.basis,
                keep_voice: !keepVoiceInput || keepVoiceInput.checked,
                review_summary: attempt.review ? (attempt.review.verdict + ' (' + attempt.review.overallScore + '/100)') : ''
            })
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) {
                if (!response.ok) throw new Error(data.error || 'The coach is unavailable right now.');
                return data.response || 'The coach is unavailable right now.';
            });
        }).then(function (reply) {
            pending.classList.remove('ic1-msg--pending');
            pending.textContent = reply;
        }).catch(function (err) {
            pending.classList.remove('ic1-msg--pending');
            pending.textContent = (err && err.message) || 'The coach is unavailable right now.';
        });
    }

    coachForm.addEventListener('submit', function (event) {
        event.preventDefault();
        var message = coachInput.value.trim();
        if (!message) return;
        coachInput.value = '';
        askCoach(message);
    });

    $all('[data-ic1-coach-chip]').forEach(function (chip) {
        chip.addEventListener('click', function () { askCoach(chip.textContent.trim()); });
    });

    /* ------------------------------------------------------------------
       Retry comparison
       ------------------------------------------------------------------ */
    function renderRetryComparison() {
        var first = firstAttempt.review;
        var retry = retryAttempt.review;

        renderSubmitted(retryAttempt.text, null);
        submittedLabel.textContent = 'Your improved answer';

        scoreFirstEl.textContent = first.overallScore;
        scoreRetryEl.textContent = retry.overallScore;

        var diff = retry.overallScore - first.overallScore;
        // Honest comparison language — scores can stay flat or decline.
        retryHeadline.textContent = diff > 0
            ? 'Your answer became stronger.'
            : diff === 0 ? 'Your score held steady.' : 'This retry scored lower — that happens.';
        retrySub.textContent = diff > 0
            ? 'You kept the same story while making your ownership and impact clearer.'
            : diff === 0 ? 'Compare the dimension changes below to see what moved and what to try next.'
            : 'Look at which dimensions dipped below — the coach’s takeaway explains what to adjust.';

        deltasEl.textContent = '';
        var firstDims = {};
        (first.dimensions || []).forEach(function (d) { firstDims[d.key] = d.score; });
        (retry.dimensions || []).forEach(function (d) {
            // Compare only dimensions present in BOTH attempts.
            if (!(d.key in firstDims)) return;
            var li = document.createElement('li');
            var name = document.createElement('span');
            name.textContent = DIM_LABELS[d.key] || d.key;
            var before = document.createElement('small');
            before.textContent = firstDims[d.key];
            var bar = document.createElement('span');
            bar.className = 'ic1-bar';
            var fill = document.createElement('i');
            fill.style.setProperty('--w', d.score + '%');
            bar.appendChild(fill);
            var after = document.createElement('b');
            var delta = d.score - firstDims[d.key];
            after.textContent = d.score;
            after.className = delta > 0 ? 'is-up' : delta < 0 ? 'is-down' : '';
            li.setAttribute('aria-label', (DIM_LABELS[d.key] || d.key) + ': ' + firstDims[d.key] + ' before, ' + d.score + ' after.');
            li.appendChild(name);
            li.appendChild(before);
            li.appendChild(bar);
            li.appendChild(after);
            deltasEl.appendChild(li);
        });

        retryTakeaway.textContent = retry.encouragement || retry.verdict;

        setStage('compared');
        announce('Retry complete. First attempt ' + first.overallScore + ', retry ' + retry.overallScore + ' out of 100.');
    }

    $('[data-ic1-open-retry-review]').addEventListener('click', function () {
        if (retryAttempt) renderReview(retryAttempt);
    });

    $('[data-ic1-practice-again]').addEventListener('click', function () {
        if (retryAttempt) answerEl.value = retryAttempt.text;
        syncCounts();
        setStage('retrying');
        answerEl.focus();
    });

    /* ------------------------------------------------------------------
       Evidence drawer
       ------------------------------------------------------------------ */
    var drawerReturnFocus = null;

    function openEvidenceDrawer() {
        drawerReturnFocus = document.activeElement;
        drawerVeil.hidden = false;
        evidenceDrawer.hidden = false;
        evidenceDrawer.querySelector('.ic1-drawer__close').focus();
    }

    function closeEvidenceDrawer() {
        drawerVeil.hidden = true;
        evidenceDrawer.hidden = true;
        if (drawerReturnFocus && drawerReturnFocus.focus) drawerReturnFocus.focus();
    }

    $('[data-ic1-open-evidence]').addEventListener('click', openEvidenceDrawer);
    $('[data-ic1-drawer-close]').addEventListener('click', closeEvidenceDrawer);
    drawerVeil.addEventListener('click', closeEvidenceDrawer);

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !evidenceDrawer.hidden) closeEvidenceDrawer();
    });

    /* "Add to draft" appends the cited metric at the end of the draft —
       always user-initiated, never automatic. */
    $all('[data-ic1-evidence-add]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var item = btn.closest('.ic1-evidenceitem');
            var metric = item.querySelector('strong').textContent;
            var label = item.querySelector('span').textContent;
            if (stage !== 'answering' && stage !== 'retrying') {
                announce('Start answering first, then add evidence to your draft.');
                return;
            }
            var addition = (answerEl.value.trim() ? ' ' : '') + '[' + metric + ' — ' + label + ']';
            answerEl.value += addition;
            syncCounts();
            saveDraft();
            closeEvidenceDrawer();
            answerEl.focus();
        });
    });

    /* ------------------------------------------------------------------
       Mode tabs (roving tabindex + arrow keys)
       ------------------------------------------------------------------ */
    var modeTabs = $all('[data-ic1-mode]');

    function setMode(mode) {
        if (stage === 'answering' && answerEl.value.trim() && mode !== 'me') {
            var ok = window.confirm('Leave Interview Me? Your draft stays saved for this question.');
            if (!ok) return;
            saveDraft(false);
        }
        modeTabs.forEach(function (tab) {
            var on = tab.getAttribute('data-ic1-mode') === mode;
            tab.setAttribute('aria-selected', String(on));
            tab.tabIndex = on ? 0 : -1;
        });
        $all('[data-ic1-mode-panel]').forEach(function (panel) {
            var on = panel.getAttribute('data-ic1-mode-panel') === mode;
            panel.hidden = !on;
            panel.classList.toggle('is-active', on);
        });
        announce(mode === 'me' ? 'Interview Me: you answer, the coach reviews.'
            : mode === 'you' ? 'Interview You: you ask, the AI answers as the candidate.'
            : 'Video Me: delivery practice (prototype).');
    }

    modeTabs.forEach(function (tab, index) {
        tab.addEventListener('click', function () { setMode(tab.getAttribute('data-ic1-mode')); });
        tab.addEventListener('keydown', function (event) {
            var dir = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
            if (!dir) return;
            event.preventDefault();
            var nextTab = modeTabs[(index + dir + modeTabs.length) % modeTabs.length];
            nextTab.focus();
            setMode(nextTab.getAttribute('data-ic1-mode'));
        });
    });

    /* ------------------------------------------------------------------
       Interview You mode (model answers, basis-aware)
       ------------------------------------------------------------------ */
    var youForm = $('[data-ic1-you-form]');
    var youInput = document.getElementById('ic1-you-question');
    var youAnswer = $('[data-ic1-you-answer]');
    var youBusy = false;

    function syncYouBasisNote() {
        var note = $('[data-ic1-you-basis-note]');
        if (!note) return;
        note.innerHTML = '';
        note.appendChild(document.createTextNode('Answer basis: '));
        var b = document.createElement('strong');
        b.textContent = BASIS_LABELS[session.basis];
        note.appendChild(b);
        note.appendChild(document.createTextNode(session.basis === 'my-history'
            ? ' — grounded only in verified slate evidence.'
            : ' — a realistic illustrative answer, clearly labeled as fictional.'));
    }

    youForm.addEventListener('submit', function (event) {
        event.preventDefault();
        if (youBusy) return;
        var q = youInput.value.trim() || (currentQuestion() ? currentQuestion().text : '');
        if (!q) return;
        youBusy = true;
        youAnswer.innerHTML = '<p class="ic1-empty">Building the candidate’s answer…</p>';

        var prompt = session.basis === 'my-history'
            ? 'Answer this interview question with a model answer, speaking in first person as Pete Carter. ' +
              'Ground every claim in Pete’s real career history, accomplishments, and skills evidence — do not invent anything. ' +
              'Use a STAR shape in two short plain-text paragraphs, about 150 words total, with one or two concrete metrics. ' +
              'Interview question: "' + q + '"'
            : 'Answer this interview question as a realistic FICTIONAL example candidate (not Pete Carter, no real names). ' +
              'Use a STAR shape in two short plain-text paragraphs, about 150 words total, with one or two plausible illustrative metrics. ' +
              'Interview question: "' + q + '"';

        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: prompt })
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) {
                if (!response.ok) throw new Error(data.error || 'The assistant is unavailable right now.');
                return data.response || data.error || 'The assistant is unavailable right now.';
            });
        }).then(function (reply) {
            youAnswer.textContent = '';
            reply.split(/\n{2,}/).forEach(function (part) {
                if (!part.trim()) return;
                var p = document.createElement('p');
                p.textContent = part.trim();
                youAnswer.appendChild(p);
            });
            var label = document.createElement('p');
            label.className = 'ic1-youanswer__label';
            label.textContent = session.basis === 'my-history'
                ? 'Grounded in Pete’s approved slate evidence.'
                : 'Illustrative example — fictional candidate, not a real history.';
            youAnswer.appendChild(label);
        }).catch(function (err) {
            youAnswer.innerHTML = '';
            var p = document.createElement('p');
            p.className = 'ic1-empty';
            p.textContent = (err && err.message) || 'The assistant is unavailable right now.';
            youAnswer.appendChild(p);
        }).finally(function () {
            youBusy = false;
        });
    });

    /* ------------------------------------------------------------------
       Boot: preview the first question with a disabled composer
       ------------------------------------------------------------------ */
    buildQueue();
    renderQuestion();
    syncCounts();
    setStage('setup');
})();

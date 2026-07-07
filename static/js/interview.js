// Interview Me — Interview Practice Studio.
// Runs the question studio on templates/interview_me.html: question
// cycling by mode, typed or SPOKEN answers, slate-grounded sample
// answers, coach feedback with a 0-100 score ring, and a running
// session average. All AI calls hit the SAME /api/chat endpoint the
// chatbot and Ask Pete AI features use, so the coach is grounded in
// Pete's knowledge files. Browser-only: no keys, no secrets.

(function () {
    'use strict';

    // ---------- Question bank (read from the on-page lists) ----------
    // The 60 questions live in the HTML question-bank sections so they
    // render without JS; the studio reads them from the DOM.
    const bank = Array.from(document.querySelectorAll('.iq-item')).map(function (btn) {
        return {
            text: btn.textContent.trim(),
            mode: btn.dataset.mode,          // "star" | "behavioral"
            topic: btn.dataset.topic || 'General',
            el: btn
        };
    });

    if (!bank.length) {
        return; // not on the Interview Me page
    }

    // ---------- Studio elements ----------
    const questionEl = document.getElementById('iv-question');
    const counterEl = document.getElementById('iv-counter');
    const topicChip = document.getElementById('iv-topic-chip');
    const modeChip = document.getElementById('iv-mode-chip');
    const answerEl = document.getElementById('iv-answer');
    const countEl = document.getElementById('iv-count');
    const feedbackEl = document.getElementById('iv-feedback');
    const scoreEl = document.getElementById('iv-score');
    const scoreNum = document.getElementById('iv-score-num');
    const scoreTier = document.getElementById('iv-score-tier');
    const sessionEl = document.getElementById('iv-session');
    const suggestedEl = document.getElementById('iv-suggested');
    const modeButtons = Array.from(document.querySelectorAll('.iv-mode'));
    const evidenceCard = document.getElementById('iv-evidence');
    const evidenceToggle = document.getElementById('iv-evidence-toggle');

    // ---------- State ----------
    let mode = 'star';                  // star | behavioral | leadership | mixed
    let current = null;                 // current question object
    let history = [];                   // visited questions (for the back arrow)
    let asked = 0;                      // question number shown in the counter
    let session = { answered: 0, totalScore: 0 };
    let mockMode = false;
    let busy = false;

    function pool() {
        if (mode === 'star' || mode === 'behavioral') {
            return bank.filter(function (q) { return q.mode === mode; });
        }
        if (mode === 'leadership') {
            return bank.filter(function (q) { return q.topic === 'Leadership'; });
        }
        return bank; // mixed
    }

    function pickQuestion() {
        const candidates = pool().filter(function (q) { return q !== current; });
        return candidates[Math.floor(Math.random() * candidates.length)];
    }

    function showQuestion(q, options) {
        if (!q) { return; }
        if (current && (!options || !options.fromHistory)) {
            history.push(current);
        }
        current = q;
        asked += 1;
        questionEl.textContent = q.text;
        topicChip.textContent = q.topic;
        modeChip.textContent = q.mode === 'star' ? 'STAR' : 'Behavioral';
        counterEl.textContent = mockMode
            ? 'Mock interview · question ' + (session.answered + 1)
            : 'Question ' + asked;
        answerEl.value = restoreDraft(q.text) || '';
        updateCount();
        clearFeedback();
    }

    // ---------- Drafts (saved locally per question) ----------
    function draftKey(text) {
        return 'ivDraft:' + text.slice(0, 60);
    }

    function saveDraft() {
        if (!current) { return; }
        try {
            localStorage.setItem(draftKey(current.text), answerEl.value);
        } catch (err) { /* storage full or blocked — drafts just won't persist */ }
        flashLabel(document.getElementById('iv-save'), 'Saved ✓', 'Save Draft');
    }

    function restoreDraft(text) {
        try {
            return localStorage.getItem(draftKey(text));
        } catch (err) {
            return '';
        }
    }

    function flashLabel(btn, tempText, backText) {
        if (!btn) { return; }
        btn.textContent = tempText;
        setTimeout(function () { btn.textContent = backText; }, 1400);
    }

    // ---------- Character counter ----------
    function updateCount() {
        countEl.textContent = answerEl.value.length.toLocaleString() + ' / 1,200 characters';
    }

    // ---------- AI plumbing (same endpoint as Ask Pete AI) ----------
    function askCoach(message) {
        return fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) {
                    throw new Error(data.error || 'The coach is unavailable right now.');
                }
                return data.response || data.error || 'The coach is unavailable right now.';
            });
        });
    }

    function setFeedback(text) {
        feedbackEl.textContent = '';
        text.split(/\n{2,}|\n(?=[-•])/).forEach(function (part) {
            if (!part.trim()) { return; }
            const p = document.createElement('p');
            p.textContent = part.trim();
            feedbackEl.appendChild(p);
        });
    }

    function clearFeedback() {
        feedbackEl.innerHTML = '<p class="iv-feedback__empty">Answer the question above and press <strong>Get Feedback</strong> — the coach reviews your draft against Pete’s slate and scores it.</p>';
        scoreEl.style.setProperty('--p', 0);
        scoreEl.setAttribute('aria-label', 'No score yet');
        scoreNum.textContent = '–';
        scoreTier.textContent = 'Not rated';
        const nextBtn = document.getElementById('iv-mock-next');
        if (nextBtn) { nextBtn.remove(); }
    }

    function applyScore(score) {
        const tier = score >= 85 ? 'Strong' : score >= 70 ? 'Solid' : 'Keep practicing';
        scoreEl.style.setProperty('--p', score);
        scoreEl.setAttribute('aria-label', 'Score ' + score + ' out of 100 — ' + tier);
        scoreNum.textContent = score;
        scoreTier.textContent = tier;
        session.answered += 1;
        session.totalScore += score;
        const avg = Math.round(session.totalScore / session.answered);
        sessionEl.textContent = 'This session: ' + session.answered + ' answered · average ' + avg + '/100';
    }

    // In mock mode, a "Next question" button appears under the feedback.
    function offerNextQuestion() {
        if (!mockMode || document.getElementById('iv-mock-next')) { return; }
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.id = 'iv-mock-next';
        btn.className = 'btn btn-primary iv-btn';
        btn.textContent = 'Next question →';
        btn.addEventListener('click', function () {
            showQuestion(pickQuestion());
            document.querySelector('.iv-question-card').scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
        feedbackEl.appendChild(btn);
    }

    function getFeedback() {
        if (busy || !current) { return; }
        const answer = answerEl.value.trim();
        if (!answer) {
            setFeedback('Write or record your answer first — then the coach can score it. If you’re stuck, try "Coach me with a sample answer."');
            return;
        }
        busy = true;
        setFeedback('The coach is reviewing your answer…');
        const prompt =
            'You are an interview coach helping Pete Carter practice. ' +
            'Interview question: "' + current.text + '". ' +
            'Candidate’s draft answer: "' + answer + '". ' +
            'In plain text (no markdown): give 2 or 3 short, specific coaching points to strengthen the answer — STAR structure, specificity, and measurable impact from Pete’s real background where relevant. ' +
            'Then, on the final line by itself, write exactly: Score: NN/100 (your honest rating of the draft).';
        askCoach(prompt).then(function (reply) {
            const match = reply.match(/Score:\s*(\d{1,3})\s*\/\s*100/i);
            let text = reply.replace(/Score:\s*\d{1,3}\s*\/\s*100\.?/i, '').trim();
            setFeedback(text);
            if (match) {
                applyScore(Math.min(100, parseInt(match[1], 10)));
            }
            offerNextQuestion();
        }).catch(function (err) {
            setFeedback(err.message);
        }).finally(function () {
            busy = false;
        });
    }

    function getSample() {
        if (busy || !current) { return; }
        busy = true;
        setFeedback('The coach is drafting a sample answer from Pete’s slate…');
        const prompt =
            'You are an interview coach. Using Pete Carter’s real background and evidence, ' +
            'write a concise sample answer to this interview question: "' + current.text + '". ' +
            'Structure it as STAR — label Situation, Task, Action, and Result — in plain text, under 170 words, first person as Pete.';
        askCoach(prompt).then(function (reply) {
            setFeedback(reply);
        }).catch(function (err) {
            setFeedback(err.message);
        }).finally(function () {
            busy = false;
        });
    }

    // ---------- Rephrase (local, instant) ----------
    const rephrasings = [
        [/^Tell me about a time/i, 'Describe a situation where'],
        [/^Describe a situation where/i, 'Give me an example of when'],
        [/^Give me an example of when/i, 'Walk me through a time'],
        [/^Walk me through a time/i, 'Tell me about a time'],
        [/^How do you/i, 'What’s your approach when you'],
        [/^What’s your approach when you/i, 'How do you']
    ];

    function rephrase() {
        const text = questionEl.textContent.trim();
        for (const pair of rephrasings) {
            if (pair[0].test(text)) {
                questionEl.textContent = text.replace(pair[0], pair[1]);
                return;
            }
        }
    }

    // ---------- Voice input (browsers that support it) ----------
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognizer = null;
    let recording = false;
    const recordBtn = document.getElementById('iv-record');

    if (!Recognition) {
        recordBtn.disabled = true;
        recordBtn.title = 'Voice input is not supported in this browser — type your answer instead.';
    }

    function toggleRecording() {
        if (!Recognition) { return; }
        if (recording) {
            recognizer.stop();
            return;
        }
        recognizer = new Recognition();
        recognizer.continuous = true;
        recognizer.interimResults = false;
        recognizer.lang = 'en-US';
        recognizer.onresult = function (event) {
            for (let i = event.resultIndex; i < event.results.length; i += 1) {
                if (event.results[i].isFinal) {
                    const spoken = event.results[i][0].transcript.trim();
                    answerEl.value = (answerEl.value ? answerEl.value + ' ' : '') + spoken;
                    updateCount();
                }
            }
        };
        recognizer.onend = function () {
            recording = false;
            recordBtn.classList.remove('is-recording');
            recordBtn.lastChild.textContent = ' Record Answer';
        };
        recognizer.onerror = recognizer.onend;
        recognizer.start();
        recording = true;
        recordBtn.classList.add('is-recording');
        recordBtn.lastChild.textContent = ' Stop Recording';
    }

    // ---------- Suggested questions ----------
    function renderSuggestions() {
        const picks = [];
        const source = pool();
        while (picks.length < 3 && picks.length < source.length) {
            const q = source[Math.floor(Math.random() * source.length)];
            if (picks.indexOf(q) === -1 && q !== current) { picks.push(q); }
        }
        suggestedEl.textContent = '';
        picks.forEach(function (q) {
            const card = document.createElement('button');
            card.type = 'button';
            card.className = 'iv-suggested__item';
            card.innerHTML = '<span></span><em></em>';
            card.querySelector('span').textContent = q.text;
            card.querySelector('em').textContent = q.topic;
            card.addEventListener('click', function () {
                showQuestion(q);
                document.querySelector('.iv-question-card').scrollIntoView({ behavior: 'smooth', block: 'center' });
            });
            suggestedEl.appendChild(card);
        });
    }

    // ---------- Wiring ----------
    modeButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
            mode = btn.dataset.mode;
            modeButtons.forEach(function (b) { b.classList.toggle('is-active', b === btn); });
            showQuestion(pickQuestion());
            renderSuggestions();
        });
    });

    document.getElementById('iv-next').addEventListener('click', function () {
        showQuestion(pickQuestion());
    });

    document.getElementById('iv-prev').addEventListener('click', function () {
        const prev = history.pop();
        if (prev) { showQuestion(prev, { fromHistory: true }); }
    });

    document.getElementById('iv-new').addEventListener('click', function () {
        showQuestion(pickQuestion());
    });

    document.getElementById('iv-rephrase').addEventListener('click', rephrase);
    document.getElementById('iv-clear').addEventListener('click', function () {
        answerEl.value = '';
        updateCount();
        answerEl.focus();
    });
    document.getElementById('iv-save').addEventListener('click', saveDraft);
    document.getElementById('iv-feedback-btn').addEventListener('click', getFeedback);
    document.getElementById('iv-sample').addEventListener('click', getSample);
    document.getElementById('iv-shuffle').addEventListener('click', renderSuggestions);
    recordBtn.addEventListener('click', toggleRecording);
    answerEl.addEventListener('input', updateCount);

    document.getElementById('iv-mock-btn').addEventListener('click', function () {
        mockMode = true;
        session = { answered: 0, totalScore: 0 };
        sessionEl.textContent = 'Mock interview started — answer each question, then take the next one.';
        showQuestion(pickQuestion());
        document.querySelector('.iv-question-card').scrollIntoView({ behavior: 'smooth', block: 'center' });
        answerEl.focus();
    });

    evidenceToggle.addEventListener('change', function () {
        evidenceCard.hidden = !evidenceToggle.checked;
    });

    // Question-bank items load straight into the studio.
    bank.forEach(function (q) {
        q.el.addEventListener('click', function () {
            mode = 'mixed';
            modeButtons.forEach(function (b) { b.classList.toggle('is-active', b.dataset.mode === 'mixed'); });
            showQuestion(q);
            document.querySelector('.iv-question-card').scrollIntoView({ behavior: 'smooth', block: 'center' });
            answerEl.focus();
        });
    });

    // ---------- Interview direction: "Interview Me" vs "Interview the AI" ----------
    // (added 2026-07-07) The studio works both ways now. "Interview Me" is
    // the original coach flow. "Interview the AI" flips the table: the
    // visitor asks (the current question, or their own) and the AI answers
    // as Pete — a model answer to measure your own attempt against. Same
    // /api/chat endpoint as every other AI feature on the site.

    const dirMeBtn = document.getElementById('iv-dir-me');
    const dirAiBtn = document.getElementById('iv-dir-ai');
    const askaiCard = document.getElementById('iv-askai-card');
    const askaiInput = document.getElementById('iv-askai-input');
    const askaiBtn = document.getElementById('iv-askai-btn');
    const askaiAnswer = document.getElementById('iv-askai-answer');
    const responseCard = document.querySelector('.iv-response-card');
    const feedbackCard = document.getElementById('iv-feedback-card');
    const mockSection = document.querySelector('.iv-mock');

    let aiDirection = false;

    function setDirection(ai) {
        aiDirection = ai;

        dirMeBtn.classList.toggle('is-active', !ai);
        dirAiBtn.classList.toggle('is-active', ai);
        dirMeBtn.setAttribute('aria-selected', String(!ai));
        dirAiBtn.setAttribute('aria-selected', String(ai));

        // Swap which cards the studio shows. The question card stays for
        // both directions — it feeds whichever side is answering.
        askaiCard.hidden = !ai;
        responseCard.hidden = ai;
        feedbackCard.hidden = ai;
        if (mockSection) { mockSection.hidden = ai; }
    }

    if (dirMeBtn && dirAiBtn && askaiCard) {
        dirMeBtn.addEventListener('click', function () { setDirection(false); });
        dirAiBtn.addEventListener('click', function () { setDirection(true); });
    }

    function renderModelAnswer(text) {
        askaiAnswer.innerHTML = '';
        text.split(/\n{2,}/).forEach(function (part) {
            const p = document.createElement('p');
            p.textContent = part.trim();
            if (p.textContent) { askaiAnswer.appendChild(p); }
        });

        const note = document.createElement('p');
        note.className = 'iv-askai__note';
        note.textContent = 'Model answer grounded in Pete’s approved slate evidence.';
        askaiAnswer.appendChild(note);
    }

    function getModelAnswer() {
        if (busy) { return; }

        // A typed question wins; otherwise answer the current studio question.
        const question = (askaiInput.value.trim() || questionEl.textContent.trim());
        if (!question) { return; }

        busy = true;
        askaiBtn.disabled = true;
        askaiBtn.textContent = 'Thinking…';
        askaiAnswer.innerHTML =
            '<p class="iv-feedback__empty">Building a model answer from Pete’s career history and slate evidence…</p>';

        // The wording deliberately names Pete's career history, accomplishments,
        // and skills evidence — those cues route the server's knowledge picker
        // to the files a strong interview answer needs.
        const prompt =
            'Answer this interview question with a model answer, speaking in first person as Pete Carter. ' +
            'Ground every claim in Pete’s real career history, accomplishments, and skills evidence — do not invent anything. ' +
            'Use a STAR shape (situation, task, action, result) in two short plain-text paragraphs, about 150 words total, ' +
            'and include one or two concrete metrics. Interview question: "' + question + '"';

        askCoach(prompt)
            .then(function (text) {
                renderModelAnswer(text);
            })
            .catch(function (error) {
                askaiAnswer.innerHTML = '';
                const p = document.createElement('p');
                p.className = 'iv-feedback__empty';
                p.textContent = (error && error.message) || 'The assistant is unavailable right now — please try again.';
                askaiAnswer.appendChild(p);
            })
            .finally(function () {
                busy = false;
                askaiBtn.disabled = false;
                askaiBtn.textContent = 'Get Model Answer';
            });
    }

    if (askaiBtn) {
        askaiBtn.addEventListener('click', getModelAnswer);
        askaiInput.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                getModelAnswer();
            }
        });
    }

    // ---------- Boot ----------
    asked = 0;
    showQuestion(pool()[0]);
    renderSuggestions();
})();

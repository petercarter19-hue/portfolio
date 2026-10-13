/* Owner resume page: Ask AI panels (PS-RESUME-PAGE-OWNER-001, D1).
 *
 * D1 makes no AI call. The default transport answers with the truthful
 * unavailable state; the owner's private preview (PS-RESUME-PAGE-PUBLIC-001)
 * plugs in through setTransport() without changing this file's behaviour.
 * The "thinking" state is the three stones stacking, shown only while a
 * transport request is actually pending. Every answer is written as text.
 */
(function (global) {
    'use strict';

    var doc = global.document;
    var panels = Array.prototype.slice.call(doc.querySelectorAll('[data-rp-ask]'));
    if (!panels.length) return;

    var UNAVAILABLE = 'Ask AI isn’t available right now.';

    function unavailableTransport() {
        return Promise.resolve({state: 'unavailable'});
    }
    var transport = unavailableTransport;

    function el(tag, className, textValue) {
        var node = doc.createElement(tag);
        if (className) node.className = className;
        if (textValue) node.textContent = textValue;
        return node;
    }

    function stones() {
        var wrap = el('div', 'rp-thinking');
        wrap.setAttribute('role', 'status');
        var svg = doc.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('aria-hidden', 'true');
        svg.setAttribute('focusable', 'false');
        svg.setAttribute('class', 'rp-thinking__stones');
        ['M3.6 19.6C3.6 14.8 20.4 14.8 20.4 19.6C20.4 23.07 3.6 23.07 3.6 19.6Z',
            'M6.7 11.73C6.7 7.56 19.3 7.56 19.3 11.73C19.3 14.76 6.7 14.76 6.7 11.73Z',
            'M6.8 4.58C6.8 0.87 15.4 0.87 15.4 4.58C15.4 7.27 6.8 7.27 6.8 4.58Z'].forEach(function (d, i) {
            var path = doc.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', d);
            path.setAttribute('class', 'rp-stone rp-stone--' + (i + 1));
            if (i === 2) path.setAttribute('transform', 'rotate(-10 11.1 4.2)');
            svg.appendChild(path);
        });
        wrap.appendChild(svg);
        wrap.appendChild(el('span', 'rp-thinking__text', 'Thinking…'));
        return wrap;
    }

    function bind(panel) {
        var form = panel.querySelector('[data-rp-ask-form]');
        var input = panel.querySelector('[data-rp-ask-input]');
        var log = panel.querySelector('[data-rp-ask-log]');
        var go = form.querySelector('button[type="submit"]');
        var busy = false;
        var inputRevision = 0;  // bumped on every member edit; a completion only touches the box it was sent from

        function grow() {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 108) + 'px';
        }
        input.addEventListener('input', function () { inputRevision += 1; grow(); });
        input.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
                event.preventDefault();
                form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit', {cancelable: true}));
            }
        });

        function ask(question) {
            question = String(question || '').replace(/\s+/g, ' ').trim();
            if (!question || busy) { input.focus(); return Promise.resolve(); }
            busy = true;
            var sentRevision = inputRevision, sentValue = input.value;
            go.disabled = true;
            panel.setAttribute('aria-busy', 'true');
            log.hidden = false;
            var turn = el('div', 'rp-turn');
            turn.appendChild(el('p', 'rp-turn__me', question));
            var thinking = stones();
            turn.appendChild(thinking);
            log.replaceChildren(turn);
            panel.dataset.askState = 'thinking';
            if (global.PeerSlateResumePage) global.PeerSlateResumePage.updateRailAsk();
            var surface = panel.getAttribute('data-rp-ask');
            return Promise.resolve()
                .then(function () { return transport(question, {surface: surface}); })
                .catch(function () { return {state: 'unavailable'}; })
                .then(function (result) {
                    thinking.remove();
                    var answer = el('div', 'rp-turn__ai');
                    // The question stays in the conversation (turn__me); the box belongs to the member.
                    var untouched = inputRevision === sentRevision && input.value === sentValue;
                    if (result && result.state === 'answer' && result.paragraphs && result.paragraphs.length) {
                        result.paragraphs.forEach(function (p) { answer.appendChild(el('p', '', String(p))); });
                        if (untouched) input.value = '';
                        panel.dataset.askState = 'answered';
                    } else {
                        // Unavailable: the sent question is still in the box unless the member has typed since.
                        answer.classList.add('rp-turn__ai--unavailable');
                        answer.appendChild(el('p', '', UNAVAILABLE));
                        panel.dataset.askState = 'unavailable';
                    }
                    turn.appendChild(answer);
                    if (untouched) grow();
                })
                .then(function () {
                    busy = false;
                    go.disabled = false;
                    panel.removeAttribute('aria-busy');
                    if (global.PeerSlateResumePage) global.PeerSlateResumePage.updateRailAsk();
                });
        }

        form.addEventListener('submit', function (event) {
            event.preventDefault();
            ask(input.value);
        });
        panel.addEventListener('click', function (event) {
            var chip = event.target.closest('[data-rp-ask-q]');
            if (!chip || !panel.contains(chip)) return;
            input.value = chip.getAttribute('data-rp-ask-q');
            inputRevision += 1;
            grow();
            ask(input.value);
        });
        panel._rpAsk = ask;
    }

    function starters(model) {
        var first = model && model.person && model.person.firstName;
        var who = first ? first + '’s' : 'this';
        var list = [first ? 'Give me ' + who + ' 60-second recruiter brief' : 'Give me the 60-second recruiter brief',
            'What results has ' + (first || 'this person') + ' delivered?'];
        var roles = model && model.sections ? model.sections.experience : [];
        if (roles.length > 1) list.push('How has ' + (first || 'this person') + '’s work grown across roles?');
        else if (model && model.sections && model.sections.skills.length) list.push('What are ' + who + ' strongest skills?');
        return list;
    }

    function setStarters(model) {
        var list = model && !model.empty ? starters(model) : [];
        panels.forEach(function (panel) {
            var host = panel.querySelector('[data-rp-ask-chips]');
            if (!host) return;
            host.replaceChildren();
            list.forEach(function (q) {
                var b = el('button', 'rp-chip', q);
                b.type = 'button';
                b.setAttribute('data-rp-ask-q', q);
                host.appendChild(b);
            });
            host.hidden = !list.length;
            var hint = host.previousElementSibling;
            if (hint && hint.classList.contains('rp-ask__hint')) hint.hidden = !list.length;
        });
    }

    panels.forEach(bind);
    global.PeerSlateResumePageAsk = Object.freeze({
        setTransport: function (fn) { transport = typeof fn === 'function' ? fn : unavailableTransport; },
        setStarters: setStarters,
        starters: starters,
        ask: function (variant, question) {
            var panel = doc.querySelector('[data-rp-ask="' + variant + '"]');
            return panel && panel._rpAsk ? panel._rpAsk(question) : Promise.resolve();
        }
    });
})(window);

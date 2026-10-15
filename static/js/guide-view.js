/* Detached C1 section navigation. Rendering never fetches or accepts content. */
(function (global) {
    'use strict';
    var frames = new WeakMap(), choiceSerial = 0;
    // Trusted vectors copied from the approved R6q icons.js; no member HTML.
    var vectors = {
        grip: '<svg viewBox="0 0 14 20" fill="currentColor" aria-hidden="true"><circle cx="4" cy="4" r="1.6"/><circle cx="10" cy="4" r="1.6"/><circle cx="4" cy="10" r="1.6"/><circle cx="10" cy="10" r="1.6"/><circle cx="4" cy="16" r="1.6"/><circle cx="10" cy="16" r="1.6"/></svg>',
        cairn: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="12" fill="#07513a"/><g fill="#ffffff" transform="translate(12 12) scale(0.64) translate(-12 -12)"><path d="M3.6 19.6C3.6 14.8 20.4 14.8 20.4 19.6C20.4 23.07 3.6 23.07 3.6 19.6Z"/><path d="M6.7 11.73C6.7 7.56 19.3 7.56 19.3 11.73C19.3 14.76 6.7 14.76 6.7 11.73Z"/><path d="M6.8 4.58C6.8 0.87 15.4 0.87 15.4 4.58C15.4 7.27 6.8 7.27 6.8 4.58Z" transform="rotate(-10 11.1 4.2)"/></g></svg>',
        minus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M5 12h14"/></svg>',
        close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M5 5l14 14M19 5L5 19"/></svg>',
        lock: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 10V7a5 5 0 0 1 10 0v3h1.5A1.5 1.5 0 0 1 20 11.5v9A1.5 1.5 0 0 1 18.5 22h-13A1.5 1.5 0 0 1 4 20.5v-9A1.5 1.5 0 0 1 5.5 10H7zm2 0h6V7a3 3 0 0 0-6 0v3z"/></svg>',
        check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
        pencil: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/></svg>',
        doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 3h7l5 5v13H7V3z"/><path d="M14 3v5h5"/><path d="M10 13h6M10 16.5h6"/></svg>',
        chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 18l-1.5 3.5L8 19.5A9 9 0 1 0 5 18z"/></svg>',
        mic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/></svg>',
        clip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15.5 7.5l-6.8 6.8a2 2 0 0 0 2.8 2.8l7-7a4 4 0 0 0-5.7-5.7l-7 7a6 6 0 0 0 8.5 8.5L20 14.2"/></svg>',
        up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>',
        checkCircle: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="currentColor"/><path d="M7.5 12.3l3 3 6-6.3" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        spinner: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="3" opacity=".25"/><path d="M12 3a9 9 0 0 1 9 9" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>'
    };
    function vector(document, name) {
        var holder = document.createElement('span'); holder.innerHTML = vectors[name]; return holder.firstElementChild;
    }
    function publicationHeader(state, narrow) {
        // Claude's C1 ruling, coordination0b6d3fb. Counts await B2's shared
        // publish basis; neither proposal counts nor the mock's literal1 fit.
        var forms = {
            unpublished: ['Private draft. Nothing is published.', 'Private draft', 'lock'],
            published: ['Published. Changes stay private.', 'Published. Changes stay private.', 'check'],
            changes_waiting: ['Published · changes not published yet', 'Published · changes waiting', 'check'],
            unknown: ['Changes stay private. Publish status unavailable.', 'Changes stay private', 'lock']
        };
        if (!Object.prototype.hasOwnProperty.call(forms, state)) throw new TypeError('Known publication state required');
        var form = forms[state];
        return Object.freeze({fullText: form[0], visibleText: narrow ? form[1] : form[0], icon: form[2]});
    }
    // Construct once per open. The receipt-aware caller supplies the server's
    // publication state; caption refreshes never replace recoverable body input.
    function frame(root, options) {
        if (!root || root.tagName !== 'DIALOG' || !options || typeof options.onAction !== 'function') throw new TypeError('Guide dialog and action handler required');
        publicationHeader(options.publicationState, options.narrow);
        var previous = frames.get(root);
        if (previous) previous.dispose();
        var document = root.ownerDocument, handlers = [], disposed = false;
        function element(tag, className) {
            var node = document.createElement(tag); node.className = className; return node;
        }
        function icon(name) {
            return vector(document, name);
        }
        function button(label, action, className, vector) {
            var node = element('button', className); node.type = 'button';
            if (vector) { node.setAttribute('aria-label', label); node.append(icon(vector)); }
            else node.textContent = label;
            if (action) {
                node.dataset.guideAction = action;
                var handler = function () { options.onAction(action); };
                node.addEventListener('click', handler); handlers.push([node, handler]);
            }
            return node;
        }
        root.replaceChildren(); root.classList.add('ps-guide-shell');
        root.removeAttribute('aria-labelledby'); root.removeAttribute('aria-describedby');
        root.setAttribute('aria-label', 'PeerSlate Guide');
        var header = element('header', 'ps-guide-head');
        var grip = button('Move the Guide: drag, or use the arrow keys.', null, 'ps-guide-grip', 'grip');
        var avatar = element('span', 'ps-guide-avatar'); avatar.setAttribute('aria-hidden', 'true'); avatar.append(icon('cairn'));
        // Never an ellipsis: when space runs out only "Guide" shows; the brand stays for assistive technology.
        var title = element('h2', 'ps-guide-title'), brand = element('span', 'ps-guide-title-brand');
        brand.textContent = 'PeerSlate '; title.append(brand, 'Guide');
        var finish = button('Finish for now', 'finish', 'ps-guide-finish');
        var privacy = element('span', 'ps-guide-privacy');
        privacy.setAttribute('role', 'status'); privacy.setAttribute('aria-atomic', 'true');
        var publicationState = options.publicationState, caption = null, observedWidth = null;
        function publication(state, narrow) {
            var width = root.getBoundingClientRect().width;
            var form = publicationHeader(state, narrow === undefined ? state === 'unknown' || width > 0 && width <= 700 : narrow);
            publicationState = state;
            if (caption && caption.fullText === form.fullText && caption.visibleText === form.visibleText && caption.icon === form.icon) return;
            caption = form;
            var text = document.createElement('span');
            text.textContent = form.visibleText; privacy.replaceChildren(icon(form.icon), text);
            privacy.setAttribute('aria-label', form.fullText);
            fitTitle();
        }
        function fitTitle() {
            // First the privacy line shortens (above); then, only if still needed, the title.
            title.classList.remove('is-short');
            if (title.scrollWidth > title.clientWidth + 0.5) title.classList.add('is-short');
        }
        publication(options.publicationState, options.narrow);
        var controls = element('span', 'ps-guide-window-controls');
        var minimize = button('Minimize the Guide', 'minimize', 'ps-guide-window-button', 'minus');
        var close = button('Close the Guide', 'close', 'ps-guide-window-button', 'close'); controls.append(minimize, close);
        header.append(grip, avatar, title, finish, privacy, controls);
        var body = element('div', 'ps-guide-body'), composer = element('div', 'ps-guide-composer'), footer = element('footer', 'ps-guide-footer');
        var manual = button('Edit myself', 'manual', 'ps-guide-manual'); manual.prepend(icon('pencil')); footer.append(manual);
        root.append(header, body, composer, footer);
        var cancel = function (event) { event.preventDefault(); options.onAction('close'); };
        root.addEventListener('cancel', cancel);
        var observer = new global.ResizeObserver(function () {
            var width = root.getBoundingClientRect().width;
            if (width > 0 && width !== observedWidth) { observedWidth = width; publication(publicationState); fitTitle(); }
        });
        observer.observe(root);
        var result = Object.freeze({header: header, grip: grip, body: body, composer: composer, privacy: privacy, publication: publication,
            controls: Object.freeze({finish: finish, minimize: minimize, close: close, manual: manual}),
            dispose: function () {
                if (disposed) return;
                disposed = true; observer.disconnect(); root.removeEventListener('cancel', cancel);
                handlers.forEach(function (pair) { pair[0].removeEventListener('click', pair[1]); });
                frames.delete(root);
            }});
        frames.set(root, result); return result;
    }
    // D47/first_arrival names a presentation, not an eligibility decision.
    // C1 opens only on member action. B2-0/C2 supply server-qualified auto-open.
    function welcome(root, options) {
        if (!root || root.nodeType !== 1 || !options || ['first_arrival', 'manual'].indexOf(options.mode) < 0 ||
            typeof options.onAction !== 'function' || (options.mode === 'first_arrival' &&
            (typeof options.firstName !== 'string' || !options.firstName.trim()))) throw new TypeError('Explicit welcome mode, name and action handler required');
        var document = root.ownerDocument, first = options.mode === 'first_arrival';
        root.replaceChildren(); root.dataset.guideView = 'welcome';
        var heading = document.createElement('h3'); heading.className = 'ps-guide-screen-heading';
        heading.textContent = first ? 'Welcome to PeerSlate, ' + options.firstName + '.' : 'Let’s build your resume together.';
        var intro = document.createElement('p'); intro.className = 'ps-guide-screen-copy';
        intro.textContent = first ? 'Everything stays private until you share it.' : 'Nothing goes into your resume until you approve it.';
        root.append(heading, intro);
        if (first) {
            var offer = document.createElement('div'); offer.className = 'ps-guide-ask-intro';
            var words = document.createElement('span'), name = document.createElement('b'); name.textContent = 'Ask ' + options.firstName + ' AI';
            words.append(document.createTextNode('Once you publish, '), name, document.createTextNode(' can answer questions from what you’ve published.'));
            offer.append(vector(document, 'cairn'), words); root.append(offer);
        }
        var tiles = document.createElement('div'); tiles.className = 'ps-guide-start-tiles';
        var starts = [
            ['upload', 'Upload a file', 'A resume or your notes: PDF, Word or text.', 'doc'],
            // Approved D35 fallback until package8 installs/proves live words.
            ['talk', 'Talk it through', 'I’ll write it out when you stop.', 'mic'],
            ['type', 'Type or paste', 'Any order is fine.', 'pencil']
        ];
        starts.forEach(function (start) {
            var button = document.createElement('button'); button.type = 'button'; button.className = 'ps-guide-start-tile';
            button.setAttribute('aria-label', start[1]);
            var imprint = document.createElement('span'); imprint.className = 'ps-guide-tile-imprint'; imprint.setAttribute('aria-hidden', 'true'); imprint.append(vector(document, start[3]));
            var title = document.createElement('b'); title.textContent = start[1];
            var detail = document.createElement('span'); detail.className = 'ps-guide-tile-detail'; detail.textContent = start[2];
            detail.id = 'ps-guide-choice-hint-' + (++choiceSerial); button.setAttribute('aria-describedby', detail.id);
            button.append(imprint, title, detail);
            button.addEventListener('click', function () { if (root.contains(button) && button.isConnected) options.onAction(start[0]); });
            tiles.append(button);
        });
        root.append(tiles);
        if (first) {
            var hint = document.createElement('p'); hint.className = 'ps-guide-no-resume';
            var question = document.createElement('button'); question.type = 'button'; question.textContent = 'Don’t have a resume yet?';
            question.addEventListener('click', function () { if (root.contains(question) && question.isConnected) options.onAction('no_resume'); });
            hint.append(question, document.createTextNode(' I’ll ask a few questions.')); root.append(hint);
        }
    }
    function organizing(root, options) {
        if (!root || root.nodeType !== 1 || !options || options.inFlight !== true || !options.state ||
            typeof options.state.data !== 'function' || typeof options.state.loadState !== 'function') throw new TypeError('Active request and working-set state required');
        function elapsedText(seconds) {
            if (!Number.isSafeInteger(seconds) || seconds < 0) throw new TypeError('Observed elapsed seconds required');
            return Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
        }
        if (options.elapsedSeconds !== undefined) elapsedText(options.elapsedSeconds);
        var ref = options.sourceRef;
        if (ref !== undefined && (!ref || typeof ref.sourceKey !== 'string' || !ref.sourceKey ||
            !Number.isSafeInteger(ref.version) || ref.version < 1)) throw new TypeError('Exact source binding required');
        var data = options.state.loadState() === 'loaded' ? options.state.data() : null;
        var source = data && ref ? data.active_sources.find(function (row) {
            return row.source_key === ref.sourceKey && row.source_version === ref.version && row.kind === 'document' && row.state === 'active';
        }) : null;
        var document = root.ownerDocument;
        root.replaceChildren(); root.dataset.guideView = 'organizing';
        var heading = document.createElement('h3'); heading.className = 'ps-guide-screen-heading'; heading.textContent = 'Organizing your file…';
        var intro = document.createElement('p'); intro.className = 'ps-guide-screen-copy'; intro.textContent = 'Everything appears behind me at once.';
        var progress = document.createElement('div'); progress.className = 'ps-guide-progress';
        progress.setAttribute('role', 'status'); progress.setAttribute('aria-live', 'polite');
        function line(text, done) {
            var row = document.createElement('div'); row.className = done ? 'ps-guide-progress-done' : 'ps-guide-progress-current';
            row.append(vector(document, done ? 'checkCircle' : 'spinner'), document.createTextNode(text)); progress.append(row); return row;
        }
        // Only the same owner-bound source/version proves these milestones.
        // A request alone does not prove that a new upload has been retained.
        if (source) {
            line('Your file is saved privately', true);
            if (source.complete === true && Number.isSafeInteger(source.page_count) && source.page_count > 0)
                line('Read ' + source.page_count + (source.page_count === 1 ? ' page' : ' pages'), true);
        }
        var current = line('Sorting it into sections', false);
        var timer = document.createElement('span'); timer.className = 'ps-guide-progress-elapsed';
        timer.setAttribute('role', 'timer'); timer.setAttribute('aria-live', 'off'); current.append(timer);
        function elapsed(seconds) {
            var text = elapsedText(seconds);
            if (!root.contains(timer)) return false;
            timer.textContent = ' · ' + text; return true;
        }
        root.append(heading, intro, progress);
        if (options.elapsedSeconds !== undefined) elapsed(options.elapsedSeconds);
        return Object.freeze({elapsed: elapsed});
    }
    function create(root, options) {
        if (!root || root.nodeType !== 1) throw new TypeError('Guide view root required');
        var onSection = options && options.onSection;
        if (onSection !== undefined && typeof onSection !== 'function') throw new TypeError('Section callback required');
        var selected = null, document = root.ownerDocument;
        root.classList.add('ps-guide-view');
        function current(nav) {
            nav.querySelectorAll('button').forEach(function (button) {
                if (button.dataset.section === selected) button.setAttribute('aria-current', 'page');
                else button.removeAttribute('aria-current');
            });
        }
        return Object.freeze({render: function (state) {
            var data = state.data(), focused = root.contains(document.activeElement) && document.activeElement.dataset.section;
            root.replaceChildren(); root.dataset.guideView = 'sections';
            if (!data || state.loadState() !== 'loaded') {
                var status = document.createElement('p');
                status.setAttribute('role', 'status');
                status.textContent = 'The Guide is unavailable right now.';
                root.append(status);
                return false;
            }
            var sections = data.sections.filter(function (section) { return section.tab_visible; });
            if (!sections.some(function (section) { return section.key === selected; })) selected = sections.length ? sections[0].key : null;
            var nav = document.createElement('nav');
            nav.className = 'ps-guide-tabs';
            nav.setAttribute('aria-label', 'Resume sections');
            sections.forEach(function (section) {
                var button = document.createElement('button');
                button.type = 'button'; button.dataset.section = section.key;
                // Child bullets and waiting updates have separate server counts.
                // They never inflate the number of cards in a section tab.
                button.textContent = section.label + ' (' + (section.counts.saved + section.counts.waiting) + ')';
                button.addEventListener('click', function () {
                    selected = section.key; current(nav);
                    if (onSection) onSection(section.key);
                });
                nav.append(button);
            });
            current(nav); root.append(nav);
            if (focused) {
                var match = Array.from(nav.children).find(function (button) { return button.dataset.section === focused; });
                if (match) match.focus();
            }
            return true;
        }});
    }
    global.PeerSlateGuideView = Object.freeze({create: create, frame: frame, welcome: welcome, organizing: organizing, publicationHeader: publicationHeader,
        icon: function (name) {
            if (!Object.prototype.hasOwnProperty.call(vectors, name)) throw new TypeError('Known Guide icon required');
            return vector(global.document, name);
        }});
})(window);

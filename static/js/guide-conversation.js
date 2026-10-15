/* C1 transient composer. The caller owns server draft/dispatch/receipt state.
 * Local revision is only an input frontier, never authorization or DB version.
 */
(function (global) {
    'use strict';
    function createComposer(host, options) {
        if (!host || host.nodeType !== 1 || !options || typeof options.onSend !== 'function' ||
            typeof options.onAction !== 'function' || (options.onInput !== undefined && typeof options.onInput !== 'function')) throw new TypeError('Composer host and explicit handlers required');
        var document = host.ownerDocument, revision = 0, busy = false, disposed = false, observedWidth = null, attachments = [];
        var box = document.createElement('div'); box.className = 'ps-guide-compose-box';
        var fileList = document.createElement('div'); fileList.className = 'ps-guide-attachment-row'; fileList.hidden = true;
        fileList.setAttribute('role', 'group'); fileList.setAttribute('aria-label', 'Attached files, not sent yet');
        var row = document.createElement('div'); row.className = 'ps-guide-compose-row';
        var words = options.input === undefined ? document.createElement('textarea') : options.input;
        if (!words || words.tagName !== 'TEXTAREA' || words.ownerDocument !== document) throw new TypeError('Same-page input required');
        var observedText = words.value;
        function observeInput() {
            if (words.value !== observedText) { observedText = words.value; revision += 1; }
        }
        // Reuse the incumbent transport's exact node, bytes and input listeners.
        // Recording, immutable submissions and draft ownership stay with it.
        words.rows = 1; words.classList.add('ps-guide-compose-words');
        words.setAttribute('aria-label', 'Message to the Guide');
        words.placeholder = 'Ask a question or make a change…';
        var placeholder = words.placeholder;
        function button(label, icon, className) {
            var node = document.createElement('button'); node.type = 'button'; node.className = className;
            node.setAttribute('aria-label', label); node.append(global.PeerSlateGuideView.icon(icon)); return node;
        }
        var attach = button('Attach a file', 'clip', 'ps-guide-compose-attach');
        var talk = button('Record a message', 'mic', 'ps-guide-compose-talk');
        talk.setAttribute('aria-pressed', 'false');
        var send = button('Send', 'up', 'ps-guide-compose-send');
        row.append(attach, words, talk, send); box.append(fileList, row);
        // One plain line above the box says why Send is unavailable. Nothing is ever cut or sent by itself.
        var notice = document.createElement('p'); notice.className = 'ps-guide-compose-notice'; notice.setAttribute('role', 'status');
        notice.hidden = true; host.replaceChildren(notice, box);
        words.removeAttribute('maxlength');
        function snapshot() {
            observeInput();
            return Object.freeze({text: words.value, revision: revision,
                attachmentKeys: Object.freeze(attachments.filter(function (file) { return file.phase === 'attached'; })
                    .map(function (file) { return file.clientKey; }))});
        }
        function unsettled() { return attachments.some(function (file) { return file.phase === 'sending' || file.phase === 'unknown'; }); }
        function renderFiles() {
            fileList.replaceChildren(); fileList.hidden = !attachments.length;
            attachments.forEach(function (file) {
                var chip = document.createElement('span'); chip.className = 'ps-guide-file-chip';
                var name = document.createElement('b'); name.textContent = file.filename;
                var status = document.createElement('em');
                status.textContent = {attached: 'not sent yet', sending: 'sending', unknown: 'send status unavailable',
                    sent: 'sent', needs_reattach: 'choose the file again'}[file.phase];
                var remove = button('Remove ' + file.filename, 'close', 'ps-guide-file-remove');
                remove.disabled = file.removable === false;
                remove.addEventListener('click', function () {
                    if (!disposed && fileList.contains(remove)) options.onAction('remove_attachment',
                        Object.freeze({clientKey: file.clientKey, revision: revision}));
                });
                chip.append(global.PeerSlateGuideView.icon('doc'), name, status, remove); fileList.append(chip);
            });
        }
        function sync() {
            observeInput();
            var cap = parseFloat(global.getComputedStyle(words).maxHeight);
            if (!Number.isFinite(cap)) cap = 132; // R6q's about-six-line composer, before CSS is available.
            words.style.height = 'auto'; words.style.height = Math.min(cap, words.scrollHeight) + 'px';
            words.style.overflowY = words.scrollHeight > cap ? 'auto' : 'hidden';
            var over = words.value.length > 20000;
            // Words and a file are sent one at a time in C1: the file first (its receipt is store-and-read), then the words.
            var separate = typeof options.separateWordsAndFiles === 'function' ? options.separateWordsAndFiles() === true
                : options.separateWordsAndFiles === true;
            var mixed = separate && Boolean(words.value.trim()) &&
                attachments.some(function (file) { return file.phase === 'attached'; });
            notice.textContent = over ? 'That\u2019s longer than I can take in one message. Send it in parts, or attach it as a file.'
                : mixed ? 'Send the file first, then your message.' : '';
            notice.hidden = !(over || mixed);
            send.disabled = busy || over || mixed || unsettled() || attachments.some(function (file) { return file.phase === 'needs_reattach'; }) ||
                (!words.value.trim() && !attachments.some(function (file) { return file.phase === 'attached'; }));
            send.classList.toggle('is-ready', !send.disabled); box.setAttribute('aria-busy', String(busy));
        }
        function input() { sync(); if (options.onInput) options.onInput(snapshot()); }
        function submit() { if (!disposed && !send.disabled) options.onSend(snapshot()); }
        var composing = false;
        function compositionStart() { composing = true; }
        function compositionEnd() { composing = false; }
        function keydown(event) {
            if (event.key !== 'Enter' || event.shiftKey || event.ctrlKey || event.metaKey || event.altKey ||
                    event.isComposing || composing || event.keyCode === 229) return;
            event.preventDefault(); submit();
        }
        function attachment() { if (!disposed) options.onAction('attach'); }
        function recording() { if (!disposed) options.onAction('record'); }
        words.addEventListener('input', input); words.addEventListener('keydown', keydown);
        words.addEventListener('compositionstart', compositionStart); words.addEventListener('compositionend', compositionEnd);
        send.addEventListener('click', submit);
        attach.addEventListener('click', attachment); talk.addEventListener('click', recording); sync();
        var observer = new global.ResizeObserver(function () {
            var width = host.getBoundingClientRect().width;
            if (!disposed && width > 0 && width !== observedWidth) { observedWidth = width; sync(); }
        });
        observer.observe(host);
        return Object.freeze({
            snapshot: snapshot,
            setBusy: function (value) { if (typeof value !== 'boolean') throw new TypeError('Explicit busy state required'); busy = value; sync(); },
            setRecording: function (value) {
                if (typeof value !== 'boolean') throw new TypeError('Explicit recording state required');
                talk.setAttribute('aria-pressed', String(value));
                talk.setAttribute('aria-label', value ? 'Stop recording' : 'Record a message');
                words.readOnly = value;
                words.placeholder = value ? 'Stop to type or edit.' : placeholder;
            },
            // Only the controller holds File bytes and dispatch identity. These
            // descriptors and phases are supplied by that controller's actual
            // dispatch/receipt state. Sent files cannot enter another message.
            setAttachments: function (files) {
                if (disposed) return false;
                if (!Array.isArray(files)) throw new TypeError('Explicit unsent files required');
                var keys = new Set(), next = files.map(function (file) {
                    if (!file || typeof file.clientKey !== 'string' || !file.clientKey.trim() || keys.has(file.clientKey) ||
                        typeof file.filename !== 'string' || !file.filename.trim() ||
                        ['attached', 'sending', 'unknown', 'sent', 'needs_reattach'].indexOf(file.phase) < 0) throw new TypeError('Distinct file keys, names and explicit phases required');
                    if (file.removable !== undefined && typeof file.removable !== 'boolean') throw new TypeError('Explicit file action availability required');
                    keys.add(file.clientKey); return Object.freeze({clientKey: file.clientKey, filename: file.filename,
                        phase: file.phase, removable: file.removable !== false});
                });
                if (JSON.stringify(next) !== JSON.stringify(attachments)) {
                    var frontier = function (rows) { return JSON.stringify(rows.map(function (file) { return [file.clientKey, file.filename]; })); };
                    // A transport status update is not a new member edit.
                    if (frontier(next) !== frontier(attachments)) revision += 1;
                    attachments = next; renderFiles(); sync();
                }
                return true;
            },
            restore: function (text, expectedRevision) {
                observeInput();
                if (disposed || busy || unsettled() || typeof text !== 'string' || !Number.isSafeInteger(expectedRevision) || expectedRevision !== revision) return false;
                if (words.value !== text) { words.value = text; observeInput(); sync(); }
                return true;
            },
            // Invoke only after the matching server acknowledgment. Newer
            // words are never cleared by a late/unknown response.
            clear: function (expectedRevision) {
                observeInput();
                if (disposed || busy || unsettled() || !Number.isSafeInteger(expectedRevision) || expectedRevision !== revision) return false;
                if (words.value || attachments.length) { words.value = ''; observedText = ''; attachments = []; revision += 1; renderFiles(); sync(); }
                return true;
            },
            focus: function () { if (!disposed) words.focus(); },
            dispose: function () {
                disposed = true; observer.disconnect(); words.removeEventListener('input', input); words.removeEventListener('keydown', keydown);
                words.removeEventListener('compositionstart', compositionStart); words.removeEventListener('compositionend', compositionEnd);
                send.removeEventListener('click', submit);
                attach.removeEventListener('click', attachment); talk.removeEventListener('click', recording);
            }
        });
    }
    global.PeerSlateGuideConversation = Object.freeze({createComposer: createComposer});
})(window);

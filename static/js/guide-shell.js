/* Approved C1 geometry. Shell integration owns rendering and member actions. */
(function (global) {
    'use strict';
    function dimension(value) {
        if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) throw new TypeError('Visible dimensions required');
        return value;
    }
    function fit(value, low, high) { return Math.min(Math.max(low, value), Math.max(low, high)); }
    function geometry(options) {
        var width = dimension(options.width), height = dimension(options.height), task = options.task || 'standard';
        if (['standard', 'narrow', 'wide'].indexOf(task) < 0) throw new TypeError('Unknown Guide task width');
        if (width < 960) return Object.freeze({width: width, left: 0, top: 0, maxHeight: height, draggable: false, bodyScroll: false});
        // Claude's 2026-10-13 ruling: planned centered 1240px wrapper + 268px rail.
        // bind reads Lane D's live shared L; this is the one absent-page fallback.
        var leftEdge = options.leftColumnEdge;
        if (leftEdge === undefined) leftEdge = Math.max(16, (width - 1240) / 2) + 268;
        if (typeof leftEdge !== 'number' || !Number.isFinite(leftEdge) || leftEdge < 0) throw new TypeError('Valid rail edge required');
        var panelWidth = task === 'narrow' ? 560 : task === 'wide' ? Math.min(960, width - 48) : fit(width - 2 * leftEdge, 620, 744);
        var left = (width - panelWidth) / 2;
        if (task !== 'wide') left = Math.max(leftEdge, left);
        left = fit(left, 8, width - panelWidth - 8);
        return Object.freeze({width: panelWidth, left: left, top: Math.min(76, height - 8),
            maxHeight: Math.max(0, Math.min(height - 96, 950)), draggable: true, bodyScroll: height < 480});
    }
    function clampPosition(position, panel, viewport) {
        var width = dimension(viewport.width), height = dimension(viewport.height);
        var panelWidth = dimension(panel.width), panelHeight = dimension(panel.height);
        // 22px outside chevrons + 8px window margin. A view without chevrons
        // can pass sideMargin=8; wide comparisons retain their centered rule.
        var side = viewport.sideMargin === undefined ? 30 : viewport.sideMargin;
        if (typeof side !== 'number' || !Number.isFinite(side) || side < 8) throw new TypeError('Valid window margin required');
        var bottom = height - panelHeight - 8;
        var top = fit(position.bottom ? bottom : position.top, 8, bottom);
        return Object.freeze({left: fit(position.left, side, width - panelWidth - side), top: top,
            bottom: top >= bottom - 1});
    }
    function bind(panel, grip, options) {
        if (!panel || panel.nodeType !== 1 || !grip || grip.nodeType !== 1) throw new TypeError('Guide panel and grip required');
        options = options || {};
        var handle = options.dragHandle || grip;
        if (!panel.contains(grip) || !panel.contains(handle)) throw new TypeError('Guide controls must belong to the panel');
        var key = 'peerslate.guide.position', storage = null, position = null, drag = null, disposed = false;
        var sheet = false, desktopHeight = panel.style.height, touchAction = handle.style.touchAction;
        try { storage = global.sessionStorage; position = JSON.parse(storage.getItem(key)); } catch (_) { position = null; }
        if (!position || !Number.isFinite(position.left) || !Number.isFinite(position.top) || typeof position.bottom !== 'boolean') position = null;
        function save() {
            if (storage && position) { try { storage.setItem(key, JSON.stringify(position)); } catch (_) { /* In-memory placement still works. */ } }
        }
        var visual = global.visualViewport;
        function viewport() {
            if (visual && Number.isFinite(visual.width) && visual.width > 0 && Number.isFinite(visual.height) && visual.height > 0)
                return {width: visual.width, height: visual.height,
                    x: Number.isFinite(visual.offsetLeft) ? visual.offsetLeft : 0,
                    y: Number.isFinite(visual.offsetTop) ? visual.offsetTop : 0};
            return {width: global.innerWidth, height: global.innerHeight, x: 0, y: 0};
        }
        function railEdge(view) {
            if (options.leftColumnEdge !== undefined) return options.leftColumnEdge;
            try {
                var page = global.PeerSlateResumePage;
                var edge = page && typeof page.leftColumnEdge === 'function' ? page.leftColumnEdge() : undefined;
                if (typeof edge === 'number' && Number.isFinite(edge) && edge - view.x > 0 && edge - view.x < view.width) return edge - view.x;
            } catch (_) { /* An unavailable page leaves the approved fallback usable. */ }
            return undefined;
        }
        function place(next) {
            var view = viewport();
            position = clampPosition(next, panel.getBoundingClientRect(), view);
            panel.style.left = (position.left + view.x) + 'px'; panel.style.top = (position.top + view.y) + 'px';
        }
        function relayout() {
            if (disposed) return;
            var view = viewport(), layout = geometry({width: view.width, height: view.height,
                task: options.task, leftColumnEdge: railEdge(view)});
            panel.style.position = 'fixed'; panel.style.boxSizing = 'border-box';
            panel.style.width = layout.width + 'px'; panel.style.maxHeight = layout.maxHeight + 'px';
            panel.dataset.guideSheet = String(!layout.draggable); panel.dataset.guideBodyScroll = String(layout.bodyScroll);
            grip.setAttribute('aria-disabled', String(!layout.draggable));
            if (!layout.draggable) {
                if (!sheet) desktopHeight = panel.style.height;
                sheet = true; panel.style.height = view.height + 'px'; panel.style.left = view.x + 'px'; panel.style.top = view.y + 'px';
                drag = null; return;
            }
            if (sheet) { panel.style.height = desktopHeight; sheet = false; }
            place(position || {left: layout.left, top: layout.top, bottom: false});
            if (!drag) save();
        }
        function down(event) {
            var button = event.target.closest('button');
            if (sheet || event.button !== 0 || (button && button !== grip)) return;
            var rect = panel.getBoundingClientRect();
            var view = viewport();
            drag = {x: event.clientX, y: event.clientY, left: rect.left - view.x, top: rect.top - view.y, id: event.pointerId};
            handle.setPointerCapture(event.pointerId); grip.focus({preventScroll: true}); event.preventDefault();
        }
        function move(event) {
            if (!drag || event.pointerId !== drag.id) return;
            place({left: drag.left + event.clientX - drag.x, top: drag.top + event.clientY - drag.y, bottom: false});
        }
        function end() {
            if (!drag) return;
            var id = drag.id; drag = null;
            if (handle.hasPointerCapture(id)) handle.releasePointerCapture(id);
            save();
        }
        function keyboard(event) {
            if (sheet || event.altKey || event.ctrlKey || event.metaKey) return;
            var delta = {ArrowLeft: [-24, 0], ArrowRight: [24, 0], ArrowUp: [0, -24], ArrowDown: [0, 24]}[event.key];
            if (!delta) return;
            event.preventDefault();
            place({left: position.left + delta[0], top: position.top + delta[1], bottom: false}); save();
        }
        handle.style.touchAction = 'none';
        handle.addEventListener('pointerdown', down); handle.addEventListener('lostpointercapture', end);
        grip.addEventListener('keydown', keyboard);
        global.addEventListener('pointermove', move); global.addEventListener('pointerup', end);
        global.addEventListener('pointercancel', end); global.addEventListener('blur', end);
        global.addEventListener('resize', relayout);
        if (visual && typeof visual.addEventListener === 'function') {
            visual.addEventListener('resize', relayout); visual.addEventListener('scroll', relayout);
        }
        var observer = new global.ResizeObserver(relayout);
        observer.observe(panel); relayout();
        return Object.freeze({relayout: relayout, dispose: function (settings) {
            if (disposed) return;
            end(); disposed = true; observer.disconnect();
            handle.removeEventListener('pointerdown', down); handle.removeEventListener('lostpointercapture', end);
            grip.removeEventListener('keydown', keyboard);
            global.removeEventListener('pointermove', move); global.removeEventListener('pointerup', end);
            global.removeEventListener('pointercancel', end); global.removeEventListener('blur', end);
            global.removeEventListener('resize', relayout); handle.style.touchAction = touchAction;
            if (visual && typeof visual.removeEventListener === 'function') {
                visual.removeEventListener('resize', relayout); visual.removeEventListener('scroll', relayout);
            }
            if (settings && settings.clearPosition && storage) { try { storage.removeItem(key); } catch (_) { /* Storage may be disabled. */ } }
        }});
    }
    global.PeerSlateGuideShell = Object.freeze({geometry: geometry, clampPosition: clampPosition, bind: bind});
})(window);

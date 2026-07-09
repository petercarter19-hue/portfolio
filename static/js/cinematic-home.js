// Cinematic homepage (/experience) behavior.
//   1. Measures the real header height into --cine-header-h so the
//      aurora hero can slide underneath the frosted sticky header.
//   2. Scroll reveals: IntersectionObserver adds .is-visible to each
//      .reveal element the first time it enters the viewport.
//   3. Gentle parallax: drifts each scene's oversized backdrop a few
//      percent as the section crosses the viewport.
//   4. Respects prefers-reduced-motion — including flipping it on/off
//      live — by showing everything and freezing the backdrops.
// Browser-only; no data leaves the page.
(function () {
    'use strict';

    var docEl = document.documentElement;
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    // ---- 1 · header height -> CSS variable -------------------------
    var header = document.querySelector('.global-header');

    function setHeaderVar() {
        docEl.style.setProperty(
            '--cine-header-h',
            (header ? header.offsetHeight : 81) + 'px'
        );
    }
    setHeaderVar();
    window.addEventListener('resize', setHeaderVar);

    // ---- 2 · scroll reveal -----------------------------------------
    // .cine-js is stamped only here: if this script never runs, the
    // CSS never hides anything, so the page still renders without JS.
    docEl.classList.add('cine-js');

    var revealEls = Array.prototype.slice.call(
        document.querySelectorAll('.cinematic-home .reveal')
    );

    function showAll() {
        revealEls.forEach(function (el) { el.classList.add('is-visible'); });
    }

    if (!('IntersectionObserver' in window) || reduceMotion.matches) {
        showAll();
    } else {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    io.unobserve(entry.target);   // reveal once, stay visible
                }
            });
        }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });
        revealEls.forEach(function (el) { io.observe(el); });
    }

    // ---- 3 · parallax ----------------------------------------------
    // The .section-bg layers are oversized by 9% top/bottom in the CSS,
    // so a ±5% drift can never expose an edge.
    var layers = Array.prototype.slice.call(
        document.querySelectorAll('.cinematic-home [data-parallax]')
    ).filter(function (bg) {
        // Your Work is one continuous stage: keep its mountain backdrop
        // still (a transformed fixed background detaches) while the
        // foreground text and cards do the motion. Every other scene —
        // including Your Story — drifts normally.
        return !bg.closest('.cinematic-section--work');
    });
    var horizontalSections = Array.prototype.slice.call(
        document.querySelectorAll('.cinematic-home [data-cine-horizontal]')
    );
    var proofSections = Array.prototype.slice.call(
        document.querySelectorAll('.cinematic-home [data-work-proof]')
    );
    var EXAMPLE_SWAP_DELAY_MS = 5000;
    var exampleSwapTimers = {
        ask: null,
        interview: null
    };
    var exampleSwapReady = {
        ask: false,
        interview: false
    };
    var parallaxOn = false;
    var ticking = false;

    function clamp01(value) {
        return Math.max(0, Math.min(1, value));
    }

    function smoothStep(value) {
        value = clamp01(value);
        return value * value * (3 - 2 * value);
    }

    function scheduleExampleSwap(kind, shouldRun) {
        if (!shouldRun) {
            if (exampleSwapTimers[kind]) {
                window.clearInterval(exampleSwapTimers[kind]);
                exampleSwapTimers[kind] = null;
            }
            exampleSwapReady[kind] = false;
            return;
        }

        if (!exampleSwapTimers[kind]) {
            exampleSwapTimers[kind] = window.setInterval(function () {
                exampleSwapReady[kind] = !exampleSwapReady[kind];
                onScroll();
            }, EXAMPLE_SWAP_DELAY_MS);
        }
    }

    function applyHorizontalStages(vh) {
        // Two horizontal sections (work-ai + story-live) share the swap
        // timers, so collect "should this cycle run?" across ALL of them
        // before scheduling — otherwise the off-screen section's `false`
        // would cancel the on-screen section's timer every frame.
        var askRun = false;
        var interviewRun = false;

        horizontalSections.forEach(function (section) {
            var rect = section.getBoundingClientRect();
            var travel = Math.max(1, rect.height - vh);
            var panel = section.querySelector('.work-ai-panel');
            var windowEl = section.querySelector('.work-ai-window');
            var panelWidth = panel ? panel.offsetWidth : 0;
            var windowLeft = windowEl ? windowEl.getBoundingClientRect().left : 0;
            var trackDistance = windowLeft + panelWidth;

            // Arrival starts while the new scenic section enters from below.
            var arrival = smoothStep((vh - rect.top) / Math.max(1, vh * 0.85));
            var inside = clamp01(-rect.top / travel);
            var exit = smoothStep((inside - 0.88) / 0.12);
            var askExample = exampleSwapReady.ask ? 1 : 0;
            var interviewExample = exampleSwapReady.interview ? 1 : 0;

            if (inside < 0.08) {
                section.dataset.workAiSlide = '0';
            } else if (inside > 0.14) {
                section.dataset.workAiSlide = '1';
            }

            var slide = section.dataset.workAiSlide === '1' ? 1 : 0;

            var stageOpacity = (0.08 + arrival * 0.92) * (1 - exit * 0.94);
            var windowOpacity = (0.14 + arrival * 0.86) * (1 - exit * 0.96);
            var stageY = (1 - arrival) * 48 - exit * 62;
            var windowY = (1 - arrival) * 34 - exit * 46;
            var trackX = slide === 0
                ? '0px'
                : (-trackDistance).toFixed(1) + 'px';

            askRun = askRun || (arrival > 0.78 && inside < 0.36 && exit < 0.04);
            interviewRun = interviewRun || (slide > 0.9 && exit < 0.08);

            section.style.setProperty('--work-ai-stage-opacity', stageOpacity.toFixed(3));
            section.style.setProperty('--work-ai-window-opacity', windowOpacity.toFixed(3));
            section.style.setProperty('--work-ai-stage-y', stageY.toFixed(1) + 'px');
            section.style.setProperty('--work-ai-window-y', windowY.toFixed(1) + 'px');
            section.style.setProperty('--work-ai-track-x', trackX);
            section.style.setProperty('--work-ai-ask-example', askExample.toFixed(3));
            section.style.setProperty('--work-ai-interview-example', interviewExample.toFixed(3));
            section.style.setProperty('--work-ai-ask-primary-y', (-18 * askExample).toFixed(1) + 'px');
            section.style.setProperty('--work-ai-ask-alt-y', (22 * (1 - askExample)).toFixed(1) + 'px');
            section.style.setProperty('--work-ai-interview-primary-y', (-18 * interviewExample).toFixed(1) + 'px');
            section.style.setProperty('--work-ai-interview-alt-y', (22 * (1 - interviewExample)).toFixed(1) + 'px');
        });

        scheduleExampleSwap('ask', askRun);
        scheduleExampleSwap('interview', interviewRun);
    }

    function applyProofStages(vh) {
        proofSections.forEach(function (section) {
            var rect = section.getBoundingClientRect();
            var travel = Math.max(1, rect.height - vh);
            var panel = section.querySelector('.work-proof-panel');
            var windowEl = section.querySelector('.work-proof-window');
            var panelWidth = panel ? panel.offsetWidth : 0;
            var windowLeft = windowEl ? windowEl.getBoundingClientRect().left : 0;
            var trackDistance = windowLeft + panelWidth;

            var arrival = smoothStep((vh - rect.top) / Math.max(1, vh * 0.85));
            var inside = clamp01(-rect.top / travel);
            var exit = smoothStep((inside - 0.88) / 0.12);

            if (inside < 0.08) {
                section.dataset.workProofSlide = '0';
            } else if (inside > 0.14) {
                section.dataset.workProofSlide = '1';
            }

            var slide = section.dataset.workProofSlide === '1' ? 1 : 0;

            var stageOpacity = (0.08 + arrival * 0.92) * (1 - exit * 0.94);
            var windowOpacity = (0.14 + arrival * 0.86) * (1 - exit * 0.96);
            var stageY = (1 - arrival) * 58 - exit * 66;
            var windowY = (1 - arrival) * 38 - exit * 50;
            var trackX = slide === 0
                ? '0px'
                : (-trackDistance).toFixed(1) + 'px';

            section.style.setProperty('--work-proof-stage-opacity', stageOpacity.toFixed(3));
            section.style.setProperty('--work-proof-window-opacity', windowOpacity.toFixed(3));
            section.style.setProperty('--work-proof-stage-y', stageY.toFixed(1) + 'px');
            section.style.setProperty('--work-proof-window-y', windowY.toFixed(1) + 'px');
            section.style.setProperty('--work-proof-track-x', trackX);
        });
    }

    function applyParallax() {
        ticking = false;
        var vh = window.innerHeight || 1;
        layers.forEach(function (bg) {
            var rect = bg.parentElement.getBoundingClientRect();
            if (rect.bottom < -80 || rect.top > vh + 80) { return; }
            // -1 = section below the viewport, +1 = section above it
            var progress = (rect.top + rect.height / 2 - vh / 2) / (vh + rect.height) * 2;
            progress = Math.max(-1, Math.min(1, progress));
            var shift = progress * rect.height * 0.05;
            bg.style.transform = 'translate3d(0,' + shift.toFixed(1) + 'px,0)';
        });
        applyHorizontalStages(vh);
        applyProofStages(vh);
    }

    function onScroll() {
        if (!ticking) {
            ticking = true;
            window.requestAnimationFrame(applyParallax);
        }
    }

    function enableParallax() {
        if (parallaxOn || reduceMotion.matches || (!layers.length && !horizontalSections.length && !proofSections.length)) { return; }
        parallaxOn = true;
        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', onScroll);
        applyParallax();
    }

    function disableParallax() {
        if (!parallaxOn) { return; }
        parallaxOn = false;
        window.removeEventListener('scroll', onScroll);
        window.removeEventListener('resize', onScroll);
        // Stop the 5-second example-swap intervals too. Without this, a live
        // "reduce motion" toggle left them running: every tick calls onScroll()
        // -> applyParallax(), re-applying the exact styles cleared below.
        scheduleExampleSwap('ask', false);
        scheduleExampleSwap('interview', false);
        layers.forEach(function (bg) { bg.style.transform = ''; });
        horizontalSections.forEach(function (section) {
            section.style.removeProperty('--work-ai-stage-opacity');
            section.style.removeProperty('--work-ai-window-opacity');
            section.style.removeProperty('--work-ai-stage-y');
            section.style.removeProperty('--work-ai-window-y');
            section.style.removeProperty('--work-ai-track-x');
            section.style.removeProperty('--work-ai-ask-example');
            section.style.removeProperty('--work-ai-interview-example');
            section.style.removeProperty('--work-ai-ask-primary-y');
            section.style.removeProperty('--work-ai-ask-alt-y');
            section.style.removeProperty('--work-ai-interview-primary-y');
            section.style.removeProperty('--work-ai-interview-alt-y');
        });
        proofSections.forEach(function (section) {
            section.style.removeProperty('--work-proof-stage-opacity');
            section.style.removeProperty('--work-proof-window-opacity');
            section.style.removeProperty('--work-proof-stage-y');
            section.style.removeProperty('--work-proof-window-y');
            section.style.removeProperty('--work-proof-track-x');
        });
    }

    enableParallax();

    // ---- 4 · live reduced-motion changes ---------------------------
    function onPrefChange() {
        if (reduceMotion.matches) {
            disableParallax();
            showAll();
        } else {
            enableParallax();
        }
    }

    if (typeof reduceMotion.addEventListener === 'function') {
        reduceMotion.addEventListener('change', onPrefChange);
    } else if (typeof reduceMotion.addListener === 'function') {
        reduceMotion.addListener(onPrefChange);   // older Safari
    }

    // ---- 5 · cinematic Ask Pete AI popup placement ----------------
    var chatPanel = document.getElementById('chat-panel');
    var chatClose = document.getElementById('chat-close');
    var lastAnchoredChatScroll = 0;

    function closeAnchoredChatOnScroll() {
        if (
            !chatPanel ||
            !chatPanel.classList.contains('open') ||
            !document.body.classList.contains('cine-chat-anchored')
        ) {
            return;
        }

        if (Math.abs(window.scrollY - lastAnchoredChatScroll) < 24) { return; }
        chatPanel.classList.remove('open');
        chatPanel.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('cine-chat-anchored');
    }

    function anchorChatNear(button) {
        if (!chatPanel || !button) { return; }

        var rect = button.getBoundingClientRect();
        var panelWidth = Math.min(420, window.innerWidth - 32);
        var headerHeight = header ? header.offsetHeight : 81;
        var left = rect.right + 18;
        var top = rect.top - 22;

        if (left + panelWidth > window.innerWidth - 16 || left < 16) {
            left = Math.max(16, rect.left);
            top = rect.bottom + 14;
        }

        left = Math.min(Math.max(16, left), window.innerWidth - panelWidth - 16);
        top = Math.max(headerHeight + 12, Math.min(top, window.innerHeight - 260));
        docEl.style.setProperty('--cine-chat-left', left.toFixed(1) + 'px');
        docEl.style.setProperty('--cine-chat-top', top.toFixed(1) + 'px');
        document.body.classList.add('cine-chat-anchored');
        lastAnchoredChatScroll = window.scrollY;
    }

    Array.prototype.slice.call(
        document.querySelectorAll('.work-ai-panel--ask [data-chat-open]')
    ).forEach(function (button) {
        button.addEventListener('click', function () {
            window.setTimeout(function () { anchorChatNear(button); }, 0);
        });
    });

    if (chatClose) {
        chatClose.addEventListener('click', function () {
            document.body.classList.remove('cine-chat-anchored');
        });
    }

    window.addEventListener('scroll', closeAnchoredChatOnScroll, { passive: true });
})();

/* Atrium (Living Triptych) — progressive enhancement only.
   The slabs are visible and fully usable without this file. Here we add:
   1) a subtle pointer parallax on the triptych (desktop, fine pointer, motion OK)
   2) the Ask the Slate hand-off to the site assistant.
   Nothing here is required for content, links, or the entrance animation. */
(function () {
    'use strict';

    var atrium = document.querySelector('[data-atrium]');
    if (!atrium) return;

    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');

    /* 1) Pointer parallax — a few degrees of tilt that eases back on leave. */
    var triptych = atrium.querySelector('.atrium__triptych');
    if (triptych && finePointer.matches && !reduceMotion.matches) {
        var pending = null;
        var tiltX = 0;
        var tiltY = 0;

        var apply = function () {
            pending = null;
            triptych.style.setProperty('--tilt-x', tiltX.toFixed(2));
            triptych.style.setProperty('--tilt-y', tiltY.toFixed(2));
        };
        var schedule = function () { if (!pending) pending = requestAnimationFrame(apply); };

        atrium.addEventListener('pointermove', function (event) {
            if (event.pointerType && event.pointerType !== 'mouse') return;
            var rect = atrium.getBoundingClientRect();
            var px = (event.clientX - rect.left) / rect.width - 0.5;   // -0.5 .. 0.5
            var py = (event.clientY - rect.top) / rect.height - 0.5;
            tiltX = px * 5.5;
            tiltY = -py * 2.5;
            schedule();
        });
        atrium.addEventListener('pointerleave', function () {
            tiltX = 0; tiltY = 0; schedule();
        });
    }

    /* 2) Ask the Slate → open the existing assistant, seeded with the text.
       If the assistant API isn't present, the <form> just submits (GET). */
    var ask = atrium.querySelector('[data-atrium-ask]');
    if (ask) {
        ask.addEventListener('submit', function (event) {
            if (typeof window.openChatPanel !== 'function') return; // let GET fallback run
            event.preventDefault();
            var input = ask.querySelector('.atrium__ask-input');
            var question = input ? input.value.trim() : '';
            window.openChatPanel();
            if (!question) return;
            try {
                var target = document.querySelector(
                    '#chat-input, [data-chat-input], #chat-panel textarea, #chat-panel input[type="text"], #chat-form textarea'
                );
                if (target) {
                    target.value = question;
                    target.dispatchEvent(new Event('input', { bubbles: true }));
                    target.focus();
                }
            } catch (err) { /* seeding is best-effort */ }
        });
    }
})();

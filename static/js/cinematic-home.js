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
    );
    var parallaxOn = false;
    var ticking = false;

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
    }

    function onScroll() {
        if (!ticking) {
            ticking = true;
            window.requestAnimationFrame(applyParallax);
        }
    }

    function enableParallax() {
        if (parallaxOn || reduceMotion.matches || !layers.length) { return; }
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
        layers.forEach(function (bg) { bg.style.transform = ''; });
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
})();

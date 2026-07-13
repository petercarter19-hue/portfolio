/* PROJECT CASE STUDY (2026-07-13)
   Progressive enhancement: tracks the visitor's position through the six
   scenes and reflects it in the chapter rail (aria-current + .is-current).
   The rail links are real anchors and work without JS. */
(function () {
    'use strict';

    var root = document.querySelector('[data-pjc]');
    if (!root) return;

    var links = Array.prototype.slice.call(root.querySelectorAll('[data-pjc-chapter]'));
    var scenes = Array.prototype.slice.call(root.querySelectorAll('[data-pjc-scene]'));
    if (!links.length || !scenes.length) return;

    function setCurrent(key) {
        links.forEach(function (a) {
            var on = a.getAttribute('data-pjc-chapter') === key;
            a.classList.toggle('is-current', on);
            if (on) a.setAttribute('aria-current', 'true');
            else a.removeAttribute('aria-current');
        });
    }

    if ('IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    setCurrent(entry.target.getAttribute('data-pjc-scene'));
                }
            });
        }, { rootMargin: '-40% 0px -55% 0px' });
        scenes.forEach(function (s) { observer.observe(s); });
    }

    /* Smooth-scroll respect: the site sets scroll-behavior globally; when
       reduced motion is on, force instant jumps for rail clicks. */
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        links.forEach(function (a) {
            a.addEventListener('click', function (event) {
                var target = document.getElementById(a.getAttribute('href').slice(1));
                if (target) {
                    event.preventDefault();
                    target.scrollIntoView({ behavior: 'auto', block: 'start' });
                    target.setAttribute('tabindex', '-1');
                    target.focus({ preventScroll: true });
                }
            });
        });
    }
})();

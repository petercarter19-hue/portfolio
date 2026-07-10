// Gentle scroll reveals for the sky-glass showcase pages (My Story,
// Skills, Projects). Elements marked data-reveal float up as they enter
// the viewport; when JavaScript is absent or reduced motion is set,
// everything simply stays visible.
document.addEventListener('DOMContentLoaded', function () {
    var targets = Array.prototype.slice.call(document.querySelectorAll('[data-reveal]'));
    if (!targets.length || !('IntersectionObserver' in window)) { return; }

    document.body.classList.add('sky-reveal-on');

    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (!entry.isIntersecting) { return; }
            entry.target.classList.add('is-revealed');
            observer.unobserve(entry.target);
        });
    }, { rootMargin: '0px 0px -8% 0px' });

    targets.forEach(function (el) { observer.observe(el); });
});

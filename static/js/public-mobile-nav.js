// Public phone navigation helpers.
// 1) The public header menu keeps all three global destinations available.
// 2) A bottom tab bar mirrors a page's primary section tabs.
(function () {
    'use strict';

    var menuToggle = document.querySelector('[data-platform-menu-toggle]');
    var menu = document.querySelector('[data-platform-menu]');

    if (menuToggle && menu) {
        function setMenuOpen(open, restoreFocus) {
            menu.hidden = !open;
            menuToggle.setAttribute('aria-expanded', String(open));
            document.body.classList.toggle('has-platform-menu-open', open);

            if (open) {
                var firstFocus = menu.querySelector('a, input, button');
                if (firstFocus) firstFocus.focus();
            } else if (restoreFocus) {
                menuToggle.focus();
            }
        }

        menuToggle.addEventListener('click', function () {
            setMenuOpen(menu.hidden, false);
        });

        menu.addEventListener('click', function (event) {
            if (event.target.closest('a[href]')) setMenuOpen(false, false);
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !menu.hidden) {
                setMenuOpen(false, true);
            }
        });

        document.addEventListener('pointerdown', function (event) {
            if (
                !menu.hidden &&
                !menu.contains(event.target) &&
                !menuToggle.contains(event.target)
            ) {
                setMenuOpen(false, false);
            }
        });

        window.addEventListener('resize', function () {
            if (window.innerWidth > 1024 && !menu.hidden) {
                setMenuOpen(false, false);
            }
        });
    }

    var bar = document.getElementById('mobile-tabbar');
    var source = document.querySelector('[data-mobile-tabsource]');
    if (!bar || !source) return;

    var links = source.querySelectorAll('a[href]');
    if (!links.length) return;

    links.forEach(function (link) {
        var item = document.createElement('a');
        item.href = link.getAttribute('href');
        item.className = 'mobile-tabbar__item';
        if (link.hasAttribute('aria-current')) {
            item.setAttribute('aria-current', 'page');
        }
        item.textContent = link.textContent.trim();
        bar.appendChild(item);
    });

    bar.hidden = false;
    document.body.classList.add('has-mobile-tabbar');

    var lastY = window.pageYOffset;
    var shown = true;
    var ticking = false;

    function setShown(next) {
        if (next === shown) return;
        shown = next;
        bar.classList.toggle('is-hidden', !shown);
    }

    function onScroll() {
        var y = window.pageYOffset;
        var delta = y - lastY;

        if (y < 120) {
            setShown(true);
        } else if (delta > 6) {
            setShown(false);
        } else if (delta < -6) {
            setShown(true);
        }

        lastY = y;
        ticking = false;
    }

    window.addEventListener('scroll', function () {
        if (!ticking) {
            window.requestAnimationFrame(onScroll);
            ticking = true;
        }
    }, { passive: true });
})();

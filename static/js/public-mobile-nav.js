// Public shell behaviour (PS-PUBLIC-NAV-001, extended by PS-SHELL-001).
//
// 1) The header Menu opens the one server-rendered destination sheet.
// 2) The medium-width room switcher opens the same five destinations.
// 3) The account control opens My Slate + Sign out.
// 4) The one bottom bar mirrors a page's section tabs where the page has
//    them, and otherwise carries the global four-slot structure.
//
// Every destination, label, href, aria-current and account state below comes
// from server-rendered markup. This script only shows and hides what the
// server already wrote, and never builds a destination or reads auth state.
(function () {
    'use strict';

    var menuToggle = document.querySelector('[data-platform-menu-toggle]');
    var menu = document.querySelector('[data-platform-menu]');
    var menuOpener = menuToggle;

    function setMenuOpen(open, restoreFocus) {
        if (!menu) return;

        menu.hidden = !open;
        document.body.classList.toggle('has-platform-menu-open', open);
        if (menuToggle) menuToggle.setAttribute('aria-expanded', String(open));
        if (menuOpener && menuOpener !== menuToggle) {
            menuOpener.setAttribute('aria-expanded', String(open));
        }

        if (open) {
            var firstFocus = menu.querySelector('a, input, button');
            if (firstFocus) firstFocus.focus();
        } else if (restoreFocus && menuOpener) {
            menuOpener.focus();
        }
    }

    function openMenuFrom(opener) {
        if (!menu) return;
        var isOpen = menu.hidden;
        if (menuOpener && menuOpener !== opener) {
            menuOpener.setAttribute('aria-expanded', 'false');
        }
        menuOpener = opener;
        setMenuOpen(isOpen, false);
    }

    if (menuToggle && menu) {
        menuToggle.addEventListener('click', function () {
            openMenuFrom(menuToggle);
        });
    }

    if (menu) {
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
                !(menuOpener && menuOpener.contains(event.target))
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

    /* ---- Disclosure controls: the room switcher and the account menu ----
       Same contract for both: labelled trigger, aria-expanded kept honest,
       Escape and outside pointer dismiss, focus returned to the trigger. */
    function wireDisclosure(trigger, panel) {
        if (!trigger || !panel) return;

        function setOpen(open, restoreFocus) {
            panel.hidden = !open;
            trigger.setAttribute('aria-expanded', String(open));

            if (open) {
                var firstFocus = panel.querySelector('a[href], button');
                if (firstFocus) firstFocus.focus();
            } else if (restoreFocus) {
                trigger.focus();
            }
        }

        trigger.addEventListener('click', function () {
            setOpen(panel.hidden, false);
        });

        panel.addEventListener('click', function (event) {
            if (event.target.closest('a[href]')) setOpen(false, false);
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !panel.hidden) {
                setOpen(false, true);
            }
        });

        document.addEventListener('pointerdown', function (event) {
            if (
                !panel.hidden &&
                !panel.contains(event.target) &&
                !trigger.contains(event.target)
            ) {
                setOpen(false, false);
            }
        });
    }

    wireDisclosure(
        document.querySelector('[data-platform-roomswitcher-trigger]'),
        document.querySelector('[data-platform-roomswitcher-list]')
    );
    wireDisclosure(
        document.querySelector('[data-platform-account-trigger]'),
        document.querySelector('[data-platform-account-menu]')
    );

    /* ---- The one bottom bar ----
       A page that publishes [data-mobile-tabsource] keeps the released
       behaviour exactly: its section tabs are mirrored and nothing global
       is added. Only a page without section tabs gets the global four-slot
       structure, cloned from the server-rendered [data-global-tabsource]
       list. There is never a second fixed bar. */
    var bar = document.getElementById('mobile-tabbar');
    if (!bar) return;

    var source = document.querySelector('[data-mobile-tabsource]');
    var globalSource = document.querySelector('[data-global-tabsource]');
    var isGlobal = false;

    if (!source) {
        source = globalSource;
        isGlobal = true;
    }
    if (!source) return;

    var links = source.querySelectorAll('a[href]');
    if (!links.length) return;

    // A slot's mark and label are server-rendered. Cloning the <svg> node
    // keeps that true — nothing here builds markup from data.
    function fillSlot(item, sourceEl) {
        var mark = sourceEl.querySelector('svg');
        if (mark) {
            item.appendChild(mark.cloneNode(true));
            var label = document.createElement('span');
            label.className = 'mobile-tabbar__label';
            label.textContent = sourceEl.textContent.trim();
            item.appendChild(label);
        } else {
            // A page-owned section-tab source has no mark; keep the released
            // plain-text slot exactly as it was.
            item.textContent = sourceEl.textContent.trim();
        }
    }

    links.forEach(function (link) {
        var item = document.createElement('a');
        item.href = link.getAttribute('href');
        item.className = 'mobile-tabbar__item';
        if (link.hasAttribute('aria-current')) {
            item.setAttribute('aria-current', 'page');
        }
        // A slot may carry the room's full name for assistive technology
        // while showing the short label the bar has room for. The full name
        // always contains the visible text (WCAG 2.2 SC 2.5.3).
        if (link.hasAttribute('aria-label')) {
            item.setAttribute('aria-label', link.getAttribute('aria-label'));
        }
        fillSlot(item, link);
        bar.appendChild(item);
    });

    var moreSource = isGlobal ? source.querySelector('[data-global-more]') : null;
    if (moreSource && menu) {
        // Slot 4. It opens the same sheet the header Menu opens, so the
        // phone has one destination list rather than two.
        var more = document.createElement('button');
        more.type = 'button';
        more.className = 'mobile-tabbar__item mobile-tabbar__item--more';
        more.setAttribute('aria-expanded', 'false');
        more.setAttribute('aria-controls', menu.id || 'platform-mobile-menu');
        fillSlot(more, moreSource);
        more.addEventListener('click', function () {
            openMenuFrom(more);
        });
        bar.appendChild(more);
        document.body.classList.add('has-global-tabbar');

        // Self-correction. The global bar is a signed-in affordance and it
        // hides the header Menu, so it must not survive the session. After a
        // sign-out a Back navigation can restore a bfcached signed-in page:
        // auth-state.js hides the account controls on pageshow, but the bar
        // is already cloned. Watching the server-derived state attribute
        // covers that, a session expiry, and a sign-out in another tab.
        var controls = document.querySelector('[data-ps-auth-controls]');
        if (controls && window.MutationObserver) {
            new MutationObserver(function () {
                if (controls.getAttribute('data-ps-auth-state') === 'authenticated') return;
                bar.hidden = true;
                while (bar.firstChild) bar.removeChild(bar.firstChild);
                document.body.classList.remove('has-global-tabbar', 'has-mobile-tabbar');
                if (menu && !menu.hidden) setMenuOpen(false, false);
            }).observe(controls, { attributes: true, attributeFilter: ['data-ps-auth-state'] });
        }
    }

    bar.hidden = false;
    document.body.classList.add('has-mobile-tabbar');

    // Scroll-away belongs to a SECTION-tab bar, where the header Menu is
    // still on screen and nothing is lost by tucking the bar out of the way.
    // The global bar is different: it stands the header Menu down, so hiding
    // it on scroll left a signed-in phone with no destination navigation at
    // all until the reader scrolled back up. Global navigation stays put.
    if (isGlobal) return;

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

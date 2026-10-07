/* Approved Sage Mist composition. Move existing nodes; never clone public data or AI state. */
(() => {
    'use strict';
    document.addEventListener('DOMContentLoaded', () => {
        const page = document.querySelector('#living-resume-page[data-sage-mist]');
        if (!page) return;
        const rail = page.querySelector('[data-sage-rail]');
        const home = page.querySelector('[data-sage-ai-home]');
        const mount = page.querySelector('[data-sage-rail-ai]');
        const companion = page.querySelector('[data-ask-pete-companion]');
        const contact = page.querySelector('[data-sage-contact]');
        const contactOrigin = contact ? document.createComment('Contact details return here on narrow screens') : null;
        if (contact) contact.before(contactOrigin);
        const hero = page.querySelector('.overview-opening, .work-impact-hero, .r2-summary');
        const navigation = page.querySelector('.sage-rail-navigation');
        const selector = page.querySelector('[data-sage-section-select]');
        let pending = false;
        let heroAway = false;
        let homeHeight = 0;

        function clearance() {
            let bottom = 12;
            document.querySelectorAll('.global-header, .profile-tabs').forEach((header) => {
                const rect = header.getBoundingClientRect();
                if (rect.top <= 0 && rect.bottom > 0) bottom = Math.max(bottom, rect.bottom + 12);
            });
            return Math.min(bottom, window.innerHeight * .35);
        }

        function balance(container, itemSelector, minimum, maximum) {
            if (!container || container.hidden || container.clientWidth === 0) return;
            const items = [...container.querySelectorAll(itemSelector)];
            if (!items.length) return;
            const capacity = Math.min(maximum, items.length, Math.max(1, Math.floor((container.clientWidth + 8) / (minimum + 8))));
            let columns = capacity;
            for (let candidate = capacity; candidate >= Math.max(2, capacity - 2); candidate -= 1) {
                if (items.length % candidate === 0) { columns = candidate; break; }
            }
            const rows = Math.ceil(items.length / columns);
            const base = Math.floor(items.length / rows);
            const extra = items.length % rows;
            const sizes = Array.from({ length: rows }, (_, index) => base + (index < extra ? 1 : 0));
            const key = sizes.join(',');
            if (container.dataset.sageRows === key) return;
            const focused = document.activeElement;
            const fragment = document.createDocumentFragment();
            let offset = 0;
            sizes.forEach((size) => {
                const row = document.createElement('div');
                row.className = 'sage-balanced-row';
                items.slice(offset, offset + size).forEach((item) => row.appendChild(item));
                fragment.appendChild(row);
                offset += size;
            });
            container.replaceChildren(fragment);
            container.dataset.sageRows = key;
            if (focused instanceof HTMLElement && container.contains(focused)) focused.focus({ preventScroll: true });
        }

        function update() {
            pending = false;
            const wide = window.matchMedia('(min-width: 901px)').matches;
            const top = clearance();
            page.style.setProperty('--sage-top', `${top}px`);
            page.style.setProperty('--sage-rail-height', `${Math.max(200, window.innerHeight - top - 16)}px`);
            page.dataset.sageTight = String(window.innerHeight < 620);
            if (contact) {
                if (wide && contact.parentElement !== rail) rail.prepend(contact);
                else if (!wide && contactOrigin.parentElement !== contact.parentElement) contactOrigin.after(contact);
            }
            const nextHeroAway = Boolean(hero && hero.getBoundingClientRect().bottom <= top);
            if (contact && nextHeroAway !== heroAway) contact.open = !nextHeroAway;
            heroAway = nextHeroAway;
            page.dataset.sageHeroAway = String(heroAway);
            if (navigation) {
                if (wide && navigation.parentElement !== rail) rail.insertBefore(navigation, mount);
                else if (!wide && hero && navigation.parentElement !== hero.parentElement) hero.after(navigation);
            }
            if (companion && home && mount) {
                if (companion.parentElement === home) homeHeight = Math.ceil(home.getBoundingClientRect().height);
                const away = home.getBoundingClientRect().bottom <= top;
                page.dataset.sageAiAway = String(away);
                const placement = away ? (wide ? 'rail' : 'sheet') : 'inline';
                const parent = away ? (wide ? mount : page) : home;
                if (companion.parentElement !== parent || companion.dataset.sagePlacement !== placement) {
                    const focused = companion.contains(document.activeElement) ? document.activeElement : null;
                    home.style.minHeight = away ? `${homeHeight}px` : '';
                    parent.appendChild(companion);
                    companion.dataset.sagePlacement = placement;
                    page.dispatchEvent(new CustomEvent('resume:sage-placement', { detail: { placement, focused: Boolean(focused) } }));
                    if (focused && !companion.hidden) focused.focus({ preventScroll: true });
                }
            }
            balance(page.querySelector('[data-r2-skill-overview]'), '[data-r2-skill-toggle]', wide ? 150 : 116, 8);
            balance(page.querySelector('.r2-impact__panel'), '.r2-impact__item', 114, 4);
            balance(page.querySelector('.r2-credential-overview'), '.r2-credential-card', 220, 3);
        }
        function schedule() {
            if (pending) return;
            pending = true;
            window.requestAnimationFrame(update);
        }
        page.querySelectorAll('[data-sage-impact-flip]').forEach((button) => {
            button.addEventListener('click', () => {
                const expanded = button.getAttribute('aria-expanded') !== 'true';
                button.setAttribute('aria-expanded', String(expanded));
                button.querySelector('[data-sage-impact-front]').hidden = expanded;
                document.getElementById(button.getAttribute('aria-controls')).hidden = !expanded;
                button.classList.remove('is-flipping');
                void button.offsetWidth;
                button.classList.add('is-flipping');
            });
        });
        if (selector) {
            selector.addEventListener('change', () => {
                const link = [...page.querySelectorAll('[data-resume-nav]')].find((item) => item.hash === `#${selector.value}`);
                if (link) link.click();
                const target = document.getElementById(selector.value);
                if (target) { target.tabIndex = -1; target.focus({ preventScroll: true }); }
            });
            page.addEventListener('r2:section-change', (event) => {
                if (event.detail && [...selector.options].some((option) => option.value === event.detail.sectionId)) selector.value = event.detail.sectionId;
            });
        }
        document.addEventListener('pointerdown', (event) => {
            if (contact && heroAway && contact.parentElement === rail && !contact.contains(event.target)) contact.open = false;
        });
        document.addEventListener('keydown', (event) => {
            if (event.defaultPrevented) return;
            if (event.key === 'Escape' && contact && heroAway && contact.open) {
                contact.open = false;
                contact.querySelector('summary').focus({ preventScroll: true });
            }
        });
        window.addEventListener('scroll', schedule, { passive: true });
        window.addEventListener('resize', schedule);
        if (window.visualViewport) window.visualViewport.addEventListener('resize', schedule);
        const observer = new ResizeObserver(schedule);
        const content = page.querySelector('.r2-content');
        if (content) observer.observe(content);
        if (home) observer.observe(home);
        page.dataset.sageReady = '';
        update();
    });
})();

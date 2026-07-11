/* ==========================================================================
   MY STORY — four-act behaviors
   Entrance reveals, story-progress rail, chapter expansion, and the Act
   Four AI invitation. Everything degrades gracefully: without JS the page
   is fully readable (no hidden content besides chapter deep-dives, which
   open via the toggle; reveals only engage once body.sa-js is set).
   ========================================================================== */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        const root = document.querySelector('.story-acts');
        if (!root) return;

        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

        /* ----- Entrance reveals (opt-in via body class so no-JS shows all) */
        const revealTargets = Array.from(root.querySelectorAll('.sa-reveal'));
        if ('IntersectionObserver' in window && revealTargets.length) {
            document.body.classList.add('sa-js');
            const revealObserver = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-in');
                        revealObserver.unobserve(entry.target);
                    }
                });
            }, { rootMargin: '0px 0px -6% 0px' });
            revealTargets.forEach((el) => revealObserver.observe(el));

            // Keyboard access: focusing into an unrevealed card reveals it
            // immediately so focus is never sent to invisible content.
            root.addEventListener('focusin', (event) => {
                const card = event.target.closest('.sa-reveal');
                if (card && !card.classList.contains('is-in')) {
                    card.classList.add('is-in');
                    revealObserver.unobserve(card);
                }
            });
        }

        /* ----- Story rail scroll-spy */
        const railLinks = Array.from(root.querySelectorAll('[data-rail-link]'));
        const acts = Array.from(root.querySelectorAll('[data-story-act]'));
        if (railLinks.length && acts.length && 'IntersectionObserver' in window) {
            const setCurrent = (id) => {
                railLinks.forEach((link) => {
                    if (link.dataset.railLink === id) {
                        link.setAttribute('aria-current', 'true');
                    } else {
                        link.removeAttribute('aria-current');
                    }
                });
            };
            const actObserver = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) setCurrent(entry.target.id);
                });
            }, { rootMargin: '-35% 0px -55% 0px' });
            acts.forEach((act) => actObserver.observe(act));
        }

        /* ----- Chapter expansion: one open per act, Escape restores focus */
        acts.forEach((act) => {
            const toggles = Array.from(act.querySelectorAll('[data-sc-toggle]'));

            function setOpen(toggle, open) {
                const card = toggle.closest('.st-card');
                const panel = document.getElementById(toggle.getAttribute('aria-controls'));
                const label = toggle.querySelector('[data-sc-toggle-label]');
                toggle.setAttribute('aria-expanded', String(open));
                if (panel) panel.hidden = !open;
                if (card) card.classList.toggle('is-open', open);
                if (label) label.textContent = open ? 'Close the chapter' : 'Read the chapter';
            }

            toggles.forEach((toggle) => {
                toggle.addEventListener('click', () => {
                    const opening = toggle.getAttribute('aria-expanded') !== 'true';
                    toggles.forEach((other) => {
                        if (other !== toggle) setOpen(other, false);
                    });
                    setOpen(toggle, opening);
                    if (opening && !reducedMotion.matches) {
                        toggle.closest('.st-card').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                });
            });

            act.addEventListener('keydown', (event) => {
                if (event.key !== 'Escape') return;
                const open = toggles.find((toggle) => toggle.getAttribute('aria-expanded') === 'true');
                if (!open) return;
                setOpen(open, false);
                open.focus();
            });
        });

        /* ----- Chapter "Ask AI" buttons hand their context to the chat */
        root.querySelectorAll('[data-story-ask]').forEach((button) => {
            button.addEventListener('click', () => {
                if (typeof window.askPeteAI === 'function') {
                    window.askPeteAI(button.dataset.storyAsk);
                }
            });
        });

        /* ----- Act Four suggestion chips fill the inline form and submit */
        const aiCard = root.querySelector('.sc-ai');
        if (aiCard) {
            const form = aiCard.querySelector('[data-hero-ai-search]');
            const input = form ? form.querySelector('.hero-ai-search__input') : null;
            aiCard.querySelectorAll('[data-story-suggestion]').forEach((chip) => {
                chip.addEventListener('click', () => {
                    if (!form || !input) return;
                    input.value = chip.textContent.trim();
                    input.focus();
                    if (typeof form.requestSubmit === 'function') {
                        form.requestSubmit();
                    } else {
                        form.dispatchEvent(new Event('submit', { cancelable: true }));
                    }
                });
            });
        }
    });
}());

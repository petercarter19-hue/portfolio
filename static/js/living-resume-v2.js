document.addEventListener('DOMContentLoaded', () => {
    const page = document.getElementById('living-resume-page');
    if (!page) return;

    const isResume2 = page.classList.contains('resume-v2');
    const tabs = [...page.querySelectorAll('[data-ledger-event]')];
    const panels = [...page.querySelectorAll('[data-ledger-panel]')];
    const constellationNodes = [...page.querySelectorAll('.lr-constellation-node[data-event-id]')];
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const resumeNavLinks = [...page.querySelectorAll('[data-resume-nav]')];
    const resumeSections = [...page.querySelectorAll('[data-resume-section], [data-resume-section-target]')];
    const resumeDock = page.querySelector('.lr-resume-dock');
    const resumeRail = page.querySelector('.lr-ledger__rail');
    const ledgerBody = page.querySelector('.lr-resume-layout');
    const constellation = page.querySelector('.lr-constellation');
    const ledgerStatus = page.querySelector('[data-ledger-status]');

    function setCurrentResumeSection(sectionId) {
        resumeNavLinks.forEach((link) => {
            const isCurrent = link.hash === `#${sectionId}`;
            link.classList.toggle('is-current', isCurrent);
            if (isCurrent) {
                link.setAttribute('aria-current', 'location');
            } else {
                link.removeAttribute('aria-current');
            }
        });
    }

    function updatePersistentNavigation() {
        const readingLine = window.innerWidth <= 768 ? 170 : 150;
        let activeSectionId = 'resume-overview';

        resumeSections.forEach((section) => {
            if (section.getBoundingClientRect().top <= readingLine) {
                activeSectionId = section.dataset.resumeSectionTarget || section.id;
            }
        });

        setCurrentResumeSection(activeSectionId);

        if (!resumeDock || !resumeRail || !ledgerBody) return;

        const railBounds = resumeRail.getBoundingClientRect();
        const bodyBounds = ledgerBody.getBoundingClientRect();
        const readerHasReachedResume = bodyBounds.top <= readingLine;
        const railIsVisible = railBounds.bottom > readingLine && railBounds.top < window.innerHeight;
        const constellationHasReachedReader = Boolean(
            isResume2
            && constellation
            && constellation.getBoundingClientRect().top <= readingLine
        );
        const showDock = readerHasReachedResume && !railIsVisible && !constellationHasReachedReader;

        resumeDock.classList.toggle('is-visible', showDock);
        resumeDock.setAttribute('aria-hidden', String(!showDock));
        resumeDock.inert = !showDock;
        resumeDock.querySelectorAll('a').forEach((link) => {
            link.tabIndex = showDock ? 0 : -1;
        });
    }

    let navigationFrame = null;
    function requestNavigationUpdate() {
        if (navigationFrame) return;
        navigationFrame = window.requestAnimationFrame(() => {
            updatePersistentNavigation();
            navigationFrame = null;
        });
    }

    // The rail glides to the vertical center of the viewport while the
    // sections scroll past, then releases with the last section. Sticky
    // handles the motion; this just keeps the centered offset current.
    function updateRailCenter() {
        if (!resumeRail) return;
        const headerClearance = 76;
        const centered = (window.innerHeight - resumeRail.offsetHeight) / 2;
        resumeRail.style.setProperty('--lr-rail-top', `${Math.max(headerClearance, Math.round(centered))}px`);
    }

    window.addEventListener('resize', updateRailCenter);
    updateRailCenter();

    resumeNavLinks.forEach((link) => {
        link.addEventListener('click', (event) => {
            const target = page.querySelector(link.hash);
            if (!target) return;

            event.preventDefault();
            setCurrentResumeSection(target.id);
            target.scrollIntoView({
                behavior: reducedMotion.matches ? 'auto' : 'smooth',
                block: 'start',
            });
        });
    });

    window.addEventListener('scroll', requestNavigationUpdate, { passive: true });
    window.addEventListener('resize', requestNavigationUpdate);
    updatePersistentNavigation();

    function selectEvent(eventId, options = {}) {
        let selectedTab = null;

        tabs.forEach((tab) => {
            const isSelected = tab.dataset.ledgerEvent === eventId;
            tab.setAttribute('aria-selected', String(isSelected));
            tab.classList.toggle('is-selected', isSelected);
            tab.tabIndex = isSelected ? 0 : -1;
            if (isSelected) selectedTab = tab;
        });

        panels.forEach((panel) => {
            const isSelected = panel.dataset.ledgerPanel === eventId;
            panel.hidden = !isSelected;
            panel.classList.toggle('is-active', isSelected);
            if (isSelected && ledgerStatus) {
                const heading = panel.querySelector('h2');
                ledgerStatus.textContent = heading
                    ? `Showing ${heading.textContent.trim()} chapter.`
                    : 'Showing selected resume chapter.';
            }
        });

        constellationNodes.forEach((node) => {
            node.classList.toggle('is-current', node.dataset.eventId === eventId);
        });

        if (options.focusTab && selectedTab) {
            selectedTab.focus({ preventScroll: true });
        }

        return selectedTab;
    }

    function scrollToLedger(eventId) {
        const selectedTab = selectEvent(eventId, { focusTab: true });
        document.getElementById('ledger').scrollIntoView({
            behavior: reducedMotion.matches ? 'auto' : 'smooth',
            block: 'start',
        });
        return selectedTab;
    }

    tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => {
            selectEvent(tab.dataset.ledgerEvent);
        });

        tab.addEventListener('keydown', (event) => {
            const targetIndexes = {
                ArrowRight: (index + 1) % tabs.length,
                ArrowDown: (index + 1) % tabs.length,
                ArrowLeft: (index - 1 + tabs.length) % tabs.length,
                ArrowUp: (index - 1 + tabs.length) % tabs.length,
                Home: 0,
                End: tabs.length - 1,
            };

            if (!(event.key in targetIndexes)) return;

            event.preventDefault();
            const nextTab = tabs[targetIndexes[event.key]];
            selectEvent(nextTab.dataset.ledgerEvent, { focusTab: true });
        });
    });

    const initialTab = tabs.find((tab) => tab.getAttribute('aria-selected') === 'true');
    if (initialTab) selectEvent(initialTab.dataset.ledgerEvent);

    page.querySelectorAll('[data-constellation-target]').forEach((button) => {
        button.addEventListener('click', () => {
            scrollToLedger(button.dataset.constellationTarget);
        });
    });

    page.querySelectorAll('[data-chapter-jump]').forEach((button) => {
        button.addEventListener('click', () => {
            scrollToLedger(button.dataset.chapterJump);
        });
    });

    const revealTargets = [...page.querySelectorAll('[data-reveal]')];
    if (revealTargets.length && 'IntersectionObserver' in window) {
        page.classList.add('lr-js-reveal');
        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('is-revealed');
                revealObserver.unobserve(entry.target);
            });
        }, { rootMargin: '0px 0px -10% 0px' });
        revealTargets.forEach((target) => {
            target.addEventListener('focusin', () => target.classList.add('is-revealed'));
            revealObserver.observe(target);
        });
    }

    page.querySelectorAll('[data-metric-event]').forEach((button) => {
        button.addEventListener('click', () => {
            const eventId = button.dataset.metricEvent;
            const evidenceId = button.dataset.evidenceTarget;
            selectEvent(eventId);

            const selectedPanel = page.querySelector(`[data-ledger-panel="${eventId}"]`);
            const fullRecord = selectedPanel?.querySelector('.lr-full-record');
            if (fullRecord) fullRecord.open = true;

            const evidence = evidenceId ? document.getElementById(evidenceId) : null;
            const target = evidence || selectedPanel;
            if (!target) return;

            target.scrollIntoView({
                behavior: reducedMotion.matches ? 'auto' : 'smooth',
                block: 'center',
            });
            target.classList.remove('lr-highlight');
            window.requestAnimationFrame(() => target.classList.add('lr-highlight'));

            if (typeof target.focus === 'function') {
                target.setAttribute('tabindex', '-1');
                target.focus({ preventScroll: true });
            }
        });
    });

    const skillDetails = [...page.querySelectorAll('[data-skill-evidence]')];
    skillDetails.forEach((detail) => {
        detail.addEventListener('toggle', () => {
            if (!detail.open) return;
            skillDetails.forEach((other) => {
                if (other !== detail) other.open = false;
            });
        });
    });

    page.querySelectorAll('[data-ask-resume]').forEach((button) => {
        button.addEventListener('click', () => {
            const prompt = button.dataset.ask;
            if (prompt && window.askPeteAI) {
                window.askPeteAI(prompt);
            }
        });
    });

    const categoryTabs = [...page.querySelectorAll('[data-r2-category]')];
    const skillGroups = [...page.querySelectorAll('[data-r2-skill-group]')];
    const evidencePanels = [...page.querySelectorAll('[data-r2-evidence-panel]')];
    const skillButtons = [...page.querySelectorAll('[data-r2-skill]')];
    const skillStatus = page.querySelector('[data-r2-skill-status]');

    function selectResume2Skill(skillId) {
        skillButtons.forEach((button) => {
            button.setAttribute('aria-pressed', String(button.dataset.r2Skill === skillId));
        });

        evidencePanels.forEach((panel) => {
            const isSelected = panel.dataset.r2EvidencePanel === skillId;
            panel.hidden = !isSelected;
            if (isSelected && skillStatus) {
                const heading = panel.querySelector('h3');
                skillStatus.textContent = heading
                    ? `Showing evidence for ${heading.textContent.trim()}.`
                    : 'Showing selected skill evidence.';
            }
        });
    }

    function selectResume2Category(categoryId, options = {}) {
        let selectedTab = null;
        categoryTabs.forEach((tab) => {
            const isSelected = tab.dataset.r2Category === categoryId;
            tab.setAttribute('aria-selected', String(isSelected));
            tab.tabIndex = isSelected ? 0 : -1;
            if (isSelected) selectedTab = tab;
        });

        let activeGroup = null;
        skillGroups.forEach((group) => {
            const isSelected = group.dataset.r2SkillGroup === categoryId;
            group.hidden = !isSelected;
            if (isSelected) activeGroup = group;
        });

        const firstSkill = activeGroup?.querySelector('[data-r2-skill]');
        if (firstSkill) selectResume2Skill(firstSkill.dataset.r2Skill);
        if (options.focus && selectedTab) selectedTab.focus({ preventScroll: true });
    }

    categoryTabs.forEach((tab, index) => {
        tab.addEventListener('click', () => selectResume2Category(tab.dataset.r2Category));
        tab.addEventListener('keydown', (event) => {
            const targetIndexes = {
                ArrowRight: (index + 1) % categoryTabs.length,
                ArrowDown: (index + 1) % categoryTabs.length,
                ArrowLeft: (index - 1 + categoryTabs.length) % categoryTabs.length,
                ArrowUp: (index - 1 + categoryTabs.length) % categoryTabs.length,
                Home: 0,
                End: categoryTabs.length - 1,
            };
            if (!(event.key in targetIndexes)) return;
            event.preventDefault();
            const nextTab = categoryTabs[targetIndexes[event.key]];
            selectResume2Category(nextTab.dataset.r2Category, { focus: true });
        });
    });

    skillButtons.forEach((button) => {
        button.addEventListener('click', () => selectResume2Skill(button.dataset.r2Skill));
    });

    const shareButton = page.querySelector('[data-share-resume]');
    const shareStatus = page.querySelector('[data-share-status]');
    if (shareButton) {
        shareButton.addEventListener('click', async () => {
            const shareData = { title: document.title, url: window.location.href };
            try {
                if (navigator.share) {
                    await navigator.share(shareData);
                    if (shareStatus) shareStatus.textContent = 'Share options opened.';
                } else if (navigator.clipboard) {
                    await navigator.clipboard.writeText(shareData.url);
                    if (shareStatus) shareStatus.textContent = 'Resume link copied.';
                } else if (shareStatus) {
                    shareStatus.textContent = 'Copy the page URL to share this resume.';
                }
            } catch (error) {
                if (error?.name !== 'AbortError' && shareStatus) {
                    shareStatus.textContent = 'Sharing is unavailable. Copy the page URL instead.';
                }
            }
        });
    }

    const skillFlips = [...page.querySelectorAll('[data-skill-flip]')];

    function setFlipped(card, flipped) {
        card.classList.toggle('is-flipped', flipped);
        card.setAttribute('aria-expanded', String(flipped));
        const front = card.querySelector('.lr-skill-flip__front');
        const back = card.querySelector('.lr-skill-flip__back');
        if (front) front.setAttribute('aria-hidden', String(flipped));
        if (back) back.setAttribute('aria-hidden', String(!flipped));
    }

    function toggleFlip(card) {
        const flip = !card.classList.contains('is-flipped');
        skillFlips.forEach((other) => {
            if (other !== card) setFlipped(other, false);
        });
        setFlipped(card, flip);
    }

    skillFlips.forEach((card) => {
        card.addEventListener('click', () => toggleFlip(card));
        card.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            toggleFlip(card);
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        skillDetails.forEach((detail) => {
            detail.open = false;
        });
        skillFlips.forEach((card) => setFlipped(card, false));
    });

    document.addEventListener('click', (event) => {
        skillDetails.forEach((detail) => {
            if (detail.open && !detail.contains(event.target)) {
                detail.open = false;
            }
        });
        skillFlips.forEach((card) => {
            if (card.classList.contains('is-flipped') && !card.contains(event.target)) {
                setFlipped(card, false);
            }
        });
    });
});

/* ==========================================================================
   Resume 2 additions (2026-07-10): expandable Experience chapters, the
   inline Ask AI suggestion chips, and the full-screen constellation stage.
   Kept in a separate listener so the original module above stays intact.
   ========================================================================== */
document.addEventListener('DOMContentLoaded', () => {
    const page = document.getElementById('living-resume-page');
    if (!page || !page.classList.contains('resume-v2')) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    /* ----- Skills & Evidence: chip → overlay evidence popup -----
       Clicking a skill chip highlights it and opens a compact pointer bubble
       beside that chip. The popup is moved to the document layer and fixed to
       the viewport so later resume cards cannot paint over it. All content is
       data-driven from the JSON island rendered by the template. */
    const skillmap = page.querySelector('[data-skillmap]');
    if (skillmap) {
        const chips = Array.from(skillmap.querySelectorAll('[data-skill-chip]'));
        const pop = skillmap.querySelector('#r2-skillpop');
        const popContent = pop && pop.querySelector('.r2-skillpop__content');
        const tail = pop && pop.querySelector('.r2-skillpop__tail');
        const titleEl = pop && pop.querySelector('[data-skillpop-title]');
        const summaryEl = pop && pop.querySelector('[data-skillpop-summary]');
        const listEl = pop && pop.querySelector('[data-skillpop-list]');
        const ctaEl = pop && pop.querySelector('[data-skillpop-cta]');
        const closeEl = pop && pop.querySelector('[data-skillpop-close]');
        const dataScript = skillmap.querySelector('[data-skillmap-data]');

        let skillData = {};
        try {
            skillData = JSON.parse(dataScript.textContent);
        } catch (err) {
            skillData = {};
        }

        let activeChip = null;

        if (pop) document.body.appendChild(pop);

        function positionPop(chip) {
            if (!pop) return;
            if (popContent) popContent.style.maxHeight = '';
            const chipRect = chip.getBoundingClientRect();
            const viewportGap = 12;
            const pointerGap = 7;
            const belowTop = chipRect.bottom + pointerGap;
            const belowSpace = window.innerHeight - belowTop - viewportGap;
            const aboveSpace = chipRect.top - pointerGap - viewportGap;
            let popRect = pop.getBoundingClientRect();
            const placeAbove = popRect.height > belowSpace && aboveSpace > belowSpace;
            const availableSpace = Math.max(160, placeAbove ? aboveSpace : belowSpace);

            if (popContent && popRect.height > availableSpace) {
                popContent.style.maxHeight = `${Math.round(availableSpace)}px`;
                popRect = pop.getBoundingClientRect();
            }

            const top = placeAbove
                ? chipRect.top - popRect.height - pointerGap
                : belowTop;
            const left = Math.max(
                viewportGap,
                Math.min(chipRect.left, window.innerWidth - popRect.width - viewportGap),
            );

            pop.classList.toggle('is-above', placeAbove);
            pop.style.top = `${Math.max(viewportGap, Math.round(top))}px`;
            pop.style.left = `${Math.round(left)}px`;

            if (!tail) return;
            const centre = chipRect.left + chipRect.width / 2 - left;
            const edge = 26; // keep the tail clear of the popup's rounded corners
            tail.style.left = Math.max(edge, Math.min(popRect.width - edge, centre)) + 'px';
        }

        function openPop(chip) {
            const id = chip.getAttribute('data-skill-chip');
            const entry = skillData[id];
            if (!entry || !pop) return;

            titleEl.textContent = entry.name || '';
            summaryEl.textContent = entry.summary || '';
            summaryEl.hidden = !entry.summary;

            listEl.innerHTML = '';
            (entry.evidence || []).forEach((text) => {
                const li = document.createElement('li');
                li.textContent = text;
                listEl.appendChild(li);
            });

            if (ctaEl) ctaEl.dataset.ask = entry.ask || '';

            chips.forEach((other) => {
                other.setAttribute('aria-expanded', String(other === chip));
            });
            activeChip = chip;
            pop.hidden = false;
            // Wait for the content-sized popup to lay out before anchoring it
            // within a few pixels of the selected skill.
            window.requestAnimationFrame(() => {
                positionPop(chip);
            });
        }

        function closePop() {
            if (!pop) return;
            pop.hidden = true;
            chips.forEach((chip) => chip.setAttribute('aria-expanded', 'false'));
            activeChip = null;
        }

        chips.forEach((chip) => {
            chip.addEventListener('click', () => {
                if (activeChip === chip) {
                    closePop();
                } else {
                    openPop(chip);
                }
            });
        });

        if (closeEl) {
            closeEl.addEventListener('click', () => {
                const returnTo = activeChip;
                closePop();
                if (returnTo) returnTo.focus();
            });
        }

        if (ctaEl) {
            ctaEl.addEventListener('click', () => {
                const prompt = ctaEl.dataset.ask;
                if (prompt && window.askPeteAI) window.askPeteAI(prompt);
            });
        }

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && activeChip) {
                const returnTo = activeChip;
                closePop();
                returnTo.focus();
            }
        });

        document.addEventListener('click', (event) => {
            if (activeChip && !skillmap.contains(event.target) && !pop.contains(event.target)) closePop();
        });

        window.addEventListener('resize', () => {
            if (activeChip) positionPop(activeChip);
        });

        window.addEventListener('scroll', () => {
            if (activeChip) positionPop(activeChip);
        });
    }

    /* ----- Experience: one open chapter, the others step aside ----- */
    const expSection = page.querySelector('[data-r2-exp]');
    if (expSection) {
        const stage = expSection.querySelector('[data-r2-exp-stage]');
        const cards = Array.from(expSection.querySelectorAll('[data-r2-exp-card]'));
        const status = expSection.querySelector('[data-r2-exp-status]');

        function announce(text) {
            if (status) status.textContent = text;
        }

        function setCardState(card, state) {
            // state: 'open' | 'aside' | 'rest'
            const toggle = card.querySelector('[data-r2-exp-toggle]');
            const label = card.querySelector('[data-r2-exp-label]');
            const full = card.querySelector('.r2-exp-card__full');
            card.classList.toggle('is-open', state === 'open');
            card.classList.toggle('is-aside', state === 'aside');
            if (full) full.hidden = state !== 'open';
            if (toggle) toggle.setAttribute('aria-expanded', String(state === 'open'));
            if (label) label.textContent = state === 'open' ? 'Close chapter' : 'View chapter';
        }

        // Bring the just-opened chapter into a comfortable frame. Generic for
        // any number of cards and any expanded height (careers vary — some
        // profiles have more or fewer roles): a card that fits under the
        // sticky header is centred; one taller than the viewport is aligned to
        // its top so the start of the record is never clipped. The card's CSS
        // scroll-margin-top keeps that top clear of the sticky header. Runs
        // after the expand/stagger transition settles (flex-grow is 420ms) so
        // it measures the card's final laid-out height.
        function frameOpenCard(card) {
            window.setTimeout(() => {
                // The visitor may have closed or switched chapters within the
                // settle delay — don't yank the page to a no-longer-open card.
                if (!card.classList.contains('is-open')) return;
                const header = document.querySelector('.global-header');
                const headerH = header && getComputedStyle(header).position === 'sticky'
                    ? header.getBoundingClientRect().height
                    : 0;
                const fits = card.getBoundingClientRect().height <= window.innerHeight - headerH - 32;
                card.scrollIntoView({
                    behavior: reducedMotion.matches ? 'auto' : 'smooth',
                    block: fits ? 'center' : 'start',
                });
            }, 580);
        }

        function openChapter(card) {
            stage.classList.add('is-expanded');
            cards.forEach((other) => setCardState(other, other === card ? 'open' : 'aside'));
            announce('Showing the full ' + (card.dataset.r2ExpName || 'chapter') + ' record.');
            frameOpenCard(card);
        }

        function closeAll() {
            stage.classList.remove('is-expanded');
            cards.forEach((card) => setCardState(card, 'rest'));
            announce('All chapters restored.');
        }

        cards.forEach((card) => {
            const toggle = card.querySelector('[data-r2-exp-toggle]');
            if (toggle) {
                toggle.addEventListener('click', (event) => {
                    event.stopPropagation();
                    if (card.classList.contains('is-open')) {
                        closeAll();
                        toggle.focus();
                    } else {
                        openChapter(card);
                    }
                });
            }
            // A slimmed-aside card is one big target: clicking anywhere on
            // it swaps the open chapter (the toggle stays the accessible
            // control; this is a pointer convenience).
            card.addEventListener('click', (event) => {
                if (!card.classList.contains('is-aside')) return;
                if (event.target.closest('a, button')) return;
                openChapter(card);
            });
        });

        expSection.addEventListener('keydown', (event) => {
            if (event.key !== 'Escape') return;
            const open = cards.find((card) => card.classList.contains('is-open'));
            if (!open) return;
            closeAll();
            const toggle = open.querySelector('[data-r2-exp-toggle]');
            if (toggle) toggle.focus();
        });
    }

    /* ----- Ask AI suggestion chips fill the inline search and submit ----- */
    const aiCard = page.querySelector('.r2-ai-card');
    if (aiCard) {
        const form = aiCard.querySelector('[data-hero-ai-search]');
        const input = form ? form.querySelector('.hero-ai-search__input') : null;
        aiCard.querySelectorAll('[data-r2-ai-suggestion]').forEach((chip) => {
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

    /* ----- Sub-header Ask AI takes over once the identity card scrolls away -----
       The résumé already offers the full Ask AI panel inside the identity card,
       so the compact field in the sub-header would be redundant while that card
       is on screen. It stays hidden until the card leaves the viewport, then
       fades in — keeping the assistant one field away for the rest of the page. */
    const subheaderAsk = document.querySelector('[data-resume-subheader-ask]');
    if (subheaderAsk) {
        const setSubheaderAsk = (visible) => {
            subheaderAsk.classList.toggle('is-visible', visible);
            subheaderAsk.setAttribute('aria-hidden', String(!visible));
        };

        if (aiCard && 'IntersectionObserver' in window) {
            setSubheaderAsk(false);
            const cardWatcher = new IntersectionObserver((entries) => {
                // isIntersecting is true while any part of the card is visible.
                setSubheaderAsk(!entries[0].isIntersecting);
            });
            cardWatcher.observe(aiCard);
        } else {
            // No card or no observer support: keep the field available.
            setSubheaderAsk(true);
        }
    }

});

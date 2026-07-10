document.addEventListener('DOMContentLoaded', () => {
    const page = document.getElementById('living-resume-page');
    if (!page) return;

    const tabs = [...page.querySelectorAll('[data-ledger-event]')];
    const panels = [...page.querySelectorAll('[data-ledger-panel]')];
    const constellationNodes = [...page.querySelectorAll('.lr-constellation-node[data-event-id]')];
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const resumeNavLinks = [...page.querySelectorAll('[data-resume-nav]')];
    const resumeSections = [...page.querySelectorAll('[data-resume-section], [data-resume-section-target]')];
    const resumeDock = page.querySelector('.lr-resume-dock');
    const resumeRail = page.querySelector('.lr-ledger__rail');
    const ledgerBody = page.querySelector('.lr-resume-layout');

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
        const showDock = readerHasReachedResume && !railIsVisible;

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
        revealTargets.forEach((target) => revealObserver.observe(target));
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

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        skillDetails.forEach((detail) => {
            detail.open = false;
        });
    });

    document.addEventListener('click', (event) => {
        skillDetails.forEach((detail) => {
            if (detail.open && !detail.contains(event.target)) {
                detail.open = false;
            }
        });
    });
});

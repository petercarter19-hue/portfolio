document.addEventListener('DOMContentLoaded', () => {
    const page = document.getElementById('living-resume-page');
    if (!page || !page.classList.contains('resume-v3')) return;

    const stage = page.querySelector('[data-r3-carousel-stage]');
    const sticky = stage?.querySelector('.r3-experience__sticky');
    const viewport = stage?.querySelector('[data-r3-carousel-viewport]');
    const track = stage?.querySelector('[data-r3-carousel-track]');
    const cards = [...(stage?.querySelectorAll('[data-r3-carousel-card]') || [])];
    const pages = [...(stage?.querySelectorAll('[data-r3-carousel-page]') || [])];
    const previous = stage?.querySelector('[data-r3-carousel-previous]');
    const next = stage?.querySelector('[data-r3-carousel-next]');
    const status = stage?.querySelector('[data-r3-carousel-status]');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    if (!stage || !sticky || !viewport || !track || !cards.length) return;

    let activeIndex = 0;
    let scrollStart = 0;
    let scrollTravel = 0;
    let trackEnd = 0;
    let animationFrame = null;

    function useStaticFlow() {
        return reducedMotion.matches || window.innerWidth <= 768 || cards.length < 2;
    }

    function setCardState(nextIndex, announce = false) {
        activeIndex = Math.max(0, Math.min(cards.length - 1, nextIndex));

        cards.forEach((card, index) => {
            const isActive = index === activeIndex;
            card.classList.toggle('is-active', isActive);
            card.classList.toggle('is-before', index < activeIndex);
            card.classList.toggle('is-after', index > activeIndex);
            card.toggleAttribute('inert', !isActive && !useStaticFlow());
            if (useStaticFlow()) {
                card.removeAttribute('aria-hidden');
            } else {
                card.setAttribute('aria-hidden', String(!isActive));
            }
        });

        pages.forEach((button, index) => {
            const isActive = index === activeIndex;
            button.setAttribute('aria-selected', String(isActive));
            button.tabIndex = isActive ? 0 : -1;
        });

        if (previous) previous.disabled = activeIndex === 0;
        if (next) next.disabled = activeIndex === cards.length - 1;

        if (announce && status) {
            const chapterName = cards[activeIndex]
                .getAttribute('aria-label')
                ?.split(':')
                .slice(1)
                .join(':')
                .trim() || `chapter ${activeIndex + 1}`;
            status.textContent = `Showing chapter ${activeIndex + 1} of ${cards.length}: ${chapterName}.`;
        }
    }

    function updateCardDepth(offset) {
        const viewportCenter = viewport.clientWidth / 2;

        cards.forEach((card) => {
            const cardCenter = card.offsetLeft + (card.offsetWidth / 2) - offset;
            const distance = Math.min(1, Math.abs(cardCenter - viewportCenter) / viewport.clientWidth);
            const scale = 1 - (distance * 0.14);
            const opacity = 1 - (distance * 0.25);

            card.style.setProperty('--r3-card-scale', scale.toFixed(3));
            card.style.setProperty('--r3-card-opacity', opacity.toFixed(3));
        });
    }

    function updateFromScroll() {
        animationFrame = null;
        if (useStaticFlow()) return;

        const progress = scrollTravel > 0
            ? Math.max(0, Math.min(1, (window.scrollY - scrollStart) / scrollTravel))
            : 0;
        const offset = trackEnd * progress;
        const nearestIndex = Math.round(progress * (cards.length - 1));

        track.style.transform = `translate3d(${-offset}px, 0, 0)`;
        updateCardDepth(offset);
        if (nearestIndex !== activeIndex) setCardState(nearestIndex, true);
    }

    function requestScrollUpdate() {
        if (animationFrame || useStaticFlow()) return;
        animationFrame = window.requestAnimationFrame(updateFromScroll);
    }

    function layoutStage() {
        const staticFlow = useStaticFlow();
        stage.classList.toggle('is-static', staticFlow);
        stage.classList.toggle('is-enhanced', !staticFlow);
        track.style.transform = '';
        track.style.paddingInline = '';

        if (staticFlow) {
            stage.style.minHeight = '';
            cards.forEach((card) => {
                card.style.removeProperty('--r3-card-scale');
                card.style.removeProperty('--r3-card-opacity');
            });
            setCardState(activeIndex);
            return;
        }

        const cardWidth = cards[0].offsetWidth;
        const sidePadding = Math.max(0, (viewport.clientWidth - cardWidth) / 2);
        track.style.paddingInline = `${sidePadding}px`;

        const firstCenter = cards[0].offsetLeft + (cards[0].offsetWidth / 2);
        const lastCard = cards[cards.length - 1];
        const lastCenter = lastCard.offsetLeft + (lastCard.offsetWidth / 2);
        trackEnd = Math.max(0, lastCenter - firstCenter);

        const stageTop = stage.getBoundingClientRect().top + window.scrollY;
        const scrollLength = Math.max(
            window.innerHeight * 0.72,
            (cards.length - 1) * window.innerHeight * 0.72,
        );
        stage.style.minHeight = `${sticky.offsetHeight + scrollLength}px`;
        scrollStart = stageTop;
        scrollTravel = Math.max(1, stage.offsetHeight - sticky.offsetHeight);
        updateFromScroll();
    }

    function scrollToCard(index) {
        const targetIndex = Math.max(0, Math.min(cards.length - 1, index));

        if (useStaticFlow()) {
            cards[targetIndex].scrollIntoView({
                behavior: reducedMotion.matches ? 'auto' : 'smooth',
                block: 'nearest',
                inline: 'center',
            });
            setCardState(targetIndex, true);
            return;
        }

        const progress = cards.length === 1 ? 0 : targetIndex / (cards.length - 1);
        window.scrollTo({
            top: scrollStart + (scrollTravel * progress),
            behavior: reducedMotion.matches ? 'auto' : 'smooth',
        });
        setCardState(targetIndex, true);
    }

    previous?.addEventListener('click', () => scrollToCard(activeIndex - 1));
    next?.addEventListener('click', () => scrollToCard(activeIndex + 1));

    pages.forEach((button, index) => {
        button.addEventListener('click', () => scrollToCard(index));
        button.addEventListener('keydown', (event) => {
            const nextIndexes = {
                ArrowRight: (index + 1) % pages.length,
                ArrowDown: (index + 1) % pages.length,
                ArrowLeft: (index - 1 + pages.length) % pages.length,
                ArrowUp: (index - 1 + pages.length) % pages.length,
                Home: 0,
                End: pages.length - 1,
            };
            if (!(event.key in nextIndexes)) return;
            event.preventDefault();
            const targetIndex = nextIndexes[event.key];
            pages[targetIndex].focus();
            scrollToCard(targetIndex);
        });
    });

    stage.addEventListener('keydown', (event) => {
        if (event.target !== stage) return;
        if (event.key === 'ArrowLeft') {
            event.preventDefault();
            scrollToCard(activeIndex - 1);
        }
        if (event.key === 'ArrowRight') {
            event.preventDefault();
            scrollToCard(activeIndex + 1);
        }
    });

    window.addEventListener('scroll', requestScrollUpdate, { passive: true });
    window.addEventListener('resize', layoutStage);
    reducedMotion.addEventListener?.('change', layoutStage);

    setCardState(0);
    layoutStage();
});

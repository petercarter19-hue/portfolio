// Interactive resume page behavior (redesign 5).
// What this file handles now:
//   1. Skill cards: clicking a skill opens its resume-evidence popover.
//   2. Career role cards: clicking a role shows that role's detail panel.
//   3. Impact metric cards: clicking a metric jumps to the connected role evidence.
//   4. "Ask the AI About This Role" buttons: send a prompt to the chat assistant.
//   5. Suggested-question chips in the hero AI panel: submit through the AI search box.
// The old recruiter-track filtering, case-study panels, and print/copy buttons
// were removed along with their sections in resume.html.

document.addEventListener('DOMContentLoaded', function () {
    const page = document.getElementById('resume-page');
    if (!page) return;

    page.classList.add('resume-js');

    const skillCards = Array.from(document.querySelectorAll('[data-skill-card]'));
    const metricCards = Array.from(document.querySelectorAll('[data-metric-id]'));
    const roleCards = Array.from(document.querySelectorAll('[data-role-select]'));
    const rolePanels = Array.from(document.querySelectorAll('[data-role-panel]'));

    // ---------- Skill evidence popovers ----------

    function closeSkillPopover(card) {
        const button = card.querySelector('[data-skill-popover-trigger]');
        const popover = card.querySelector('[data-skill-popover]');

        card.classList.remove('is-popover-open', 'is-popover-right');

        if (button) {
            button.setAttribute('aria-expanded', 'false');
        }

        if (popover) {
            popover.hidden = true;
        }
    }

    function closeOtherSkillPopovers(currentCard) {
        skillCards.forEach(function (card) {
            if (card !== currentCard) closeSkillPopover(card);
        });
    }

    function openSkillPopover(card) {
        const button = card.querySelector('[data-skill-popover-trigger]');
        const popover = card.querySelector('[data-skill-popover]');
        if (!button || !popover) return;

        closeOtherSkillPopovers(card);

        popover.hidden = false;
        card.classList.add('is-popover-open');
        button.setAttribute('aria-expanded', 'true');

        // If the popover would run off the right edge of the screen,
        // flip it so it hangs from the card's right side instead.
        const popoverRect = popover.getBoundingClientRect();
        card.classList.toggle('is-popover-right', popoverRect.right > window.innerWidth - 16);

        if (card.classList.contains('is-popover-right')) {
            const adjustedRect = popover.getBoundingClientRect();
            if (adjustedRect.left < 16) {
                card.classList.remove('is-popover-right');
            }
        }
    }

    skillCards.forEach(function (card) {
        const button = card.querySelector('[data-skill-popover-trigger]');
        if (!button) return;

        button.addEventListener('click', function (event) {
            event.stopPropagation();
            if (card.classList.contains('is-popover-open')) {
                closeSkillPopover(card);
                return;
            }

            openSkillPopover(card);
        });

        button.addEventListener('mouseleave', function () {
            closeSkillPopover(card);
        });

        button.addEventListener('blur', function () {
            window.setTimeout(function () {
                if (!card.matches(':hover') && !card.contains(document.activeElement)) {
                    closeSkillPopover(card);
                }
            }, 80);
        });
    });

    // ---------- Career role selection ----------

    function scrollAndHighlight(element, shouldFocus) {
        if (!element) return;

        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        element.classList.remove('resume-highlight');
        window.setTimeout(function () {
            element.classList.add('resume-highlight');
        }, 20);

        if (shouldFocus && typeof element.focus === 'function') {
            window.setTimeout(function () {
                element.focus({ preventScroll: true });
            }, 250);
        }
    }

    function selectRole(roleId, shouldScroll) {
        const selectedCard = roleCards.find(function (card) {
            return card.dataset.roleSelect === roleId;
        });
        const selectedPanel = rolePanels.find(function (panel) {
            return panel.dataset.rolePanel === roleId;
        });

        if (!selectedCard || !selectedPanel) return;

        roleCards.forEach(function (card) {
            const isSelected = card === selectedCard;
            card.classList.toggle('is-selected', isSelected);
            card.setAttribute('aria-pressed', String(isSelected));
        });

        rolePanels.forEach(function (panel) {
            panel.classList.toggle('is-active', panel === selectedPanel);
        });

        if (shouldScroll) {
            scrollAndHighlight(selectedPanel, true);
        }
    }

    roleCards.forEach(function (card) {
        card.addEventListener('click', function () {
            selectRole(card.dataset.roleSelect, true);
        });
    });

    // ---------- Impact metric cards ----------
    // Each metric card knows which role and which accomplishment bullet
    // back it up, so clicking scrolls straight to that evidence.

    metricCards.forEach(function (card) {
        card.addEventListener('click', function () {
            const roleId = card.dataset.roleTarget;
            const evidenceId = card.dataset.evidenceTarget;

            if (roleId) {
                selectRole(roleId, false);
            }

            if (evidenceId && document.getElementById(evidenceId)) {
                scrollAndHighlight(document.getElementById(evidenceId), true);
            }
        });
    });

    // ---------- Chat assistant hooks ----------

    function runAssistantPrompt(prompt) {
        if (!prompt) return;

        // askPeteAI is defined in chatbot.js and opens the floating chat panel.
        if (window.askPeteAI) {
            window.askPeteAI(prompt);
            return;
        }

        const panel = document.getElementById('chat-panel');
        const input = document.getElementById('chat-input');

        if (panel && input) {
            panel.classList.add('open');
            input.value = prompt;
            input.focus();
        }
    }

    // Suggested-question chips inside the hero AI panel: put the question in
    // the shared AI search box and submit the form. chatbot.js listens for
    // that submit event and renders the answer inside the panel.
    const aiPanelForm = document.querySelector('.resume-ai-panel [data-hero-ai-search]');
    const aiPanelInput = aiPanelForm ? aiPanelForm.querySelector('.hero-ai-search__input') : null;

    document.querySelectorAll('[data-ai-suggestion]').forEach(function (chip) {
        chip.addEventListener('click', function () {
            if (!aiPanelForm || !aiPanelInput) return;

            aiPanelInput.value = chip.textContent.trim();
            aiPanelForm.requestSubmit();
        });
    });

    document.addEventListener('click', function (event) {
        // Clicking anywhere outside a skill card closes any open popover.
        if (!event.target.closest('[data-skill-card]')) {
            skillCards.forEach(closeSkillPopover);
        }

        const askButton = event.target.closest('[data-ask-resume]');
        if (askButton) {
            event.stopPropagation();
            runAssistantPrompt(askButton.dataset.ask || askButton.textContent.trim());
        }
    });

    document.addEventListener('pointermove', function (event) {
        skillCards.forEach(function (card) {
            if (!card.classList.contains('is-popover-open')) return;

            const button = card.querySelector('[data-skill-popover-trigger]');
            if (button && !button.contains(event.target)) {
                closeSkillPopover(card);
            }
        });
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            skillCards.forEach(closeSkillPopover);
        }
    });
});

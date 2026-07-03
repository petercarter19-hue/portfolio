// Interactive resume page behavior.
// Keeps the resume evidence visible while recruiter filters prioritize the most relevant items.

document.addEventListener('DOMContentLoaded', function () {
    const page = document.getElementById('resume-page');
    if (!page) return;

    page.classList.add('resume-js');

    const trackButtons = Array.from(document.querySelectorAll('[data-track-filter]'));
    const metricCards = Array.from(document.querySelectorAll('[data-metric-id]'));
    const skillCategoryButtons = Array.from(document.querySelectorAll('[data-skill-category]'));
    const skillCards = Array.from(document.querySelectorAll('[data-skill-card]'));
    const roleCards = Array.from(document.querySelectorAll('[data-role-select]'));
    const rolePanels = Array.from(document.querySelectorAll('[data-role-panel]'));
    const caseCards = Array.from(document.querySelectorAll('[data-case-card]'));
    const casePanels = Array.from(document.querySelectorAll('[data-case-panel]'));
    const promptGrid = document.getElementById('resume-prompt-grid');
    const matchSummary = document.getElementById('resume-match-summary');
    const printButton = document.querySelector('[data-print-resume]');
    const copyLinkedInButton = document.querySelector('[data-copy-linkedin]');

    const tracks = normalizeTracks(readJson('resume-track-data', []));
    const tracksById = tracks.reduce(function (map, track) {
        map[track.id] = track;
        return map;
    }, {});
    const defaultQuestions = readJson('resume-default-questions', []);

    const originalSkillOrder = new Map();
    const originalRoleOrder = new Map();
    const originalCaseOrder = new Map();

    skillCards.forEach(function (card, index) {
        originalSkillOrder.set(card, index);
    });
    roleCards.forEach(function (card, index) {
        originalRoleOrder.set(card, index);
    });
    caseCards.forEach(function (card, index) {
        originalCaseOrder.set(card, index);
    });

    let activeTrackId = 'all';
    let activeSkillCategory = 'all';

    function readJson(elementId, fallback) {
        const element = document.getElementById(elementId);
        if (!element) return fallback;

        try {
            return JSON.parse(element.textContent);
        } catch (error) {
            return fallback;
        }
    }

    function normalizeTracks(value) {
        if (Array.isArray(value)) return value;
        if (value && typeof value === 'object') return Object.values(value);
        return [];
    }

    function listFromData(element, key) {
        return (element.dataset[key] || '').split(/\s+/).filter(Boolean);
    }

    function setPressed(buttons, activeButton) {
        buttons.forEach(function (button) {
            const isActive = button === activeButton;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
    }

    function idsFromTrack(track, key) {
        return new Set((track && Array.isArray(track[key])) ? track[key] : []);
    }

    function orderedIndex(id, ids) {
        const index = ids.indexOf(id);
        return index === -1 ? 999 : index;
    }

    function applySkillCategory(categoryId) {
        activeSkillCategory = categoryId || 'all';

        skillCategoryButtons.forEach(function (button) {
            const isActive = button.dataset.skillCategory === activeSkillCategory;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });

        skillCards.forEach(function (card) {
            let shouldShow = true;

            if (activeSkillCategory === 'featured') {
                shouldShow = card.dataset.featured === 'true';
            } else if (activeSkillCategory !== 'all') {
                shouldShow = card.dataset.categoryId === activeSkillCategory;
            }

            card.classList.toggle('is-hidden-by-category', !shouldShow);
        });
    }

    function clearTrackPriorities(skillCategory) {
        activeTrackId = 'all';

        const showAllButton = trackButtons.find(function (button) {
            return button.dataset.trackFilter === 'all';
        });
        if (showAllButton) setPressed(trackButtons, showAllButton);

        metricCards.forEach(function (card) {
            card.classList.remove('is-relevant');
            card.style.order = '';
        });
        skillCards.forEach(function (card) {
            card.classList.remove('is-relevant');
            card.style.order = originalSkillOrder.get(card);
        });
        roleCards.forEach(function (card) {
            card.classList.remove('is-relevant');
            card.style.order = originalRoleOrder.get(card);
        });
        caseCards.forEach(function (card) {
            card.classList.remove('is-relevant');
            card.style.order = originalCaseOrder.get(card);
        });

        applySkillCategory(skillCategory || 'all');
        updatePromptGrid(defaultQuestions);
        updateSummary();
    }

    function applyTrack(trackId) {
        if (trackId === 'clear') {
            clearTrackPriorities('all');
            return;
        }

        if (trackId === 'all') {
            clearTrackPriorities('all');
            return;
        }

        const track = tracksById[trackId];
        if (!track) {
            clearTrackPriorities('all');
            return;
        }

        activeTrackId = track.id;
        const metricIds = idsFromTrack(track, 'featured_metric_ids');
        const skillIds = idsFromTrack(track, 'matching_skill_ids');
        const roleIds = idsFromTrack(track, 'featured_role_ids');
        const caseIds = idsFromTrack(track, 'featured_case_study_ids');
        const skillOrder = track.matching_skill_ids || [];
        const roleOrder = track.featured_role_ids || [];
        const caseOrder = track.featured_case_study_ids || [];

        const activeButton = trackButtons.find(function (button) {
            return button.dataset.trackFilter === track.id;
        });
        if (activeButton) setPressed(trackButtons, activeButton);

        metricCards.forEach(function (card, index) {
            const isRelevant = metricIds.has(card.dataset.metricId) || listFromData(card, 'trackIds').includes(track.id);
            card.classList.toggle('is-relevant', isRelevant);
            card.style.order = isRelevant ? orderedIndex(card.dataset.metricId, track.featured_metric_ids || []) : 100 + index;
        });

        skillCards.forEach(function (card) {
            const skillId = card.dataset.skillId;
            const isRelevant = skillIds.has(skillId) || listFromData(card, 'trackIds').includes(track.id);
            card.classList.toggle('is-relevant', isRelevant);
            card.style.order = isRelevant ? orderedIndex(skillId, skillOrder) : 100 + originalSkillOrder.get(card);
        });

        roleCards.forEach(function (card) {
            const roleId = card.dataset.roleSelect;
            const isRelevant = roleIds.has(roleId);
            card.classList.toggle('is-relevant', isRelevant);
            card.style.order = isRelevant ? orderedIndex(roleId, roleOrder) : 100 + originalRoleOrder.get(card);
        });

        caseCards.forEach(function (card) {
            const caseId = card.dataset.caseCard;
            const isRelevant = caseIds.has(caseId) || listFromData(card, 'trackIds').includes(track.id);
            card.classList.toggle('is-relevant', isRelevant);
            card.style.order = isRelevant ? orderedIndex(caseId, caseOrder) : 100 + originalCaseOrder.get(card);
        });

        applySkillCategory('all');
        if (track.featured_role_ids && track.featured_role_ids.length) {
            selectRole(track.featured_role_ids[0], false);
        }
        updatePromptGrid(track.suggested_ai_questions || defaultQuestions);
        updateSummary(track);
    }

    function updateSummary(track) {
        if (!matchSummary) return;

        if (!track) {
            matchSummary.textContent = 'Showing all approved public resume evidence.';
            return;
        }

        const relevantMetrics = metricCards.filter(function (card) {
            return card.classList.contains('is-relevant');
        }).length;
        const relevantSkills = skillCards.filter(function (card) {
            return card.classList.contains('is-relevant');
        }).length;
        const relevantRoles = roleCards.filter(function (card) {
            return card.classList.contains('is-relevant');
        }).length;

        matchSummary.textContent = track.label + ' selected. ' +
            relevantSkills + ' supporting skills, ' +
            relevantMetrics + ' quantified outcomes, and ' +
            relevantRoles + ' strongly aligned roles are prioritized below.';
    }

    function updatePromptGrid(questions) {
        if (!promptGrid) return;

        const prompts = Array.isArray(questions) && questions.length ? questions : defaultQuestions;
        promptGrid.innerHTML = '';

        prompts.forEach(function (prompt) {
            const button = document.createElement('button');
            button.className = 'resume-prompt-btn';
            button.type = 'button';
            button.dataset.askResume = '';
            button.dataset.ask = prompt;
            button.textContent = prompt;
            promptGrid.appendChild(button);
        });
    }

    function closeOtherSkillCards(currentCard) {
        skillCards.forEach(function (card) {
            if (card !== currentCard) setSkillFlipped(card, false);
        });
    }

    function setSkillFlipped(card, isFlipped) {
        const button = card.querySelector('.resume-skill-flip');
        const nameElement = card.querySelector('.resume-skill-face--front strong');
        const skillName = nameElement ? nameElement.textContent.trim() : 'Skill card';

        card.classList.toggle('is-flipped', isFlipped);
        if (button) {
            button.setAttribute('aria-pressed', String(isFlipped));
            button.setAttribute(
                'aria-label',
                isFlipped ?
                    skillName + ' evidence shown. Activate to return to the summary.' :
                    skillName + '. Activate to view supporting evidence.'
            );
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

    function selectCase(caseId, shouldScroll) {
        const selectedCard = caseCards.find(function (card) {
            return card.dataset.caseCard === caseId;
        });
        const selectedPanel = casePanels.find(function (panel) {
            return panel.dataset.casePanel === caseId;
        });

        if (!selectedCard || !selectedPanel) return;

        caseCards.forEach(function (card) {
            const isSelected = card === selectedCard;
            card.classList.toggle('is-selected', isSelected);
            card.setAttribute('aria-expanded', String(isSelected));
        });

        casePanels.forEach(function (panel) {
            panel.classList.toggle('is-active', panel === selectedPanel);
        });

        if (shouldScroll) {
            scrollAndHighlight(selectedPanel, true);
        }
    }

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

    function runAssistantPrompt(prompt) {
        if (!prompt) return;

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

    trackButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            applyTrack(button.dataset.trackFilter);
        });
    });

    skillCategoryButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            applySkillCategory(button.dataset.skillCategory);
        });
    });

    skillCards.forEach(function (card) {
        const button = card.querySelector('.resume-skill-flip');
        if (!button) return;

        button.addEventListener('click', function () {
            const shouldFlip = !card.classList.contains('is-flipped');
            closeOtherSkillCards(card);
            setSkillFlipped(card, shouldFlip);
        });
    });

    roleCards.forEach(function (card) {
        card.addEventListener('click', function () {
            selectRole(card.dataset.roleSelect, true);
        });
    });

    metricCards.forEach(function (card) {
        card.addEventListener('click', function () {
            const roleId = card.dataset.roleTarget;
            const evidenceId = card.dataset.evidenceTarget;
            const caseId = card.dataset.caseTarget;
            const educationId = card.dataset.educationTarget;

            if (educationId) {
                scrollAndHighlight(document.getElementById(educationId), true);
                return;
            }

            if (roleId) {
                selectRole(roleId, false);
            }

            if (evidenceId && document.getElementById(evidenceId)) {
                scrollAndHighlight(document.getElementById(evidenceId), true);
                return;
            }

            if (caseId) {
                selectCase(caseId, true);
            }
        });
    });

    caseCards.forEach(function (card) {
        card.addEventListener('click', function () {
            selectCase(card.dataset.caseCard, true);
        });
    });

    document.addEventListener('click', function (event) {
        const askButton = event.target.closest('[data-ask-resume]');
        if (askButton) {
            event.stopPropagation();
            runAssistantPrompt(askButton.dataset.ask || askButton.textContent.trim());
            return;
        }

        const askFitButton = event.target.closest('[data-ask-fit]');
        if (askFitButton) {
            const track = tracksById[activeTrackId];
            const label = track ? track.label : 'the selected role';
            runAssistantPrompt(
                'What roles and evidence make Pete a fit for ' + label +
                '? Use only approved public resume information and state any public-information limits.'
            );
            return;
        }

        const scrollButton = event.target.closest('[data-scroll-target]');
        if (scrollButton) {
            scrollAndHighlight(document.getElementById(scrollButton.dataset.scrollTarget), true);
        }
    });

    if (printButton) {
        printButton.addEventListener('click', function () {
            window.print();
        });
    }

    if (copyLinkedInButton) {
        copyLinkedInButton.addEventListener('click', function () {
            const url = copyLinkedInButton.dataset.linkedin;
            const originalText = copyLinkedInButton.textContent;

            if (!navigator.clipboard || !url) return;

            navigator.clipboard.writeText(url).then(function () {
                copyLinkedInButton.textContent = 'LinkedIn URL Copied';
                window.setTimeout(function () {
                    copyLinkedInButton.textContent = originalText;
                }, 1800);
            });
        });
    }

    applySkillCategory(activeSkillCategory);
    updatePromptGrid(defaultQuestions);
});

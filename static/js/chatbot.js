// =========================================================
// CHATBOT WIDGET - chatbot.js
//
// This file controls everything the chat widget does:
// opening, closing, sending messages, and displaying replies.
//
// MVP 1: The widget sends visitor questions to Flask's
// /api/chat route. Flask keeps the API key private, calls
// Claude on the server, and returns the answer to the browser.
// =========================================================


// Wait until the page is ready before running any code. If this file is
// loaded after the page is already ready, run the setup immediately.
function initializeChatbot() {


    // -------------------------------------------------------
    // GRAB THE HTML ELEMENTS WE NEED
    // We store references here so we don't have to search
    // the page for them every single time we use them.
    // -------------------------------------------------------

    const openButtons = document.querySelectorAll('[data-chat-open]'); // Header launchers
    const toggle      = document.getElementById('chat-toggle');      // Floating launcher
    const panel       = document.getElementById('chat-panel');       // The slide-in chat panel
    const closeBtn    = document.getElementById('chat-close');       // The X button inside the header
    const messages    = document.getElementById('chat-messages');    // Scrollable message area
    const input       = document.getElementById('chat-input');       // The text input field
    const sendBtn     = document.getElementById('chat-send');        // The Send button
    const suggestions = document.querySelectorAll('.suggestion-btn'); // All 4 suggestion chips

    if (!panel || !closeBtn || !messages || !input || !sendBtn) return;

    let lastChatOpener = null;

    // Wraps a plain-English message in a real JavaScript Error, tagged with
    // isFriendlyChatError so the .catch() blocks below can tell "this is a
    // message safe to show the visitor" apart from an unexpected crash.
    function friendlyError(message) {
        const error = new Error(message);
        error.isFriendlyChatError = true;
        return error;
    }

    // Sends the visitor's question to Flask's /api/chat route (see app.py)
    // and hands back a promise that resolves with { response: "..." } on
    // success. Turns HTTP error statuses into friendlyError messages so
    // callers always get a sentence they can display, not a raw status code.
    function requestChatReply(text) {
        return fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        })
        .then(function(response) {
            return response.json()
                .catch(function () {
                    return {};
                })
                .then(function (data) {
                    if (!response.ok) {
                        if (response.status === 400 && data.error) {
                            throw friendlyError(data.error);
                        }

                        if (response.status === 429) {
                            throw friendlyError('Too many questions in a short time. Please wait a moment and try again.');
                        }

                        throw friendlyError('Something went wrong. Please try again.');
                    }

                    return data;
                });
        });
    }

    // -------------------------------------------------------
    // OPEN AND CLOSE THE PANEL
    // -------------------------------------------------------

    function openChat(opener, shouldFocus) {
        if (opener) {
            lastChatOpener = opener;
        }

        panel.classList.add('open');
        panel.setAttribute('aria-hidden', 'false');

        if (shouldFocus !== false) {
            input.focus();
        }
    }

    function closeChat(shouldReturnFocus) {
        panel.classList.remove('open');
        panel.setAttribute('aria-hidden', 'true');

        // Returning focus helps keyboard users land back where they started.
        if (shouldReturnFocus !== false && lastChatOpener && document.contains(lastChatOpener)) {
            lastChatOpener.focus();
        }
    }

    openButtons.forEach(function (button) {
        button.addEventListener('click', function (event) {
            event.stopPropagation();
            openChat(button);
        });
    });

    if (toggle) {
        toggle.addEventListener('click', function (event) {
            event.stopPropagation();
            openChat(toggle);
        });
    }

    // -------------------------------------------------------
    // FLOATING LAUNCHER VISIBILITY (re-anchored 2026-07-07)
    // The old anchor (.profile-actions [data-chat-open]) was removed in
    // the profile-band redesign, which left the launcher permanently
    // hidden on every page. New behavior: watch the page's primary
    // Ask-AI element — the launcher stays hidden while that element is
    // on screen and fades in once the visitor scrolls past it. Pages
    // with no ask element (feed views, placeholder pages) show the
    // launcher right away, so the assistant is one click away everywhere.
    // -------------------------------------------------------

    const pageAskAnchor = document.querySelector(
        '.ps-askbar, .profile-tabs__ask, .resume-ai-panel, .story-hero__ai, .page-ai-after-hero, .ct-ai, .hero-ai-panel, .bd-assistant'
    );

    if (toggle) {
        if (pageAskAnchor && 'IntersectionObserver' in window) {
            const askAnchorWatcher = new IntersectionObserver(function (entries) {
                // isIntersecting is true while the ask element is visible.
                toggle.classList.toggle('is-visible', !entries[0].isIntersecting);
            });

            askAnchorWatcher.observe(pageAskAnchor);
        } else {
            // No ask element on this page: the floating launcher is the
            // only way to reach the assistant, so it is always visible.
            toggle.classList.add('is-visible');
        }
    }

    closeBtn.addEventListener('click', function () {
        closeChat(true);
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && panel.classList.contains('open')) {
            closeChat(true);
        }
    });

    // Clicking outside the open panel dismisses it without exposing state drift to screen readers.
    document.addEventListener('click', function (event) {
        const clickedLauncher = event.target.closest('[data-chat-open], #chat-toggle');

        if (
            panel.classList.contains('open') &&
            !panel.contains(event.target) &&
            !clickedLauncher
        ) {
            closeChat(false);
        }
    });


    // -------------------------------------------------------
    // SUGGESTION BUTTONS
    // When a visitor clicks a suggested question chip, it
    // acts exactly like they typed that question and hit Send.
    // -------------------------------------------------------

    suggestions.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const question = btn.textContent.trim();

            sendMessage(question);
        });
    });


    // -------------------------------------------------------
    // SENDING A MESSAGE
    // Two ways to send: click the Send button, or press Enter
    // -------------------------------------------------------

    sendBtn.addEventListener('click', handleSend);

    input.addEventListener('keydown', function (e) {
        // Send on Enter key, but allow Shift+Enter to add a new line
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();     // Stops the browser from adding a blank line
            handleSend();
        }
    });

    // Reads the input, clears it, and triggers the message flow
    function handleSend() {
        const text = input.value.trim();    // Remove extra spaces from both ends
        if (!text) return;                  // Do nothing if the box is empty
        input.value = '';                   // Clear the input field
        sendMessage(text);
    }


    // -------------------------------------------------------
    // THE MESSAGE FLOW - MVP 1
    // Sends the user's message to Flask, which calls the
    // real Claude API and returns an intelligent answer.
    // -------------------------------------------------------

    function sendMessage(text) {
        // 1. Hide the suggestion chips after the visitor sends any question.
        const suggestionsBox = document.getElementById('chat-suggestions');
        if (suggestionsBox) {
            suggestionsBox.style.display = 'none';
        }

        // 2. Display the user's message (right side, gold bubble)
        addMessage(text, 'user');

        // 3. Show a "..." thinking bubble while we wait for Claude's response.
        //    This gives the user visual feedback that something is happening.
        const thinkingBubble = addMessage('...', 'bot');

        // 4. Disable the input and button so the user can't send another
        //    message while we're waiting for a response
        input.disabled = true;
        sendBtn.disabled = true;

        // 5. Ask Flask for the answer and update the thinking bubble.
        requestChatReply(text)
        .then(function(data) {
            if (data.response) {
                thinkingBubble.textContent = data.response;
            } else {
                // If the server returned an error field, show a friendly message.
                thinkingBubble.textContent = data.error || "Something went wrong. Please try again.";
            }
            scrollToBottom();
        })

        // 8. If the network request itself failed (e.g. Flask isn't running),
        //    show a fallback message instead of breaking silently.
        .catch(function(error) {
            if (error && error.isFriendlyChatError && error.message) {
                thinkingBubble.textContent = error.message;
            } else {
                thinkingBubble.textContent = "I could not reach the assistant. Please check the connection and try again.";
            }
            scrollToBottom();
        })

        // 9. Whether it succeeded or failed, always re-enable the input
        //    so the user can try again.
        .finally(function() {
            input.disabled = false;
            sendBtn.disabled = false;
            input.focus();
        });
    }

    // Named helpers make the shared chat behavior reusable from page-specific UI.
    // They also keep browser JavaScript from knowing anything about API keys.
    window.openChatPanel = function () {
        openChat(document.activeElement);
    };

    window.closeChatPanel = function () {
        closeChat(true);
    };

    window.sendChatMessage = function (question) {
        const text = String(question || '').trim();
        if (!text) return;
        input.value = '';
        sendMessage(text);
    };

    // Exposes one safe doorway for page-specific buttons, such as the
    // interactive resume prompts, to open the same chat assistant and send
    // a question without duplicating the chatbot logic in another file.
    window.askPeteAI = function (question) {
        openChat(document.activeElement);
        window.sendChatMessage(question);
    };

    // Lowercase alias matching the homepage search specification.
    window.askPeteAi = function (question) {
        window.askPeteAI(question);
    };

    const heroSearches = document.querySelectorAll('[data-hero-ai-search]');
    heroSearches.forEach(function (heroSearch) {
        const heroInput = heroSearch.querySelector('.hero-ai-search__input');
        const heroStatus = heroSearch.querySelector('[data-hero-ai-status]');
        const heroAnswer = heroSearch.querySelector('[data-hero-ai-answer]');
        const heroButton = heroSearch.querySelector('.hero-ai-search__button');
        const defaultStatus = 'Answers use approved public portfolio evidence.';

        function renderHeroAnswer(question, responseText, isLoading) {
            if (!heroAnswer) return;

            heroAnswer.hidden = false;
            heroAnswer.innerHTML = [
                '<button class="hero-ai-answer__close" type="button" data-hero-ai-answer-close aria-label="Close AI answer">×</button>',
                '<div class="hero-ai-answer__question"></div>',
                '<div class="hero-ai-answer__response"></div>'
            ].join('');

            heroAnswer.querySelector('.hero-ai-answer__question').textContent = question;
            heroAnswer.querySelector('.hero-ai-answer__response').textContent = responseText;
            heroAnswer.classList.toggle('is-loading', Boolean(isLoading));
        }

        function closeHeroAnswer() {
            if (!heroAnswer) return;

            heroAnswer.hidden = true;
            heroAnswer.classList.remove('is-loading');
            heroAnswer.textContent = '';
        }

        function submitHeroQuestion(question) {
            const promptText = String(question || '').trim();
            if (!promptText) return;

            heroSearch.classList.add('is-searching');
            if (heroStatus) {
                heroStatus.textContent = 'Searching approved portfolio evidence...';
            }
            if (heroButton) {
                heroButton.disabled = true;
            }
            renderHeroAnswer(promptText, 'Searching approved portfolio evidence...', true);

            requestChatReply(promptText)
                .then(function (data) {
                    const response = data.response || data.error || 'Something went wrong. Please try again.';
                    renderHeroAnswer(promptText, response, false);
                })
                .catch(function (error) {
                    const response =
                        error && error.isFriendlyChatError && error.message
                            ? error.message
                            : 'I could not reach the assistant. Please check the connection and try again.';
                    renderHeroAnswer(promptText, response, false);
                })
                .finally(function () {
                    heroSearch.classList.remove('is-searching');
                    if (heroStatus) {
                        heroStatus.textContent = defaultStatus;
                    }
                    if (heroButton) {
                        heroButton.disabled = false;
                    }
                    if (heroInput) {
                        heroInput.focus();
                    }
                });

        }

        heroSearch.addEventListener('click', function (event) {
            if (event.target.closest('[data-hero-ai-answer-close]')) {
                closeHeroAnswer();
                if (heroInput) {
                    heroInput.focus();
                }
            }
        });

        heroSearch.addEventListener('submit', function (event) {
            event.preventDefault();
            submitHeroQuestion(heroInput ? heroInput.value : '');
            if (heroInput) {
                heroInput.value = '';
            }
        });
    });

    // -------------------------------------------------------
    // HEADER SEARCH HANDOFF (?ask=...)
    // The header search bar's "Ask Pete's AI" row navigates with
    // ?ask=<question>. Prefill the page's first Ask-AI search and
    // submit it for real; if this page has no ask bar, open the chat
    // panel with the question instead — it is never dropped.
    // -------------------------------------------------------

    const askParam = new URLSearchParams(window.location.search).get('ask');

    if (askParam && askParam.trim()) {
        const askQuestion = askParam.trim().slice(0, 240);
        const firstHeroSearch = document.querySelector('[data-hero-ai-search]');

        if (firstHeroSearch) {
            const firstHeroInput = firstHeroSearch.querySelector('.hero-ai-search__input');
            if (firstHeroInput) {
                firstHeroInput.value = askQuestion;
            }
            firstHeroSearch.scrollIntoView({ block: 'center' });
            firstHeroSearch.dispatchEvent(new Event('submit', { cancelable: true }));
        } else {
            window.askPeteAI(askQuestion);
        }

        // Clean the URL so refresh/back never silently re-asks.
        window.history.replaceState(null, '', window.location.pathname);
    }


    // -------------------------------------------------------
    // ADD A MESSAGE BUBBLE TO THE CONVERSATION
    // Creates a div, gives it the right style class, adds the
    // text, and appends it to the messages area.
    // Returns the element so we can update it later (used for
    // the "..." placeholder above).
    // -------------------------------------------------------

    function addMessage(text, sender) {
        const bubble = document.createElement('div');
        bubble.classList.add('chat-message');
        bubble.classList.add(sender === 'bot' ? 'bot-message' : 'user-message');
        bubble.textContent = text;
        messages.appendChild(bubble);
        scrollToBottom();
        return bubble;
    }


    // -------------------------------------------------------
    // SCROLL TO THE NEWEST MESSAGE
    // Called after every message so the most recent one is
    // always visible without the user having to scroll.
    // -------------------------------------------------------

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }



}  // End of initializeChatbot

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeChatbot);
} else {
    initializeChatbot();
}

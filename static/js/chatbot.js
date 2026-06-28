// =========================================================
// CHATBOT WIDGET — chatbot.js
//
// This file controls everything the chat widget DOES:
// opening, closing, sending messages, and responding.
//
// MVP 0: This is the visual prototype. Responses are
// hardcoded mock text — no real AI is connected yet.
// In MVP 1 we will replace getMockResponse() with a
// real call to the Flask API, which will call Claude.
// =========================================================


// Wait until the full page has finished loading before
// running any code. This prevents errors from trying to
// find HTML elements that don't exist yet.
document.addEventListener('DOMContentLoaded', function () {


    // -------------------------------------------------------
    // GRAB THE HTML ELEMENTS WE NEED
    // We store references here so we don't have to search
    // the page for them every single time we use them.
    // -------------------------------------------------------

    const toggle      = document.getElementById('chat-toggle');      // Floating "Ask Pete AI" button
    const panel       = document.getElementById('chat-panel');       // The slide-in chat panel
    const closeBtn    = document.getElementById('chat-close');       // The X button inside the header
    const messages    = document.getElementById('chat-messages');    // Scrollable message area
    const input       = document.getElementById('chat-input');       // The text input field
    const sendBtn     = document.getElementById('chat-send');        // The Send button
    const suggestions = document.querySelectorAll('.suggestion-btn'); // All 4 suggestion chips


    // -------------------------------------------------------
    // OPEN AND CLOSE THE PANEL
    // -------------------------------------------------------

    // Clicking the floating button toggles the panel open or closed
    toggle.addEventListener('click', function () {
        panel.classList.toggle('open');

        // When the panel opens, move focus to the input field
        // so the user can start typing right away
        if (panel.classList.contains('open')) {
            input.focus();
        }
    });

    // Clicking the X button closes the panel
    closeBtn.addEventListener('click', function () {
        panel.classList.remove('open');
    });

    // Clicking anywhere outside the panel and button closes the panel
    document.addEventListener('click', function (e) {
        if (!panel.contains(e.target) && !toggle.contains(e.target)) {
            panel.classList.remove('open');
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

            // Hide the suggestion chips — they've served their purpose
            const suggestionsBox = document.getElementById('chat-suggestions');
            if (suggestionsBox) {
                suggestionsBox.style.display = 'none';
            }

            sendMessage(question);
        });
    });


    // -------------------------------------------------------
    // SENDING A MESSAGE
    // Two ways to send: click the Send button, or press Enter
    // -------------------------------------------------------

    sendBtn.addEventListener('click', handleSend);

    input.addEventListener('keydown', function (e) {
        // Send on Enter key — but allow Shift+Enter to add a new line
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
    // THE MESSAGE FLOW
    // Shows the user's message, then gets and shows a response
    // -------------------------------------------------------

    function sendMessage(text) {
        // 1. Display the user's message (right side, gold bubble)
        addMessage(text, 'user');

        // 2. Show a "..." placeholder while we "wait" for a response.
        //    In MVP 0 the response is instant, but this placeholder
        //    sets up the same pattern we'll use in MVP 1 when real
        //    API calls take a second or two to come back.
        const thinkingBubble = addMessage('...', 'bot');

        // 3. After a short delay, replace the placeholder with the response
        setTimeout(function () {
            const response = getMockResponse(text);
            thinkingBubble.textContent = response;
            scrollToBottom();
        }, 700);
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


    // -------------------------------------------------------
    // MOCK RESPONSES — MVP 0 placeholder
    //
    // This function returns a pre-written response based on
    // keywords found in the user's question. It is a stand-in
    // for real AI.
    //
    // In MVP 1, this entire function will be replaced with a
    // fetch() call to the Flask /api/chat route, which will
    // send the question to the Claude API and stream back a
    // real answer grounded in Pete's knowledge base files.
    // -------------------------------------------------------

    function getMockResponse(text) {
        const q = text.toLowerCase();

        if (q.includes('experience') || q.includes('background') || q.includes('career')) {
            return "Pete has 20+ years of experience in systems engineering across the Air Force, DoD, L3Harris, and Northrop Grumman. He specializes in requirements engineering, MBSE, and digital engineering. [Source: Professional Summary]";
        }

        if (q.includes('mbse') || q.includes('systems engineering') || q.includes('model') || q.includes('sysml')) {
            return "Pete is proficient in MBSE using Cameo/MagicDraw and SysML. He applies model-based approaches to architecture, requirements traceability, and interface management across defense programs. [Source: Technical Skills]";
        }

        if (q.includes('certif') || q.includes('pmp') || q.includes('phd') || q.includes('degree')) {
            return "Pete holds a PMP certification and a PhD. He is an experienced digital engineering practitioner in his current role at Northrop Grumman. [Source: Accomplishments]";
        }

        if (q.includes('leader') || q.includes('manag') || q.includes('team')) {
            return "Pete has led cross-functional engineering teams, managed requirements baselines for major defense programs, and mentored junior engineers throughout his career. [Source: Career History]";
        }

        if (q.includes('ai') || q.includes('automation') || q.includes('python') || q.includes('software')) {
            return "Pete is actively learning Python and building AI-enabled tools. This portfolio site — built with Flask and the Claude API — is a live demonstration of those skills in action. [Source: Professional Summary]";
        }

        if (q.includes('northrop') || q.includes('l3') || q.includes('harris') || q.includes('dod') || q.includes('air force')) {
            return "Pete has worked across several major defense organizations, including the U.S. Air Force, DoD, L3Harris, and his current role at Northrop Grumman in systems and requirements engineering. [Source: Career History]";
        }

        if (q.includes('contact') || q.includes('hire') || q.includes('reach') || q.includes('available')) {
            return "You can reach Pete through the Contact page on this site. He is open to discussing engineering leadership and digital engineering opportunities.";
        }

        // Default — used when nothing matches
        return "That's a great question! I'm grounded in Pete's approved portfolio information. Try asking about his experience, MBSE background, certifications, leadership, or AI interests — or use the Contact page to reach him directly.";
    }


});  // End of DOMContentLoaded

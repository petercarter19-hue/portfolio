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

    const toggle      = document.getElementById('chat-toggle');      // Optional floating launcher; currently removed from base.html
    const panel       = document.getElementById('chat-panel');       // The slide-in chat panel
    const closeBtn    = document.getElementById('chat-close');       // The X button inside the header
    const messages    = document.getElementById('chat-messages');    // Scrollable message area
    const input       = document.getElementById('chat-input');       // The text input field
    const sendBtn     = document.getElementById('chat-send');        // The Send button
    const suggestions = document.querySelectorAll('.suggestion-btn'); // All 4 suggestion chips


    // -------------------------------------------------------
    // OPEN AND CLOSE THE PANEL
    // -------------------------------------------------------

    // If a floating launcher is added back later, this keeps it working.
    // The current site opens the chat from the top navigation button instead.
    if (toggle) {
        // Clicking the floating button toggles the panel open or closed
        toggle.addEventListener('click', function () {
            panel.classList.toggle('open');

            // When the panel opens, move focus to the input field
            // so the user can start typing right away
            if (panel.classList.contains('open')) {
                input.focus();
            }
        });
    }

    // Clicking the X button closes the panel
    closeBtn.addEventListener('click', function () {
        panel.classList.remove('open');
    });

    // Clicking anywhere outside the panel and button closes the panel
    document.addEventListener('click', function (e) {
        if (!panel.contains(e.target) && (!toggle || !toggle.contains(e.target))) {
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

        // 5. Send the message to our Flask /api/chat route using fetch().
        //    fetch() is a built-in browser tool for making HTTP requests.
        //    We're sending a POST request with the message as JSON.
        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        })

        // 6. The response comes back as JSON, so parse it.
        .then(function(response) {
            return response.json();
        })

        // 7. Use the parsed data to update the thinking bubble with Claude's answer.
        .then(function(data) {
            if (data.response) {
                thinkingBubble.textContent = data.response;
            } else {
                // If the server returned an error field, show a friendly message.
                thinkingBubble.textContent = "Sorry, I couldn't get a response. Please try again.";
            }
            scrollToBottom();
        })

        // 8. If the network request itself failed (e.g. Flask isn't running),
        //    show a fallback message instead of breaking silently.
        .catch(function() {
            thinkingBubble.textContent = "Something went wrong connecting to the server. Please refresh and try again.";
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

    // Exposes one safe doorway for page-specific buttons, such as the
    // interactive resume prompts, to open the same chat assistant and send
    // a question without duplicating the chatbot logic in another file.
    window.askPeteAI = function (question) {
        panel.classList.add('open');
        input.value = '';
        sendMessage(question);
    };


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

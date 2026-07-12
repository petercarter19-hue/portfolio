// Optional Azure SQL-backed behavior for the Break view.
// The static preview stays intact unless PEERSLATE_DATABASE_UI_ENABLED is on.

(function () {
    var page = document.querySelector('[data-break-api="true"]');
    if (!page) { return; }

    var status = page.querySelector('[data-break-status]');
    var challengeId = null;
    var pollId = null;
    var pickMeUpId = null;

    function announce(message) {
        if (status) { status.textContent = message; }
    }

    function api(url, options) {
        var settings = options || {};
        settings.headers = Object.assign({}, settings.headers || {}, {
            'X-PeerSlate-Request': 'same-origin'
        });
        if (settings.body) {
            settings.headers['Content-Type'] = 'application/json';
        }
        return fetch(url, settings).then(function (response) {
            return response.json().then(function (payload) {
                if (!response.ok || !payload.success) {
                    throw new Error(payload.message || 'PeerSlate could not complete the request.');
                }
                return payload;
            });
        });
    }

    function hydrateFeed(cards) {
        var challenge = cards.find(function (card) { return card.card_type === 'challenge'; });
        var pickMeUp = cards.find(function (card) {
            return card.card_type === 'quote' || card.card_type === 'pick_me_up';
        });

        if (challenge) {
            challengeId = challenge.content_item_id;
            var title = page.querySelector('[data-db-challenge-title]');
            var body = page.querySelector('[data-db-challenge-body]');
            if (title) { title.textContent = challenge.title || 'Today\'s challenge'; }
            if (body) { body.textContent = challenge.body || ''; }
        }

        if (pickMeUp) {
            pickMeUpId = pickMeUp.content_item_id;
            var quote = page.querySelector('[data-db-pickme-body]');
            var author = page.querySelector('[data-db-pickme-author]');
            if (quote) { quote.textContent = pickMeUp.body || pickMeUp.title || ''; }
            if (author) { author.textContent = pickMeUp.author ? '— ' + pickMeUp.author : ''; }
        }
    }

    function hydratePoll(options) {
        if (!options.length) { return; }
        pollId = options[0].poll_content_item_id;
        var question = page.querySelector('[data-db-poll-question]');
        if (question) { question.textContent = options[0].poll_question; }

        var rows = page.querySelectorAll('[data-db-poll-options] li');
        options.slice(0, rows.length).forEach(function (option, index) {
            var row = rows[index];
            var label = row.querySelector('.bk-poll__label');
            var percent = row.querySelector('.bk-poll__pct');
            if (label) { label.textContent = option.option_text; }
            if (percent) { percent.textContent = 'Vote'; }
            row.dataset.optionPosition = option.option_position;
            row.tabIndex = 0;
            row.setAttribute('role', 'button');
            row.setAttribute('aria-label', 'Vote for ' + option.option_text);
        });
    }

    Promise.all([
        api('/api/feed/break'),
        api('/api/polls/today/options')
    ]).then(function (responses) {
        hydrateFeed(responses[0].cards || []);
        hydratePoll(responses[1].options || []);
        announce('Today\'s Break content is loaded.');
    }).catch(function (error) {
        announce(error.message + ' The preview content remains available.');
    });

    var challengeButton = page.querySelector('[data-break-toggle]');
    if (challengeButton) {
        challengeButton.addEventListener('click', function () {
            if (!challengeId) { return; }
            challengeButton.disabled = true;
            api('/api/challenges/' + challengeId + '/complete', {
                method: 'POST',
                body: JSON.stringify({})
            }).then(function () {
                announce('Challenge marked complete.');
            }).catch(function (error) {
                announce(error.message);
                challengeButton.classList.remove('is-joined');
            }).finally(function () {
                challengeButton.disabled = false;
            });
        });
    }

    function vote(row) {
        if (!pollId || !row.dataset.optionPosition) { return; }
        api('/api/polls/' + pollId + '/votes', {
            method: 'POST',
            body: JSON.stringify({ option_position: Number(row.dataset.optionPosition) })
        }).then(function () {
            page.querySelectorAll('[data-db-poll-options] li').forEach(function (item) {
                item.setAttribute('aria-pressed', String(item === row));
            });
            announce('Your poll vote was recorded.');
        }).catch(function (error) {
            announce(error.message);
        });
    }

    page.querySelectorAll('[data-db-poll-options] li').forEach(function (row) {
        row.addEventListener('click', function () { vote(row); });
        row.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                vote(row);
            }
        });
    });

    var saveButton = page.querySelector('.bk-pickme .bk-heart');
    if (saveButton) {
        saveButton.removeAttribute('aria-disabled');
        saveButton.addEventListener('click', function () {
            if (!pickMeUpId) { return; }
            api('/api/saved-boards/Break Favorites/items/' + pickMeUpId, {
                method: 'POST',
                body: JSON.stringify({ note: 'Saved from the Break view.' })
            }).then(function () {
                saveButton.setAttribute('aria-pressed', 'true');
                announce('Saved privately to Break Favorites.');
            }).catch(function (error) {
                announce(error.message);
            });
        });
    }
})();

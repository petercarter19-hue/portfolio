"""Local-only deterministic browser fixture for the visual-facelift evidence.

It starts the real Flask application on an unshared loopback port, replaces the
remote AI provider with validated fixture replies, and is never production code.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from flask import request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import app as app_module


_profile, _evidence = app_module._interview_page_context('petec')
EVIDENCE_ID = _evidence[0]['id']


class FixtureMessages:
    def create(self, **kwargs):
        system = kwargs.get('system', '')
        if 'overallScore' in system:
            payload = {
                'overallScore': 82,
                'verdict': 'Clear, credible foundation',
                'encouragement': 'Your answer shows ownership and a constructive result.',
                'dimensions': [
                    {'key': 'relevance', 'score': 17, 'rationale': 'You answered the question directly.', 'nextAction': 'Name the decision earlier.'},
                    {'key': 'structure', 'score': 16, 'rationale': 'The story follows a clear sequence.', 'nextAction': 'Separate task from action.'},
                    {'key': 'specificity', 'score': 16, 'rationale': 'The example includes concrete actions.', 'nextAction': 'Add one precise detail.'},
                    {'key': 'evidence', 'score': 16, 'rationale': 'The evidence supports your judgment.', 'nextAction': 'Connect evidence to impact.'},
                    {'key': 'impact', 'score': 17, 'rationale': 'The result is useful and believable.', 'nextAction': 'State the lasting benefit.'},
                ],
                'star': {
                    'situation': {'status': 'strong', 'reason': 'The context is clear.'},
                    'task': {'status': 'present', 'reason': 'The responsibility is stated.'},
                    'action': {'status': 'strong', 'reason': 'Your response is specific.'},
                    'result': {'status': 'present', 'reason': 'The outcome is credible.'},
                },
                'strengths': ['Clear ownership', 'Constructive decision', 'Credible result'],
                'improvements': ['Name the task sooner', 'Add one verified detail'],
                'evidenceSuggestions': [{
                    'opportunity': 'A confirmed result could sharpen a future answer.',
                    'suggestedUse': 'Connect the result only if it is true for your story.',
                    'evidenceId': EVIDENCE_ID,
                }],
            }
        elif 'Rewrite a submitted answer' in system:
            payload = {
                'draft': 'I led a cross-functional effort to simplify onboarding. I clarified the problem, aligned the team around the highest-friction steps, and delivered a clearer experience. I would bring the same evidence-led approach to this role.',
                'changes': ['Clarified the situation', 'Strengthened the action', 'Closed with the result'],
                'evidenceIds': [],
            }
        elif 'Give two or three concise hints' in system:
            payload = {
                'hints': [
                    'Name the disagreement and the risk clearly.',
                    'Explain the evidence that guided your response.',
                    'Close with the outcome and lesson.',
                ],
            }
        elif 'GENERIC best-practice' in system:
            payload = {
                'status': 'answered',
                'answer': 'At a previous employer, I surfaced a delivery risk early, gathered the right partners, and proposed a practical alternative. We protected the goal, learned from the tradeoff, and shared the approach with the team.',
                'whyItWorks': ['Shows ownership', 'Uses a clear decision sequence', 'Ends with a reflection'],
                'evidenceIds': [],
            }
        else:
            payload = {
                'status': 'answered',
                'answer': 'I approached the decision by clarifying the risk, bringing the relevant evidence, and offering a practical alternative. The team protected the schedule and used the lesson to improve how we planned future work.',
                'whyItWorks': ['Grounded in approved public history', 'Shows clear judgment', 'Connects action to outcome'],
                'evidenceIds': [EVIDENCE_ID],
            }
        return SimpleNamespace(
            content=[SimpleNamespace(text=json.dumps(payload))],
            stop_reason='end_turn',
        )


class FixtureClient:
    messages = FixtureMessages()


app_module.client = FixtureClient()
app_module.limiter.enabled = False


@app_module.app.after_request
def seed_locked_history_fixture(response):
    """Seed only the comparable browser-local History evidence state.

    The production application never receives this behavior: it exists only in
    this loopback fixture process and only after an explicit query flag.  The
    records mirror the released browser-local record schema (including the
    intentionally scoreless video metadata) and are removed from the URL before
    the screenshot is taken.
    """
    if response.mimetype != "text/html":
        return response

    scripts = []
    if (
        request.args.get("fixture_history") == "locked"
        and request.path == "/interview-studio/history"
    ):
        records = [
            {
                "id": "fixture-me-2026-07-28",
                "createdAt": "2026-07-28T16:10:00.000Z",
                "mode": "me",
                "question": "Tell me about a time you disagreed with a supervisor.",
                "family": "behavioral",
                "competency": "Conflict",
                "score": 82,
                "dimensions": {
                    "relevance": 17,
                    "structure": 16,
                    "specificity": 16,
                    "evidence": 16,
                    "impact": 17,
                },
                "status": "Completed",
                "answer": "Fixture evidence only: a locally reviewed written practice answer.",
                "verdict": "Clear, credible foundation",
                "encouragement": "Your answer shows ownership and a constructive result.",
                "strengths": ["Clear ownership", "Constructive decision"],
                "improvements": ["Name the task sooner", "Add one verified detail"],
            },
            {
                "id": "fixture-video-2026-07-28",
                "createdAt": "2026-07-28T15:55:00.000Z",
                "mode": "video",
                "question": "Describe a decision you made with incomplete information.",
                "family": "behavioral",
                "competency": "Decisions",
                "score": None,
                "durationSeconds": 64,
                "status": "Recorded locally",
            },
        ]
        seed = json.dumps(records).replace("</", "<\\/")
        scripts.append(
            f"""
<script>
(() => {{
  const prefix = 'peerslate:interview-studio:petec:v1';
  Object.keys(window.localStorage).forEach((key) => {{
    if (key.indexOf(prefix) === 0) window.localStorage.removeItem(key);
  }});
  window.localStorage.setItem(prefix + ':history', JSON.stringify({seed}));
  window.localStorage.setItem(prefix + ':goal', '85');
  const url = new URL(window.location.href);
  url.searchParams.delete('fixture_history');
  window.location.replace(url.pathname + (url.search || '') + url.hash);
}})();
</script>
"""
        )

    if (
        request.args.get("fixture_scroll") == "video-camera"
        and request.path == "/interview-studio"
    ):
        scripts.append(
            """
<script>
window.addEventListener('load', () => {
  window.requestAnimationFrame(() => {
    const camera = document.querySelector('.is__camera');
    if (camera) camera.scrollIntoView({ behavior: 'auto', block: 'start' });
    const url = new URL(window.location.href);
    url.searchParams.delete('fixture_scroll');
    window.history.replaceState({}, '', url.pathname + (url.search || '') + url.hash);
  });
});
</script>
"""
        )

    if not scripts:
        return response
    body = response.get_data(as_text=True)
    response.set_data(body.replace("</body>", "".join(scripts) + "</body>"))
    return response


app_module.app.run(host='127.0.0.1', port=5018, debug=False)

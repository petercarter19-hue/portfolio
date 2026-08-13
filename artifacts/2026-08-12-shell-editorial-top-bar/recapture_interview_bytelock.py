"""Recapture the four PS-INTERVIEW byte-lock constants after the shell change.

Why this exists
---------------
`tests/test_interview_studio.py::InterviewStudioFlagOffByteComparabilityTests`
locks the byte length and normalized sha256 of the anonymous `/interview-studio`
and `/interview-studio/history` renders. Both pages render the SHARED global
shell, so any shell markup change fails that lock by construction. It is not an
Interview Studio regression.

That the delta is shell markup only was established independently, not asserted:
the reviewer rendered the same route with the BASE `base.html` injected through a
Jinja `ChoiceLoader` (touching no file), measured base 111295 -> final 114617 —
matching the test's own 111406 -> 114728 offset at the time — and then replaced
the `<header class="global-header">` block and the `<ul class="global-tabsource">`
list with placeholders in both documents, which made them byte-identical.
Nothing in the Interview Studio body changed.

This script only prints the replacement constants. It changes nothing. Run it
from the implementation worktree with the project venv.
"""

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app  # noqa: E402
from tests.test_interview_studio import _INTERVIEW_JS_VERSION_TOKEN  # noqa: E402


def capture(client, path):
    response = client.get(path, base_url='http://localhost')
    if response.status_code != 200:
        raise SystemExit(f'{path} returned {response.status_code}, expected 200')
    body = response.get_data(as_text=True)
    normalized = _INTERVIEW_JS_VERSION_TOKEN.sub(r'\1TOKEN', body)
    return len(response.data), hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def main():
    original = app.config.get('PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED')
    app.config['PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED'] = False
    try:
        client = app.test_client()
        length, digest = capture(client, '/interview-studio')
        history_length, history_digest = capture(client, '/interview-studio/history')
    finally:
        app.config['PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED'] = original

    print('FLAG_OFF_INTERVIEW_STUDIO_BYTE_LENGTH =', length)
    print("FLAG_OFF_INTERVIEW_STUDIO_SHA256 = '" + digest + "'")
    print('FLAG_OFF_INTERVIEW_STUDIO_HISTORY_BYTE_LENGTH =', history_length)
    print("FLAG_OFF_INTERVIEW_STUDIO_HISTORY_SHA256 = '" + history_digest + "'")


if __name__ == '__main__':
    main()

"""Tests for PS-ASK-PETE-DIRECT-001, the private recruiter-question path.

Most tests here build their own minimal Flask application and register the
blueprint on it directly (``tests/ask_pete_direct/support.py``). That is
deliberate and outlives the registration leg: it proves the blueprint is
self-contained — it carries its own gate, hardening, and error handlers rather
than leaning on anything in ``app.py`` — and it keeps the bulk of the suite
free of that module's import cost and environment requirements.

``test_darkness.py`` is the exception, and has to be. Since the registration
leg (2026-08-08) the real application registers the blueprint, so the
properties that actually protect a visitor — the flag defaulting off, all three
routes answering a neutral 404, ``/petec/resume`` rendering unchanged, and the
limiter genuinely attached — can only be asserted against the real ``app``.

No test in this package opens a database connection or calls a model provider.
"""

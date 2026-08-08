"""Tests for PS-ASK-PETE-DIRECT-001, the private recruiter-question path.

Nothing in this package imports ``app`` or depends on the blueprint being
registered anywhere. The feature is dark by construction: ``app.py`` is owned
by another lane, so ``ask_pete_direct_routes`` is never registered by
production code. Every route test here builds its own minimal Flask
application and registers the blueprint on it directly (see
``tests/ask_pete_direct/support.py``), which is also the only way these tests
can assert the flag-off and unregistered behaviour honestly.
"""

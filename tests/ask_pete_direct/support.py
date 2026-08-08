"""A throwaway Flask application that registers the blueprint directly.

The production application never registers ``ask_pete_direct`` (``app.py``
belongs to another lane, and the feature is dark by construction), so these
tests cannot reach it through ``app``. They build their own minimal app
instead, which has three further advantages:

* it proves the blueprint is self-contained - it carries its own gate,
  hardening, and error handlers rather than leaning on anything in ``app.py``;
* it keeps the suite free of ``app`` import cost and of that module's
  environment requirements; and
* nothing here can accidentally mutate the real application's configuration.

The database is always mocked at the ``database_service`` seam. No test in this
package opens a connection, and none needs one.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

import ask_pete_direct_routes
from services.ask_pete_direct_service import AskPeteDirectService


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OWNER_USER_KEY = "owner-user-key-1"
OTHER_USER_KEY = "some-other-member"


class RecordingDatabase:
    """Records every call and returns whatever the test queued."""

    def __init__(self, rows=None, result_sets=None, error=None):
        self.rows = list(rows or [])
        self.result_sets = result_sets
        self.error = error
        self.calls = []

    def first_row(self, procedure_name, parameters=None):
        self.calls.append((procedure_name, list(parameters or [])))
        if self.error:
            raise self.error
        return self.rows.pop(0) if self.rows else None

    def execute_procedure(self, procedure_name, parameters=None):
        self.calls.append((procedure_name, list(parameters or [])))
        if self.error:
            raise self.error
        return self.result_sets if self.result_sets is not None else []

    def parameters(self, index=0):
        return dict(self.calls[index][1])

    @property
    def procedures(self):
        return [name for name, _ in self.calls]


class DirectRouteTestCase(unittest.TestCase):
    """Base case: one app per test, with the service seam patched and restored."""

    def make_app(
        self,
        *,
        enabled=True,
        owner_user_keys=OWNER_USER_KEY,
        owner_emails="",
        dev_user_key=None,
        rows=None,
        result_sets=None,
        error=None,
    ):
        """Build the test app and return ``(client, recording_database)``.

        ``dev_user_key`` drives ``identity.get_current_principal``'s
        development branch (``PEERSLATE_ALLOW_DEV_IDENTITY`` plus
        ``PEERSLATE_DEV_USER_KEY``), which is how the rest of this
        repository's tests present a signed-in member without a database.
        Leave it ``None`` for an anonymous visitor.
        """
        app = Flask(
            "ask_pete_direct_test_app",
            root_path=str(REPOSITORY_ROOT),
            template_folder="templates",
            static_folder="static",
        )
        app.config.update(
            TESTING=True,
            PEERSLATE_ASK_PETE_DIRECT_ENABLED=enabled,
            PEERSLATE_OWNER_EMAILS=owner_emails,
            PEERSLATE_OWNER_USER_KEYS=owner_user_keys,
            PEERSLATE_ALLOW_DEV_IDENTITY=dev_user_key is not None,
            PEERSLATE_DEV_USER_KEY=dev_user_key,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
        )
        app.register_blueprint(ask_pete_direct_routes.ask_pete_direct)

        database = RecordingDatabase(rows=rows, result_sets=result_sets, error=error)
        patcher = patch.object(
            ask_pete_direct_routes,
            "ask_pete_direct_service",
            AskPeteDirectService(database=database),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.app = app
        return app.test_client(), database


def json_headers(*, idempotency_key="idem-test-1", **overrides):
    """The headers the companion form actually sends."""
    headers = {
        "X-PeerSlate-Request": "same-origin",
        "Origin": "http://localhost",
        "Sec-Fetch-Site": "same-origin",
        "Content-Type": "application/json",
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    for name, value in overrides.items():
        header = name.replace("_", "-")
        if value is None:
            headers.pop(header, None)
        else:
            headers[header] = value
    return headers


def form_headers(**overrides):
    """What a real same-origin HTML form post carries (no custom header)."""
    headers = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}
    for name, value in overrides.items():
        header = name.replace("_", "-")
        if value is None:
            headers.pop(header, None)
        else:
            headers[header] = value
    return headers


def question_payload(**overrides):
    payload = {
        "question": "Which parts of the recovery effort did Pete run himself?",
        "contact": "Dana Reyes, Northwind Talent, dana@example.com",
        "consent": True,
    }
    payload.update(overrides)
    return {key: value for key, value in payload.items() if value is not ...}

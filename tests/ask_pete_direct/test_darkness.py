"""The feature is registered and OFF. These are the tests that keep it off.

Until 2026-08-08 this module asserted the stronger property: that no
production module imported or registered ``ask_pete_direct`` at all. That was
true while ``app.py`` belonged to another lane, and the two assertions existed
precisely so that leaving that state could never happen quietly. The Interview
lane closed, released ``app.py``, and the recorded registration leg ran — so
both guards fired exactly as designed, and both are replaced here rather than
deleted.

What replaces them is the property that now matters. Registration was never
the safety control; it was scaffolding. The control is, and always was, the
flag:

* ``PEERSLATE_ASK_PETE_DIRECT_ENABLED`` defaults false and is read with
  ``is True``, so no string, integer, or truthy object can open it.
* With it off, all three routes answer a neutral 404 — the *same* 404 to a
  cross-site caller as to a same-origin one, so the surface never confirms it
  exists — and ``/petec/resume`` renders exactly as it did before the
  blueprint was registered.
* Registering unconditionally is what makes that true. The gate lives in the
  blueprint's own ``before_request``, so "off" means a 404 from a route that
  exists, and the flag can be flipped without a redeploy.

The scope guard also survives, in a narrower form: ``app.py`` may carry the
four recorded registration edits and nothing else.
"""

from __future__ import annotations

import ast
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT_MODULE = "ask_pete_direct_routes"
ENV_EXAMPLE = ROOT / ".env.example"
APP = ROOT / "app.py"

os.environ.setdefault("ANTHROPIC_API_KEY", "ask-pete-direct-darkness-test-key")


# Every Python module that is part of the running application, i.e. everything
# at the repository root plus services/, excluding tests and tooling.
def _production_modules():
    modules = sorted(path for path in ROOT.glob("*.py"))
    modules += sorted(path for path in (ROOT / "services").rglob("*.py"))
    return [path for path in modules if path.name != f"{BLUEPRINT_MODULE}.py"]


class RegistrationTests(unittest.TestCase):
    def test_the_blueprint_is_registered_exactly_once(self):
        import app as app_module

        self.assertIn("ask_pete_direct", app_module.app.blueprints)
        source = APP.read_text(encoding="utf-8")
        self.assertEqual(source.count("app.register_blueprint(ask_pete_direct)"), 1)

    def test_it_is_registered_unconditionally(self):
        """The gate belongs in the blueprint's before_request, not here.

        A conditional registration would make "off" mean the route does not
        exist, which changes the refusal, forces a redeploy to flip the flag,
        and makes the flag-off 404 distinguishable from a real one.
        """
        source = APP.read_text(encoding="utf-8")
        line = next(
            candidate
            for candidate in source.splitlines()
            if "app.register_blueprint(ask_pete_direct)" in candidate
        )
        self.assertEqual(line, "app.register_blueprint(ask_pete_direct)")

    def test_all_three_routes_exist(self):
        import app as app_module

        rules = {
            str(rule): sorted(rule.methods - {"HEAD", "OPTIONS"})
            for rule in app_module.app.url_map.iter_rules()
            if rule.endpoint.startswith("ask_pete_direct.")
        }
        self.assertEqual(
            rules,
            {
                "/api/ask-pete/direct-question": ["POST"],
                "/owner/ask-pete-inbox": ["GET"],
                "/owner/ask-pete-inbox/<string:question_key>/status": ["POST"],
            },
        )

    def test_the_planned_rate_limits_are_actually_attached(self):
        import app as app_module
        from ask_pete_direct_routes import PLANNED_RATE_LIMITS

        self.assertTrue(PLANNED_RATE_LIMITS)
        for endpoint in PLANNED_RATE_LIMITS:
            with self.subTest(endpoint=endpoint):
                view = app_module.app.view_functions[endpoint]
                self.assertIsNotNone(
                    getattr(view, "__wrapped__", None),
                    f"{endpoint} was registered but never wrapped by the limiter",
                )

    def test_app_py_reads_the_budgets_rather_than_restating_them(self):
        """Restating them in app.py is how a declaration and its application
        drift apart."""
        source = APP.read_text(encoding="utf-8")
        self.assertIn("for _direct_endpoint, _direct_limit in PLANNED_RATE_LIMITS.items():", source)
        self.assertNotIn("'ask_pete_direct.submit_direct_question':", source)

    def test_app_py_carries_only_the_four_recorded_registration_edits(self):
        """The lane's recorded scope for app.py is exactly these four things.

        Anything else naming this package in app.py is out of that scope and
        should fail review here first.
        """
        source = APP.read_text(encoding="utf-8")
        expected = {
            "from ask_pete_direct_routes import PLANNED_RATE_LIMITS, ask_pete_direct": 1,
            "PEERSLATE_ASK_PETE_DIRECT_ENABLED=(": 1,
            "app.register_blueprint(ask_pete_direct)": 1,
            "for _direct_endpoint, _direct_limit in PLANNED_RATE_LIMITS.items():": 1,
        }
        for fragment, count in expected.items():
            with self.subTest(fragment=fragment):
                self.assertEqual(source.count(fragment), count)

        # No route, view, template call, or service reference belonging to this
        # package may live in app.py. The blueprint owns all of that.
        for forbidden in (
            "ask_pete_direct_service",
            "recruiter_question",
            "ask_pete_inbox.html",
            "@app.route('/api/ask-pete",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_the_blueprint_imports_nothing_from_app(self):
        """A reusable blueprint must never import the module that registers it."""
        tree = ast.parse((ROOT / f"{BLUEPRINT_MODULE}.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertNotIn("app", imported)

    def test_the_service_is_reached_only_through_the_blueprint(self):
        offenders = []
        for path in _production_modules():
            if path.name == "ask_pete_direct_service.py":
                continue
            if "ask_pete_direct_service" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_the_module_docstring_no_longer_claims_to_be_unregistered(self):
        import ask_pete_direct_routes

        docstring = ask_pete_direct_routes.__doc__
        self.assertNotIn("NOT REGISTERED", docstring)
        self.assertIn("PEERSLATE_ASK_PETE_DIRECT_ENABLED", docstring)


class FlagOffTests(unittest.TestCase):
    """Registered, and still unreachable. This is now the whole safety story."""

    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app = app_module.app

    def setUp(self):
        self.original = {
            key: self.app.config.get(key)
            for key in ("TESTING", "PEERSLATE_ASK_PETE_DIRECT_ENABLED")
        }
        self.app.config.update(TESTING=True, PEERSLATE_ASK_PETE_DIRECT_ENABLED=False)
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.config.update(**self.original)

    def test_the_flag_defaults_off_from_the_environment(self):
        """Nothing but PEERSLATE_ASK_PETE_DIRECT_ENABLED=true opens this."""
        self.assertIs(self.original["PEERSLATE_ASK_PETE_DIRECT_ENABLED"], False)

    def test_every_route_answers_404(self):
        headers = {
            "X-PeerSlate-Request": "same-origin",
            "Origin": "http://localhost",
            "Sec-Fetch-Site": "same-origin",
            "Idempotency-Key": "flag-off",
        }
        post = self.client.post(
            "/api/ask-pete/direct-question",
            json={"question": "q", "consent": True},
            headers=headers,
        )
        page = self.client.get("/owner/ask-pete-inbox")
        action = self.client.post(
            "/owner/ask-pete-inbox/6f1b7e3a-8a4a-4a1e-9f0e-2b6c9f7d1a55/status",
            data={"status": "read", "expected_version": "00000000000004d2"},
            headers={"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"},
        )
        for label, response in (("post", post), ("page", page), ("action", action)):
            with self.subTest(route=label):
                self.assertEqual(response.status_code, 404)

    def test_the_refusal_is_identical_for_a_cross_site_caller(self):
        """Otherwise the 404 tells an attacker the route is real but gated."""
        base = {
            "X-PeerSlate-Request": "same-origin",
            "Origin": "http://localhost",
            "Idempotency-Key": "flag-off",
        }
        same = self.client.post(
            "/api/ask-pete/direct-question",
            json={"question": "q", "consent": True},
            headers={**base, "Sec-Fetch-Site": "same-origin"},
        )
        cross = self.client.post(
            "/api/ask-pete/direct-question",
            json={"question": "q", "consent": True},
            headers={**base, "Sec-Fetch-Site": "cross-site"},
        )
        self.assertEqual(same.status_code, cross.status_code)
        self.assertEqual(same.get_data(), cross.get_data())

    def test_the_resume_carries_no_trace_of_the_private_path(self):
        """The registration leg measured this as byte-identical to the
        pre-registration render, in both the legacy and companion modes. This
        keeps the durable half of that claim: nothing from this package can
        reach the page while the flag is off."""
        original = self.app.config.get("PEERSLATE_ASK_PETE_GROUNDED_ENABLED")
        try:
            for grounded in (False, True):
                self.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = grounded
                html = self.client.get("/petec/resume").get_data(as_text=True)
                with self.subTest(grounded=grounded):
                    self.assertEqual(self.client.get("/petec/resume").status_code, 200)
                    for token in (
                        "ask-pete-direct",
                        "/api/ask-pete/direct-question",
                        "company_website",
                    ):
                        self.assertNotIn(token, html)
        finally:
            self.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = original


class FlagOnTests(unittest.TestCase):
    """Flipped on in-process, so the wiring is proven end to end.

    Each test uses its own X-Forwarded-For address: app.py keys the limiter on
    the rightmost forwarded entry, so a distinct address gives each test its
    own budget and the 429 test cannot starve its neighbours.
    """

    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app = app_module.app

    def setUp(self):
        import ask_pete_direct_routes
        from services.ask_pete_direct_service import AskPeteDirectService

        self.routes = ask_pete_direct_routes
        self.original_service = ask_pete_direct_routes.ask_pete_direct_service
        self.original = {
            key: self.app.config.get(key)
            for key in (
                "TESTING",
                "PEERSLATE_ASK_PETE_DIRECT_ENABLED",
                "PEERSLATE_OWNER_USER_KEYS",
                "PEERSLATE_OWNER_EMAILS",
            )
        }
        self.calls = []

        outer = self

        class Recording:
            def first_row(self, name, parameters=None):
                outer.calls.append(name)
                return {"outcome": "success"}

            def execute_procedure(self, name, parameters=None):
                outer.calls.append(name)
                return []

        ask_pete_direct_routes.ask_pete_direct_service = AskPeteDirectService(
            database=Recording()
        )
        self.app.config.update(
            TESTING=True,
            PEERSLATE_ASK_PETE_DIRECT_ENABLED=True,
            PEERSLATE_OWNER_USER_KEYS="the-owner",
            PEERSLATE_OWNER_EMAILS="",
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.routes.ask_pete_direct_service = self.original_service
        self.app.config.update(**self.original)

    def _headers(self, address, key="on-1"):
        return {
            "X-PeerSlate-Request": "same-origin",
            "Origin": "http://localhost",
            "Sec-Fetch-Site": "same-origin",
            "Idempotency-Key": key,
            "X-Forwarded-For": address,
        }

    def test_the_endpoint_answers_and_stores_through_the_allowlisted_procedure(self):
        response = self.client.post(
            "/api/ask-pete/direct-question",
            json={"question": "Would Pete consider Denver?", "consent": True},
            headers=self._headers("203.0.113.10"),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["state"], "sent")
        self.assertEqual(self.calls, ["usp_SubmitRecruiterQuestion"])

    def test_consent_is_still_required_once_the_flag_is_on(self):
        response = self.client.post(
            "/api/ask-pete/direct-question",
            json={"question": "No consent given.", "consent": False},
            headers=self._headers("203.0.113.11"),
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["code"], "consent_required")
        self.assertEqual(self.calls, [])

    def test_the_owner_inbox_is_still_404_for_a_non_owner(self):
        response = self.client.get("/owner/ask-pete-inbox")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.calls, [])

    def test_the_limiter_answers_in_this_blueprints_json_shape(self):
        """Not the application's HTML default. The companion renders this as
        its honest "Not sent - too many questions" state."""
        limited = None
        for index in range(40):
            response = self.client.post(
                "/api/ask-pete/direct-question",
                json={"question": "q", "consent": True},
                headers=self._headers("203.0.113.99", key=f"burst-{index}"),
            )
            if response.status_code == 429:
                limited = response
                break
        self.assertIsNotNone(limited, "30 per hour was never enforced")
        self.assertEqual(limited.mimetype, "application/json")
        self.assertEqual(
            limited.get_json(),
            {
                "success": False,
                "code": "rate_limited",
                "message": "Too many questions from this connection. Try again later.",
            },
        )


class FlagDocumentationTests(unittest.TestCase):
    def test_the_flag_is_documented_off_in_env_example(self):
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        self.assertIn("PEERSLATE_ASK_PETE_DIRECT_ENABLED=false", text)

    def test_the_env_entry_names_the_owner_key_prerequisite(self):
        """Turning the flag on without a single owner user key would leave the
        form visible and every send answering 503. Say so where it is set."""
        block = _env_block(
            ENV_EXAMPLE.read_text(encoding="utf-8"), "PEERSLATE_ASK_PETE_DIRECT_ENABLED"
        )
        self.assertIn("PEERSLATE_OWNER_USER_KEYS", block)


def _env_block(text, key):
    """The comment block immediately above an .env.example assignment."""
    lines = text.splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith(f"{key}="))
    start = index
    while start > 0 and (lines[start - 1].startswith("#") or not lines[start - 1].strip()):
        if not lines[start - 1].strip():
            break
        start -= 1
    return "\n".join(lines[start : index + 1])


if __name__ == "__main__":
    unittest.main()

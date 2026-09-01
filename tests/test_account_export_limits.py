"""Availability budgets for the account-export surface, and their wiring.

PS-SETTINGS-ACCOUNT-EXPORT-AVAILABILITY-001, the second of C3's two
recorded gaps. Three properties are pinned here:

* ``owner_routes.ACCOUNT_EXPORT_PLANNED_RATE_LIMITS`` covers exactly the
  export endpoints that exist, with the exact budgets the package
  approved, and every method that does work is budget-bound -- HEAD
  included, because Flask dispatches HEAD to the same view at full cost
  and strips the body only afterwards. Entries are bare specs (binding
  all served methods) except on the dual-verb request route, whose one
  view serves POST and GET/HEAD with different budgets and therefore
  carries ``(spec, methods)`` pairs.
* ``app.py`` actually attached those budgets after blueprint registration,
  and reads the mapping rather than restating it — the same
  declaration-versus-application discipline
  ``tests/ask_pete_direct/test_darkness.py`` pins for its own blueprint.
* A breached budget answers with the app's one static, content-free JSON
  sentence. The limiter is keyed on the CALLER, never on the job, so the
  429 must be byte-identical whatever job key is asked for: a refusal may
  never become a way to learn whether a job key exists.

Everything here runs offline against the real ``app`` module: no
database, storage, or network. The export flag stays OFF throughout —
the limiter runs before the view, so even the flag-off 404 path is
budgeted, which is itself part of the contract (the budget must not be
avoidable by probing a disabled surface).
"""

from __future__ import annotations

import os
import types
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "account-export-limits-test-key")

import app as app_module
from owner_routes import ACCOUNT_EXPORT_PLANNED_RATE_LIMITS


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "app.py"

REFUSAL_SENTENCE = "Too many requests. Please wait a moment and try again."

EXPECTED_BUDGETS = {
    "owner.account_export": (
        ("10 per hour", ("POST",)),
        ("60 per minute", ("GET", "HEAD")),
    ),
    "owner.account_export_status": ("60 per minute",),
    "owner.account_export_download": ("30 per hour",),
}


class PlannedBudgetDeclarationTests(unittest.TestCase):
    """The mapping itself: coverage, exact budgets, and shape."""

    def test_the_mapping_covers_exactly_the_export_endpoints_that_exist(self):
        """An export route added later without a budget fails here, not in
        production — and a budget whose route disappears fails too."""
        export_endpoints = {
            endpoint
            for endpoint in app_module.app.view_functions
            if endpoint.startswith("owner.account_export")
        }
        self.assertTrue(export_endpoints)
        self.assertEqual(export_endpoints, set(ACCOUNT_EXPORT_PLANNED_RATE_LIMITS))

    def test_the_exact_budgets_and_methods_are_the_approved_ones(self):
        self.assertEqual(
            dict(ACCOUNT_EXPORT_PLANNED_RATE_LIMITS), EXPECTED_BUDGETS
        )

    def test_entries_are_bare_specs_unless_one_view_serves_split_budgets(self):
        """A bare spec binds every method the route serves, HEAD included,
        and therefore cannot accidentally exempt a verb that does work.
        Method-scoped pairs are reserved for the one route where a single
        view genuinely serves verbs with different budgets (independent
        review HIGH 1: a methods=("GET",) pair on the download proxy let
        HEAD bypass the budget entirely)."""
        for endpoint, limits in ACCOUNT_EXPORT_PLANNED_RATE_LIMITS.items():
            with self.subTest(endpoint=endpoint):
                self.assertIsInstance(limits, tuple)
                self.assertTrue(limits)
                for entry in limits:
                    if isinstance(entry, str):
                        continue
                    spec, methods = entry
                    self.assertIsInstance(spec, str)
                    self.assertIsInstance(methods, tuple)
                    self.assertTrue(methods)
                    self.assertEqual(
                        endpoint,
                        "owner.account_export",
                        "method-scoped pairs are reserved for the "
                        "dual-verb request route; every other entry must "
                        "be a bare spec so no served verb escapes",
                    )

    def test_every_method_that_does_work_is_budget_bound(self):
        """HEAD is deliberately NOT subtracted here: Flask dispatches it
        to the same view as GET at full cost and strips the body only
        afterwards, so it does the work and must burn a budget. Only
        OPTIONS -- answered by Flask before any view runs -- is exempt.
        (Independent review HIGH 1: the first candidate subtracted HEAD
        in this very test, which is exactly how an unbudgeted HEAD went
        unnoticed.) A budget naming a method the route never serves would
        be dead configuration that LOOKS like protection."""
        served = {
            rule.endpoint: rule.methods - {"OPTIONS"}
            for rule in app_module.app.url_map.iter_rules()
            if rule.endpoint in ACCOUNT_EXPORT_PLANNED_RATE_LIMITS
        }
        for endpoint, limits in ACCOUNT_EXPORT_PLANNED_RATE_LIMITS.items():
            covered = set()
            for entry in limits:
                if isinstance(entry, str):
                    # A bare spec binds everything the route serves.
                    covered |= served[endpoint]
                else:
                    _spec, methods = entry
                    # A scoped entry may only name methods actually served.
                    self.assertLessEqual(set(methods), served[endpoint])
                    covered |= set(methods)
            with self.subTest(endpoint=endpoint):
                self.assertEqual(covered, served[endpoint])

    def test_the_mapping_is_immutable(self):
        self.assertIsInstance(
            ACCOUNT_EXPORT_PLANNED_RATE_LIMITS, types.MappingProxyType
        )
        with self.assertRaises(TypeError):
            ACCOUNT_EXPORT_PLANNED_RATE_LIMITS["owner.account_export"] = ()


class AppliedWiringTests(unittest.TestCase):
    """app.py attached the declared budgets to the registered views."""

    def test_the_planned_budgets_are_actually_attached(self):
        for endpoint in ACCOUNT_EXPORT_PLANNED_RATE_LIMITS:
            with self.subTest(endpoint=endpoint):
                view = app_module.app.view_functions[endpoint]
                self.assertIsNotNone(
                    getattr(view, "__wrapped__", None),
                    f"{endpoint} was registered but never wrapped by the limiter",
                )

    def test_app_py_reads_the_budgets_rather_than_restating_them(self):
        """Restating them in app.py is how a declaration and its
        application drift apart."""
        source = APP_SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            "ACCOUNT_EXPORT_PLANNED_RATE_LIMITS.items()",
            source,
        )
        self.assertNotIn("'owner.account_export'", source)
        self.assertNotIn('"owner.account_export"', source)


class RefusalContractTests(unittest.TestCase):
    """What a caller who trips a budget is actually told."""

    def setUp(self):
        self._original_enabled = app_module.limiter.enabled
        self._original_config = {
            key: app_module.app.config.get(key)
            for key in ("TESTING", "PEERSLATE_ACCOUNT_EXPORT_ENABLED")
        }
        app_module.limiter.enabled = True
        app_module.limiter.reset()
        app_module.app.config.update(
            TESTING=True,
            # The flag stays OFF: the limiter runs before the view, so the
            # budget must hold even while the surface answers 404.
            PEERSLATE_ACCOUNT_EXPORT_ENABLED=False,
        )
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.limiter.reset()
        app_module.limiter.enabled = self._original_enabled
        app_module.app.config.update(**self._original_config)

    def test_a_breached_budget_answers_the_static_content_free_sentence(self):
        """Thirty per hour on the download proxy: the thirty-first request
        is refused with the app-wide static JSON sentence and a Retry-After.

        The refusal is deliberately keyed on the CALLER, not the job: no
        job exists here at all (the flag is off and there is no database),
        and the 429 must read exactly the same when one does. A refusal
        that varied by job existence would be an unauthenticated probe for
        other people's job keys.
        """
        first_key = "11111111-1111-4111-8111-111111111111"
        for _ in range(30):
            probed = self.client.get(f"/app/settings/export/{first_key}/download")
            self.assertEqual(probed.status_code, 404)

        refused = self.client.get(f"/app/settings/export/{first_key}/download")
        self.assertEqual(refused.status_code, 429)
        self.assertEqual(refused.get_json(), {"error": REFUSAL_SENTENCE})
        self.assertGreaterEqual(int(refused.headers["Retry-After"]), 1)

        # A different job key from the same caller: byte-identical refusal.
        other_key = "22222222-2222-4222-8222-222222222222"
        also_refused = self.client.get(
            f"/app/settings/export/{other_key}/download"
        )
        self.assertEqual(also_refused.status_code, 429)
        self.assertEqual(also_refused.get_data(), refused.get_data())

    def test_head_burns_the_download_budget_it_cannot_bypass_it(self):
        """A HEAD request is a full execution of the download proxy --
        Flask calls the same view and strips the body only afterwards --
        so it must consume the same budget as GET. The first frozen
        candidate exempted HEAD via methods=("GET",), measured in
        independent review as 100 HEADs = 100 full executions, zero 429s
        and zero budget burn. This test is the positive proof that can
        never pass with HEAD unbounded again."""
        key = "33333333-3333-4333-8333-333333333333"
        for _ in range(30):
            probed = self.client.head(f"/app/settings/export/{key}/download")
            self.assertEqual(probed.status_code, 404)

        # The 31st request is refused whichever verb carries it: the
        # verbs that do the work share one budget.
        refused_head = self.client.head(
            f"/app/settings/export/{key}/download"
        )
        self.assertEqual(refused_head.status_code, 429)

        refused_get = self.client.get(f"/app/settings/export/{key}/download")
        self.assertEqual(refused_get.status_code, 429)
        self.assertEqual(refused_get.get_json(), {"error": REFUSAL_SENTENCE})

    def test_the_post_budget_does_not_consume_the_get_budget(self):
        """The two verbs of the request route carry separate budgets: a
        caller who exhausts the POST budget can still LOAD the page (and
        vice versa), because a member locked out of reading their own
        request page by failed submissions would be a self-inflicted
        outage."""
        for _ in range(10):
            posted = self.client.post("/app/settings/export")
            self.assertEqual(posted.status_code, 404)

        refused_post = self.client.post("/app/settings/export")
        self.assertEqual(refused_post.status_code, 429)

        still_served_get = self.client.get("/app/settings/export")
        self.assertEqual(still_served_get.status_code, 404)

    def test_the_handler_itself_never_leaks_the_breached_limit(self):
        """The static sentence is app-wide policy: the exception's own
        description carries the limit string, which is operational detail
        an abusive caller should not be handed."""
        with app_module.app.test_request_context("/app/settings/export"):
            response = app_module.too_many_requests(None)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.get_json(), {"error": REFUSAL_SENTENCE})
        self.assertIn("Retry-After", response.headers)


if __name__ == "__main__":
    unittest.main()

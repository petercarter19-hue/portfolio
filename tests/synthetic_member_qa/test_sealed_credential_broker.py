from __future__ import annotations

import base64
import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from qa.synthetic_member import sealed_credential_broker as broker
from qa.synthetic_member.contracts import JOURNEY_BY_ID


NOW = datetime(2026, 8, 28, 18, 0, tzinfo=timezone.utc)
SUBJECT_A = "11111111-1111-1111-1111-111111111111"
SUBJECT_B = "22222222-2222-2222-2222-222222222222"
TENANT_ID = "33333333-3333-3333-3333-333333333333"
ISSUER = "synthetic-tenant.onmicrosoft.com"
AUTH_ISSUER = "https://synthetic-tenant.ciamlogin.com"
REQUIRED_CONDITIONALS = {
    "member_a_cannot_update_member_b": "neutral_denial_not_distinguishable",
    "member_b_cannot_update_member_a": "neutral_denial_not_distinguishable",
    "member_a_forged_reference_denied": "feature_surface_unavailable",
    "member_b_forged_reference_denied": "feature_surface_unavailable",
    "member_a_cannot_export_member_b": "feature_surface_unavailable",
    "member_b_cannot_export_member_a": "feature_surface_unavailable",
    "member_a_expired_session_safe": "session_expiry_not_controllable",
    "member_b_expired_session_safe": "session_expiry_not_controllable",
}


def fake_graph_token(*, tenant_id=TENANT_ID, audience="https://graph.microsoft.com"):
    payload = base64.urlsafe_b64encode(
        json.dumps({"tid": tenant_id, "aud": audience}).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"header.{payload}.signature"


def _forbid_live_outbound(*_args, **_kwargs):
    raise AssertionError("focused tests must use injected fake adapters")


def setUpModule():
    global _OUTBOUND_GUARDS
    _OUTBOUND_GUARDS = (
        patch.object(broker.subprocess, "run", side_effect=_forbid_live_outbound),
        patch.object(broker, "urlopen", side_effect=_forbid_live_outbound),
        patch.object(broker, "_start_playwright", side_effect=_forbid_live_outbound),
        patch.object(broker.retirement, "open_production_connection", side_effect=_forbid_live_outbound),
    )
    for guard in _OUTBOUND_GUARDS:
        guard.start()


def tearDownModule():
    for guard in reversed(_OUTBOUND_GUARDS):
        guard.stop()


def complete_outcome(*, conditional=None):
    observations = {
        journey_id: broker.JourneyObservation(
            status="pass", observed_outcome=journey.expected_outcome, note_code="none"
        )
        for journey_id, journey in JOURNEY_BY_ID.items()
    }
    for journey_id, note_code in (REQUIRED_CONDITIONALS if conditional is None else conditional).items():
        observations[journey_id] = broker.JourneyObservation(
            status="conditional", observed_outcome="limitation_recorded", note_code=note_code
        )
    return broker.BrowserOutcome(
        journey_outcomes=observations,
        created_item_counts={"member_a": 1, "member_b": 1},
        active_residue_counts={"member_a": 0, "member_b": 0},
        archived_residue_counts={"member_a": 0, "member_b": 0},
        clean_start_confirmed=True,
    )


class FakeBrowserSession:
    def __init__(self, events, *, outcome=None, cleanup=None, auth_issuer=AUTH_ISSUER):
        self.events = events
        self.outcome = outcome or complete_outcome()
        self.cleanup = cleanup or broker.BrowserCleanup(4, True)
        self.auth_issuer_value = auth_issuer
        self.destroy_calls = 0

    def auth_issuer(self):
        self.events.append("auth_routing")
        return broker.SealedValue(self.auth_issuer_value)

    def exercise_canonical_journeys(self, identities):
        self.events.append("journeys")
        self.aliases = tuple(identity.alias for identity in identities)
        return self.outcome

    def destroy_and_verify(self):
        self.destroy_calls += 1
        self.events.append("browser_cleanup")
        if isinstance(self.cleanup, Exception):
            raise self.cleanup
        return self.cleanup


class FakeBrowser:
    def __init__(self, events, *, outcome=None, cleanup=None, auth_issuer=AUTH_ISSUER):
        self.events = events
        self.session = FakeBrowserSession(
            events, outcome=outcome, cleanup=cleanup, auth_issuer=auth_issuer
        )

    def prepare_attended_session(self):
        self.events.extend(("browser_runtime_preflight", "signed_out_baseline"))
        return self.session


class FakeGraph:
    def __init__(self, events, *, fail_after=None):
        self.events = events
        self.fail_after = fail_after
        self.calls = 0

    def resolve_graph_issuer(self):
        self.events.append("graph_tenant_binding")
        if "signed_out_baseline" not in self.events:
            raise AssertionError("Graph binding ran before signed-out baseline")
        return broker.SealedValue(ISSUER)

    def create_customer(self, identity, *, graph_issuer):
        del graph_issuer
        self.calls += 1
        self.events.append(f"graph_post_{identity.alias}")
        if self.fail_after is not None and self.calls > self.fail_after:
            raise RuntimeError("fake graph failure")
        return (SUBJECT_A, SUBJECT_B)[self.calls - 1]


class FakeRetirement:
    def __init__(self, events, *, report=None):
        self.events = events
        self.report = report or {
            "result": "pass",
            "state": "retired",
            "counts": {"retired_members": 2},
        }
        self.calls = 0

    def retire(self, subjects, *, auth_issuer, cutoff):
        del auth_issuer, cutoff
        self.calls += 1
        if "browser_cleanup" not in self.events:
            raise AssertionError("retirement ran before browser cleanup")
        self.events.append("retirement")
        self.subjects = tuple(subject.reveal() for subject in subjects)
        return self.report


class SealedBrokerLifecycleTests(unittest.TestCase):
    def test_orders_runtime_baseline_before_graph_and_cleanup_before_retirement(self):
        events = []
        browser_adapter = FakeBrowser(events)
        retirement = FakeRetirement(events)
        report = broker.run_broker(
            run_id="qa-20260828-0001",
            cutoff=NOW,
            graph=FakeGraph(events),
            browser=browser_adapter,
            retirement_adapter=retirement,
            choice=lambda _alphabet: "z",
        )
        self.assertEqual(report["result"], "conditional")
        self.assertEqual(report["counts"], {
            "requested_identities": 2,
            "provisioned_identities": 2,
            "member_arrivals": 2,
            "account_switches": 2,
            "canonical_journeys": 38,
            "conditional_journeys": 8,
            "created_items": 2,
            "active_residue": 0,
            "destroyed_contexts": 4,
            "retired_members": 2,
        })
        self.assertEqual(browser_adapter.session.aliases, ("member_a", "member_b"))
        self.assertEqual(retirement.subjects, (SUBJECT_A, SUBJECT_B))
        self.assertLess(events.index("signed_out_baseline"), events.index("graph_post_member_a"))
        self.assertLess(events.index("browser_cleanup"), events.index("retirement"))

    def test_requires_the_exact_eight_conditional_journeys_before_retirement(self):
        required_items = list(REQUIRED_CONDITIONALS.items())
        missing_one = dict(REQUIRED_CONDITIONALS)
        missing_one.pop("member_b_expired_session_safe")
        wrong_code = dict(REQUIRED_CONDITIONALS)
        wrong_code["member_a_cannot_update_member_b"] = "feature_surface_unavailable"
        wrong_journey = dict(REQUIRED_CONDITIONALS)
        wrong_journey.pop("member_a_cannot_update_member_b")
        wrong_journey["member_a_cross_tab_signout_safe"] = (
            "neutral_denial_not_distinguishable"
        )
        ten_conditionals = dict(REQUIRED_CONDITIONALS)
        ten_conditionals.update(
            {
                "member_a_cross_tab_signout_safe": "cross_tab_signout_unreconciled",
                "member_b_cross_tab_signout_safe": "cross_tab_signout_unreconciled",
            }
        )
        scenarios = {
            "zero": {},
            "two": dict(required_items[:2]),
            "ten": ten_conditionals,
            "missing_one": missing_one,
            "extra_one": {
                **REQUIRED_CONDITIONALS,
                "member_a_cross_tab_signout_safe": "cross_tab_signout_unreconciled",
            },
            "wrong_code": wrong_code,
            "wrong_journey": wrong_journey,
        }
        for name, conditional in scenarios.items():
            with self.subTest(name=name):
                events = []
                retirement = FakeRetirement(events)
                with self.assertRaisesRegex(
                    broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
                ):
                    broker.run_broker(
                        run_id="qa-20260828-0001",
                        cutoff=NOW,
                        graph=FakeGraph(events),
                        browser=FakeBrowser(
                            events, outcome=complete_outcome(conditional=conditional)
                        ),
                        retirement_adapter=retirement,
                    )
                self.assertEqual(retirement.calls, 0)

        incomplete = complete_outcome()
        incomplete = broker.BrowserOutcome(
            journey_outcomes={
                journey_id: observation
                for journey_id, observation in incomplete.journey_outcomes.items()
                if journey_id != "repeat_run_clean_start"
            },
            created_item_counts={"member_a": 1, "member_b": 1},
            active_residue_counts={"member_a": 0, "member_b": 0},
            archived_residue_counts={"member_a": 0, "member_b": 0},
            clean_start_confirmed=False,
        )
        retirement = FakeRetirement(events)
        with self.assertRaisesRegex(broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"):
            broker.run_broker(
                run_id="qa-20260828-0001",
                cutoff=NOW,
                graph=FakeGraph(events),
                browser=FakeBrowser(events, outcome=incomplete),
                retirement_adapter=retirement,
            )
        self.assertEqual(retirement.calls, 0)

    def test_partial_graph_and_cleanup_failures_are_indeterminate_without_retirement(self):
        events = []
        retirement = FakeRetirement(events)
        with self.assertRaisesRegex(broker.BrokerIndeterminate, "graph_creation_indeterminate"):
            broker.run_broker(
                run_id="qa-20260828-0001",
                cutoff=NOW,
                graph=FakeGraph(events, fail_after=1),
                browser=FakeBrowser(events),
                retirement_adapter=retirement,
            )
        self.assertNotIn("journeys", events)
        self.assertEqual(retirement.calls, 0)

        events = []
        retirement = FakeRetirement(events)
        with self.assertRaisesRegex(broker.BrokerIndeterminate, "sealed_browser_cleanup_indeterminate"):
            broker.run_broker(
                run_id="qa-20260828-0001",
                cutoff=NOW,
                graph=FakeGraph(events),
                browser=FakeBrowser(events, cleanup=broker.BrokerIndeterminate("sealed_browser_cleanup_indeterminate")),
                retirement_adapter=retirement,
            )
        self.assertEqual(retirement.calls, 0)

    def test_main_has_no_secret_or_mailbox_prompt_and_only_allowlisted_output(self):
        events = []
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = broker.main(
                ["run", "--run-id", "qa-20260828-0001", "--created-after-utc", "2026-08-28T17:00:00Z", "--execute", "--confirm-exact-two-synthetic-members", "--confirm-no-production-proof", "--confirm-retirement-handoff"],
                clock=lambda: NOW,
                graph_factory=lambda: FakeGraph(events),
                browser_factory=lambda: FakeBrowser(events),
                retirement_factory=lambda: FakeRetirement(events),
            )
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(output.getvalue())), {"result", "state", "counts"})
        rendered = output.getvalue().lower()
        for forbidden in ("password", "mailbox", "issuer", "subject", "token", ISSUER, AUTH_ISSUER):
            self.assertNotIn(forbidden.lower(), rendered)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class MicrosoftGraphAdapterTests(unittest.TestCase):
    @staticmethod
    def _runner(calls):
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return type("Result", (), {"returncode": 0, "stdout": fake_graph_token()})()
        return runner

    @staticmethod
    def _organization(*, tenant_id=TENANT_ID, initial=True, issuer=ISSUER):
        return {"value": [{"id": tenant_id, "verifiedDomains": [{"name": issuer, "isInitial": initial}]}]}

    def test_derives_verified_issuer_and_excludes_it_from_azure_cli_child(self):
        child_calls, requests = [], []

        def opener(request, timeout):
            del timeout
            requests.append(request)
            return _Response(self._organization() if request.get_method() == "GET" else {"id": SUBJECT_A})

        adapter = broker.MicrosoftGraphAdapter(
            broker.AzureCliGraphTokenProvider(self._runner(child_calls), environment={"PATH": "C:\\Windows", "EXTERNAL_ISSUER": ISSUER}),
            opener,
        )
        issuer = adapter.resolve_graph_issuer()
        identity = broker._generate_identities(issuer, run_id="qa-20260828-0001")[0]
        self.assertEqual(adapter.create_customer(identity, graph_issuer=issuer), SUBJECT_A)
        self.assertEqual([request.get_method() for request in requests], ["GET", "GET", "POST"])
        self.assertEqual(child_calls[0][0], broker.AzureCliGraphTokenProvider.command_prefix)
        self.assertNotIn(ISSUER, child_calls[0][0])
        self.assertNotIn("EXTERNAL_ISSUER", child_calls[0][1]["env"])

    def test_tenant_or_issuer_mismatch_refuses_before_any_post(self):
        for payload in (self._organization(tenant_id="44444444-4444-4444-4444-444444444444"), self._organization(initial=False)):
            requests = []
            def opener(request, timeout):
                del timeout
                requests.append(request)
                return _Response(payload)
            adapter = broker.MicrosoftGraphAdapter(broker.AzureCliGraphTokenProvider(self._runner([])), opener)
            with self.assertRaisesRegex(broker.BrokerRefusal, "graph_tenant_issuer_mismatch"):
                adapter.resolve_graph_issuer()
            self.assertEqual([request.get_method() for request in requests], ["GET"])

    def test_auth_and_graph_tenant_mismatch_refuse_after_organization_read_before_identity_or_post(self):
        for graph_issuer, auth_issuer in (
            (ISSUER, "https://other-tenant.ciamlogin.com"),
            ("other-tenant.onmicrosoft.com", AUTH_ISSUER),
        ):
            with self.subTest(graph_issuer=graph_issuer, auth_issuer=auth_issuer):
                requests, generated = [], []

                def opener(request, timeout):
                    del timeout
                    requests.append(request)
                    return _Response(self._organization(issuer=graph_issuer))

                graph = broker.MicrosoftGraphAdapter(
                    broker.AzureCliGraphTokenProvider(self._runner([])), opener
                )
                with self.assertRaisesRegex(broker.BrokerRefusal, "auth_graph_tenant_mismatch"):
                    broker.run_broker(
                        run_id="qa-20260828-0001",
                        cutoff=NOW,
                        graph=graph,
                        browser=FakeBrowser([], auth_issuer=auth_issuer),
                        retirement_adapter=FakeRetirement([]),
                        choice=lambda alphabet: generated.append(alphabet) or "z",
                    )
                self.assertEqual([request.get_method() for request in requests], ["GET"])
                self.assertEqual(generated, [])


class FakeLocator:
    def __init__(self, count=0, href=None):
        self._count, self._href = count, href
    def count(self): return self._count
    def fill(self, _value): return None
    def click(self): return None
    def check(self): return None
    def get_attribute(self, _name): return self._href
    def input_value(self): return "fake-version"


class FakePage:
    def __init__(self, *, marker_present=False, preview=True):
        self.url = "https://peerslate.com/"
        self.marker_present = marker_present
        self.preview = preview
        self.visited = []
    def goto(self, url, *, wait_until):
        del wait_until
        self.visited.append(url)
        self.url = "https://synthetic-tenant.ciamlogin.com/authorize" if "/.auth/login/" in url else url
    def locator(self, selector):
        return FakeLocator(
            1
            if selector
            in {
                "input[name='expected_row_version']",
                broker.AUTHENTICATED_WORKSHOP_CONTROL,
            }
            or (selector == ".wk-status-banner--preview" and self.preview)
            else 0
        )
    def get_by_text(self, _text, *, exact):
        del exact
        return FakeLocator(1 if self.marker_present else 0)
    def get_by_role(self, _role, *, name):
        del name
        return FakeLocator(href="/app/workshop?item=opaque-item")
    def wait_for_url(self, _pattern, *, timeout):
        del _pattern, timeout
        self.url = "https://peerslate.com/app"
    def reload(self, *, wait_until): del wait_until
    def close(self): return None


class FakeContext:
    def __init__(self, fail_close=False): self.fail_close, self.closed = fail_close, False
    def new_page(self): return FakePage()
    def clear_cookies(self): return None
    def close(self):
        self.closed = True
        if self.fail_close: raise RuntimeError("fake cleanup failure")


class FakeBrowserProcess:
    def __init__(self, fail_context_close=False):
        self.fail_context_close, self.contexts, self.closed = fail_context_close, [], False
    def new_context(self, **kwargs):
        context = FakeContext(self.fail_context_close)
        context.options = kwargs
        self.contexts.append(context)
        return context
    def close(self): self.closed = True


class FakePlaywrightRuntime:
    def __init__(self, fail_context_close=False):
        self.process = FakeBrowserProcess(fail_context_close)
        self.chromium = self
        self.launch_options = None
        self.stopped = False
    def launch(self, **kwargs):
        self.launch_options = kwargs
        return self.process
    def stop(self): self.stopped = True


class PlaywrightBrowserAdapterTests(unittest.TestCase):
    def test_signed_out_preflight_selector_matches_the_rendered_preview_banner(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "partials" / "workshop" / "_preview_banner.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("wk-status-banner--preview", template)
        self.assertNotIn("wk-preview-banner", template)

    def test_fake_runtime_creates_four_no_capture_contexts_and_scrubs_child_environment(self):
        runtime = FakePlaywrightRuntime()
        with tempfile.TemporaryDirectory() as root:
            adapter = broker.PlaywrightBrowserAdapter(
                environment={"SystemRoot": "C:\\Windows", "PEERSLATE_AUTH_ISSUER": AUTH_ISSUER, "EXTERNAL_ISSUER": ISSUER, "AUTHORIZATION_REF": "opaque"},
                workspace_root=root,
                playwright_factory=lambda: runtime,
            )
            session = adapter.prepare_attended_session()
            self.assertEqual(session.auth_issuer().reveal(), AUTH_ISSUER)
            self.assertEqual(len(runtime.process.contexts), 4)
            self.assertEqual(set(runtime.launch_options), {"headless", "downloads_path", "env"})
            self.assertFalse(runtime.launch_options["headless"])
            for forbidden in ("PEERSLATE_AUTH_ISSUER", "EXTERNAL_ISSUER", "AUTHORIZATION_REF", "PATH"):
                self.assertNotIn(forbidden, runtime.launch_options["env"])
            self.assertTrue(all(context.options == {"accept_downloads": False} for context in runtime.process.contexts))
            self.assertEqual(session.destroy_and_verify(), broker.BrowserCleanup(4, True))
            self.assertTrue(runtime.process.closed and runtime.stopped)
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_cleanup_or_capture_environment_failure_never_returns_success(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = FakePlaywrightRuntime(fail_context_close=True)
            session = broker.PlaywrightBrowserAdapter(environment={"SystemRoot": "C:\\Windows"}, workspace_root=root, playwright_factory=lambda: runtime).prepare_attended_session()
            with self.assertRaisesRegex(broker.BrokerIndeterminate, "sealed_browser_cleanup_indeterminate"):
                session.destroy_and_verify()
            debug_adapter = broker.PlaywrightBrowserAdapter(environment={"PWDEBUG": "1"}, workspace_root=root, playwright_factory=lambda: (_ for _ in ()).throw(AssertionError("must not start")))
            with self.assertRaisesRegex(broker.BrokerRefusal, "sealed_browser_environment_refused"):
                debug_adapter.prepare_attended_session()

    def test_item_lifecycle_selects_the_archive_view_before_restore(self):
        page = FakePage(marker_present=True, preview=False)
        session = broker._PlaywrightAttendedSession(
            adapter=broker.PlaywrightBrowserAdapter(playwright_factory=lambda: None),
            contexts={},
            browser=None,
            playwright=None,
            workspace=Path(tempfile.gettempdir()),
            auth_issuer=broker.SealedValue(AUTH_ISSUER),
            signed_out_page=page,
            preflight_outcomes={
                "clean_client_a_start": broker._pass_observation("clean_client_a_start"),
                "clean_client_b_start": broker._pass_observation("clean_client_b_start"),
                "clean_signed_out_control_start": broker._pass_observation("clean_signed_out_control_start"),
                "signed_out_private_baseline": broker._pass_observation("signed_out_private_baseline"),
            },
        )
        session._archive_and_restore_item(
            page,
            broker._SealedItemHandle(
                key=broker.SealedValue("opaque-item"), version=broker.SealedValue("fake-version")
            ),
            "safe-marker",
        )
        self.assertEqual(page.visited, [
            "https://peerslate.com/app/workshop?item=opaque-item",
            "https://peerslate.com/app/workshop?item=opaque-item&status=archived",
            "https://peerslate.com/app/workshop?item=opaque-item",
        ])


class DirectRetirementAdapterTests(unittest.TestCase):
    def test_uses_the_unchanged_programmatic_retirement_core(self):
        class Connection:
            def __init__(self): self.commits = self.rollbacks = self.closes = 0
            def commit(self): self.commits += 1
            def rollback(self): self.rollbacks += 1
            def close(self): self.closes += 1
        connection = Connection()
        with patch.object(broker.retirement, "SqlRetirementStore", return_value=object()), patch.object(
            broker.retirement, "execute", return_value={"result": "pass", "state": "retired", "counts": {"eligible_members": 2}}
        ) as execute:
            report = broker.DirectRetirementAdapter(lambda: connection).retire(
                [broker.SealedValue(SUBJECT_A), broker.SealedValue(SUBJECT_B)], auth_issuer=broker.SealedValue(AUTH_ISSUER), cutoff=NOW
            )
        self.assertEqual(report["counts"], {"retired_members": 2})
        self.assertEqual(connection.commits, 1)
        self.assertEqual(execute.call_args.kwargs["subjects"], [SUBJECT_A, SUBJECT_B])


if __name__ == "__main__":
    unittest.main()

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
from uuid import UUID

from qa.synthetic_member import sealed_credential_broker as broker


NOW = datetime(2026, 8, 28, 18, 0, tzinfo=timezone.utc)
SUBJECT_A = "11111111-1111-1111-1111-111111111111"
SUBJECT_B = "22222222-2222-2222-2222-222222222222"
TENANT_ID = "33333333-3333-3333-3333-333333333333"


def fake_graph_token(*, tenant_id=TENANT_ID, audience="https://graph.microsoft.com"):
    encoded = base64.urlsafe_b64encode(
        json.dumps({"tid": tenant_id, "aud": audience}).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"header.{encoded}.signature"


def _forbid_live_outbound(*_args, **_kwargs):
    raise AssertionError("focused tests must use injected fake adapters")


def setUpModule():
    global _OUTBOUND_GUARDS
    _OUTBOUND_GUARDS = (
        patch.object(broker.subprocess, "run", side_effect=_forbid_live_outbound),
        patch.object(broker, "urlopen", side_effect=_forbid_live_outbound),
        patch.object(broker, "_start_playwright", side_effect=_forbid_live_outbound),
        patch.object(
            broker.retirement,
            "open_production_connection",
            side_effect=_forbid_live_outbound,
        ),
    )
    for guard in _OUTBOUND_GUARDS:
        guard.start()


def tearDownModule():
    for guard in reversed(_OUTBOUND_GUARDS):
        guard.stop()


class FakeGraph:
    def __init__(self, *, fail_after: int | None = None):
        self.fail_after = fail_after
        self.calls = 0
        self.identities = []

    def create_customer(self, identity, *, graph_issuer):
        del graph_issuer
        self.calls += 1
        self.identities.append(identity)
        if self.fail_after is not None and self.calls > self.fail_after:
            raise RuntimeError("private graph failure")
        return (SUBJECT_A, SUBJECT_B)[self.calls - 1]


class FakeBrowser:
    def __init__(self, outcome=None):
        self.outcome = outcome or broker.BrowserOutcome(2, 2, 3)
        self.calls = 0
        self.preflight_calls = 0

    def preflight(self):
        self.preflight_calls += 1

    def exercise_sign_in_and_switch(self, identities, *, auth_issuer):
        del auth_issuer
        self.calls += 1
        self.aliases = tuple(identity.alias for identity in identities)
        return self.outcome


class FakeRetirement:
    def __init__(self, report=None):
        self.report = report or {
            "result": "pass",
            "state": "retired",
            "counts": {"retired_members": 2},
        }
        self.calls = 0

    def retire(self, subjects, *, auth_issuer, cutoff):
        del auth_issuer, cutoff
        self.calls += 1
        self.subjects = tuple(subject.reveal() for subject in subjects)
        return self.report


def sealed_inputs():
    return {
        "run_id": "qa-20260828-0001",
        "cutoff": NOW,
        "graph_issuer": broker.SealedValue("example.onmicrosoft.com"),
        "mailbox": broker.SealedValue("qa-inbox@example.com"),
        "auth_issuer": broker.SealedValue("https://example.ciamlogin.com/example/v2.0"),
    }


class SealedBrokerTests(unittest.TestCase):
    def test_run_transfers_only_opaque_subjects_and_returns_structural_report(self):
        graph = FakeGraph()
        browser = FakeBrowser()
        retirement = FakeRetirement()
        values = sealed_inputs()

        report = broker.run_broker(
            **values,
            graph=graph,
            browser=browser,
            retirement_adapter=retirement,
            choice=lambda _alphabet: "z",
        )

        self.assertEqual(
            report,
            {
                "result": "pass",
                "state": "retired_pending_external_deletion",
                "counts": {
                    "requested_identities": 2,
                    "provisioned_identities": 2,
                    "member_arrivals": 2,
                    "account_switches": 2,
                    "retired_members": 2,
                },
            },
        )
        self.assertEqual(graph.calls, 2)
        self.assertEqual(browser.calls, 1)
        self.assertEqual(browser.aliases, broker.ALLOWED_ALIASES)
        self.assertEqual(retirement.calls, 1)
        self.assertEqual(retirement.subjects, (SUBJECT_A, SUBJECT_B))
        for identity in graph.identities:
            self.assertEqual(repr(identity), f"SealedIdentity(alias={identity.alias!r}, material=<sealed>)")
            with self.assertRaisesRegex(broker.BrokerRefusal, "sealed_value_cleared"):
                identity.password.reveal()

    def test_second_graph_failure_is_indeterminate_and_never_retries_or_retires(self):
        graph = FakeGraph(fail_after=1)
        browser = FakeBrowser()
        retirement = FakeRetirement()

        with self.assertRaisesRegex(broker.BrokerIndeterminate, "graph_creation_indeterminate"):
            broker.run_broker(
                **sealed_inputs(),
                graph=graph,
                browser=browser,
                retirement_adapter=retirement,
            )

        self.assertEqual(graph.calls, 2)
        self.assertEqual(browser.calls, 0)
        self.assertEqual(retirement.calls, 0)

    def test_refusal_after_first_graph_creation_is_indeterminate(self):
        class RefusingSecondGraph(FakeGraph):
            def create_customer(self, identity, *, graph_issuer):
                self.calls += 1
                self.identities.append(identity)
                del graph_issuer
                if self.calls == 2:
                    raise broker.BrokerRefusal("graph_authorization_unavailable")
                return SUBJECT_A

        graph = RefusingSecondGraph()
        with self.assertRaisesRegex(broker.BrokerIndeterminate, "graph_creation_indeterminate"):
            broker.run_broker(
                **sealed_inputs(),
                graph=graph,
                browser=FakeBrowser(),
                retirement_adapter=FakeRetirement(),
            )
        self.assertEqual(graph.calls, 2)

    def test_wrong_browser_result_is_indeterminate_after_graph_mutation(self):
        graph = FakeGraph()
        browser = FakeBrowser(broker.BrowserOutcome(2, 1, 3))
        retirement = FakeRetirement()

        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
        ):
            broker.run_broker(
                **sealed_inputs(),
                graph=graph,
                browser=browser,
                retirement_adapter=retirement,
            )

        self.assertEqual(graph.calls, 2)
        self.assertEqual(retirement.calls, 0)

    def test_graph_subjects_must_be_distinct(self):
        class DuplicateGraph(FakeGraph):
            def create_customer(self, identity, *, graph_issuer):
                del identity, graph_issuer
                self.calls += 1
                return SUBJECT_A

        with self.assertRaisesRegex(broker.BrokerIndeterminate, "graph_creation_indeterminate"):
            broker.run_broker(
                **sealed_inputs(),
                graph=DuplicateGraph(),
                browser=FakeBrowser(),
                retirement_adapter=FakeRetirement(),
            )

    def test_cli_refuses_before_prompt_or_adapter_creation_without_confirmations(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = broker.main(
                [
                    "run",
                    "--run-id",
                    "qa-20260828-0001",
                    "--created-after-utc",
                    "2026-08-28T17:59:00Z",
                ],
                secret_reader=lambda _prompt: self.fail("must not prompt"),
                graph_factory=lambda: self.fail("must not create graph"),
                browser_factory=lambda: self.fail("must not create browser"),
                retirement_factory=lambda: self.fail("must not create retirement"),
                clock=lambda: NOW,
            )
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(output.getvalue()),
            {"result": "refused", "reason_code": "sealed_broker_confirmations_required"},
        )

    def test_cli_uses_only_closed_output_for_a_fake_run(self):
        graph = FakeGraph()
        browser = FakeBrowser()
        retirement = FakeRetirement()
        answers = iter(
            [
                "approval:valid-123",
                "https://example.ciamlogin.com/example/v2.0",
                "example.onmicrosoft.com",
                "qa-inbox@example.com",
            ]
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = broker.main(
                [
                    "run",
                    "--run-id",
                    "qa-20260828-0001",
                    "--created-after-utc",
                    "2026-08-28T17:59:00Z",
                    "--execute",
                    "--confirm-exact-two-synthetic-members",
                    "--confirm-no-production-proof",
                    "--confirm-retirement-handoff",
                ],
                secret_reader=lambda _prompt: next(answers),
                stdin_isatty=lambda: True,
                clock=lambda: NOW,
                graph_factory=lambda: graph,
                browser_factory=lambda: browser,
                retirement_factory=lambda: retirement,
            )
        self.assertEqual(code, 0)
        rendered = output.getvalue()
        for forbidden in (
            "example.onmicrosoft.com",
            "qa-inbox@example.com",
            SUBJECT_A,
            SUBJECT_B,
            "approval:valid-123",
            "https://example.ciamlogin.com/example/v2.0",
        ):
            self.assertNotIn(forbidden, rendered)
        self.assertEqual(json.loads(rendered)["state"], "retired_pending_external_deletion")

    def test_plan_requires_no_identity_or_graph_runtime(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = broker.main(["plan"])
        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads(output.getvalue()),
            {
                "result": "planned",
                "counts": {"customer_identities": 2, "switches": 2},
                "external_deletion": "withheld",
            },
        )


class MicrosoftGraphAdapterTests(unittest.TestCase):
    def test_create_customer_sends_only_the_fixed_graph_request_and_redacts_material(self):
        class TokenProvider:
            def acquire(self):
                return broker.SealedValue(fake_graph_token())

        class Response:
            def read(self):
                return json.dumps({"id": SUBJECT_A}).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        observed = []

        def opener(request, *, timeout):
            observed.append(
                {
                    "url": request.full_url,
                    "timeout": timeout,
                    "method": request.get_method(),
                    "body": request.data.decode("utf-8") if request.data else None,
                    "authorization": request.get_header("Authorization"),
                }
            )
            if request.get_method() == "GET":
                response = Response()
                response.read = lambda: json.dumps(
                    {
                        "value": [
                            {
                                "id": TENANT_ID,
                                "verifiedDomains": [{"name": "example.onmicrosoft.com"}],
                            }
                        ]
                    }
                ).encode("utf-8")
                return response
            return Response()

        identity = broker.SealedIdentity(
            alias="member_a",
            login_identifier=broker.SealedValue("qa-inbox+run@example.com"),
            password=broker.SealedValue("do-not-print-this-password"),
            mail_nickname=broker.SealedValue("psqa-run-member-a"),
        )
        subject = broker.MicrosoftGraphAdapter(TokenProvider(), opener).create_customer(
            identity, graph_issuer=broker.SealedValue("example.onmicrosoft.com")
        )

        self.assertEqual(subject, str(UUID(SUBJECT_A)))
        self.assertEqual(observed[0]["url"], broker.ALLOWED_GRAPH_ORGANIZATION_ENDPOINT)
        self.assertEqual(observed[0]["method"], "GET")
        self.assertEqual(observed[1]["url"], broker.ALLOWED_GRAPH_ENDPOINT)
        self.assertEqual(observed[1]["timeout"], 60)
        self.assertEqual(observed[1]["method"], "POST")
        self.assertIn('"signInType":"emailAddress"', observed[1]["body"])
        self.assertIn('"passwordPolicies":"DisablePasswordExpiration"', observed[1]["body"])
        self.assertEqual(observed[1]["authorization"], f"Bearer {fake_graph_token()}")
        self.assertNotIn("do-not-print-this-password", repr(identity))

    def test_tenant_mismatch_refuses_before_any_customer_post(self):
        class TokenProvider:
            def acquire(self):
                return broker.SealedValue(fake_graph_token())

        methods = []

        class Response:
            def read(self):
                return json.dumps(
                    {
                        "value": [
                            {
                                "id": TENANT_ID,
                                "verifiedDomains": [{"name": "other.onmicrosoft.com"}],
                            }
                        ]
                    }
                ).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        def opener(request, *, timeout):
            del timeout
            methods.append(request.get_method())
            return Response()

        identity = broker.SealedIdentity(
            alias="member_a",
            login_identifier=broker.SealedValue("qa-inbox+run@example.com"),
            password=broker.SealedValue("do-not-print-this-password"),
            mail_nickname=broker.SealedValue("psqa-run-member-a"),
        )
        with self.assertRaisesRegex(broker.BrokerRefusal, "graph_tenant_issuer_mismatch"):
            broker.MicrosoftGraphAdapter(TokenProvider(), opener).create_customer(
                identity, graph_issuer=broker.SealedValue("example.onmicrosoft.com")
            )
        self.assertEqual(methods, ["GET"])

    def test_cli_token_request_excludes_issuer_from_child_arguments_and_environment(self):
        observed = {}

        class Result:
            returncode = 0
            stdout = fake_graph_token()

        def runner(command, **kwargs):
            observed["command"] = command
            observed["kwargs"] = kwargs
            return Result()

        token = broker.AzureCliGraphTokenProvider(
            runner,
            environment={
                "SystemRoot": "C:\\Windows",
                "PEERSLATE_AUTH_ISSUER": "https://must-not-reach-child.example",
                "AUTHORIZATION_REF": "must-not-reach-child",
            },
        ).acquire()

        self.assertEqual(token.reveal(), fake_graph_token())
        self.assertEqual(observed["command"], broker.AzureCliGraphTokenProvider.command_prefix)
        self.assertNotIn("example.onmicrosoft.com", observed["command"])
        self.assertEqual(observed["kwargs"]["env"], {"SystemRoot": "C:\\Windows"})
        self.assertTrue(observed["kwargs"]["capture_output"])


class FakeOnlyOutboundGuardTests(unittest.TestCase):
    def test_default_subprocess_backend_is_globally_guarded(self):
        with self.assertRaisesRegex(AssertionError, "injected fake adapters"):
            broker.AzureCliGraphTokenProvider().acquire()


class FakeLocator:
    def fill(self, _value):
        return None

    def click(self):
        return None


class FakePage:
    def __init__(self):
        self.url = ""

    def goto(self, url, *, wait_until):
        del wait_until
        if "/.auth/login/aad" in url:
            self.url = "https://example.ciamlogin.com/example/v2.0"
        else:
            self.url = url

    def locator(self, _selector):
        return FakeLocator()

    def wait_for_url(self, _pattern, *, timeout):
        del timeout
        self.url = "https://peerslate.com/app"


class FakeContext:
    def __init__(self, *, fail_close=False):
        self.fail_close = fail_close
        self.closed = False

    def new_page(self):
        return FakePage()

    def close(self):
        if self.fail_close:
            raise RuntimeError("fake context close failure")
        self.closed = True


class FakeBrowserProcess:
    def __init__(self, *, fail_context_close=False):
        self.fail_context_close = fail_context_close
        self.context_options = []
        self.contexts = []
        self.closed = False

    def new_context(self, **kwargs):
        self.context_options.append(kwargs)
        context = FakeContext(fail_close=self.fail_context_close)
        self.contexts.append(context)
        return context

    def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self, browser):
        self.browser = browser
        self.launch_options = None

    def launch(self, **kwargs):
        self.launch_options = kwargs
        return self.browser


class FakePlaywrightRuntime:
    def __init__(self, *, fail_context_close=False):
        self.browser = FakeBrowserProcess(fail_context_close=fail_context_close)
        self.chromium = FakeChromium(self.browser)
        self.stopped = False

    def stop(self):
        self.stopped = True


class PlaywrightBrowserAdapterTests(unittest.TestCase):
    @staticmethod
    def _identities():
        return broker._generate_identities(
            broker.SealedValue("qa-inbox@example.com"),
            run_id="qa-20260828-0001",
            choice=lambda _alphabet: "z",
        )

    def test_nonpersistent_fake_contexts_use_only_a_disposable_sanitized_workspace(self):
        runtime = FakePlaywrightRuntime()
        with tempfile.TemporaryDirectory() as temp_root:
            adapter = broker.PlaywrightBrowserAdapter(
                environment={
                    "SystemRoot": "C:\\Windows",
                    "PEERSLATE_AUTH_ISSUER": "https://must-not-reach-child.example",
                    "AUTHORIZATION_REF": "must-not-reach-child",
                },
                workspace_root=temp_root,
                playwright_factory=lambda: runtime,
            )
            outcome = adapter.exercise_sign_in_and_switch(
                self._identities(),
                auth_issuer=broker.SealedValue("https://example.ciamlogin.com/example/v2.0"),
            )

            self.assertEqual(outcome, broker.BrowserOutcome(2, 2, 3))
            self.assertEqual(
                set(runtime.chromium.launch_options),
                {"headless", "downloads_path", "env"},
            )
            self.assertFalse(runtime.chromium.launch_options["headless"])
            child_environment = runtime.chromium.launch_options["env"]
            self.assertNotIn("PEERSLATE_AUTH_ISSUER", child_environment)
            self.assertNotIn("AUTHORIZATION_REF", child_environment)
            self.assertNotIn("PATH", child_environment)
            self.assertEqual(child_environment["SystemRoot"], "C:\\Windows")
            self.assertTrue(
                Path(runtime.chromium.launch_options["downloads_path"]).is_relative_to(
                    Path(temp_root)
                )
            )
            self.assertEqual(runtime.browser.context_options, [{"accept_downloads": False}] * 3)
            self.assertTrue(runtime.browser.closed)
            self.assertTrue(runtime.stopped)
            self.assertTrue(all(context.closed for context in runtime.browser.contexts))
            self.assertEqual(list(Path(temp_root).iterdir()), [])

    def test_context_or_workspace_cleanup_failure_is_indeterminate_and_never_passes(self):
        runtime = FakePlaywrightRuntime(fail_context_close=True)
        with tempfile.TemporaryDirectory() as temp_root:
            adapter = broker.PlaywrightBrowserAdapter(
                environment={"SystemRoot": "C:\\Windows"},
                workspace_root=temp_root,
                playwright_factory=lambda: runtime,
            )
            with self.assertRaisesRegex(
                broker.BrokerIndeterminate, "sealed_browser_cleanup_indeterminate"
            ):
                adapter.exercise_sign_in_and_switch(
                    self._identities(),
                    auth_issuer=broker.SealedValue("https://example.ciamlogin.com/example/v2.0"),
                )
            self.assertEqual(list(Path(temp_root).iterdir()), [])

    def test_capture_debug_environment_and_prior_workspace_residue_refuse_before_start(self):
        with tempfile.TemporaryDirectory() as temp_root:
            start_calls = []
            debug_adapter = broker.PlaywrightBrowserAdapter(
                environment={"PWDEBUG": "1"},
                workspace_root=temp_root,
                playwright_factory=lambda: start_calls.append(True),
            )
            with self.assertRaisesRegex(broker.BrokerRefusal, "sealed_browser_environment_refused"):
                debug_adapter.preflight()
            self.assertEqual(start_calls, [])

            residue = Path(temp_root) / f"{broker.BROWSER_TEMP_PREFIX}interrupted"
            residue.mkdir()
            residue_adapter = broker.PlaywrightBrowserAdapter(
                environment={},
                workspace_root=temp_root,
                playwright_factory=lambda: start_calls.append(True),
            )
            with self.assertRaisesRegex(broker.BrokerRefusal, "sealed_browser_workspace_residue"):
                residue_adapter.preflight()
            self.assertEqual(start_calls, [])


class DirectRetirementAdapterTests(unittest.TestCase):
    def test_adapter_uses_existing_programmatic_retirement_core_without_subject_output(self):
        class Connection:
            def __init__(self):
                self.commits = 0
                self.rollbacks = 0
                self.closes = 0

            def commit(self):
                self.commits += 1

            def rollback(self):
                self.rollbacks += 1

            def close(self):
                self.closes += 1

        connection = Connection()
        with patch.object(broker.retirement, "SqlRetirementStore", return_value=object()) as store, patch.object(
            broker.retirement,
            "execute",
            return_value={
                "result": "pass",
                "state": "retired",
                "counts": {"eligible_members": 2},
            },
        ) as execute:
            report = broker.DirectRetirementAdapter(lambda: connection).retire(
                [broker.SealedValue(SUBJECT_A), broker.SealedValue(SUBJECT_B)],
                auth_issuer=broker.SealedValue("https://example.ciamlogin.com/example/v2.0"),
                cutoff=NOW,
            )

        self.assertEqual(report, {"result": "pass", "state": "retired", "counts": {"retired_members": 2}})
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertEqual(connection.closes, 1)
        store.assert_called_once_with(connection)
        self.assertEqual(execute.call_args.kwargs["subjects"], [SUBJECT_A, SUBJECT_B])

    def test_bad_core_report_rolls_back_before_any_commit(self):
        class Connection:
            def __init__(self):
                self.commits = 0
                self.rollbacks = 0

            def commit(self):
                self.commits += 1

            def rollback(self):
                self.rollbacks += 1

            def close(self):
                pass

        connection = Connection()
        with patch.object(broker.retirement, "SqlRetirementStore", return_value=object()), patch.object(
            broker.retirement,
            "execute",
            return_value={"result": "pass", "state": "retired", "counts": {"eligible_members": 1}},
        ):
            with self.assertRaisesRegex(broker.BrokerIndeterminate, "retirement_indeterminate"):
                broker.DirectRetirementAdapter(lambda: connection).retire(
                    [broker.SealedValue(SUBJECT_A), broker.SealedValue(SUBJECT_B)],
                    auth_issuer=broker.SealedValue("https://example.ciamlogin.com/example/v2.0"),
                    cutoff=NOW,
                )

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)


if __name__ == "__main__":
    unittest.main()

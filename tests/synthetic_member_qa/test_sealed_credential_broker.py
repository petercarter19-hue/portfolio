from __future__ import annotations

import base64
import contextlib
import io
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlparse

from qa.synthetic_member import sealed_credential_broker as broker
from qa.synthetic_member.sealed_credential_broker import child_worker
from qa.synthetic_member.contracts import JOURNEY_BY_ID


NOW = datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc)
SUBJECT_A = "11111111-1111-1111-1111-111111111111"
SUBJECT_B = "22222222-2222-2222-2222-222222222222"
TENANT_ID = broker.GRAPH_PUBLIC_CLIENT_TENANT_ID
OPERATOR_ID = "44444444-4444-4444-4444-444444444444"
GRAPH_ISSUER = "synthetic-tenant.onmicrosoft.com"
DISCOVERY_ISSUER = f"https://synthetic-tenant.ciamlogin.com/{TENANT_ID}/v2.0"
OIDC_ISSUER = f"https://{TENANT_ID}.ciamlogin.com/{TENANT_ID}/v2.0"
AUTHORIZATION_ORIGIN = "https://synthetic-tenant.ciamlogin.com"
AUTHORIZATION_ENDPOINT = (
    f"{AUTHORIZATION_ORIGIN}/{TENANT_ID}/oauth2/v2.0/authorize"
)


class FakeAzureCliLayout:
    """Filesystem-only stand-in for the installed Windows Azure CLI layout."""

    def __init__(
        self,
        root: Path,
        *,
        runtime_name: str = "CLI2",
        launcher_directory: str = "wbin",
        include_python: bool = True,
    ):
        self.runtime_root = (root / runtime_name).resolve()
        self.launcher = self.runtime_root / launcher_directory / "az.cmd"
        self.launcher.parent.mkdir(parents=True)
        self.launcher.write_text("fake", encoding="utf-8")
        self.python_executable = self.runtime_root / "python.exe"
        if include_python:
            self.python_executable.write_text("fake", encoding="utf-8")

    def discover(self, command: str) -> str:
        if command != "az":
            raise AssertionError("unexpected Azure CLI discovery")
        return str(self.launcher)

    @property
    def command_prefix(self) -> tuple[str, ...]:
        return (
            str(self.python_executable.resolve()),
            "-I",
            "-B",
            "-m",
            "azure.cli",
        )


class FakeHomebrewAzureCliLayout:
    """Filesystem-only stand-in for the Darwin arm64 Homebrew CLI layout."""

    def __init__(
        self,
        root: Path,
        *,
        cli_version: str = "2.87.0",
        python_series: str = "3.13",
        python_formula_version: str = "3.13.14",
        launcher_contents: bytes | None = None,
        python_prefix: bytes = broker.DARWIN_ARM64_MACHO_PREFIX,
    ):
        self.prefix = (root / "homebrew").resolve()
        self.runtime_root = (
            self.prefix / "Cellar" / "azure-cli" / cli_version
        )
        self.launcher = self.runtime_root / "bin" / "az"
        self.launcher.parent.mkdir(parents=True)
        self.python_executable = self.runtime_root / "libexec" / "bin" / "python"
        self.python_executable.parent.mkdir(parents=True)

        python_formula_root = (
            self.prefix
            / "Cellar"
            / f"python@{python_series}"
            / python_formula_version
        )
        self.resolved_python = (
            python_formula_root
            / "Frameworks"
            / "Python.framework"
            / "Versions"
            / python_series
            / "bin"
            / f"python{python_series}"
        )
        self.resolved_python.parent.mkdir(parents=True)
        self.resolved_python.write_bytes(python_prefix + b"fake")
        self.resolved_python.chmod(0o755)

        formula_bin = python_formula_root / "bin"
        formula_bin.mkdir()
        (formula_bin / f"python{python_series}").symlink_to(
            Path("..")
            / "Frameworks"
            / "Python.framework"
            / "Versions"
            / python_series
            / "bin"
            / f"python{python_series}"
        )
        opt_root = self.prefix / "opt"
        opt_root.mkdir()
        (opt_root / f"python@{python_series}").symlink_to(
            Path("..")
            / "Cellar"
            / f"python@{python_series}"
            / python_formula_version
        )
        versioned_python = self.python_executable.with_name(
            f"python{python_series}"
        )
        versioned_python.symlink_to(
            f"../../../../../opt/python@{python_series}/bin/python{python_series}"
        )
        self.python_executable.symlink_to(f"python{python_series}")

        expected_launcher = (
            "#!/usr/bin/env bash\n"
            f'AZ_INSTALLER=HOMEBREW {self.python_executable} '
            '-Im azure.cli "$@"\n'
        ).encode("ascii")
        self.launcher.write_bytes(
            expected_launcher if launcher_contents is None else launcher_contents
        )
        self.launcher.chmod(0o555)
        self.discovery_link = self.prefix / "bin" / "az"
        self.discovery_link.parent.mkdir()
        self.discovery_link.symlink_to(
            Path("..") / "Cellar" / "azure-cli" / cli_version / "bin" / "az"
        )

    def discover(self, command: str) -> str:
        if command != "az":
            raise AssertionError("unexpected Azure CLI discovery")
        return str(self.discovery_link)

    @property
    def command_prefix(self) -> tuple[str, ...]:
        return (
            str(self.python_executable),
            "-I",
            "-B",
            "-m",
            "azure.cli",
        )


def _forbid_live(*_args, **_kwargs):
    raise AssertionError("focused broker tests must use fake-only dependencies")


def setUpModule():
    global _OUTBOUND_GUARDS
    _OUTBOUND_GUARDS = (
        patch.object(broker.subprocess, "run", side_effect=_forbid_live),
        patch.object(broker.subprocess, "Popen", side_effect=_forbid_live),
        patch.object(broker, "_open_without_redirect", side_effect=_forbid_live),
        patch.object(
            broker.retirement,
            "open_production_connection",
            side_effect=_forbid_live,
        ),
    )
    for guard in _OUTBOUND_GUARDS:
        guard.start()


def tearDownModule():
    for guard in reversed(_OUTBOUND_GUARDS):
        guard.stop()


def authority_binding() -> broker.AuthorityBinding:
    return broker.AuthorityBinding(
        oidc_issuer=broker.SealedValue(OIDC_ISSUER),
        authorization_origin=broker.SealedValue(AUTHORIZATION_ORIGIN),
        tenant_id=broker.SealedValue(TENANT_ID),
        tenant_label=broker.SealedValue("synthetic-tenant"),
    )


def complete_outcome(*, conditionals=None, active_residue=0) -> broker.BrowserOutcome:
    observations = {
        journey_id: broker.JourneyObservation(
            status="pass",
            observed_outcome=journey.expected_outcome,
            note_code="none",
        )
        for journey_id, journey in JOURNEY_BY_ID.items()
    }
    mapping = (
        broker.REQUIRED_CONDITIONAL_OUTCOMES
        if conditionals is None
        else conditionals
    )
    for journey_id, note_code in mapping.items():
        observations[journey_id] = broker.JourneyObservation(
            status="conditional",
            observed_outcome="limitation_recorded",
            note_code=note_code,
        )
    return broker.BrowserOutcome(
        journey_outcomes=observations,
        created_item_counts={"member_a": 1, "member_b": 1},
        edit_counts={"member_a": 2, "member_b": 2},
        retained_version_counts={"member_a": 3, "member_b": 3},
        retained_source_proof_counts={"member_a": 3, "member_b": 3},
        downstream_disclosure_counts={"member_a": 1, "member_b": 1},
        active_residue_counts={"member_a": active_residue, "member_b": 0},
        archived_residue_counts={"member_a": 0, "member_b": 0},
        clean_start_confirmed=True,
    )


class FakeAuthority:
    def __init__(self, events):
        self.events = events

    def resolve(self):
        self.events.append("authority")
        return authority_binding()


class FakeSession:
    def __init__(self, events, *, outcome=None, cleanup=None, preflight=None):
        self.events = events
        self.outcome = outcome or complete_outcome()
        self.cleanup = cleanup or broker.BrowserCleanup(4, True)
        self.preflight = preflight or broker.BrowserPreflight(True, True, True, 4, True)
        self.cleaned = False

    def pre_graph_proof(self):
        self.events.append("browser_preflight_proof")
        return self.preflight

    def exercise_canonical_journeys(self, identities):
        self.events.append("journeys")
        self.aliases = tuple(identity.alias for identity in identities)
        return self.outcome

    def destroy_and_verify(self):
        if not self.cleaned:
            self.events.append("browser_cleanup")
            self.cleaned = True
        if isinstance(self.cleanup, Exception):
            raise self.cleanup
        return self.cleanup


class FakeBrowser:
    def __init__(self, events, **session_options):
        self.events = events
        self.session = FakeSession(events, **session_options)

    def prepare_attended_session(self, authority):
        self.events.append("browser_prepare")
        if authority.authorization_origin.reveal() != AUTHORIZATION_ORIGIN:
            raise AssertionError("browser received the wrong authority")
        return self.session


class FakeGraph:
    def __init__(self, events, *, fail_create_after=None, deletion=None):
        self.events = events
        self.fail_create_after = fail_create_after
        self.deletion = deletion or broker.GraphDeletionOutcome(2, 4, 2, 4)
        self.create_calls = 0
        self.delete_calls = 0
        self.cleared = False

    def prepare(self, authority):
        self.events.append("graph_prepare")
        if authority.tenant_id.reveal() != TENANT_ID:
            raise AssertionError("Graph was not tenant-pinned")
        return broker.SealedValue(GRAPH_ISSUER)

    def prove_customer_absence(self, identities, *, authority, graph_issuer):
        del authority, graph_issuer
        self.events.append("graph_absence")
        self.asserted_aliases = tuple(identity.alias for identity in identities)
        return 4

    def create_customer(self, identity, *, authority, graph_issuer):
        del authority, graph_issuer
        self.create_calls += 1
        self.events.append(f"graph_create_{identity.alias}")
        if (
            self.fail_create_after is not None
            and self.create_calls > self.fail_create_after
        ):
            raise broker.BrokerRefusal("graph_authorization_unavailable")
        return broker.GraphCreationOutcome(
            "known_created",
            NOW,
            broker.SealedValue((SUBJECT_A, SUBJECT_B)[self.create_calls - 1]),
        )

    def delete_exact_pair(self, subjects, *, authority, graph_issuer):
        del authority, graph_issuer
        self.delete_calls += 1
        self.events.append("graph_delete_pair")
        self.subjects = tuple(subject.reveal() for subject in subjects)
        if isinstance(self.deletion, Exception):
            raise self.deletion
        return self.deletion

    def contain_partial_creation(
        self,
        identities,
        *,
        creation_states,
        attempted_after,
        authority,
        graph_issuer,
    ):
        del identities, authority, graph_issuer
        self.events.append("graph_contain_partial_creation")
        self.creation_states = dict(creation_states)
        self.attempted_after = dict(attempted_after)

    def clear(self):
        self.cleared = True
        self.events.append("graph_clear")


class FakeRetirement:
    def __init__(self, events, *, report=None):
        self.events = events
        self.calls = 0
        self.report = report or {
            "result": "pass",
            "state": "retired",
            "counts": {"retired_members": 2},
        }

    def retire(self, subjects, *, oidc_issuer, cutoff):
        del cutoff
        self.calls += 1
        self.events.append("retirement")
        self.subjects = tuple(subject.reveal() for subject in subjects)
        self.issuer = oidc_issuer.reveal()
        return self.report


class SealedLifecycleTests(unittest.TestCase):
    def test_complete_order_and_structural_report(self):
        events = []
        graph = FakeGraph(events)
        retirement = FakeRetirement(events)
        browser = FakeBrowser(events)
        report = broker.run_broker(
            run_id="qa-20260829-0001",
            cutoff=NOW,
            authority_adapter=FakeAuthority(events),
            graph=graph,
            browser=browser,
            retirement_adapter=retirement,
            choice=lambda _alphabet: "z",
        )

        self.assertEqual(report["result"], "conditional")
        self.assertEqual(report["state"], "retired_and_permanently_deleted")
        self.assertEqual(
            report["counts"],
            {
                "requested_identities": 2,
                "precreation_absence_proofs": 4,
                "provisioned_identities": 2,
                "member_arrivals": 2,
                "account_switches": 2,
                "canonical_journeys": 38,
                "conditional_journeys": 10,
                "created_items": 2,
                "item_edits": 4,
                "retained_versions": 6,
                "retained_source_proofs": 6,
                "downstream_disclosures": 2,
                "active_residue": 0,
                "archived_residue": 0,
                "destroyed_contexts": 4,
                "retired_members": 2,
                "soft_deleted_identities": 2,
                "soft_state_proofs": 4,
                "permanently_deleted_identities": 2,
                "final_absence_proofs": 4,
            },
        )
        self.assertEqual(browser.session.aliases, ("member_a", "member_b"))
        self.assertEqual(retirement.subjects, (SUBJECT_A, SUBJECT_B))
        self.assertEqual(retirement.issuer, OIDC_ISSUER)
        self.assertEqual(graph.subjects, (SUBJECT_A, SUBJECT_B))
        self.assertEqual(
            events[:-1],
            [
                "authority",
                "browser_prepare",
                "browser_preflight_proof",
                "graph_prepare",
                "graph_absence",
                "graph_create_member_a",
                "graph_create_member_b",
                "journeys",
                "browser_cleanup",
                "retirement",
                "graph_delete_pair",
            ],
        )
        self.assertEqual(events[-1], "graph_clear")

    def test_exact_eight_conditionals_and_complete_browser_evidence_are_required(self):
        missing = dict(broker.REQUIRED_CONDITIONAL_OUTCOMES)
        missing.pop("member_b_expired_session_safe")
        wrong = dict(broker.REQUIRED_CONDITIONAL_OUTCOMES)
        wrong["member_a_cannot_update_member_b"] = "feature_surface_unavailable"
        scenarios = {
            "zero": {},
            "missing": missing,
            "wrong": wrong,
        }
        for name, conditionals in scenarios.items():
            with self.subTest(name=name):
                events = []
                retirement = FakeRetirement(events)
                graph = FakeGraph(events)
                with self.assertRaisesRegex(
                    broker.BrokerIndeterminate,
                    "sealed_browser_operation_indeterminate",
                ):
                    broker.run_broker(
                        run_id="qa-20260829-0001",
                        cutoff=NOW,
                        authority_adapter=FakeAuthority(events),
                        graph=graph,
                        browser=FakeBrowser(
                            events,
                            outcome=complete_outcome(conditionals=conditionals),
                        ),
                        retirement_adapter=retirement,
                    )
                # Once both Graph users exist, browser proof failure remains
                # indeterminate but exact retirement/deletion containment must
                # still run rather than strand identity material.
                self.assertEqual(retirement.calls, 1)
                self.assertEqual(graph.delete_calls, 1)

        incomplete = complete_outcome()
        incomplete = broker.BrowserOutcome(
            **{
                **incomplete.__dict__,
                "retained_source_proof_counts": {"member_a": 2, "member_b": 3},
            }
        )
        events = []
        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
        ):
            broker.run_broker(
                run_id="qa-20260829-0001",
                cutoff=NOW,
                authority_adapter=FakeAuthority(events),
                graph=FakeGraph(events),
                browser=FakeBrowser(events, outcome=incomplete),
                retirement_adapter=FakeRetirement(events),
            )

    def test_partial_create_and_cleanup_ambiguity_are_indeterminate(self):
        events = []
        retirement = FakeRetirement(events)
        graph = FakeGraph(events, fail_create_after=1)
        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "graph_creation_indeterminate"
        ):
            broker.run_broker(
                run_id="qa-20260829-0001",
                cutoff=NOW,
                authority_adapter=FakeAuthority(events),
                graph=graph,
                browser=FakeBrowser(events),
                retirement_adapter=retirement,
            )
        self.assertEqual(retirement.calls, 0)
        self.assertEqual(graph.delete_calls, 0)
        self.assertLess(
            events.index("graph_contain_partial_creation"),
            events.index("browser_cleanup"),
        )

        events = []
        retirement = FakeRetirement(events)
        graph = FakeGraph(events)
        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "sealed_browser_cleanup_indeterminate"
        ):
            broker.run_broker(
                run_id="qa-20260829-0001",
                cutoff=NOW,
                authority_adapter=FakeAuthority(events),
                graph=graph,
                browser=FakeBrowser(
                    events,
                    cleanup=broker.BrowserCleanup(
                        destroyed_contexts=3,
                        temporary_root_removed=True,
                    ),
                ),
                retirement_adapter=retirement,
        )
        self.assertEqual(retirement.calls, 0)
        self.assertEqual(graph.delete_calls, 0)

        events = []
        retirement = FakeRetirement(events)
        graph = FakeGraph(events)
        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "sealed_browser_cleanup_indeterminate"
        ):
            broker.run_broker(
                run_id="qa-20260829-0001",
                cutoff=NOW,
                authority_adapter=FakeAuthority(events),
                graph=graph,
                browser=FakeBrowser(
                    events,
                    cleanup=broker.BrokerIndeterminate(
                        "sealed_browser_cleanup_indeterminate"
                    ),
                ),
                retirement_adapter=retirement,
            )
        self.assertEqual(retirement.calls, 0)
        self.assertEqual(graph.delete_calls, 0)

    def test_owner_ref_is_constant_and_main_output_is_allowlisted(self):
        with self.assertRaisesRegex(
            broker.BrokerRefusal, "owner_authorization_mismatch"
        ):
            broker.run_broker(
                run_id="qa-20260829-0001",
                cutoff=NOW,
                authority_adapter=FakeAuthority([]),
                graph=FakeGraph([]),
                browser=FakeBrowser([]),
                retirement_adapter=FakeRetirement([]),
                owner_authorization_ref="wrong",
            )

        events = []
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = broker.main(
                [
                    "run",
                    "--run-id",
                    "qa-20260829-0001",
                    "--created-after-utc",
                    "2026-08-29T09:00:00Z",
                    "--execute",
                    "--confirm-exact-two-synthetic-members",
                    "--confirm-no-production-proof",
                    "--confirm-permanent-exact-two-deletion",
                ],
                clock=lambda: NOW,
                authority_factory=lambda: FakeAuthority(events),
                graph_factory=lambda: FakeGraph(events),
                browser_factory=lambda: FakeBrowser(events),
                retirement_factory=lambda: FakeRetirement(events),
            )
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(output.getvalue())), {"result", "state", "counts"})
        rendered = output.getvalue().lower()
        for forbidden in (
            "password",
            "mailbox",
            "issuer",
            "subject",
            "token",
            TENANT_ID,
            OIDC_ISSUER,
            broker.OWNER_AUTHORIZATION_REF,
        ):
            self.assertNotIn(forbidden.lower(), rendered)


class FakeHttpResponse:
    def __init__(self, *, url, payload=None, status=200, body=None):
        self._url = url
        self.status = status
        self._body = (
            body
            if body is not None
            else json.dumps(payload if payload is not None else {}).encode("utf-8")
        )

    def geturl(self):
        return self._url

    def getcode(self):
        return self.status

    def read(self, limit=-1):
        return self._body if limit < 0 else self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class WindowsAzureCliTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        system = patch.object(broker.platform, "system", return_value="Windows")
        machine = patch.object(broker.platform, "machine", return_value="AMD64")
        system.start()
        machine.start()
        self.addCleanup(machine.stop)
        self.addCleanup(system.stop)


class AzureCliDarwinRuntimeTests(unittest.TestCase):
    def _resolve(self, layout, *, resolver=None):
        with (
            patch.object(broker, "DARWIN_HOMEBREW_PREFIX", layout.prefix),
            patch.object(broker.platform, "system", return_value="Darwin"),
            patch.object(broker.platform, "machine", return_value="arm64"),
        ):
            return broker._resolve_azure_cli_runtime(resolver or layout.discover)

    def _assert_refusal(self, layout, *, discovery=None):
        with self.assertRaisesRegex(
            broker.BrokerRefusal, "production_authority_unavailable"
        ):
            self._resolve(
                layout,
                resolver=(
                    None if discovery is None else lambda _command: discovery
                ),
            )

    def test_exact_homebrew_launcher_binds_same_version_arm64_interpreter(self):
        with tempfile.TemporaryDirectory() as root:
            layout = FakeHomebrewAzureCliLayout(Path(root))
            runtime = self._resolve(layout)
            self.assertEqual(runtime.python_executable, layout.python_executable)
            self.assertEqual(
                runtime.command(("account", "show")),
                (*layout.command_prefix, "account", "show"),
            )

    def test_homebrew_runtime_is_used_only_for_two_authority_reads(self):
        with tempfile.TemporaryDirectory() as root:
            layout = FakeHomebrewAzureCliLayout(Path(root))
            azure_calls = []

            def runner(command, **kwargs):
                azure_calls.append((tuple(command), kwargs))
                arguments = tuple(command[len(layout.command_prefix) :])
                if arguments == broker.AzureAppAuthorityResolver.auth_command:
                    payload = {"enabled": True, "issuer": DISCOVERY_ISSUER}
                elif arguments == broker.AzureAppAuthorityResolver.settings_command:
                    payload = [
                        {"name": "PEERSLATE_AUTH_ISSUER", "value": OIDC_ISSUER}
                    ]
                else:
                    raise AssertionError("unexpected Azure command")
                return type(
                    "Result",
                    (),
                    {"returncode": 0, "stdout": json.dumps(payload)},
                )()

            endpoint = f"{DISCOVERY_ISSUER}/.well-known/openid-configuration"
            opener = lambda _request, timeout: FakeHttpResponse(
                url=endpoint,
                payload={
                    "issuer": OIDC_ISSUER,
                    "authorization_endpoint": AUTHORIZATION_ENDPOINT,
                },
            )
            with (
                patch.object(broker, "DARWIN_HOMEBREW_PREFIX", layout.prefix),
                patch.object(broker.platform, "system", return_value="Darwin"),
                patch.object(broker.platform, "machine", return_value="arm64"),
            ):
                binding = broker.AzureAppAuthorityResolver(
                    runner,
                    opener,
                    environment={"PATH": "/safe"},
                    launcher_resolver=layout.discover,
                ).resolve()
            self.assertEqual(len(azure_calls), 2)
            self.assertTrue(
                all(call[0][:5] == layout.command_prefix for call in azure_calls)
            )
            self.assertEqual(
                [
                    call[0][len(layout.command_prefix) :]
                    for call in azure_calls
                ],
                [
                    broker.AzureAppAuthorityResolver.auth_command,
                    broker.AzureAppAuthorityResolver.settings_command,
                ],
            )
            binding.clear()

    def test_darwin_refuses_windows_shaped_path_injection(self):
        with tempfile.TemporaryDirectory() as root:
            windows_layout = FakeAzureCliLayout(Path(root))
            with (
                patch.object(broker.platform, "system", return_value="Darwin"),
                patch.object(broker.platform, "machine", return_value="arm64"),
                self.assertRaisesRegex(
                    broker.BrokerRefusal, "production_authority_unavailable"
                ),
            ):
                broker._resolve_azure_cli_runtime(windows_layout.discover)

    def test_runtime_revalidates_interpreter_before_each_child(self):
        with tempfile.TemporaryDirectory() as root:
            layout = FakeHomebrewAzureCliLayout(Path(root))
            runtime = self._resolve(layout)
            versioned_python = layout.python_executable.with_name("python3.13")
            escaped = layout.prefix.parent / "late-escaped-python"
            escaped.write_bytes(broker.DARWIN_ARM64_MACHO_PREFIX + b"fake")
            escaped.chmod(0o755)
            versioned_python.unlink()
            versioned_python.symlink_to(escaped)
            with self.assertRaisesRegex(
                broker.BrokerRefusal, "production_authority_unavailable"
            ):
                runtime.command(("account", "show"))

    def test_homebrew_binding_refuses_malformed_or_escaped_layouts(self):
        with tempfile.TemporaryDirectory() as root:
            malformed = FakeHomebrewAzureCliLayout(
                Path(root), launcher_contents=b"#!/bin/sh\nexit 0\n"
            )
            self._assert_refusal(malformed)

        with tempfile.TemporaryDirectory() as root:
            wrong_arch = FakeHomebrewAzureCliLayout(
                Path(root), python_prefix=b"not-macho"
            )
            self._assert_refusal(wrong_arch)

        with tempfile.TemporaryDirectory() as root:
            escaped = FakeHomebrewAzureCliLayout(Path(root))
            outside = escaped.prefix.parent / "escaped-python"
            outside.write_bytes(broker.DARWIN_ARM64_MACHO_PREFIX + b"fake")
            outside.chmod(0o755)
            versioned_python = escaped.python_executable.with_name("python3.13")
            versioned_python.unlink()
            versioned_python.symlink_to(outside)
            self._assert_refusal(escaped)

        with tempfile.TemporaryDirectory() as root:
            direct_cellar = FakeHomebrewAzureCliLayout(Path(root))
            self._assert_refusal(
                direct_cellar, discovery=str(direct_cellar.launcher)
            )

        with tempfile.TemporaryDirectory() as root:
            indirect_alias = FakeHomebrewAzureCliLayout(Path(root))
            indirect_alias.discovery_link.unlink()
            indirect_alias.discovery_link.symlink_to(indirect_alias.launcher)
            self._assert_refusal(indirect_alias)

        with tempfile.TemporaryDirectory() as root:
            wrong_keg = FakeHomebrewAzureCliLayout(
                Path(root), cli_version="2.87"
            )
            self._assert_refusal(wrong_keg)

        with tempfile.TemporaryDirectory() as root:
            changed_chain = FakeHomebrewAzureCliLayout(Path(root))
            versioned_python = changed_chain.python_executable.with_name(
                "python3.13"
            )
            versioned_python.unlink()
            versioned_python.symlink_to(changed_chain.resolved_python)
            self._assert_refusal(changed_chain)

    def test_homebrew_binding_refuses_non_darwin_or_non_arm64_host(self):
        with tempfile.TemporaryDirectory() as root:
            layout = FakeHomebrewAzureCliLayout(Path(root))
            for system, machine in (("Linux", "arm64"), ("Darwin", "x86_64")):
                with self.subTest(system=system, machine=machine):
                    with (
                        patch.object(
                            broker, "DARWIN_HOMEBREW_PREFIX", layout.prefix
                        ),
                        patch.object(
                            broker.platform, "system", return_value=system
                        ),
                        patch.object(
                            broker.platform, "machine", return_value=machine
                        ),
                        self.assertRaisesRegex(
                            broker.BrokerRefusal,
                            "production_authority_unavailable",
                        ),
                    ):
                        broker._resolve_azure_cli_runtime(layout.discover)


class AzureAuthorityResolverTests(WindowsAzureCliTestCase):
    @staticmethod
    def _runner(
        calls,
        cli_layout,
        *,
        settings_issuer=OIDC_ISSUER,
        auth_payload=None,
    ):
        def run(command, **kwargs):
            calls.append((tuple(command), kwargs))
            if tuple(command[len(cli_layout.command_prefix) :]) == (
                broker.AzureAppAuthorityResolver.auth_command
            ):
                payload = (
                    {"enabled": True, "issuer": DISCOVERY_ISSUER}
                    if auth_payload is None
                    else auth_payload
                )
            elif tuple(command[len(cli_layout.command_prefix) :]) == (
                broker.AzureAppAuthorityResolver.settings_command
            ):
                payload = [
                    {"name": "PEERSLATE_AUTH_ISSUER", "value": settings_issuer}
                ]
            else:
                raise AssertionError("unexpected Azure command")
            return type(
                "Result", (), {"returncode": 0, "stdout": json.dumps(payload)}
            )()

        return run

    @staticmethod
    def _metadata(*, issuer=OIDC_ISSUER, authorization=AUTHORIZATION_ENDPOINT):
        return {"issuer": issuer, "authorization_endpoint": authorization}

    def test_binds_fixed_app_metadata_setting_and_authorization_origin(self):
        calls = []

        def opener(request, timeout):
            self.assertEqual(timeout, 60)
            endpoint = f"{DISCOVERY_ISSUER}/.well-known/openid-configuration"
            self.assertEqual(request.full_url, endpoint)
            return FakeHttpResponse(url=endpoint, payload=self._metadata())

        with tempfile.TemporaryDirectory() as root:
            cli_layout = FakeAzureCliLayout(Path(root))
            binding = broker.AzureAppAuthorityResolver(
                self._runner(calls, cli_layout),
                opener,
                environment={"PATH": "/safe", "UNRELATED_SECRET": "not-forwarded"},
                launcher_resolver=cli_layout.discover,
            ).resolve()
        self.assertEqual(binding.oidc_issuer.reveal(), OIDC_ISSUER)
        self.assertEqual(binding.authorization_origin.reveal(), AUTHORIZATION_ORIGIN)
        self.assertEqual(binding.tenant_id.reveal(), TENANT_ID)
        self.assertEqual(binding.tenant_label.reveal(), "synthetic-tenant")
        self.assertEqual(
            calls[0][0][len(cli_layout.command_prefix) :],
            broker.AzureAppAuthorityResolver.auth_command,
        )
        self.assertEqual(calls[0][0][:5], cli_layout.command_prefix)
        self.assertEqual(calls[1][0][:5], cli_layout.command_prefix)
        self.assertEqual(
            calls[0][0][calls[0][0].index("--query") + 1],
            "{enabled:enabled,issuer:issuer}",
        )
        for _command, kwargs in calls:
            self.assertNotIn("UNRELATED_SECRET", kwargs["env"])
            self.assertIs(kwargs["stdin"], broker.subprocess.DEVNULL)

    def test_mismatch_redirect_status_and_duplicate_setting_refuse(self):
        endpoint = f"{DISCOVERY_ISSUER}/.well-known/openid-configuration"
        scenarios = {
            "metadata_tenant": (
                self._metadata(
                    issuer=(
                        "https://55555555-5555-5555-5555-555555555555.ciamlogin.com/"
                        "55555555-5555-5555-5555-555555555555/v2.0"
                    )
                ),
                endpoint,
                200,
                OIDC_ISSUER,
            ),
            "authorization_host": (
                self._metadata(
                    authorization=(
                        f"https://other.ciamlogin.com/{TENANT_ID}/oauth2/v2.0/authorize"
                    )
                ),
                endpoint,
                200,
                OIDC_ISSUER,
            ),
            "authorization_trailing_slash": (
                self._metadata(authorization=f"{AUTHORIZATION_ENDPOINT}/"),
                endpoint,
                200,
                OIDC_ISSUER,
            ),
            "principal_extra_host_label": (
                self._metadata(
                    issuer=(
                        f"https://{TENANT_ID}.extra.ciamlogin.com/"
                        f"{TENANT_ID}/v2.0"
                    )
                ),
                endpoint,
                200,
                OIDC_ISSUER,
            ),
            "principal_noncanonical_path": (
                self._metadata(
                    issuer=(
                        f"https://{TENANT_ID}.ciamlogin.com//"
                        f"{TENANT_ID}/v2.0"
                    )
                ),
                endpoint,
                200,
                OIDC_ISSUER,
            ),
            "redirect": (self._metadata(), f"{endpoint}/redirected", 200, OIDC_ISSUER),
            "status": (self._metadata(), endpoint, 503, OIDC_ISSUER),
            "setting": (self._metadata(), endpoint, 200, "https://wrong.example"),
        }
        with tempfile.TemporaryDirectory() as root:
            cli_layout = FakeAzureCliLayout(Path(root))
            for name, (metadata, final_url, status, setting) in scenarios.items():
                with self.subTest(name=name):
                    resolver = broker.AzureAppAuthorityResolver(
                        self._runner([], cli_layout, settings_issuer=setting),
                        lambda _request, timeout: FakeHttpResponse(
                            url=final_url, payload=metadata, status=status
                        ),
                        environment={"PATH": "/safe"},
                        launcher_resolver=cli_layout.discover,
                    )
                    with self.assertRaises(broker.BrokerRefusal):
                        resolver.resolve()

    def test_malformed_top_level_auth_shape_refuses_before_browser_or_graph(self):
        scenarios = {
            "missing_issuer": {"enabled": True},
            "wrong_enabled_type": {"enabled": "true", "issuer": DISCOVERY_ISSUER},
            "extra_field": {
                "enabled": True,
                "issuer": DISCOVERY_ISSUER,
                "unexpected": "value",
            },
            "legacy_shape": {
                "platformEnabled": True,
                "openIdIssuer": DISCOVERY_ISSUER,
            },
        }
        with tempfile.TemporaryDirectory() as root:
            cli_layout = FakeAzureCliLayout(Path(root))
            for name, auth_payload in scenarios.items():
                with self.subTest(name=name):
                    calls = []
                    events = []
                    graph = FakeGraph(events)
                    resolver = broker.AzureAppAuthorityResolver(
                        self._runner(
                            calls, cli_layout, auth_payload=auth_payload
                        ),
                        lambda *_args, **_kwargs: self.fail(
                            "malformed auth shape must stop before metadata"
                        ),
                        environment={"PATH": "/safe"},
                        launcher_resolver=cli_layout.discover,
                    )
                    with self.assertRaisesRegex(
                        broker.BrokerRefusal, "production_oidc_authority_mismatch"
                    ):
                        broker.run_broker(
                            run_id="qa-20260829-0001",
                            cutoff=NOW,
                            authority_adapter=resolver,
                            graph=graph,
                            browser=FakeBrowser(events),
                            retirement_adapter=FakeRetirement(events),
                        )
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(graph.create_calls, 0)
                    self.assertEqual(events, ["graph_clear"])

    def _assert_invalid_runtime_refuses_before_azure_or_graph(self, discovery):
        calls = []
        events = []
        graph = FakeGraph(events)
        resolver = broker.AzureAppAuthorityResolver(
            lambda *_args, **_kwargs: calls.append("azure"),
            lambda *_args, **_kwargs: calls.append("metadata"),
            environment={"PATH": "/safe"},
            launcher_resolver=lambda _command: discovery,
        )
        with self.assertRaisesRegex(
            broker.BrokerRefusal, "production_authority_unavailable"
        ):
            broker.run_broker(
                run_id="qa-20260829-0001",
                cutoff=NOW,
                authority_adapter=resolver,
                graph=graph,
                browser=FakeBrowser(events),
                retirement_adapter=FakeRetirement(events),
            )
        self.assertEqual(calls, [])
        self.assertEqual(graph.create_calls, 0)
        self.assertNotIn("graph_prepare", events)

    def test_invalid_cli_layout_refuses_before_any_azure_or_graph_call(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            scenarios = {
                "unrelated_source": str(Path(broker.__file__).resolve()),
                "missing_sibling_python": FakeAzureCliLayout(
                    root_path / "missing-python", include_python=False
                ).discover("az"),
                "wrong_wbin_adjacency": FakeAzureCliLayout(
                    root_path / "wrong-wbin", launcher_directory="bin"
                ).discover("az"),
                "wrong_cli2_runtime_root": FakeAzureCliLayout(
                    root_path / "wrong-root", runtime_name="OtherRuntime"
                ).discover("az"),
                "missing_discovery": None,
            }
            for name, discovery in scenarios.items():
                with self.subTest(name=name):
                    self._assert_invalid_runtime_refuses_before_azure_or_graph(
                        discovery
                    )

    def test_escaped_cli_python_refuses_before_any_azure_or_graph_call(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            cli_layout = FakeAzureCliLayout(root_path / "runtime")
            escaped = root_path / "escaped" / "python.exe"
            escaped.parent.mkdir()
            escaped.write_text("fake", encoding="utf-8")
            original_resolve = Path.resolve

            def escaped_python_resolve(path, strict=False):
                if original_resolve(path) == original_resolve(
                    cli_layout.python_executable
                ):
                    return original_resolve(escaped, strict=True)
                return original_resolve(path, strict=strict)

            with patch.object(broker.Path, "resolve", escaped_python_resolve):
                self._assert_invalid_runtime_refuses_before_azure_or_graph(
                    cli_layout.discover("az")
                )


def fake_graph_token(
    *,
    operator=OPERATOR_ID,
    tenant_id=TENANT_ID,
    client_id=broker.GRAPH_PUBLIC_CLIENT_ID,
    authorized_party=None,
    audience=broker.MICROSOFT_GRAPH_AUDIENCE,
    scopes=None,
    roles=None,
    expires=None,
):
    payload = {
        "tid": tenant_id,
        "oid": operator,
        "appid": client_id,
        "azp": client_id if authorized_party is None else authorized_party,
        "aud": audience,
        "scp": " ".join(
            sorted(broker.REQUIRED_GRAPH_SCOPES) if scopes is None else scopes
        ),
        "wids": (
            ["fe930be7-5e62-47db-91af-98c3a49a38b1"]
            if roles is None
            else roles
        ),
        "exp": int(
            (NOW + timedelta(hours=1) if expires is None else expires).timestamp()
        ),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{encoded}.signature"


class StaticGraphTokenProvider:
    """Fake Graph-token source used only to exercise production claim checks."""

    def __init__(self, token):
        self.token = token
        self.calls = []

    def acquire(self, tenant_id):
        self.calls.append(tenant_id.reveal())
        return broker.SealedValue(self.token, max_length=broker.MAX_TOKEN_LENGTH)


class FakeMsalTokenCache:
    def __init__(self):
        # MSAL 1.31.1 TokenCache has a private mutable backing mapping, not a
        # public clear() method.  The fake deliberately mirrors that shape.
        self._cache = {}


class FakeMsalPublicClientApplication:
    def __init__(self, module, client_id, **kwargs):
        self._module = module
        self.client_id = client_id
        self.kwargs = kwargs
        self.interactive_calls = []
        module.applications.append(self)

    def acquire_token_interactive(self, *, scopes):
        decorated_scopes = set(scopes)
        decorated_scopes.update({"openid", "profile", "offline_access"})
        decorated_scopes.difference_update(self.kwargs["exclude_scopes"])
        self.interactive_calls.append(frozenset(decorated_scopes))
        self.kwargs["token_cache"]._cache = {
            "AccessToken": {"operation": "fake"},
            "IdToken": {"operation": "fake"},
        }
        return self._module.result


class FakeMsalModule:
    def __init__(self, result):
        self.result = result
        self.__file__ = broker.__file__
        self.caches = []
        self.applications = []

    def TokenCache(self):
        cache = FakeMsalTokenCache()
        self.caches.append(cache)
        return cache

    def PublicClientApplication(self, client_id, **kwargs):
        return FakeMsalPublicClientApplication(self, client_id, **kwargs)


def fake_msal_distribution(package_name, *, version_overrides=None):
    package_name = str(package_name).lower()
    versions = dict(broker.MSAL_LOCKED_DISTRIBUTIONS)
    versions.update(version_overrides or {})
    if package_name not in versions:
        raise broker.importlib.metadata.PackageNotFoundError(package_name)
    root = Path(broker.__file__).resolve().parent.parent
    return SimpleNamespace(
        version=versions[package_name],
        locate_file=lambda _relative: root,
    )


class MicrosoftGraphCreationTests(WindowsAzureCliTestCase):
    def test_token_is_tenant_pinned_and_creation_requires_bound_authority(self):
        requests = []
        created_identity = []
        fake_msal = FakeMsalModule({"access_token": fake_graph_token()})

        def opener(request, timeout):
            del timeout
            requests.append(request)
            if request.full_url == broker.ALLOWED_GRAPH_ORGANIZATION_ENDPOINT:
                return FakeHttpResponse(
                    url=broker.ALLOWED_GRAPH_ORGANIZATION_ENDPOINT,
                    payload={
                        "value": [
                            {
                                "id": TENANT_ID,
                                "verifiedDomains": [
                                    {"name": GRAPH_ISSUER, "isInitial": True}
                                ],
                            }
                        ]
                    },
                )
            if request.get_method() == "GET":
                if request.full_url == (
                    f"{broker.ALLOWED_GRAPH_ENDPOINT}/{SUBJECT_A}?$select="
                    f"{broker.GRAPH_CUSTOMER_SHAPE_SELECT}"
                ):
                    identity = created_identity[0]
                    return FakeHttpResponse(
                        url=request.full_url,
                        payload={
                            "id": SUBJECT_A,
                            "accountEnabled": True,
                            "userType": "Member",
                            "creationType": "LocalAccount",
                            "displayName": "PeerSlate synthetic QA member_a",
                            "mailNickname": identity.mail_nickname.reveal(),
                            "identities": [
                                {
                                    "signInType": "emailAddress",
                                    "issuer": GRAPH_ISSUER,
                                    "issuerAssignedId": identity.login_identifier.reveal(),
                                }
                            ],
                            "createdDateTime": "2026-08-29T10:00:00Z",
                            "passwordPolicies": "DisablePasswordExpiration",
                        },
                    )
                self.assertTrue(
                    request.full_url.startswith(f"{broker.ALLOWED_GRAPH_ENDPOINT}?")
                    or request.full_url.startswith(
                        f"{broker.ALLOWED_GRAPH_DELETED_ITEMS_ENDPOINT}/microsoft.graph.user?"
                    )
                )
                self.assertIsNone(request.get_header("Consistencylevel"))
                return FakeHttpResponse(url=request.full_url, payload={"value": []})
            return FakeHttpResponse(
                url=broker.ALLOWED_GRAPH_ENDPOINT,
                status=201,
                payload={"id": SUBJECT_A},
            )

        with (
            patch.object(
                broker.importlib.metadata,
                "distribution",
                side_effect=fake_msal_distribution,
            ),
            patch.object(broker.importlib, "import_module", return_value=fake_msal),
        ):
            graph = broker.MicrosoftGraphAdapter(
                broker.MsalSystemBrowserGraphTokenProvider(),
                opener,
                clock=lambda: NOW,
            )
            authority = authority_binding()
            issuer = graph.prepare(authority)
            identity = broker._generate_identities(
                issuer, run_id="qa-20260829-0001", choice=lambda _alphabet: "z"
            )[0]
            created_identity.append(identity)
            identities = broker._generate_identities(
                issuer, run_id="qa-20260829-0001", choice=lambda _alphabet: "z"
            )
            self.assertTrue(
                all(len(item.login_identifier.reveal()) <= 64 for item in identities)
            )
            self.assertEqual(
                graph.prove_customer_absence(
                    identities, authority=authority, graph_issuer=issuer
                ),
                4,
            )
            outcome = graph.create_customer(
                identity, authority=authority, graph_issuer=issuer
            )
            self.assertEqual(outcome.state, "known_created")
            self.assertEqual(outcome.subject.reveal(), SUBJECT_A)
            outcome.clear()
            graph.clear()
        self.assertEqual(
            [request.get_method() for request in requests],
            ["GET"] * 10 + ["POST", "GET"],
        )
        posted = json.loads(requests[-2].data.decode("utf-8"))
        self.assertEqual(posted["userType"], "Member")
        self.assertEqual(posted["creationType"], "LocalAccount")
        self.assertEqual(posted["mailNickname"], identity.mail_nickname.reveal())
        self.assertTrue(fake_msal.applications)
        self.assertTrue(all(cache._cache == {} for cache in fake_msal.caches))
        for application in fake_msal.applications:
            self.assertEqual(application.client_id, broker.GRAPH_PUBLIC_CLIENT_ID)
            self.assertEqual(
                application.kwargs,
                {
                    "authority": broker.GRAPH_PUBLIC_CLIENT_AUTHORITY,
                    "token_cache": application.kwargs["token_cache"],
                    "exclude_scopes": ["offline_access"],
                    "enable_broker_on_windows": False,
                    "enable_broker_on_mac": False,
                },
            )
            self.assertEqual(
                application.interactive_calls,
                [frozenset({*broker.MSAL_GRAPH_SCOPES, "openid", "profile"})],
            )

    def test_missing_scope_role_or_operator_switch_refuses(self):
        organization = {
            "value": [
                {
                    "id": TENANT_ID,
                    "verifiedDomains": [
                        {"name": GRAPH_ISSUER, "isInitial": True}
                    ],
                }
            ]
        }

        def org_opener(request, timeout):
            del timeout
            return FakeHttpResponse(url=request.full_url, payload=organization)

        for name, token in (
            ("scope", fake_graph_token(scopes=["User.Read"])),
            (
                "extra_scope",
                fake_graph_token(
                    scopes=[*broker.MSAL_GRAPH_SCOPES, "Directory.Read.All"]
                ),
            ),
            (
                "duplicated_scope",
                fake_graph_token(scopes=[*broker.MSAL_GRAPH_SCOPES, "User.Read"]),
            ),
            (
                "role",
                fake_graph_token(roles=["00000000-0000-0000-0000-000000000000"]),
            ),
            (
                "extra_role",
                fake_graph_token(
                    roles=[
                        "fe930be7-5e62-47db-91af-98c3a49a38b1",
                        "00000000-0000-0000-0000-000000000000",
                    ]
                ),
            ),
            (
                "privileged_authentication_administrator_is_not_create_capable",
                fake_graph_token(
                    roles=["7be44c8a-adaf-4e2a-84d6-ab2649e08a13"]
                ),
            ),
            (
                "appid",
                fake_graph_token(client_id="55555555-5555-5555-5555-555555555555"),
            ),
            (
                "azp",
                fake_graph_token(
                    authorized_party="55555555-5555-5555-5555-555555555555"
                ),
            ),
            (
                "tenant",
                fake_graph_token(
                    tenant_id="33333333-3333-3333-3333-333333333333"
                ),
            ),
            (
                "graph_url_audience",
                fake_graph_token(audience="https://graph.microsoft.com"),
            ),
            ("expiry", fake_graph_token(expires=NOW + timedelta(seconds=120))),
        ):
            with self.subTest(name=name):
                provider = StaticGraphTokenProvider(token)
                with self.assertRaisesRegex(
                    broker.BrokerRefusal, "graph_delegated_authority_unverified"
                ):
                    broker.MicrosoftGraphAdapter(
                        provider, org_opener, clock=lambda: NOW
                    ).prepare(authority_binding())

class MsalSystemBrowserGraphTokenTests(unittest.TestCase):
    def test_fixed_public_client_uses_exact_memory_only_system_browser_flow(self):
        fake_msal = FakeMsalModule({"access_token": fake_graph_token()})
        provider = broker.MsalSystemBrowserGraphTokenProvider()
        with (
            patch.object(
                broker.importlib.metadata,
                "distribution",
                side_effect=fake_msal_distribution,
            ),
            patch.object(broker.importlib, "import_module", return_value=fake_msal),
        ):
            token = provider.acquire(broker.SealedValue(TENANT_ID))
        self.assertEqual(token.reveal(), fake_graph_token())
        self.assertEqual(len(fake_msal.applications), 1)
        application = fake_msal.applications[0]
        self.assertEqual(application.client_id, broker.GRAPH_PUBLIC_CLIENT_ID)
        self.assertEqual(application.kwargs["authority"], broker.GRAPH_PUBLIC_CLIENT_AUTHORITY)
        self.assertIs(application.kwargs["token_cache"], fake_msal.caches[0])
        self.assertEqual(application.kwargs["exclude_scopes"], ["offline_access"])
        self.assertFalse(application.kwargs["enable_broker_on_windows"])
        self.assertFalse(application.kwargs["enable_broker_on_mac"])
        self.assertEqual(
            application.interactive_calls,
            [frozenset({*broker.MSAL_GRAPH_SCOPES, "openid", "profile"})],
        )
        self.assertEqual(fake_msal.caches[0]._cache, {})
        token.clear()

    def test_tenant_or_locked_runtime_mismatch_refuses_before_import(self):
        provider = broker.MsalSystemBrowserGraphTokenProvider()
        with patch.object(broker.importlib, "import_module") as module_import:
            with self.assertRaisesRegex(
                broker.BrokerRefusal, "graph_token_tenant_unverified"
            ):
                provider.acquire(broker.SealedValue("33333333-3333-3333-3333-333333333333"))
        module_import.assert_not_called()

        with (
            patch.object(
                broker.importlib.metadata,
                "distribution",
                side_effect=lambda name: fake_msal_distribution(
                    name, version_overrides={"requests": "0.0.0"}
                ),
            ),
            patch.object(broker.importlib, "import_module") as module_import,
            self.assertRaisesRegex(
                broker.BrokerRefusal, "graph_authorization_unavailable"
            ),
        ):
            provider.acquire(broker.SealedValue(TENANT_ID))
        module_import.assert_not_called()

    def test_complete_hashed_lock_and_imported_module_provenance_are_required(self):
        lock_content = broker.MSAL_REQUIREMENTS_LOCK_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            broker.MsalSystemBrowserGraphTokenProvider._parse_locked_requirements(
                lock_content
            ),
            broker.MSAL_LOCKED_DISTRIBUTIONS,
        )
        missing_transitive = lock_content.replace(
            "pycparser==3.0 "
            "--hash=sha256:b727414169a36b7d524c1c3e31839a521725078d7b2ff038656844266160a992\n",
            "",
        )
        unhashed_transitive = lock_content.replace(
            "certifi==2026.7.22 "
            "--hash=sha256:62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775\n",
            "certifi==2026.7.22\n",
        )
        for malformed_lock in (missing_transitive, unhashed_transitive):
            with self.subTest(malformed_lock=malformed_lock):
                with self.assertRaisesRegex(
                    broker.BrokerRefusal, "graph_authorization_unavailable"
                ):
                    broker.MsalSystemBrowserGraphTokenProvider._parse_locked_requirements(
                        malformed_lock
                    )

        fake_msal = FakeMsalModule({"access_token": fake_graph_token()})
        fake_msal.__file__ = str(Path(__file__).resolve())
        with (
            patch.object(
                broker.importlib.metadata,
                "distribution",
                side_effect=fake_msal_distribution,
            ),
            patch.object(broker.importlib, "import_module", return_value=fake_msal),
            self.assertRaisesRegex(
                broker.BrokerRefusal, "graph_authorization_unavailable"
            ),
        ):
            broker.MsalSystemBrowserGraphTokenProvider().acquire(
                broker.SealedValue(TENANT_ID)
            )
        self.assertEqual(fake_msal.applications, [])

    def test_memory_cache_requires_the_bound_msal_backing_mapping(self):
        cache = FakeMsalTokenCache()
        cache._cache = {"RefreshToken": {"operation": "must-not-survive"}}
        self.assertTrue(
            broker.MsalSystemBrowserGraphTokenProvider._dispose_memory_cache(cache)
        )
        self.assertEqual(cache._cache, {})

        class ClearOnlyCache:
            def clear(self):
                self.called = True

        self.assertFalse(
            broker.MsalSystemBrowserGraphTokenProvider._dispose_memory_cache(
                ClearOnlyCache()
            )
        )

    def test_interactive_failure_refuses_before_graph_http_without_token_output(self):
        fake_msal = FakeMsalModule({"error": "interaction_required"})
        graph_requests = []

        def opener(request, _timeout):
            graph_requests.append(request)
            self.fail("interactive failure must stop before Graph HTTP")

        with (
            patch.object(
                broker.importlib.metadata,
                "distribution",
                side_effect=fake_msal_distribution,
            ),
            patch.object(broker.importlib, "import_module", return_value=fake_msal),
        ):
            graph = broker.MicrosoftGraphAdapter(
                broker.MsalSystemBrowserGraphTokenProvider(),
                opener,
                clock=lambda: NOW,
            )
            with self.assertRaisesRegex(
                broker.BrokerRefusal, "graph_authorization_unavailable"
            ) as refusal:
                graph.prepare(authority_binding())
        self.assertEqual(graph_requests, [])
        self.assertNotIn("interaction_required", str(refusal.exception))

class FakeProbePage:
    def __init__(self, *, signed_out=False):
        self.url = "about:blank"
        self.signed_out = signed_out
        self.closed = False

    def goto(self, url, *, wait_until):
        del wait_until
        if "/.auth/login/" in url:
            self.url = f"{AUTHORIZATION_ORIGIN}/authorize"
        else:
            self.url = url

    def locator(self, selector):
        count = 0
        if selector == ".wk-status-banner--preview" and self.signed_out:
            count = 1
        if selector == "input[type='email']" and self.url.startswith(
            AUTHORIZATION_ORIGIN
        ):
            count = 1
        return type(
            "Locator",
            (),
            {
                "count": lambda _self: count,
                "evaluate_all": lambda _self, _expression, payload: (
                    count if payload["operation"] == "count" else None
                )
            },
        )()

    def evaluate(self, _expression, payload):
        parsed = urlparse(self.url)
        if (
            payload.get("expectedOrigin") != broker.ALLOWED_SITE_ORIGIN
            or parsed.scheme != "https"
            or parsed.netloc != "peerslate.com"
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise RuntimeError("Workshop document refused")
        return True

    def close(self):
        self.closed = True


class FakeRuntimeContext:
    def __init__(self, *, signed_out=False):
        self.page = FakeProbePage(signed_out=signed_out)
        self.closed = False

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class FakeRuntimeBrowser:
    version = "151.0.7922.34"

    def __init__(self, *, actual=False):
        self.actual = actual
        self.contexts = []
        self.closed = False

    def new_context(self, **options):
        signed_out = self.actual and len(self.contexts) == 2
        context = FakeRuntimeContext(signed_out=signed_out)
        context.options = options
        self.contexts.append(context)
        return context

    def close(self):
        self.closed = True


class FakeRuntimePlaywright:
    def __init__(self):
        self.chromium = self
        self.browsers = []
        self.launches = []
        self.stopped = False

    def launch(self, **options):
        self.launches.append(options)
        browser = FakeRuntimeBrowser(actual=bool(self.browsers))
        self.browsers.append(browser)
        return browser

    def stop(self):
        self.stopped = True


class FakeRuntimeProvider:
    expected_browser_version = "151.0.7922.34"

    def __init__(self, *, executable_present=True):
        self.playwright = FakeRuntimePlaywright()
        self.released = False
        self.executable_present = executable_present
        self.chromium_executable = None

    def start(self, workspace, environment):
        del environment
        browsers = workspace / "runtime" / "browsers"
        browsers.mkdir(parents=True)
        self.chromium_executable = browsers / "chromium-1234" / "chrome"
        if self.executable_present:
            self.chromium_executable.parent.mkdir()
            self.chromium_executable.write_text("fake", encoding="utf-8")
        return broker.StartedPlaywrightRuntime(
            playwright=self.playwright,
            chromium_executable=self.chromium_executable,
        )

    def release(self):
        self.released = True


def _protocol_frame(payload):
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
    )


def _ready_frame():
    return _protocol_frame(
        {
            "schema_version": broker.BROWSER_CHILD_PROTOCOL_SCHEMA,
            "type": "ready",
            "preflight": {
                "locked_runtime": True,
                "probe_launch_closed": True,
                "probe_root_removed": True,
                "prepared_contexts": 4,
                "signed_out_private_baseline": True,
            },
        }
    )


def _complete_frame(*, result="ok", cleanup_complete=True):
    payload = {
        "schema_version": broker.BROWSER_CHILD_PROTOCOL_SCHEMA,
        "type": "complete",
        "result": result,
        "cleanup": {
            "destroyed_contexts": 4,
            "complete": cleanup_complete,
        },
    }
    if result == "ok":
        payload["outcome"] = child_worker._browser_outcome_payload(
            complete_outcome()
        )
    elif result == "indeterminate":
        payload["reason_code"] = "sealed_browser_cleanup_indeterminate"
    return _protocol_frame(payload)


class RetainedProtocolInput(io.BytesIO):
    def __init__(self):
        super().__init__()
        self.closed_by_parent = False

    def close(self):
        # Keep the fake frame bytes inspectable after the parent closes its
        # anonymous-pipe endpoint.
        self.closed_by_parent = True


class RecordingProtocolOutput(io.BytesIO):
    def __init__(self, frames, events):
        super().__init__(b"".join(frames))
        self._events = events

    def readline(self, size=-1):
        frame = super().readline(size)
        if frame:
            self._events.append(f"child_{json.loads(frame)['type']}")
        return frame


class FakeChildProcess:
    def __init__(self, *, frames, events, workspace, final_return_code=0):
        self.stdin = RetainedProtocolInput()
        self.stdout = RecordingProtocolOutput(frames, events)
        self._events = events
        self._workspace = workspace
        self._final_return_code = final_return_code
        self.returncode = None

    def poll(self):
        return self.returncode

    def wait(self, *, timeout):
        self._events.append("child_exit")
        if not self._workspace.is_dir():
            raise AssertionError("parent removed the root before child exit")
        self.returncode = self._final_return_code
        return self.returncode

    def terminate(self):
        raise AssertionError("healthy fake child must not be terminated")

    def kill(self):
        raise AssertionError("healthy fake child must not be killed")


class FakeExactTreeContainment:
    def __init__(self, events):
        self.events = events
        self.events.append("process_tree_bound")

    def terminate_tree(self):
        raise AssertionError("healthy fake child tree must not be terminated")

    def release_after_exit(self, *, exited):
        self.events.append("process_tree_closed")
        return exited


class HangingAfterReadyOutput:
    def __init__(self, events):
        self.events = events
        self.release = threading.Event()
        self.ready_sent = False

    def readline(self, _size=-1):
        if not self.ready_sent:
            self.ready_sent = True
            self.events.append("child_ready")
            return _ready_frame()
        self.events.append("child_stdout_hang")
        self.release.wait(timeout=5)
        return b""

    def close(self):
        self.release.set()


class HangingChildProcess:
    def __init__(self, events, workspace):
        self.events = events
        self.workspace = workspace
        self.stdin = RetainedProtocolInput()
        self.stdout = HangingAfterReadyOutput(events)
        self.returncode = None
        self.tree_terminated = False

    def poll(self):
        return self.returncode

    def wait(self, *, timeout):
        self.events.append("child_wait")
        if not self.tree_terminated:
            raise broker.subprocess.TimeoutExpired("fake-child", timeout)
        self.returncode = 3
        return self.returncode

    def terminate(self):
        self.events.append("child_terminate")

    def kill(self):
        self.events.append("child_kill")


class DirectOnlyTerminatedChildProcess(HangingChildProcess):
    def terminate(self):
        self.events.append("direct_child_terminate")
        self.tree_terminated = True
        self.stdout.release.set()


class FakeForcedTreeContainment:
    def __init__(self, process, events):
        self.process = process
        self.events = events

    def terminate_tree(self):
        self.events.append("process_tree_terminate")
        self.process.tree_terminated = True
        self.process.stdout.release.set()
        return True

    def release_after_exit(self, *, exited):
        self.events.append("process_tree_reaped")
        return False if exited else False


class FakeProvisioningProvider:
    expected_browser_version = "151.0.7922.34"

    def __init__(self, events):
        self.events = events
        self.workspace = None
        self.venv_python = None

    def provision(self, workspace, environment):
        self.events.append("runtime_provision")
        self.workspace = workspace
        runtime_root = workspace / "runtime"
        venv_root = runtime_root / "venv"
        self.venv_python = venv_root / "bin" / "python"
        site_packages = venv_root / "lib" / "python3.13" / "site-packages"
        browsers = runtime_root / "browsers"
        self.venv_python.parent.mkdir(parents=True)
        self.venv_python.write_text("fake", encoding="utf-8")
        site_packages.mkdir(parents=True)
        browsers.mkdir(parents=True)
        return broker.ProvisionedPlaywrightRuntime(
            venv_python=self.venv_python.resolve(),
            site_packages=site_packages.resolve(),
            browsers=browsers.resolve(),
            environment=broker.PinnedPlaywrightRuntime._runtime_environment(
                workspace, environment, browsers
            ),
            expected_browser_version=self.expected_browser_version,
        )

    def start(self, workspace, environment):
        del workspace, environment
        raise AssertionError("the parent must not start or import Playwright")

    def release(self):
        self.events.append("runtime_release")
        if self.workspace is not None and not self.workspace.is_dir():
            raise AssertionError("runtime released after parent root removal")


class WindowsJobContainmentTests(unittest.TestCase):
    def test_accounting_query_returns_active_process_count(self):
        import ctypes

        class Accounting(ctypes.Structure):
            _fields_ = [("ActiveProcesses", ctypes.c_uint32)]

        class Kernel32:
            def __init__(self):
                self.calls = []

            def QueryInformationJobObject(
                self, handle, information_class, output, output_size, returned
            ):
                self.calls.append((handle, information_class, output_size))
                ctypes.cast(output, ctypes.POINTER(Accounting)).contents.ActiveProcesses = 3
                ctypes.cast(
                    returned, ctypes.POINTER(ctypes.c_uint32)
                ).contents.value = ctypes.sizeof(Accounting)
                return 1

        job = object.__new__(broker._WindowsKillOnCloseJob)
        job._handle = 41
        job._kernel32 = Kernel32()
        job._ctypes = ctypes
        job._dword_type = ctypes.c_uint32
        job._basic_accounting_type = Accounting

        self.assertEqual(job._active_processes(), 3)
        self.assertEqual(
            job._kernel32.calls,
            [(41, broker._WindowsKillOnCloseJob._BASIC_ACCOUNTING_INFORMATION, 4)],
        )

    def test_empty_job_requires_active_processes_to_reach_zero(self):
        job = object.__new__(broker._WindowsKillOnCloseJob)
        with (
            patch.object(job, "_active_processes", side_effect=[2, 1, 0]) as query,
            patch.object(broker.time, "sleep", return_value=None),
        ):
            self.assertTrue(job._wait_empty(1_000))
        self.assertEqual(query.call_count, 3)

        with patch.object(job, "_active_processes", return_value=1):
            self.assertFalse(job._wait_empty(0))
        with patch.object(job, "_active_processes", return_value=None):
            self.assertFalse(job._wait_empty(5_000))


class IsolatedBrowserChildProtocolTests(unittest.TestCase):
    def _adapter(
        self,
        root,
        events,
        frames,
        *,
        containment_factory=None,
        final_return_code=0,
    ):
        provider = FakeProvisioningProvider(events)
        launched = {}

        def process_factory(command, **options):
            events.append("child_launch")
            process = FakeChildProcess(
                frames=frames,
                events=events,
                workspace=Path(options["cwd"]),
                final_return_code=final_return_code,
            )
            launched.update(command=command, options=options, process=process)
            return process

        adapter = broker.PlaywrightBrowserAdapter(
            environment={
                "SystemRoot": r"C:\Windows",
                "PATH": r"C:\Windows\System32",
                "COMSPEC": r"C:\Windows\System32\cmd.exe",
                "SSL_CERT_FILE": r"C:\attacker\root.pem",
                "SSL_CERT_DIR": r"C:\attacker\roots",
                "AUTHORIZATION_REF": "must-not-reach-child",
                "PEERSLATE_AUTH_ISSUER": "must-not-reach-child",
                "PYTHONPATH": "must-not-reach-child",
            },
            workspace_root=root,
            runtime_provider_factory=lambda: provider,
            process_factory=process_factory,
            containment_factory=(
                containment_factory
                or (lambda _process: FakeExactTreeContainment(events))
            ),
        )
        return adapter, provider, launched

    def test_fake_child_is_exact_shell_free_pipe_and_exits_before_retirement(self):
        events = []
        graph = FakeGraph(events)
        retirement = FakeRetirement(events)
        real_rmtree = broker.shutil.rmtree
        with tempfile.TemporaryDirectory() as root:
            system_root = Path(root) / "deterministic-windows-root"
            system_root.mkdir()
            canonical_system_root = str(system_root.resolve())
            adapter, provider, launched = self._adapter(
                root, events, [_ready_frame(), _complete_frame()]
            )

            def recording_rmtree(path, *args, **kwargs):
                events.append("parent_root_remove")
                return real_rmtree(path, *args, **kwargs)

            with (
                patch.object(
                    broker.importlib,
                    "import_module",
                    side_effect=AssertionError(
                        "the parent must not import native Playwright"
                    ),
                ),
                patch.object(broker.shutil, "rmtree", side_effect=recording_rmtree),
                patch.object(
                    broker,
                    "_canonical_windows_system_root",
                    return_value=system_root.resolve(),
                ),
            ):
                report = broker.run_broker(
                    run_id="qa-20260829-0001",
                    cutoff=NOW,
                    authority_adapter=FakeAuthority(events),
                    graph=graph,
                    browser=adapter,
                    retirement_adapter=retirement,
                    choice=lambda _alphabet: "z",
                )

            self.assertEqual(report["result"], "conditional")
            self.assertLess(
                events.index("process_tree_bound"), events.index("child_ready")
            )
            self.assertLess(events.index("child_ready"), events.index("graph_prepare"))
            self.assertLess(events.index("child_complete"), events.index("child_exit"))
            self.assertLess(
                events.index("child_exit"), events.index("process_tree_closed")
            )
            self.assertLess(
                events.index("process_tree_closed"), events.index("runtime_release")
            )
            self.assertLess(
                events.index("runtime_release"), events.index("parent_root_remove")
            )
            self.assertLess(events.index("parent_root_remove"), events.index("retirement"))
            self.assertFalse(provider.workspace.exists())

        command = launched["command"]
        options = launched["options"]
        self.assertEqual(
            command,
            (
                str(provider.venv_python.resolve()),
                "-I",
                "-B",
                str(broker.CHILD_WORKER_PATH.resolve()),
            ),
        )
        self.assertEqual(
            {
                "stdin": options["stdin"],
                "stdout": options["stdout"],
                "stderr": options["stderr"],
                "shell": options["shell"],
                "close_fds": options["close_fds"],
                "bufsize": options["bufsize"],
            },
            {
                "stdin": broker.subprocess.PIPE,
                "stdout": broker.subprocess.PIPE,
                "stderr": broker.subprocess.DEVNULL,
                "shell": False,
                "close_fds": True,
                "bufsize": 0,
            },
        )
        self.assertNotIn("capture_output", options)
        for secret_name in (
            "AUTHORIZATION_REF",
            "PEERSLATE_AUTH_ISSUER",
            "PYTHONPATH",
            "PATH",
            "COMSPEC",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        ):
            self.assertNotIn(secret_name, options["env"])
        self.assertEqual(options["env"]["SYSTEMROOT"], canonical_system_root)
        self.assertEqual(options["env"]["WINDIR"], canonical_system_root)

        process = launched["process"]
        self.assertTrue(process.stdin.closed_by_parent)
        frames = [json.loads(line) for line in process.stdin.getvalue().splitlines()]
        self.assertEqual([frame["type"] for frame in frames], ["prepare", "identities"])
        self.assertEqual(
            set(frames[0]), {"schema_version", "type", "authorization_origin"}
        )
        identities_payload = frames[1]["identities"]
        self.assertEqual(
            [identity["alias"] for identity in identities_payload],
            ["member_a", "member_b"],
        )
        self.assertTrue(
            all(
                set(identity)
                == {"alias", "login_identifier", "password", "mail_nickname"}
                for identity in identities_payload
            )
        )
        wire_text = json.dumps(frames)
        self.assertNotIn(SUBJECT_A, wire_text)
        self.assertNotIn(SUBJECT_B, wire_text)
        for identity in identities_payload:
            self.assertNotIn(identity["password"], json.dumps(command))
            self.assertNotIn(identity["password"], json.dumps(options["env"]))

    def test_graph_refusal_sends_abort_without_identities_or_retirement(self):
        events = []

        class RefusingGraph(FakeGraph):
            def prepare(self, authority):
                del authority
                self.events.append("graph_prepare")
                raise broker.BrokerRefusal("graph_authorization_unavailable")

        graph = RefusingGraph(events)
        retirement = FakeRetirement(events)
        with tempfile.TemporaryDirectory() as root:
            adapter, provider, launched = self._adapter(
                root, events, [_ready_frame(), _complete_frame(result="aborted")]
            )
            with self.assertRaisesRegex(
                broker.BrokerRefusal, "graph_authorization_unavailable"
            ):
                broker.run_broker(
                    run_id="qa-20260829-0001",
                    cutoff=NOW,
                    authority_adapter=FakeAuthority(events),
                    graph=graph,
                    browser=adapter,
                    retirement_adapter=retirement,
                )
            self.assertFalse(provider.workspace.exists())

        frames = [
            json.loads(line)
            for line in launched["process"].stdin.getvalue().splitlines()
        ]
        self.assertEqual([frame["type"] for frame in frames], ["prepare", "abort"])
        self.assertEqual(frames[1], {"schema_version": 1, "type": "abort"})
        self.assertEqual(retirement.calls, 0)
        self.assertEqual(graph.create_calls, 0)

    def test_claimed_cleanup_after_indeterminate_child_result_cannot_retire(self):
        events = []
        graph = FakeGraph(events)
        retirement = FakeRetirement(events)
        with tempfile.TemporaryDirectory() as root:
            adapter, provider, _launched = self._adapter(
                root,
                events,
                [_ready_frame(), _complete_frame(result="indeterminate")],
            )
            with self.assertRaisesRegex(
                broker.BrokerIndeterminate, "sealed_browser_cleanup_indeterminate"
            ):
                broker.run_broker(
                    run_id="qa-20260829-0001",
                    cutoff=NOW,
                    authority_adapter=FakeAuthority(events),
                    graph=graph,
                    browser=adapter,
                    retirement_adapter=retirement,
                    choice=lambda _alphabet: "z",
                )
            self.assertFalse(provider.workspace.exists())
        self.assertEqual(retirement.calls, 0)
        self.assertNotIn("retirement", events)

    def test_production_noop_exact_protocol_exit_is_narrow_root_admission(self):
        events = []
        retirement = FakeRetirement(events)
        real_rmtree = broker.shutil.rmtree
        with tempfile.TemporaryDirectory() as root:
            adapter, provider, _launched = self._adapter(
                root,
                events,
                [_ready_frame(), _complete_frame()],
                containment_factory=(
                    lambda _process: broker._NoopChildProcessContainment()
                ),
            )

            def recording_rmtree(path, *args, **kwargs):
                events.append("parent_root_remove")
                return real_rmtree(path, *args, **kwargs)

            with patch.object(
                broker.shutil, "rmtree", side_effect=recording_rmtree
            ):
                report = broker.run_broker(
                    run_id="qa-20260829-0001",
                    cutoff=NOW,
                    authority_adapter=FakeAuthority(events),
                    graph=FakeGraph(events),
                    browser=adapter,
                    retirement_adapter=retirement,
                    choice=lambda _alphabet: "z",
                )

            self.assertEqual(report["result"], "conditional")
            self.assertFalse(provider.workspace.exists())
        self.assertNotIn("process_tree_closed", events)
        self.assertLess(events.index("parent_root_remove"), events.index("retirement"))

    def test_production_noop_abnormal_exit_retains_root_and_blocks_retirement(self):
        cases = (
            ("missing_ready", [], 0),
            ("malformed_ready", [b"{malformed\n"], 0),
            ("missing_result", [_ready_frame()], 0),
            ("malformed_result", [_ready_frame(), b"{malformed\n"], 0),
            (
                "trailing_output",
                [
                    _ready_frame(),
                    _complete_frame(),
                    _protocol_frame({"schema_version": 1, "type": "trailing"}),
                ],
                0,
            ),
            (
                "nonzero_return",
                [_ready_frame(), _complete_frame()],
                7,
            ),
            (
                "cleanup_failed",
                [_ready_frame(), _complete_frame(cleanup_complete=False)],
                0,
            ),
        )
        for label, frames, return_code in cases:
            with self.subTest(label=label):
                events = []
                retirement = FakeRetirement(events)
                real_rmtree = broker.shutil.rmtree
                with tempfile.TemporaryDirectory() as root:
                    adapter, provider, _launched = self._adapter(
                        root,
                        events,
                        frames,
                        containment_factory=(
                            lambda _process: broker._NoopChildProcessContainment()
                        ),
                        final_return_code=return_code,
                    )

                    def recording_rmtree(path, *args, **kwargs):
                        events.append("parent_root_remove")
                        return real_rmtree(path, *args, **kwargs)

                    with (
                        patch.object(
                            broker.shutil,
                            "rmtree",
                            side_effect=recording_rmtree,
                        ),
                        self.assertRaisesRegex(
                            broker.BrokerIndeterminate,
                            "sealed_browser_cleanup_indeterminate",
                        ),
                    ):
                        broker.run_broker(
                            run_id="qa-20260829-0001",
                            cutoff=NOW,
                            authority_adapter=FakeAuthority(events),
                            graph=FakeGraph(events),
                            browser=adapter,
                            retirement_adapter=retirement,
                            choice=lambda _alphabet: "z",
                        )

                    self.assertTrue(provider.workspace.exists())
                    self.assertNotIn("parent_root_remove", events)
                self.assertEqual(retirement.calls, 0)
                self.assertNotIn("retirement", events)
                self.assertFalse(
                    any(event.startswith("process_tree_") for event in events)
                )

    def test_production_noop_timeout_kills_only_direct_child_and_retains_root(self):
        events = []
        retirement = FakeRetirement(events)
        provider = FakeProvisioningProvider(events)
        launched = {}

        def process_factory(_command, **options):
            process = DirectOnlyTerminatedChildProcess(
                events, Path(options["cwd"])
            )
            launched["process"] = process
            return process

        real_rmtree = broker.shutil.rmtree
        with tempfile.TemporaryDirectory() as root:
            adapter = broker.PlaywrightBrowserAdapter(
                environment={},
                workspace_root=root,
                runtime_provider_factory=lambda: provider,
                process_factory=process_factory,
                containment_factory=(
                    lambda _process: broker._NoopChildProcessContainment()
                ),
            )

            def recording_rmtree(path, *args, **kwargs):
                events.append("parent_root_remove")
                return real_rmtree(path, *args, **kwargs)

            with (
                patch.object(
                    broker, "BROWSER_CHILD_RESULT_TIMEOUT_SECONDS", 0.01
                ),
                patch.object(broker.shutil, "rmtree", side_effect=recording_rmtree),
                self.assertRaisesRegex(
                    broker.BrokerIndeterminate,
                    "sealed_browser_cleanup_indeterminate",
                ),
            ):
                broker.run_broker(
                    run_id="qa-20260829-0001",
                    cutoff=NOW,
                    authority_adapter=FakeAuthority(events),
                    graph=FakeGraph(events),
                    browser=adapter,
                    retirement_adapter=retirement,
                    choice=lambda _alphabet: "z",
                )

            self.assertTrue(provider.workspace.exists())
        self.assertIn("direct_child_terminate", events)
        self.assertNotIn("parent_root_remove", events)
        self.assertEqual(retirement.calls, 0)
        self.assertNotIn("retirement", events)
        self.assertFalse(any(event.startswith("process_tree_") for event in events))
        self.assertTrue(launched["process"].stdin.closed_by_parent)

    def test_protocol_rejects_duplicate_keys_and_non_finite_numbers(self):
        for frame in (
            b'{"type":"ready","type":"complete"}\n',
            b'{"schema_version":NaN}\n',
        ):
            with self.subTest(frame=frame), self.assertRaisesRegex(
                broker.BrokerIndeterminate, "sealed_browser_protocol_indeterminate"
            ):
                broker._read_child_message(io.BytesIO(frame))

    def test_result_pipe_timeout_reaps_tree_and_blocks_retirement(self):
        events = []
        graph = FakeGraph(events)
        retirement = FakeRetirement(events)
        provider = FakeProvisioningProvider(events)
        launched = {}

        def process_factory(_command, **options):
            events.append("child_launch")
            process = HangingChildProcess(events, Path(options["cwd"]))
            launched["process"] = process
            return process

        def containment_factory(process):
            return FakeForcedTreeContainment(process, events)

        real_rmtree = broker.shutil.rmtree
        with tempfile.TemporaryDirectory() as root:
            adapter = broker.PlaywrightBrowserAdapter(
                environment={"SYSTEMROOT": r"C:\Windows"},
                workspace_root=root,
                runtime_provider_factory=lambda: provider,
                process_factory=process_factory,
                containment_factory=containment_factory,
            )

            def recording_rmtree(path, *args, **kwargs):
                events.append("parent_root_remove")
                return real_rmtree(path, *args, **kwargs)

            with (
                patch.object(
                    broker,
                    "BROWSER_CHILD_RESULT_TIMEOUT_SECONDS",
                    0.01,
                ),
                patch.object(broker.shutil, "rmtree", side_effect=recording_rmtree),
                self.assertRaisesRegex(
                    broker.BrokerIndeterminate,
                    "sealed_browser_cleanup_indeterminate",
                ),
            ):
                broker.run_broker(
                    run_id="qa-20260829-0001",
                    cutoff=NOW,
                    authority_adapter=FakeAuthority(events),
                    graph=graph,
                    browser=adapter,
                    retirement_adapter=retirement,
                    choice=lambda _alphabet: "z",
                )

            self.assertTrue(provider.workspace.exists())

        process = launched["process"]
        self.assertTrue(process.stdin.closed_by_parent)
        self.assertLess(
            events.index("process_tree_terminate"),
            events.index("process_tree_reaped"),
        )
        self.assertNotIn("parent_root_remove", events)
        self.assertFalse(provider.workspace.exists())
        self.assertEqual(retirement.calls, 0)
        self.assertEqual(graph.delete_calls, 0)
        self.assertNotIn("retirement", events)
        frames = [
            json.loads(line) for line in process.stdin.getvalue().splitlines()
        ]
        self.assertEqual([frame["type"] for frame in frames], ["prepare", "identities"])

    def test_reader_start_failure_reaps_raw_child_before_root_removal(self):
        events = []
        real_rmtree = broker.shutil.rmtree
        with tempfile.TemporaryDirectory() as root:
            adapter, provider, launched = self._adapter(root, events, [_ready_frame()])

            def recording_rmtree(path, *args, **kwargs):
                events.append("parent_root_remove")
                return real_rmtree(path, *args, **kwargs)

            with (
                patch.object(
                    broker.threading.Thread,
                    "start",
                    side_effect=RuntimeError("fake thread refusal"),
                ),
                patch.object(broker.shutil, "rmtree", side_effect=recording_rmtree),
                self.assertRaisesRegex(
                    broker.BrokerRefusal, "sealed_browser_runtime_unavailable"
                ),
            ):
                adapter.prepare_attended_session(authority_binding())

            self.assertFalse(provider.workspace.exists())

        process = launched["process"]
        self.assertTrue(process.stdin.closed_by_parent)
        self.assertLess(events.index("child_exit"), events.index("process_tree_closed"))
        self.assertLess(
            events.index("process_tree_closed"), events.index("runtime_release")
        )
        self.assertLess(
            events.index("runtime_release"), events.index("parent_root_remove")
        )

    def test_unstarted_cleanup_retains_root_without_tree_empty_proof(self):
        events = []

        class UnprovedContainment:
            def release_after_exit(self, *, exited):
                events.append("process_tree_unproved")
                self.exited = exited
                return False

            def terminate_tree(self):
                raise AssertionError("the directly exited child is not terminated")

        for label, containment in (
            ("uncontained", None),
            ("unproved", UnprovedContainment()),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as root:
                workspace = Path(root) / f"{broker.BROWSER_TEMP_PREFIX}retained"
                workspace.mkdir()
                process = FakeChildProcess(
                    frames=[], events=events, workspace=workspace
                )
                provider = FakeProvisioningProvider(events)
                provider.workspace = workspace
                with (
                    patch.object(broker.shutil, "rmtree") as remove,
                    self.assertRaisesRegex(
                        broker.BrokerIndeterminate,
                        "sealed_browser_cleanup_indeterminate",
                    ),
                ):
                    broker.PlaywrightBrowserAdapter._remove_unstarted_workspace(
                        workspace,
                        provider,
                        process,
                        containment,
                    )
                remove.assert_not_called()
                self.assertTrue(workspace.exists())
        self.assertIn("process_tree_unproved", events)


class PinnedBrowserPreflightTests(unittest.TestCase):
    def test_windows_environment_uses_only_os_reported_system_root(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            workspace = root_path / "operation"
            browsers = workspace / "runtime" / "browsers"
            trusted = root_path / "trusted-windows"
            attacker = root_path / "attacker-windows"
            browsers.mkdir(parents=True)
            trusted.mkdir()
            attacker.mkdir()
            source = {
                "SYSTEMROOT": str(attacker),
                "SystemRoot": str(attacker),
                "WINDIR": str(attacker),
                "PATH": str(attacker),
                "COMSPEC": str(attacker / "cmd.exe"),
                "SSL_CERT_FILE": str(attacker / "root.pem"),
                "SSL_CERT_DIR": str(attacker),
            }
            with patch.object(
                broker,
                "_canonical_windows_system_root",
                return_value=trusted.resolve(),
            ):
                environment = broker.PinnedPlaywrightRuntime._runtime_environment(
                    workspace, source, browsers
                )

            self.assertEqual(environment["SYSTEMROOT"], str(trusted.resolve()))
            self.assertEqual(environment["WINDIR"], str(trusted.resolve()))
            for name in (
                "PATH",
                "COMSPEC",
                "SSL_CERT_FILE",
                "SSL_CERT_DIR",
            ):
                self.assertNotIn(name, environment)

    def test_parent_rejects_provider_substitution_of_windows_system_root(self):
        events = []

        class SubstitutingProvider(FakeProvisioningProvider):
            def provision(self, workspace, environment):
                provisioned = super().provision(workspace, environment)
                changed = dict(provisioned.environment)
                changed["SYSTEMROOT"] = str(attacker.resolve())
                changed["WINDIR"] = str(attacker.resolve())
                return broker.ProvisionedPlaywrightRuntime(
                    venv_python=provisioned.venv_python,
                    site_packages=provisioned.site_packages,
                    browsers=provisioned.browsers,
                    environment=changed,
                    expected_browser_version=provisioned.expected_browser_version,
                )

        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            trusted = root_path / "trusted-windows"
            attacker = root_path / "attacker-windows"
            trusted.mkdir()
            attacker.mkdir()
            provider = SubstitutingProvider(events)
            adapter = broker.PlaywrightBrowserAdapter(
                environment={"SYSTEMROOT": str(attacker), "PATH": str(attacker)},
                workspace_root=root_path,
                runtime_provider_factory=lambda: provider,
                process_factory=_forbid_live,
            )
            with (
                patch.object(
                    broker,
                    "_canonical_windows_system_root",
                    return_value=trusted.resolve(),
                ),
                self.assertRaisesRegex(
                    broker.BrokerRefusal, "sealed_browser_environment_refused"
                ),
            ):
                adapter.prepare_attended_session(authority_binding())

            self.assertNotIn("child_launch", events)
            self.assertFalse(provider.workspace.exists())

    def test_lock_is_exact_and_fake_probe_is_closed_removed_before_session(self):
        runtime = broker.PinnedPlaywrightRuntime()
        with (
            patch.object(broker.platform, "system", return_value="Darwin"),
            patch.object(broker.platform, "machine", return_value="arm64"),
            patch.object(
                broker.sys,
                "version_info",
                SimpleNamespace(major=3, minor=14),
            ),
        ):
            lock = runtime._lock()
        self.assertEqual(lock["chromium"]["revision"], "1234")
        self.assertEqual(lock["chromium"]["browser_version"], "151.0.7922.34")
        self.assertEqual(lock["active_target"]["venv_python"], ["bin", "python"])

        provider = FakeRuntimeProvider()
        with tempfile.TemporaryDirectory() as root:
            adapter = broker._NativePlaywrightBrowserAdapter(
                environment={
                    "SystemRoot": "/safe",
                    "PEERSLATE_AUTH_ISSUER": OIDC_ISSUER,
                    "AUTHORIZATION_REF": broker.OWNER_AUTHORIZATION_REF,
                },
                workspace_root=root,
                runtime_provider_factory=lambda: provider,
            )
            session = adapter.prepare_attended_session(authority_binding())
            self.assertEqual(
                session.pre_graph_proof(),
                broker.BrowserPreflight(True, True, True, 4, True),
            )
            self.assertEqual(len(provider.playwright.browsers), 2)
            self.assertTrue(provider.playwright.browsers[0].closed)
            self.assertTrue(provider.playwright.browsers[0].contexts[0].closed)
            self.assertEqual(len(provider.playwright.browsers[1].contexts), 4)
            for launch in provider.playwright.launches:
                self.assertFalse(launch["headless"])
                self.assertEqual(
                    launch["executable_path"],
                    str(provider.chromium_executable.resolve()),
                )
                self.assertNotIn("PEERSLATE_AUTH_ISSUER", launch["env"])
                self.assertNotIn("AUTHORIZATION_REF", launch["env"])
            self.assertFalse(
                any(Path(root).glob(f"{broker.BROWSER_PROBE_PREFIX}*"))
            )
            self.assertEqual(
                session.destroy_and_verify(), broker.BrowserCleanup(4, True)
            )
            self.assertTrue(provider.released and provider.playwright.stopped)
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_windows_target_uses_native_venv_paths_with_the_locked_browser(self):
        commands = []
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            trusted_windows = root_path / "trusted-windows"
            trusted_windows.mkdir()

            def runner(command, **_kwargs):
                command = tuple(command)
                commands.append(command)
                if "--copies" in command:
                    venv_root = Path(command[-1])
                    venv_python = venv_root / "Scripts" / "python.exe"
                    venv_python.parent.mkdir(parents=True)
                    venv_python.write_text("fake", encoding="utf-8")
                    site_packages = venv_root / "Lib" / "site-packages"
                    browser_package = site_packages / "playwright" / "driver" / "package"
                    browser_package.mkdir(parents=True)
                    (browser_package / "browsers.json").write_text(
                        json.dumps(
                            {
                                "browsers": [
                                    {
                                        "name": "chromium",
                                        "revision": "1234",
                                        "browserVersion": "151.0.7922.34",
                                        "title": "Chrome for Testing",
                                    }
                                ]
                            }
                        ),
                        encoding="utf-8",
                    )
                return type("Result", (), {"returncode": 0})()

            runtime = broker.PinnedPlaywrightRuntime(runner=runner)
            expected = broker.StartedPlaywrightRuntime(
                playwright=object(),
                chromium_executable=root_path / "runtime" / "browsers" / "chrome.exe",
            )
            with (
                patch.object(broker.platform, "system", return_value="Windows"),
                patch.object(broker.platform, "machine", return_value="AMD64"),
                patch.object(
                    broker.sys,
                    "version_info",
                    SimpleNamespace(major=3, minor=13),
                ),
                patch.object(
                    broker,
                    "_canonical_windows_system_root",
                    return_value=trusted_windows.resolve(),
                ),
                patch.object(
                    runtime,
                    "_distribution_versions",
                    return_value={
                        "greenlet": "3.5.5",
                        "playwright": "1.62.0",
                        "pyee": "13.0.1",
                        "typing-extensions": "4.16.0",
                    },
                ),
                patch.object(
                    runtime, "_load_started_playwright", return_value=expected
                ) as load_started,
            ):
                self.assertIs(
                    runtime.start(root_path, {"PATH": "/safe"}), expected
                )

            venv_python = root_path / "runtime" / "venv" / "Scripts" / "python.exe"
            site_packages = root_path / "runtime" / "venv" / "Lib" / "site-packages"
            self.assertEqual(commands[1][0], str(venv_python))
            self.assertEqual(commands[2][0], str(venv_python))
            self.assertEqual(
                commands[2],
                (
                    str(venv_python),
                    "-I",
                    "-m",
                    "playwright",
                    "install",
                    "chromium",
                    "--no-shell",
                ),
            )
            load_args, _ = load_started.call_args
            self.assertEqual(load_args[0], site_packages.resolve())
            self.assertEqual(
                load_args[1], (root_path / "runtime" / "browsers").resolve()
            )

    def test_unapproved_runtime_host_refuses_before_graph_mutation(self):
        events = []
        graph = FakeGraph(events)
        with tempfile.TemporaryDirectory() as root:
            adapter = broker.PlaywrightBrowserAdapter(
                environment={"SystemRoot": "/safe"},
                workspace_root=root,
                runtime_provider_factory=lambda: broker.PinnedPlaywrightRuntime(
                    runner=_forbid_live
                ),
            )

            class RuntimeBoundBrowser:
                def prepare_attended_session(self, authority):
                    return adapter.prepare_attended_session(authority)

            with (
                patch.object(broker.platform, "system", return_value="Linux"),
                patch.object(broker.platform, "machine", return_value="x86_64"),
                self.assertRaisesRegex(
                    broker.BrokerRefusal, "sealed_browser_lock_invalid"
                ),
            ):
                broker.run_broker(
                    run_id="qa-20260829-0001",
                    cutoff=NOW,
                    authority_adapter=FakeAuthority(events),
                    graph=graph,
                    browser=RuntimeBoundBrowser(),
                    retirement_adapter=FakeRetirement(events),
                )

        self.assertEqual(graph.create_calls, 0)
        self.assertNotIn("graph_prepare", events)

    def test_missing_runtime_executable_refuses_before_launch_or_graph_mutation(self):
        events = []
        provider = FakeRuntimeProvider(executable_present=False)

        with tempfile.TemporaryDirectory() as root:
            adapter = broker.PlaywrightBrowserAdapter(
                environment={"SystemRoot": "/safe"},
                workspace_root=root,
                runtime_provider_factory=lambda: provider,
            )

            class RuntimeBoundBrowser:
                def prepare_attended_session(self, authority):
                    return adapter.prepare_attended_session(authority)

            graph = FakeGraph(events)
            with self.assertRaisesRegex(
                broker.BrokerRefusal, "sealed_browser_runtime_unavailable"
            ):
                broker.run_broker(
                    run_id="qa-20260829-0001",
                    cutoff=NOW,
                    authority_adapter=FakeAuthority(events),
                    graph=graph,
                    browser=RuntimeBoundBrowser(),
                    retirement_adapter=FakeRetirement(events),
                )

            self.assertEqual(provider.playwright.launches, [])
            self.assertEqual(graph.create_calls, 0)
            self.assertNotIn("graph_prepare", events)
            self.assertTrue(provider.released)
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_pinned_runtime_returns_the_validated_executable_binding(self):
        class Chromium:
            def __init__(self, executable_path):
                self.executable_path = str(executable_path)

        class StartedPlaywright:
            def __init__(self, executable_path):
                self.chromium = Chromium(executable_path)
                self.stopped = False

            def stop(self):
                self.stopped = True

        class Starter:
            def __init__(self, started):
                self.started = started

            def start(self):
                return self.started

        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            site_packages = root_path / "site-packages"
            executable = root_path / "browsers" / "chromium-1234" / "chrome"
            site_packages.mkdir()
            executable.parent.mkdir(parents=True)
            executable.write_text("fake", encoding="utf-8")
            started = StartedPlaywright(executable)
            fake_sync_api = type(
                "SyncApi",
                (),
                {"sync_playwright": staticmethod(lambda: Starter(started))},
            )()
            runtime = broker.PinnedPlaywrightRuntime()

            with patch.object(
                broker.importlib, "import_module", return_value=fake_sync_api
            ):
                binding = runtime._load_started_playwright(
                    site_packages, executable.parents[1], {}
                )

            self.assertIs(binding.playwright, started)
            self.assertEqual(binding.chromium_executable, executable.resolve())
            started.stop()
            runtime.release()

    def test_partial_runtime_start_stops_local_playwright_before_release(self):
        class Chromium:
            def __init__(self, executable_path):
                self.executable_path = str(executable_path)

        class StartedPlaywright:
            def __init__(self, executable_path):
                self.chromium = Chromium(executable_path)
                self.stopped = False

            def stop(self):
                self.stopped = True

        class Starter:
            def __init__(self, started):
                self.started = started

            def start(self):
                return self.started

        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            site_packages = root_path / "site-packages"
            browsers = root_path / "browsers"
            outside = root_path / "outside" / "chromium"
            site_packages.mkdir()
            browsers.mkdir()
            outside.parent.mkdir()
            outside.write_text("fake", encoding="utf-8")
            started = StartedPlaywright(outside)
            fake_sync_api = type(
                "SyncApi",
                (),
                {"sync_playwright": staticmethod(lambda: Starter(started))},
            )()
            runtime = broker.PinnedPlaywrightRuntime()

            with patch.object(
                broker.importlib, "import_module", return_value=fake_sync_api
            ), self.assertRaisesRegex(
                broker.BrokerRefusal, "sealed_browser_runtime_unavailable"
            ):
                runtime._load_started_playwright(site_packages, browsers, {})

            self.assertTrue(started.stopped)
            self.assertIsNone(runtime._site_packages)
            self.assertNotIn(str(site_packages), broker.sys.path)

    def test_password_resolution_and_write_are_atomic_to_expected_origin(self):
        class Locator:
            def __init__(self, page, selector):
                self.page = page
                self.selector = selector

            def fill(self, value):
                del value

            def element_handle(self):
                if self.selector != "input[type='password']":
                    raise AssertionError("unexpected element handle")
                if self.page.redirect_stage == "password_resolution":
                    # Model navigation while Playwright waits for the locator;
                    # no password has crossed the element-handle boundary.
                    self.page.url = "https://unapproved.example/password"
                return self

            def evaluate(self, expression, payload):
                del expression
                if self.selector != "input[type='password']":
                    raise AssertionError("unexpected evaluated locator")
                self.page.password_evaluate_called = True
                parsed = urlparse(self.page.url)
                actual = f"{parsed.scheme}://{parsed.hostname}"
                if actual != payload["expectedOrigin"]:
                    raise RuntimeError("atomic origin refusal")
                del payload["secret"]
                self.page.password_filled = True

            def dispose(self):
                self.page.password_handle_disposed = True

            def click(self):
                if self.selector == "input[type='submit']":
                    self.page.submit_clicks += 1
                    if (
                        self.page.submit_clicks == 1
                        and self.page.redirect_stage == "email_submit"
                    ):
                        self.page.url = "https://unapproved.example/password"

        class RedirectingPage:
            def __init__(self, redirect_stage):
                self.url = "about:blank"
                self.redirect_stage = redirect_stage
                self.submit_clicks = 0
                self.password_filled = False
                self.password_handle_disposed = False
                self.password_evaluate_called = False

            def goto(self, url, *, wait_until):
                del url, wait_until
                self.url = f"{AUTHORIZATION_ORIGIN}/authorize"

            def locator(self, selector):
                return Locator(self, selector)

        identity = broker._generate_identities(
            broker.SealedValue(GRAPH_ISSUER),
            run_id="qa-20260829-0001",
            choice=lambda _alphabet: "z",
        )[0]
        for stage in ("email_submit", "password_resolution"):
            with self.subTest(stage=stage):
                page = RedirectingPage(stage)
                with self.assertRaisesRegex(
                    broker.BrokerRefusal, "unexpected_identity_host"
                ):
                    broker.PlaywrightBrowserAdapter()._sign_in(
                        page, identity, broker.SealedValue(AUTHORIZATION_ORIGIN)
                    )
                self.assertFalse(page.password_filled)
                self.assertEqual(page.submit_clicks, 1)
                self.assertFalse(page.password_evaluate_called)
                self.assertIs(
                    page.password_handle_disposed,
                    stage == "password_resolution",
                )


class DirectRetirementAdapterTests(unittest.TestCase):
    def test_uses_unchanged_core_with_exact_metadata_issuer(self):
        class Connection:
            def __init__(self):
                self.commits = self.rollbacks = self.closes = 0

            def commit(self):
                self.commits += 1

            def rollback(self):
                self.rollbacks += 1

            def close(self):
                self.closes += 1

        connection = Connection()
        with patch.object(
            broker.retirement, "SqlRetirementStore", return_value=object()
        ), patch.object(
            broker.retirement,
            "execute",
            return_value={
                "result": "pass",
                "state": "retired",
                "counts": {"eligible_members": 2},
            },
        ) as execute:
            result = broker.DirectRetirementAdapter(lambda: connection).retire(
                [broker.SealedValue(SUBJECT_A), broker.SealedValue(SUBJECT_B)],
                oidc_issuer=broker.SealedValue(OIDC_ISSUER),
                cutoff=NOW,
            )
        self.assertEqual(result["counts"], {"retired_members": 2})
        self.assertEqual(execute.call_args.kwargs["issuer"], OIDC_ISSUER)
        self.assertEqual(connection.commits, 1)


if __name__ == "__main__":
    unittest.main()

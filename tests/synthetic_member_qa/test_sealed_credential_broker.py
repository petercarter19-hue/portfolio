from __future__ import annotations

import base64
import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlparse

from qa.synthetic_member import sealed_credential_broker as broker
from qa.synthetic_member.contracts import JOURNEY_BY_ID


NOW = datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc)
SUBJECT_A = "11111111-1111-1111-1111-111111111111"
SUBJECT_B = "22222222-2222-2222-2222-222222222222"
TENANT_ID = "33333333-3333-3333-3333-333333333333"
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
        self.runtime_root = root / runtime_name
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


def _forbid_live(*_args, **_kwargs):
    raise AssertionError("focused broker tests must use fake-only dependencies")


def setUpModule():
    global _OUTBOUND_GUARDS
    _OUTBOUND_GUARDS = (
        patch.object(broker.subprocess, "run", side_effect=_forbid_live),
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


class AzureAuthorityResolverTests(unittest.TestCase):
    @staticmethod
    def _runner(calls, cli_layout, *, settings_issuer=OIDC_ISSUER):
        def run(command, **kwargs):
            calls.append((tuple(command), kwargs))
            if tuple(command[len(cli_layout.command_prefix) :]) == (
                broker.AzureAppAuthorityResolver.auth_command
            ):
                payload = {
                    "platformEnabled": True,
                    "openIdIssuer": DISCOVERY_ISSUER,
                }
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
        self.assertIn(
            "openIdIssuer:properties.identityProviders.azureActiveDirectory.registration.openIdIssuer",
            calls[0][0][calls[0][0].index("--query") + 1],
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
                if path == cli_layout.python_executable:
                    return original_resolve(escaped, strict=True)
                return original_resolve(path, strict=strict)

            with patch.object(broker.Path, "resolve", escaped_python_resolve):
                self._assert_invalid_runtime_refuses_before_azure_or_graph(
                    cli_layout.discover("az")
                )


def fake_graph_token(*, operator=OPERATOR_ID, scopes=None, roles=None):
    payload = {
        "tid": TENANT_ID,
        "oid": operator,
        "aud": "https://graph.microsoft.com",
        "scp": " ".join(scopes or sorted(broker.REQUIRED_GRAPH_SCOPES)),
        "wids": roles
        or ["fe930be7-5e62-47db-91af-98c3a49a38b1"],
        "exp": int((NOW + timedelta(hours=1)).timestamp()),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{encoded}.signature"


class MicrosoftGraphCreationTests(unittest.TestCase):
    def test_token_is_tenant_pinned_and_creation_requires_bound_authority(self):
        commands = []

        def runner(command, **kwargs):
            commands.append((tuple(command), kwargs))
            return type("Result", (), {"returncode": 0, "stdout": fake_graph_token()})()

        requests = []
        created_identity = []

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

        graph = broker.MicrosoftGraphAdapter(
            broker.AzureCliGraphTokenProvider(
                runner,
                environment={"PATH": "/safe", "SECRET": "not-forwarded"},
            ),
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
        self.assertTrue(all(len(item.login_identifier.reveal()) <= 64 for item in identities))
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
        self.assertEqual(
            [request.get_method() for request in requests],
            ["GET"] * 10 + ["POST", "GET"],
        )
        posted = json.loads(requests[-2].data.decode("utf-8"))
        self.assertEqual(posted["userType"], "Member")
        self.assertEqual(posted["creationType"], "LocalAccount")
        self.assertEqual(posted["mailNickname"], identity.mail_nickname.reveal())
        for command, kwargs in commands:
            tenant_index = command.index("--tenant")
            self.assertEqual(command[tenant_index + 1], TENANT_ID)
            self.assertNotIn("SECRET", kwargs["env"])
        graph.clear()

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
            ("role", fake_graph_token(roles=["00000000-0000-0000-0000-000000000000"])),
            (
                "privileged_authentication_administrator_is_not_create_capable",
                fake_graph_token(
                    roles=["7be44c8a-adaf-4e2a-84d6-ab2649e08a13"]
                ),
            ),
        ):
            with self.subTest(name=name):
                provider = broker.AzureCliGraphTokenProvider(
                    lambda *_args, **_kwargs: type(
                        "Result", (), {"returncode": 0, "stdout": token}
                    )(),
                )
                with self.assertRaisesRegex(
                    broker.BrokerRefusal, "graph_delegated_authority_unverified"
                ):
                    broker.MicrosoftGraphAdapter(
                        provider, org_opener, clock=lambda: NOW
                    ).prepare(authority_binding())

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


class PinnedBrowserPreflightTests(unittest.TestCase):
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
            adapter = broker.PlaywrightBrowserAdapter(
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
                    launch["executable_path"], str(provider.chromium_executable)
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

            def runner(command, **_kwargs):
                command = tuple(command)
                commands.append(command)
                if "--copies" in command:
                    venv_root = Path(command[-1])
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
            load_args, _ = load_started.call_args
            self.assertEqual(load_args[0], site_packages)
            self.assertEqual(load_args[1], root_path / "runtime" / "browsers")

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

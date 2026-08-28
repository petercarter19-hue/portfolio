"""Sealed local lifecycle for a pair of synthetic QA customer identities.

The broker is deliberately an operator tool, not PeerSlate application runtime.
It keeps generated login identifiers, passwords, Graph access tokens, and
External ID subjects inside one local worker process.  Its public output is an
allowlisted structural report only.  Importing this module never opens a
browser, contacts Microsoft Graph, obtains a token, or opens SQL.
"""

from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import contextmanager
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence
from urllib.parse import parse_qs, quote, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from qa.synthetic_member import identity_retirement as retirement
from qa.synthetic_member.contracts import JOURNEY_BY_ID, JOURNEYS, NOTE_CODES


ALLOWED_SITE_ORIGIN = "https://peerslate.com"
ALLOWED_SIGN_IN_ENDPOINT = (
    f"{ALLOWED_SITE_ORIGIN}/.auth/login/aad?post_login_redirect_uri=%2Fapp"
)
ALLOWED_GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0/users"
ALLOWED_GRAPH_ORGANIZATION_ENDPOINT = (
    "https://graph.microsoft.com/v1.0/organization?$select=id,verifiedDomains"
)
ALLOWED_ALIASES = ("member_a", "member_b")
REQUIRED_CONDITIONAL_OUTCOMES = {
    "member_a_cannot_update_member_b": "neutral_denial_not_distinguishable",
    "member_b_cannot_update_member_a": "neutral_denial_not_distinguishable",
    "member_a_forged_reference_denied": "feature_surface_unavailable",
    "member_b_forged_reference_denied": "feature_surface_unavailable",
    "member_a_cannot_export_member_b": "feature_surface_unavailable",
    "member_b_cannot_export_member_a": "feature_surface_unavailable",
    "member_a_expired_session_safe": "session_expiry_not_controllable",
    "member_b_expired_session_safe": "session_expiry_not_controllable",
}
SAFE_RUN_ID = re.compile(r"^[a-z0-9][a-z0-9-]{7,63}$")
SAFE_GRAPH_ISSUER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{2,253}$")
MAX_SECRET_LENGTH = 512
ALLOWED_AUTH_HOST_SUFFIXES = (".ciamlogin.com", ".b2clogin.com")
SAFE_TENANT_LABEL = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
AUTHENTICATED_WORKSHOP_CONTROL = (
    "div.platform-account[data-ps-auth-control='authenticated']:not([hidden])"
)
SAME_ORIGIN_MUTATION_HEADERS = {
    "Origin": ALLOWED_SITE_ORIGIN,
    "Sec-Fetch-Site": "same-origin",
}
GRAPH_AUDIENCES = {
    "00000003-0000-0000-c000-000000000000",
    "https://graph.microsoft.com",
    "https://graph.microsoft.com/",
}
BROWSER_TEMP_PREFIX = "peerslate-sealed-browser-"
REJECTED_BROWSER_ENV_NAMES = frozenset(
    {
        "PWDEBUG",
        "DEBUG",
        "PLAYWRIGHT_DEBUG",
        "CHROME_LOG_FILE",
        "CHROME_ENABLE_LOGGING",
        "CHROME_REMOTE_DEBUGGING_ADDRESS",
        "CHROME_REMOTE_DEBUGGING_PORT",
    }
)


class BrokerRefusal(RuntimeError):
    """A non-reflective failure that is safe to return to the operator."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class BrokerIndeterminate(RuntimeError):
    """A failure after an external mutation may have occurred."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class SealedValue:
    """A value that is intentionally unavailable to logs and repr().

    Python cannot promise physical memory zeroization for immutable strings.
    This boundary instead guarantees that values have no file, CLI-argument,
    environment, report, exception, or logging path, and clears the worker's
    direct references at the end of an operation.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str):
        if not isinstance(value, str) or not value or len(value) > MAX_SECRET_LENGTH:
            raise BrokerRefusal("sealed_input_invalid")
        self._value: str | None = value

    def reveal(self) -> str:
        if self._value is None:
            raise BrokerRefusal("sealed_value_cleared")
        return self._value

    def clear(self) -> None:
        self._value = None

    def __repr__(self) -> str:
        return "<sealed>"

    __str__ = __repr__


@dataclass
class SealedIdentity:
    """One ephemeral QA identity; repr never exposes its material."""

    alias: str
    login_identifier: SealedValue
    password: SealedValue
    mail_nickname: SealedValue
    subject: SealedValue | None = None

    def clear(self) -> None:
        self.login_identifier.clear()
        self.password.clear()
        self.mail_nickname.clear()
        if self.subject is not None:
            self.subject.clear()

    def __repr__(self) -> str:
        return f"SealedIdentity(alias={self.alias!r}, material=<sealed>)"


@dataclass(frozen=True)
class JourneyObservation:
    """One contract-shaped, non-reflective result held only in worker memory."""

    status: str
    observed_outcome: str
    note_code: str


@dataclass(frozen=True)
class BrowserOutcome:
    journey_outcomes: Mapping[str, JourneyObservation]
    created_item_counts: Mapping[str, int]
    active_residue_counts: Mapping[str, int]
    archived_residue_counts: Mapping[str, int]
    clean_start_confirmed: bool


@dataclass(frozen=True)
class BrowserCleanup:
    destroyed_contexts: int
    temporary_root_removed: bool


@dataclass
class _SealedItemHandle:
    """One private application handle and concurrency token, never reported."""

    key: SealedValue
    version: SealedValue

    def clear(self) -> None:
        self.key.clear()
        self.version.clear()


def _pass_observation(journey_id: str) -> JourneyObservation:
    try:
        expected = JOURNEY_BY_ID[journey_id].expected_outcome
    except KeyError:
        raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
    return JourneyObservation(status="pass", observed_outcome=expected, note_code="none")


def _conditional_observation(journey_id: str, note_code: str) -> JourneyObservation:
    if journey_id not in JOURNEY_BY_ID or note_code not in NOTE_CODES or note_code == "none":
        raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
    return JourneyObservation(
        status="conditional", observed_outcome="limitation_recorded", note_code=note_code
    )


class GraphAdapter(Protocol):
    def resolve_graph_issuer(self) -> SealedValue:
        """Derive the one verified External ID issuer from active Graph authority."""

    def create_customer(self, identity: SealedIdentity, *, graph_issuer: SealedValue) -> str:
        """Create one customer and return only its opaque Graph id to the worker."""


class AttendedBrowserSession(Protocol):
    def auth_issuer(self) -> SealedValue:
        """Return the derived, verified public authentication origin in worker memory."""

    def exercise_canonical_journeys(
        self, identities: Sequence[SealedIdentity]
    ) -> BrowserOutcome:
        """Complete the fixed journey matrix and application item lifecycle."""

    def destroy_and_verify(self) -> BrowserCleanup:
        """Destroy every context and the disposable root before retirement."""


class BrowserAdapter(Protocol):
    def prepare_attended_session(self) -> AttendedBrowserSession:
        """Launch and prove the no-capture browser baseline before Graph mutation."""


class RetirementAdapter(Protocol):
    def retire(
        self,
        subjects: Sequence[SealedValue],
        *,
        auth_issuer: SealedValue,
        cutoff: datetime,
    ) -> Mapping[str, object]:
        """Run the accepted exact-two retirement core without echoing subjects."""


class AzureCliGraphTokenProvider:
    """Acquire the active pre-authorized Graph token inside the local worker."""

    command_prefix = (
        "az",
        "account",
        "get-access-token",
        "--resource-type",
        "ms-graph",
        "--query",
        "accessToken",
        "--output",
        "tsv",
    )

    def __init__(
        self,
        runner: Callable[..., object] | None = None,
        *,
        environment: Mapping[str, str] | None = None,
    ):
        self._runner = runner or subprocess.run
        self._environment = environment

    def _child_environment(self) -> dict[str, str]:
        source = self._environment if self._environment is not None else os.environ
        allowed = (
            "SystemRoot",
            "WINDIR",
            "COMSPEC",
            "PATH",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "HOMEDRIVE",
            "HOMEPATH",
        )
        return {
            name: str(source[name])
            for name in allowed
            if source.get(name)
        }

    def acquire(self) -> SealedValue:
        try:
            result = self._runner(
                self.command_prefix,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
                stdin=subprocess.DEVNULL,
                env=self._child_environment(),
            )
        except (OSError, subprocess.SubprocessError):
            raise BrokerRefusal("graph_authorization_unavailable") from None
        if getattr(result, "returncode", 1) != 0:
            raise BrokerRefusal("graph_authorization_unavailable")
        token = str(getattr(result, "stdout", "") or "").strip()
        if len(token) < 16:
            raise BrokerRefusal("graph_authorization_unavailable")
        return SealedValue(token)


class MicrosoftGraphAdapter:
    """Narrow Microsoft Graph user creator with no diagnostic output."""

    def __init__(
        self,
        token_provider: AzureCliGraphTokenProvider | None = None,
        opener: Callable[..., object] | None = None,
    ):
        self._token_provider = token_provider or AzureCliGraphTokenProvider()
        self._opener = opener or urlopen

    @staticmethod
    def _token_tenant_id(token: SealedValue) -> str:
        try:
            _header, encoded_payload, _signature = token.reveal().split(".")
            padding = "=" * (-len(encoded_payload) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode((encoded_payload + padding).encode("ascii"))
            )
            tenant_id = str(UUID(str(payload.get("tid") or "")))
            if payload.get("aud") not in GRAPH_AUDIENCES:
                raise ValueError("unexpected audience")
            return tenant_id
        except (
            AttributeError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            binascii.Error,
            json.JSONDecodeError,
        ):
            raise BrokerRefusal("graph_token_tenant_unverified") from None

    def _verified_organization(self, token: SealedValue) -> Mapping[str, object]:
        tenant_id = self._token_tenant_id(token)
        request = Request(
            ALLOWED_GRAPH_ORGANIZATION_ENDPOINT,
            headers={
                "Authorization": f"Bearer {token.reveal()}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with self._opener(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, OSError, ValueError, UnicodeDecodeError):
            raise BrokerRefusal("graph_tenant_verification_unavailable") from None
        if not isinstance(payload, Mapping):
            raise BrokerRefusal("graph_tenant_issuer_mismatch")
        organizations = payload.get("value")
        if not isinstance(organizations, list) or len(organizations) != 1:
            raise BrokerRefusal("graph_tenant_issuer_mismatch")
        organization = organizations[0]
        if not isinstance(organization, Mapping) or str(organization.get("id") or "") != tenant_id:
            raise BrokerRefusal("graph_tenant_issuer_mismatch")
        return organization

    @staticmethod
    def _initial_verified_issuer(organization: Mapping[str, object]) -> SealedValue:
        verified_domains = organization.get("verifiedDomains")
        candidates = [
            str(domain.get("name") or "").lower()
            for domain in verified_domains or []
            if isinstance(domain, Mapping)
            and domain.get("isInitial") is True
            and SAFE_GRAPH_ISSUER.fullmatch(str(domain.get("name") or ""))
            and str(domain.get("name") or "").lower().endswith(".onmicrosoft.com")
        ]
        if len(candidates) != 1:
            raise BrokerRefusal("graph_tenant_issuer_mismatch")
        return SealedValue(candidates[0])

    def resolve_graph_issuer(self) -> SealedValue:
        """Derive the active tenant's exact initial verified issuer in memory.

        This is deliberately a pre-mutation read.  It trusts neither an
        ambient Azure CLI tenant name nor user-provided routing material: the
        active Graph JWT tenant and Graph organization must agree first.
        """

        token = self._token_provider.acquire()
        try:
            return self._initial_verified_issuer(self._verified_organization(token))
        finally:
            token.clear()

    def _verify_tenant_binding(self, token: SealedValue, graph_issuer: SealedValue) -> None:
        organization = self._verified_organization(token)
        verified_domains = organization.get("verifiedDomains")
        if not isinstance(verified_domains, list) or not any(
            isinstance(domain, Mapping)
            and str(domain.get("name") or "").lower() == graph_issuer.reveal().lower()
            for domain in verified_domains
        ):
            raise BrokerRefusal("graph_tenant_issuer_mismatch")

    def create_customer(self, identity: SealedIdentity, *, graph_issuer: SealedValue) -> str:
        _validate_graph_issuer(graph_issuer)
        token = self._token_provider.acquire()
        try:
            self._verify_tenant_binding(token, graph_issuer)
            body = {
                "accountEnabled": True,
                "displayName": f"PeerSlate synthetic QA {identity.alias}",
                "mailNickname": identity.mail_nickname.reveal(),
                "identities": [
                    {
                        "signInType": "emailAddress",
                        "issuer": graph_issuer.reveal(),
                        "issuerAssignedId": identity.login_identifier.reveal(),
                    }
                ],
                "passwordProfile": {
                    "password": identity.password.reveal(),
                    "forceChangePasswordNextSignIn": False,
                },
                "passwordPolicies": "DisablePasswordExpiration",
            }
            request = Request(
                ALLOWED_GRAPH_ENDPOINT,
                data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token.reveal()}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            try:
                with self._opener(request, timeout=60) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except (HTTPError, URLError, OSError, ValueError, UnicodeDecodeError):
                raise BrokerIndeterminate("graph_creation_indeterminate") from None
            subject = str(payload.get("id") or "")
            try:
                return str(UUID(subject))
            except (ValueError, AttributeError, TypeError):
                raise BrokerIndeterminate("graph_creation_indeterminate") from None
        finally:
            token.clear()


def _start_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise BrokerRefusal("sealed_browser_runtime_unavailable") from None
    return sync_playwright().start()


@contextmanager
def _isolated_child_environment(environment: Mapping[str, str]):
    """Start Playwright children without the worker's ambient environment."""

    original = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(environment)
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


class PlaywrightBrowserAdapter:
    """No-capture browser launcher for one sealed attended operation.

    ``prepare_attended_session`` deliberately launches the actual browser
    module and executable, creates all four non-persistent contexts, verifies
    the signed-out baseline, and derives the public authentication origin
    *before* returning control to the Graph phase.  The prepared session owns
    every transient browser object and can only return count-only outcomes.
    """

    def __init__(
        self,
        *,
        environment: Mapping[str, str] | None = None,
        workspace_root: str | Path | None = None,
        playwright_factory: Callable[[], object] | None = None,
    ):
        self._environment = environment
        self._workspace_root = (
            Path(workspace_root) if workspace_root is not None else Path(tempfile.gettempdir())
        )
        self._playwright_factory = playwright_factory or _start_playwright

    def _source_environment(self) -> Mapping[str, str]:
        return self._environment if self._environment is not None else os.environ

    def _browser_environment(self, workspace: Path) -> dict[str, str]:
        source = self._source_environment()
        child_environment = {
            "HOME": str(workspace),
            "USERPROFILE": str(workspace),
            "APPDATA": str(workspace),
            "LOCALAPPDATA": str(workspace),
            "TEMP": str(workspace),
            "TMP": str(workspace),
            "TMPDIR": str(workspace),
        }
        for name in ("SystemRoot", "WINDIR", "COMSPEC"):
            if source.get(name):
                child_environment[name] = str(source[name])
        return child_environment

    def preflight(self) -> None:
        source = self._source_environment()
        if any(source.get(name) for name in REJECTED_BROWSER_ENV_NAMES):
            raise BrokerRefusal("sealed_browser_environment_refused")
        try:
            workspace_root = self._workspace_root.resolve(strict=True)
            has_residue = any(workspace_root.glob(f"{BROWSER_TEMP_PREFIX}*"))
        except OSError:
            raise BrokerRefusal("sealed_browser_workspace_unavailable") from None
        if not workspace_root.is_dir() or has_residue:
            raise BrokerRefusal("sealed_browser_workspace_residue")

    @staticmethod
    def _auth_issuer_from_page(page) -> SealedValue:
        try:
            parsed = urlparse(str(page.url))
            host = (parsed.hostname or "").lower()
            allowed_host = any(host.endswith(suffix) for suffix in ALLOWED_AUTH_HOST_SUFFIXES)
            if (
                parsed.scheme != "https"
                or not host
                or not allowed_host
                or parsed.port is not None
                or parsed.username
                or parsed.password
            ):
                raise ValueError("unapproved auth origin")
            return SealedValue(f"https://{parsed.netloc}")
        except (TypeError, ValueError):
            raise BrokerRefusal("approved_auth_issuer_unavailable") from None

    @staticmethod
    def _auth_tenant_label(auth_issuer: SealedValue) -> str:
        host = (urlparse(auth_issuer.reveal()).hostname or "").lower()
        for suffix in ALLOWED_AUTH_HOST_SUFFIXES:
            if host.endswith(suffix):
                label = host[: -len(suffix)]
                if SAFE_TENANT_LABEL.fullmatch(label):
                    return label
        raise BrokerRefusal("auth_graph_tenant_mismatch")

    @classmethod
    def verify_auth_graph_tenant_binding(
        cls, auth_issuer: SealedValue, graph_issuer: SealedValue
    ) -> None:
        """Refuse unless the browser authority and Graph initial domain name one tenant.

        External ID's public authority is ``<tenant>.ciamlogin.com`` (or the
        equivalent b2clogin host) while the Graph organization reports the
        authoritative initial ``<tenant>.onmicrosoft.com`` domain.  The
        normalized tenant labels must match before either customer POST.
        """

        _validate_graph_issuer(graph_issuer)
        graph_label = graph_issuer.reveal().lower().removesuffix(".onmicrosoft.com")
        if not SAFE_TENANT_LABEL.fullmatch(graph_label) or cls._auth_tenant_label(
            auth_issuer
        ) != graph_label:
            raise BrokerRefusal("auth_graph_tenant_mismatch")

    @staticmethod
    def _assert_site_page(page) -> None:
        parsed = urlparse(str(page.url))
        if parsed.scheme != "https" or parsed.hostname != "peerslate.com":
            raise BrokerRefusal("signed_out_private_baseline_failed")

    def _assert_signed_out_private_baseline(self, page) -> None:
        page.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop", wait_until="domcontentloaded")
        self._assert_site_page(page)
        # A structural selector is permitted; it intentionally reads neither
        # user text nor browser storage and is never emitted from the worker.
        if page.locator(".wk-status-banner--preview").count() != 1:
            raise BrokerRefusal("signed_out_private_baseline_failed")

    @staticmethod
    def _close_resources(
        contexts: Sequence[object],
        browser: object | None,
        playwright: object | None,
        workspace: Path | None,
        *,
        expected_contexts: int,
    ) -> BrowserCleanup:
        destroyed = 0
        cleanup_failed = False
        for context in reversed(tuple(contexts)):
            try:
                context.close()
                destroyed += 1
            except Exception:
                cleanup_failed = True
        if browser is not None:
            try:
                browser.close()
            except Exception:
                cleanup_failed = True
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                cleanup_failed = True
        root_removed = workspace is None
        if workspace is not None:
            try:
                shutil.rmtree(workspace)
                root_removed = not workspace.exists()
            except OSError:
                cleanup_failed = True
        if destroyed != expected_contexts or not root_removed:
            cleanup_failed = True
        if cleanup_failed:
            raise BrokerIndeterminate("sealed_browser_cleanup_indeterminate")
        return BrowserCleanup(destroyed_contexts=destroyed, temporary_root_removed=root_removed)

    def prepare_attended_session(self) -> AttendedBrowserSession:
        self.preflight()
        workspace: Path | None = None
        browser = None
        playwright = None
        contexts: dict[str, object] = {}
        try:
            workspace = Path(tempfile.mkdtemp(prefix=BROWSER_TEMP_PREFIX, dir=str(self._workspace_root)))
            child_environment = self._browser_environment(workspace)
            with _isolated_child_environment(child_environment):
                playwright = self._playwright_factory()
                browser = playwright.chromium.launch(
                    headless=False,
                    downloads_path=str(workspace),
                    env=child_environment,
                )
            for name in ("member_a", "member_b", "signed_out", "switch"):
                contexts[name] = browser.new_context(accept_downloads=False)
            signed_out_page = contexts["signed_out"].new_page()
            self._assert_signed_out_private_baseline(signed_out_page)
            signed_out_page.goto(ALLOWED_SIGN_IN_ENDPOINT, wait_until="domcontentloaded")
            auth_issuer = self._auth_issuer_from_page(signed_out_page)
            return _PlaywrightAttendedSession(
                adapter=self,
                contexts=contexts,
                browser=browser,
                playwright=playwright,
                workspace=workspace,
                auth_issuer=auth_issuer,
                signed_out_page=signed_out_page,
                preflight_outcomes={
                    "clean_client_a_start": _pass_observation("clean_client_a_start"),
                    "clean_client_b_start": _pass_observation("clean_client_b_start"),
                    "clean_signed_out_control_start": _pass_observation(
                        "clean_signed_out_control_start"
                    ),
                    "signed_out_private_baseline": _pass_observation(
                        "signed_out_private_baseline"
                    ),
                },
            )
        except BrokerIndeterminate:
            raise
        except BrokerRefusal:
            try:
                self._close_resources(
                    tuple(contexts.values()),
                    browser,
                    playwright,
                    workspace,
                    expected_contexts=len(contexts),
                )
            except BrokerIndeterminate:
                raise
            raise
        except Exception:
            try:
                self._close_resources(
                    tuple(contexts.values()),
                    browser,
                    playwright,
                    workspace,
                    expected_contexts=len(contexts),
                )
            except BrokerIndeterminate:
                raise
            raise BrokerRefusal("sealed_browser_runtime_unavailable") from None

    def _wait_for_member_arrival(self, page) -> None:
        page.wait_for_url(re.compile(r"^https://peerslate\.com/app(?:[/?#]|$)"), timeout=60000)

    @staticmethod
    def _assert_expected_identity_host(page, auth_issuer: SealedValue) -> None:
        expected_host = urlparse(auth_issuer.reveal()).hostname
        actual_host = urlparse(str(page.url)).hostname
        if not expected_host or actual_host != expected_host:
            raise BrokerRefusal("unexpected_identity_host")

    def _sign_in(self, page, identity: SealedIdentity, auth_issuer: SealedValue) -> None:
        page.goto(ALLOWED_SIGN_IN_ENDPOINT, wait_until="domcontentloaded")
        self._assert_expected_identity_host(page, auth_issuer)
        page.locator("input[type='email']").fill(identity.login_identifier.reveal())
        page.locator("input[type='submit']").click()
        page.locator("input[type='password']").fill(identity.password.reveal())
        page.locator("input[type='submit']").click()
        self._wait_for_member_arrival(page)
        # The configured sign-in return is the generic /app landing.  Move to
        # Workshop deliberately, then let the caller prove the private shell;
        # never treat the auth callback or a generic app landing as Workshop.
        arrival = urlparse(str(page.url))
        if (
            arrival.scheme != "https"
            or arrival.netloc != urlparse(ALLOWED_SITE_ORIGIN).netloc
            or arrival.path != "/app"
        ):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        page.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop", wait_until="domcontentloaded")

    @staticmethod
    def _sign_out(page) -> None:
        page.goto(
            f"{ALLOWED_SITE_ORIGIN}/.auth/logout?post_logout_redirect_uri=%2F",
            wait_until="domcontentloaded",
        )


class _PlaywrightAttendedSession:
    """One sealed, non-persistent set of four browser contexts."""

    def __init__(
        self,
        *,
        adapter: PlaywrightBrowserAdapter,
        contexts: Mapping[str, object],
        browser: object,
        playwright: object,
        workspace: Path,
        auth_issuer: SealedValue,
        signed_out_page: object,
        preflight_outcomes: Mapping[str, JourneyObservation],
    ):
        self._adapter = adapter
        self._contexts = dict(contexts)
        self._browser = browser
        self._playwright = playwright
        self._workspace = workspace
        self._auth_issuer = auth_issuer
        self._signed_out_page = signed_out_page
        self._preflight_outcomes = dict(preflight_outcomes)
        self._cleanup: BrowserCleanup | None = None

    def auth_issuer(self) -> SealedValue:
        if self._cleanup is not None:
            raise BrokerRefusal("sealed_browser_session_closed")
        return SealedValue(self._auth_issuer.reveal())

    @staticmethod
    def _item_url(item_key: str) -> str:
        return f"{ALLOWED_SITE_ORIGIN}/app/workshop?item={quote(item_key, safe='')}"

    @staticmethod
    def _archived_item_url(item_key: str) -> str:
        return (
            f"{ALLOWED_SITE_ORIGIN}/app/workshop?item={quote(item_key, safe='')}&status=archived"
        )

    @staticmethod
    def _assert_marker_absent(page, marker: str) -> None:
        if page.get_by_text(marker, exact=True).count() != 0:
            raise BrokerRefusal("private_peer_content_exposed")

    @staticmethod
    def _assert_marker_present(page, marker: str) -> None:
        if page.get_by_text(marker, exact=True).count() < 1:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")

    @staticmethod
    def _record_pass(outcomes: dict[str, JourneyObservation], journey_id: str) -> None:
        if journey_id in outcomes:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        outcomes[journey_id] = _pass_observation(journey_id)

    @staticmethod
    def _record_conditional(
        outcomes: dict[str, JourneyObservation], journey_id: str, note_code: str
    ) -> None:
        if journey_id in outcomes:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        outcomes[journey_id] = _conditional_observation(journey_id, note_code)

    @staticmethod
    def _assert_authenticated_private_workshop(page) -> None:
        """Prove a private Workshop shell without observing member content."""

        PlaywrightBrowserAdapter._assert_site_page(page)
        if (
            urlparse(str(page.url)).path != "/app/workshop"
            or page.locator(".wk-status-banner--preview").count() != 0
            or page.locator(AUTHENTICATED_WORKSHOP_CONTROL).count() != 1
        ):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")

    @staticmethod
    def _version_from_current_item(page) -> SealedValue:
        locator = page.locator("input[name='expected_row_version']")
        if locator.count() != 1:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        return SealedValue(locator.input_value())

    def _assert_owner_item(
        self,
        page,
        handle: _SealedItemHandle,
        marker: str,
        *,
        require_unchanged: bool = False,
    ) -> None:
        page.goto(self._item_url(handle.key.reveal()), wait_until="domcontentloaded")
        self._assert_authenticated_private_workshop(page)
        self._assert_marker_present(page, marker)
        refreshed = self._version_from_current_item(page)
        if require_unchanged and refreshed.reveal() != handle.version.reveal():
            refreshed.clear()
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        handle.version.clear()
        handle.version = refreshed

    def _create_item(self, page, *, marker: str) -> _SealedItemHandle:
        page.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop/add", wait_until="domcontentloaded")
        page.locator("#wk-title").fill(marker)
        page.locator("#wk-wording").fill(f"{marker}-item")
        page.locator("input[name='classification'][value='unclassified']").check()
        page.get_by_role("button", name="Continue").click()
        page.locator("button[name='save_action'][value='confirm']").click()
        href = page.get_by_role("link", name="View in My Information").get_attribute("href")
        item_values = parse_qs(urlparse(str(href or "")).query).get("item", [])
        if len(item_values) != 1 or not item_values[0]:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        handle = _SealedItemHandle(key=SealedValue(item_values[0]), version=SealedValue("pending"))
        self._assert_owner_item(page, handle, marker)
        return handle

    def _post_foreign_mutation(
        self,
        page,
        owner_page,
        *,
        endpoint: str,
        form: Mapping[str, str],
        peer_handle: _SealedItemHandle,
        peer_marker: str,
        expected_denial: str,
    ) -> None:
        self._assert_authenticated_private_workshop(page)
        response = page.context.request.post(
            endpoint,
            form=dict(form),
            headers=SAME_ORIGIN_MUTATION_HEADERS,
            fail_on_status_code=False,
            max_redirects=0,
        )
        try:
            headers = response.headers
            if not isinstance(headers, Mapping):
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
            location = headers.get("location") or headers.get("Location")
            if expected_denial == "update":
                # ``update_item`` returns its neutral, version-fenced conflict
                # form (200, no redirect) for a foreign owner reference.
                expected_status = 200
                expected_location = None
            elif expected_denial == "delete":
                # ``delete_item`` redirects only to the actor's neutral library
                # surface with the standard changed outcome; redirects remain
                # disabled so this worker never follows a foreign reference.
                expected_status = 302
                expected_location = (
                    f"/app/workshop?item={quote(peer_handle.key.reveal(), safe='')}&error=changed"
                )
            else:
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
            if response.status != expected_status or location != expected_location:
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        finally:
            response.dispose()
        # A request-context response does not refresh this page. Revisit the
        # private shell before crediting the denial so a server-side session
        # loss cannot be mistaken for a still-authenticated actor.
        page.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop", wait_until="domcontentloaded")
        self._assert_authenticated_private_workshop(page)
        self._assert_marker_absent(page, peer_marker)
        self._assert_owner_item(
            owner_page, peer_handle, peer_marker, require_unchanged=True
        )

    def _exercise_peer_denials(
        self,
        page,
        owner_page,
        *,
        actor: str,
        actor_marker: str,
        peer: str,
        peer_handle: _SealedItemHandle,
        peer_marker: str,
        outcomes: dict[str, JourneyObservation],
    ) -> None:
        peer_key = peer_handle.key.reveal()
        page.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop", wait_until="domcontentloaded")
        self._assert_authenticated_private_workshop(page)
        self._assert_marker_absent(page, peer_marker)
        self._assert_authenticated_private_workshop(page)
        self._record_pass(outcomes, f"{actor}_cannot_list_{peer}")

        page.goto(self._item_url(peer_key), wait_until="domcontentloaded")
        self._assert_authenticated_private_workshop(page)
        self._assert_marker_absent(page, peer_marker)
        self._assert_authenticated_private_workshop(page)
        self._record_pass(outcomes, f"{actor}_cannot_read_{peer}")

        page.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop", wait_until="domcontentloaded")
        self._assert_authenticated_private_workshop(page)
        self._post_foreign_mutation(
            page,
            owner_page,
            endpoint=f"{ALLOWED_SITE_ORIGIN}/app/workshop/items/{quote(peer_key, safe='')}",
            form={
                "title": actor_marker,
                "wording": f"{actor_marker}-foreign-update",
                "classification": "unclassified",
                "save_action": "confirm",
                "expected_row_version": peer_handle.version.reveal(),
            },
            peer_handle=peer_handle,
            peer_marker=peer_marker,
            expected_denial="update",
        )
        # Workshop's neutral foreign update response is a safe 200 with no
        # structural owner-denial signal.  The independent owner reproof above
        # prevents a false access claim, but cannot distinguish that route from
        # an otherwise identical no-op, so record the approved limitation.
        self._record_conditional(
            outcomes,
            f"{actor}_cannot_update_{peer}",
            "neutral_denial_not_distinguishable",
        )

        page.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop", wait_until="domcontentloaded")
        self._assert_authenticated_private_workshop(page)
        self._post_foreign_mutation(
            page,
            owner_page,
            endpoint=f"{ALLOWED_SITE_ORIGIN}/app/workshop/items/{quote(peer_key, safe='')}/delete",
            form={
                "confirm_delete": "delete",
                "expected_row_version": peer_handle.version.reveal(),
            },
            peer_handle=peer_handle,
            peer_marker=peer_marker,
            expected_denial="delete",
        )
        self._record_pass(outcomes, f"{actor}_cannot_delete_{peer}")

        # Workshop supplies no export control or route.  Do not invent a URL:
        # the canonical export check is an explicit closed limitation instead.
        self._record_conditional(
            outcomes, f"{actor}_cannot_export_{peer}", "feature_surface_unavailable"
        )

        # Workshop exposes no distinct, safe forged-reference contract.  Do
        # not put an owner handle or version into a URL, navigation history, or
        # any retained browser surface merely to manufacture a probe.
        self._record_conditional(
            outcomes,
            f"{actor}_forged_reference_denied",
            "feature_surface_unavailable",
        )

    def _update_item(self, page, handle: _SealedItemHandle, marker: str) -> None:
        item_key = handle.key.reveal()
        page.goto(
            f"{ALLOWED_SITE_ORIGIN}/app/workshop/items/{quote(item_key, safe='')}/edit",
            wait_until="domcontentloaded",
        )
        page.locator("#wk-wording").fill(f"{marker}-updated")
        page.get_by_role("button", name="Continue").click()
        page.locator("button[name='save_action'][value='confirm']").click()
        self._assert_owner_item(page, handle, marker)

    def _archive_and_restore_item(self, page, handle: _SealedItemHandle, marker: str) -> None:
        item_key = handle.key.reveal()
        page.goto(self._item_url(item_key), wait_until="domcontentloaded")
        page.get_by_role("button", name="Archive").click()
        page.goto(self._archived_item_url(item_key), wait_until="domcontentloaded")
        self._assert_marker_present(page, marker)
        refreshed = self._version_from_current_item(page)
        handle.version.clear()
        handle.version = refreshed
        page.get_by_role("button", name="Restore").click()
        self._assert_owner_item(page, handle, marker)

    def _exercise_session_continuity(self, context, page, *, marker: str) -> None:
        page.reload(wait_until="domcontentloaded")
        self._assert_marker_present(page, marker)
        second_tab = context.new_page()
        try:
            second_tab.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop", wait_until="domcontentloaded")
            self._assert_marker_present(second_tab, marker)
        finally:
            second_tab.close()
        page.goto(ALLOWED_SITE_ORIGIN, wait_until="domcontentloaded")
        page.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop", wait_until="domcontentloaded")
        self._assert_marker_present(page, marker)

    def _delete_item(self, page, handle: _SealedItemHandle) -> None:
        item_key = handle.key.reveal()
        page.goto(
            f"{ALLOWED_SITE_ORIGIN}/app/workshop/items/{quote(item_key, safe='')}/delete",
            wait_until="domcontentloaded",
        )
        page.locator("input[name='confirm_delete']").check()
        page.get_by_role("button", name="Delete permanently").click()

    def _observe_item_residue(self, page, marker: str) -> tuple[int, int]:
        page.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop", wait_until="domcontentloaded")
        self._assert_authenticated_private_workshop(page)
        active = page.get_by_text(marker, exact=True).count()
        page.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop?status=archived", wait_until="domcontentloaded")
        self._assert_authenticated_private_workshop(page)
        archived = page.get_by_text(marker, exact=True).count()
        return active, archived

    def _sign_out_safely(self, context, page) -> None:
        second_tab = context.new_page()
        try:
            second_tab.goto(f"{ALLOWED_SITE_ORIGIN}/app/workshop", wait_until="domcontentloaded")
            self._adapter._sign_out(page)
            self._adapter._assert_signed_out_private_baseline(second_tab)
            context.clear_cookies()
            self._adapter._assert_signed_out_private_baseline(second_tab)
        finally:
            second_tab.close()

    def exercise_canonical_journeys(self, identities: Sequence[SealedIdentity]) -> BrowserOutcome:
        if self._cleanup is not None:
            raise BrokerRefusal("sealed_browser_session_closed")
        if len(identities) != 2 or tuple(item.alias for item in identities) != ALLOWED_ALIASES:
            raise BrokerRefusal("exact_alias_pair_required")
        member_a, member_b = identities
        pages = {
            "member_a": self._contexts["member_a"].new_page(),
            "member_b": self._contexts["member_b"].new_page(),
            "switch": self._contexts["switch"].new_page(),
        }
        outcomes = dict(self._preflight_outcomes)
        handles: dict[str, _SealedItemHandle] = {}
        try:
            if set(outcomes) != {
                "clean_client_a_start",
                "clean_client_b_start",
                "clean_signed_out_control_start",
                "signed_out_private_baseline",
            }:
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
            self._adapter._sign_in(pages["member_a"], member_a, self._auth_issuer)
            self._assert_authenticated_private_workshop(pages["member_a"])
            self._record_pass(outcomes, "member_a_first_arrival")
            self._adapter._sign_in(pages["member_b"], member_b, self._auth_issuer)
            self._assert_authenticated_private_workshop(pages["member_b"])
            self._record_pass(outcomes, "member_b_first_arrival")

            member_a_marker = member_a.mail_nickname.reveal()
            member_b_marker = member_b.mail_nickname.reveal()
            handles["member_a"] = self._create_item(pages["member_a"], marker=member_a_marker)
            handles["member_b"] = self._create_item(pages["member_b"], marker=member_b_marker)
            if handles["member_a"].key.reveal() == handles["member_b"].key.reveal():
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
            self._assert_marker_absent(pages["member_a"], member_b_marker)
            self._assert_marker_absent(pages["member_b"], member_a_marker)
            self._record_pass(outcomes, "member_pair_distinct_mapping")
            self._record_pass(outcomes, "simultaneous_member_a_owner_visibility")
            self._record_pass(outcomes, "simultaneous_member_b_owner_visibility")
            self._record_pass(outcomes, "browser_state_member_a_isolated")
            self._record_pass(outcomes, "browser_state_member_b_isolated")

            self._exercise_peer_denials(
                pages["member_a"], pages["member_b"], actor="member_a", actor_marker=member_a_marker,
                peer="member_b", peer_handle=handles["member_b"], peer_marker=member_b_marker, outcomes=outcomes,
            )
            self._exercise_peer_denials(
                pages["member_b"], pages["member_a"], actor="member_b", actor_marker=member_b_marker,
                peer="member_a", peer_handle=handles["member_a"], peer_marker=member_a_marker, outcomes=outcomes,
            )

            self._adapter._sign_in(pages["switch"], member_a, self._auth_issuer)
            self._assert_authenticated_private_workshop(pages["switch"])
            self._assert_marker_present(pages["switch"], member_a_marker)
            self._adapter._sign_out(pages["switch"])
            self._adapter._sign_in(pages["switch"], member_b, self._auth_issuer)
            self._assert_authenticated_private_workshop(pages["switch"])
            self._assert_marker_present(pages["switch"], member_b_marker)
            self._assert_marker_absent(pages["switch"], member_a_marker)
            self._record_pass(outcomes, "account_switch_member_a_to_member_b")
            self._adapter._sign_out(pages["switch"])
            self._adapter._sign_in(pages["switch"], member_a, self._auth_issuer)
            self._assert_authenticated_private_workshop(pages["switch"])
            self._assert_marker_present(pages["switch"], member_a_marker)
            self._assert_marker_absent(pages["switch"], member_b_marker)
            self._record_pass(outcomes, "account_switch_member_b_to_member_a")

            self._update_item(pages["member_a"], handles["member_a"], member_a_marker)
            self._update_item(pages["member_b"], handles["member_b"], member_b_marker)
            self._archive_and_restore_item(pages["member_a"], handles["member_a"], member_a_marker)
            self._archive_and_restore_item(pages["member_b"], handles["member_b"], member_b_marker)
            self._exercise_session_continuity(self._contexts["member_a"], pages["member_a"], marker=member_a_marker)
            self._record_pass(outcomes, "member_a_refresh_owner_only")
            self._record_pass(outcomes, "member_a_second_tab_owner_only")
            self._record_pass(outcomes, "member_a_public_return_owner_only")
            self._exercise_session_continuity(self._contexts["member_b"], pages["member_b"], marker=member_b_marker)
            self._record_pass(outcomes, "member_b_refresh_owner_only")
            self._record_pass(outcomes, "member_b_second_tab_owner_only")
            self._record_pass(outcomes, "member_b_public_return_owner_only")

            self._delete_item(pages["member_a"], handles["member_a"])
            self._delete_item(pages["member_b"], handles["member_b"])
            active_a, archived_a = self._observe_item_residue(pages["member_a"], member_a_marker)
            active_b, archived_b = self._observe_item_residue(pages["member_b"], member_b_marker)

            self._sign_out_safely(self._contexts["member_a"], pages["member_a"])
            self._record_pass(outcomes, "member_a_sign_out_private_absent")
            self._record_pass(outcomes, "member_a_cross_tab_signout_safe")
            self._record_conditional(outcomes, "member_a_expired_session_safe", "session_expiry_not_controllable")
            self._sign_out_safely(self._contexts["member_b"], pages["member_b"])
            self._record_pass(outcomes, "member_b_sign_out_private_absent")
            self._record_pass(outcomes, "member_b_cross_tab_signout_safe")
            self._record_conditional(outcomes, "member_b_expired_session_safe", "session_expiry_not_controllable")
            self._adapter._assert_signed_out_private_baseline(self._signed_out_page)
            self._record_pass(outcomes, "repeat_run_clean_start")
            if set(outcomes) != set(JOURNEY_BY_ID):
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
            return BrowserOutcome(
                journey_outcomes=outcomes,
                created_item_counts={"member_a": 1, "member_b": 1},
                active_residue_counts={"member_a": active_a, "member_b": active_b},
                archived_residue_counts={"member_a": archived_a, "member_b": archived_b},
                clean_start_confirmed=True,
            )
        except (BrokerRefusal, BrokerIndeterminate):
            raise
        except Exception:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
        finally:
            for handle in handles.values():
                handle.clear()

    def destroy_and_verify(self) -> BrowserCleanup:
        if self._cleanup is not None:
            return self._cleanup
        cleanup = PlaywrightBrowserAdapter._close_resources(
            tuple(self._contexts.values()),
            self._browser,
            self._playwright,
            self._workspace,
            expected_contexts=4,
        )
        self._contexts.clear()
        self._browser = None
        self._playwright = None
        self._auth_issuer.clear()
        self._cleanup = cleanup
        return cleanup


class DirectRetirementAdapter:
    """Adapter over the existing independently accepted retirement core."""

    def __init__(self, connection_factory: Callable[[], object] | None = None):
        self._connection_factory = connection_factory or retirement.open_production_connection

    def retire(
        self,
        subjects: Sequence[SealedValue],
        *,
        auth_issuer: SealedValue,
        cutoff: datetime,
    ) -> Mapping[str, object]:
        if len(subjects) != 2:
            raise BrokerRefusal("exact_subject_pair_required")
        connection = None
        committed = False
        commit_attempted = False
        close_failed = False
        report: Mapping[str, object] | None = None
        try:
            connection = self._connection_factory()
            core_report = retirement.execute(
                retirement.SqlRetirementStore(connection),
                mode="retire",
                subjects=[subject.reveal() for subject in subjects],
                issuer=auth_issuer.reveal(),
                cutoff=cutoff,
            )
            if core_report.get("result") != "pass" or core_report.get("state") != "retired":
                raise BrokerIndeterminate("retirement_indeterminate")
            counts = core_report.get("counts")
            if not isinstance(counts, Mapping) or counts.get("eligible_members") != 2:
                raise BrokerIndeterminate("retirement_indeterminate")
            commit_attempted = True
            connection.commit()
            committed = True
            report = {"result": "pass", "state": "retired", "counts": {"retired_members": 2}}
        except BrokerRefusal:
            raise
        except retirement.RetirementRefusal as error:
            raise BrokerRefusal(f"retirement_{error.code}") from None
        except Exception:
            raise BrokerIndeterminate(
                "retirement_commit_indeterminate"
                if commit_attempted
                else "retirement_indeterminate"
            ) from None
        finally:
            if connection is not None:
                if not committed:
                    try:
                        connection.rollback()
                    except Exception:
                        pass
                try:
                    connection.close()
                except Exception:
                    close_failed = True
        if close_failed:
            raise BrokerIndeterminate(
                "retirement_commit_indeterminate"
                if commit_attempted
                else "retirement_indeterminate"
            )
        if report is None:
            raise BrokerIndeterminate("retirement_indeterminate")
        return report


def _require_run_id(value: str) -> str:
    if not SAFE_RUN_ID.fullmatch(value or ""):
        raise BrokerRefusal("invalid_run_id")
    return value


def _require_confirmations(args: argparse.Namespace) -> None:
    if not (
        args.execute
        and args.confirm_exact_two_synthetic_members
        and args.confirm_no_production_proof
        and args.confirm_retirement_handoff
    ):
        raise BrokerRefusal("sealed_broker_confirmations_required")


def _validate_graph_issuer(value: SealedValue) -> None:
    if not SAFE_GRAPH_ISSUER.fullmatch(value.reveal()) or not value.reveal().lower().endswith(
        ".onmicrosoft.com"
    ):
        raise BrokerRefusal("graph_issuer_invalid")


def _generate_password(choice: Callable[[str], str] = secrets.choice) -> SealedValue:
    # Each required category is present before the remaining random characters.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*"
    required = "Aa1!"
    value = required + "".join(choice(alphabet) for _ in range(28))
    return SealedValue(value)


def _generate_identities(
    graph_issuer: SealedValue,
    *,
    run_id: str,
    choice: Callable[[str], str] = secrets.choice,
) -> tuple[SealedIdentity, SealedIdentity]:
    _require_run_id(run_id)
    _validate_graph_issuer(graph_issuer)
    # Login local parts and Graph mail nicknames have bounded provider limits.
    # This deterministic run-scoped fingerprint never leaves worker memory and
    # keeps both identifiers well below those limits even for a maximum run ID.
    run_fingerprint = hashlib.sha256(run_id.encode("ascii")).hexdigest()[:24]
    generated = []
    for alias in ALLOWED_ALIASES:
        local_part = f"psqa-{run_fingerprint}-{alias}"
        # Keep the outward-facing alias stable while using a conservative
        # mail-nickname character set for the provider-side ordinary customer.
        mail_nickname = local_part.replace("_", "-")
        generated.append(
            SealedIdentity(
                alias=alias,
                login_identifier=SealedValue(
                    f"{local_part}@{graph_issuer.reveal().lower()}"
                ),
                password=_generate_password(choice),
                mail_nickname=SealedValue(mail_nickname),
            )
        )
    return generated[0], generated[1]


def _validate_browser_outcome(outcome: BrowserOutcome, cleanup: BrowserCleanup) -> None:
    all_journeys = set(JOURNEY_BY_ID)
    conditional_outcomes: dict[str, str] = {}
    if set(outcome.journey_outcomes) != all_journeys:
        raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
    for journey_id, observation in outcome.journey_outcomes.items():
        if not isinstance(observation, JourneyObservation):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        if observation.status == "pass":
            if (
                observation.observed_outcome != JOURNEY_BY_ID[journey_id].expected_outcome
                or observation.note_code != "none"
            ):
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        elif observation.status == "conditional":
            if observation.observed_outcome != "limitation_recorded":
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
            conditional_outcomes[journey_id] = observation.note_code
        else:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
    # This attended package has a fixed Conditional ceiling.  Treat its exact
    # mapping as a completion requirement rather than a permissive allowlist:
    # missing, substituted, or extra limitations cannot reach retirement.
    if conditional_outcomes != REQUIRED_CONDITIONAL_OUTCOMES:
        raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
    if (
        outcome.created_item_counts != {"member_a": 1, "member_b": 1}
        or outcome.active_residue_counts != {"member_a": 0, "member_b": 0}
        or outcome.archived_residue_counts != {"member_a": 0, "member_b": 0}
        or not outcome.clean_start_confirmed
        or cleanup != BrowserCleanup(destroyed_contexts=4, temporary_root_removed=True)
    ):
        raise BrokerIndeterminate("sealed_browser_operation_indeterminate")


def run_broker(
    *,
    run_id: str,
    cutoff: datetime,
    graph: GraphAdapter,
    browser: BrowserAdapter,
    retirement_adapter: RetirementAdapter,
    choice: Callable[[str], str] = secrets.choice,
) -> Mapping[str, object]:
    """Execute one exact-two sealed lifecycle and return an allowlisted report."""

    _require_run_id(run_id)
    identities: tuple[SealedIdentity, SealedIdentity] = ()
    graph_issuer: SealedValue | None = None
    auth_issuer: SealedValue | None = None
    session: AttendedBrowserSession | None = None
    created = 0
    phase = "browser_preflight"
    try:
        session = browser.prepare_attended_session()
        auth_issuer = session.auth_issuer()
        graph_issuer = graph.resolve_graph_issuer()
        PlaywrightBrowserAdapter.verify_auth_graph_tenant_binding(auth_issuer, graph_issuer)
        identities = _generate_identities(graph_issuer, run_id=run_id, choice=choice)
        phase = "graph"
        for identity in identities:
            subject = graph.create_customer(identity, graph_issuer=graph_issuer)
            try:
                identity.subject = SealedValue(str(UUID(subject)))
            except (TypeError, ValueError, AttributeError):
                raise BrokerIndeterminate("graph_creation_indeterminate") from None
            created += 1
        if created != 2 or identities[0].subject is None or identities[1].subject is None:
            raise BrokerIndeterminate("graph_creation_indeterminate")
        if identities[0].subject.reveal() == identities[1].subject.reveal():
            raise BrokerIndeterminate("graph_creation_indeterminate")
        phase = "browser_journeys"
        browser_outcome = session.exercise_canonical_journeys(identities)
        phase = "browser_cleanup"
        browser_cleanup = session.destroy_and_verify()
        _validate_browser_outcome(browser_outcome, browser_cleanup)
        phase = "retirement"
        retirement_report = retirement_adapter.retire(
            [identities[0].subject, identities[1].subject],
            auth_issuer=auth_issuer,
            cutoff=cutoff,
        )
        if (
            retirement_report.get("result") != "pass"
            or retirement_report.get("state") != "retired"
            or retirement_report.get("counts") != {"retired_members": 2}
        ):
            raise BrokerIndeterminate("retirement_indeterminate")
        return {
            "result": "conditional",
            "state": "retired_pending_external_deletion",
            "counts": {
                "requested_identities": 2,
                "provisioned_identities": 2,
                "member_arrivals": 2,
                "account_switches": 2,
                "canonical_journeys": len(browser_outcome.journey_outcomes),
                "conditional_journeys": len(REQUIRED_CONDITIONAL_OUTCOMES),
                "created_items": sum(browser_outcome.created_item_counts.values()),
                "active_residue": sum(browser_outcome.active_residue_counts.values()),
                "destroyed_contexts": browser_cleanup.destroyed_contexts,
                "retired_members": 2,
            },
        }
    except BrokerRefusal as error:
        if phase in {"browser_preflight", "graph"} and not created:
            raise error
        if phase == "graph":
            raise BrokerIndeterminate("graph_creation_indeterminate") from None
        if phase.startswith("browser"):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
        raise BrokerIndeterminate("retirement_indeterminate") from None
    except BrokerIndeterminate:
        raise
    except Exception:
        raise BrokerIndeterminate(
            "graph_creation_indeterminate" if created else "sealed_broker_operation_failed"
        ) from None
    finally:
        if session is not None:
            try:
                session.destroy_and_verify()
            except BrokerIndeterminate:
                raise
        for identity in identities:
            identity.clear()
        if graph_issuer is not None:
            graph_issuer.clear()
        if auth_issuer is not None:
            auth_issuer.clear()


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        self.exit(2, "refused: invalid command syntax\n")


def _parser() -> argparse.ArgumentParser:
    parser = _SafeArgumentParser(
        description="Run the local sealed synthetic-QA credential lifecycle without identity output."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)
    subparsers.add_parser("plan", help="emit the structural lifecycle plan")
    run = subparsers.add_parser("run", help="run a separately authorized lifecycle")
    run.add_argument("--run-id", required=True)
    run.add_argument("--created-after-utc", required=True)
    run.add_argument("--execute", action="store_true")
    run.add_argument("--confirm-exact-two-synthetic-members", action="store_true")
    run.add_argument("--confirm-no-production-proof", action="store_true")
    run.add_argument("--confirm-retirement-handoff", action="store_true")
    return parser


def _emit(report: Mapping[str, object]) -> None:
    print(json.dumps(report, sort_keys=True))


def main(
    argv: Sequence[str] | None = None,
    *,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    graph_factory: Callable[[], GraphAdapter] = MicrosoftGraphAdapter,
    browser_factory: Callable[[], BrowserAdapter] = PlaywrightBrowserAdapter,
    retirement_factory: Callable[[], RetirementAdapter] = DirectRetirementAdapter,
) -> int:
    args = _parser().parse_args(argv)
    if args.mode == "plan":
        _emit(
            {
                "result": "planned",
                "counts": {"customer_identities": 2, "contexts": 4, "journeys": len(JOURNEYS)},
                "external_deletion": "withheld",
            }
        )
        return 0

    report: Mapping[str, object] = {
        "result": "refused",
        "reason_code": "sealed_broker_operation_failed",
    }
    try:
        _require_confirmations(args)
        cutoff = retirement.parse_cutoff(args.created_after_utc, clock())
        report = run_broker(
            run_id=args.run_id,
            cutoff=cutoff,
            graph=graph_factory(),
            browser=browser_factory(),
            retirement_adapter=retirement_factory(),
        )
        return_code = 0
    except BrokerRefusal as error:
        report = {"result": "refused", "reason_code": error.code}
        return_code = 2
    except retirement.RetirementRefusal as error:
        report = {"result": "refused", "reason_code": error.code}
        return_code = 2
    except BrokerIndeterminate as error:
        report = {"result": "indeterminate", "reason_code": error.code}
        return_code = 3
    except Exception:
        report = {
            "result": "refused",
            "reason_code": "sealed_broker_operation_failed",
        }
        return_code = 2
    finally:
        _emit(report)
    return return_code


__all__ = [
    "ALLOWED_ALIASES",
    "ALLOWED_GRAPH_ENDPOINT",
    "ALLOWED_SITE_ORIGIN",
    "AzureCliGraphTokenProvider",
    "BrokerIndeterminate",
    "BrokerRefusal",
    "BrowserCleanup",
    "BrowserOutcome",
    "DirectRetirementAdapter",
    "MicrosoftGraphAdapter",
    "PlaywrightBrowserAdapter",
    "REQUIRED_CONDITIONAL_OUTCOMES",
    "SealedIdentity",
    "SealedValue",
    "main",
    "run_broker",
]

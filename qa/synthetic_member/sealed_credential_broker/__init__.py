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
import getpass
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from qa.synthetic_member import identity_retirement as retirement


ALLOWED_SITE_ORIGIN = "https://peerslate.com"
ALLOWED_GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0/users"
ALLOWED_GRAPH_ORGANIZATION_ENDPOINT = (
    "https://graph.microsoft.com/v1.0/organization?$select=id,verifiedDomains"
)
ALLOWED_ALIASES = ("member_a", "member_b")
SAFE_RUN_ID = re.compile(r"^[a-z0-9][a-z0-9-]{7,63}$")
SAFE_MAILBOX = re.compile(r"^[^@\s]{1,64}@[A-Za-z0-9.-]{1,190}$")
SAFE_GRAPH_ISSUER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{2,253}$")
MAX_SECRET_LENGTH = 512
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
class BrowserOutcome:
    arrivals: int
    switches: int
    destroyed_contexts: int


class GraphAdapter(Protocol):
    def create_customer(self, identity: SealedIdentity, *, graph_issuer: SealedValue) -> str:
        """Create one customer and return only its opaque Graph id to the worker."""


class BrowserAdapter(Protocol):
    def preflight(self) -> None:
        """Refuse unsafe browser runtime state before any identity creation."""

    def exercise_sign_in_and_switch(
        self, identities: Sequence[SealedIdentity], *, auth_issuer: SealedValue
    ) -> BrowserOutcome:
        """Drive private sign-in and A-to-B/B-to-A switching without capture."""


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

    def _verify_tenant_binding(self, token: SealedValue, graph_issuer: SealedValue) -> None:
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
    """No-capture browser adapter with an explicit disposable engine workspace."""

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

    def _wait_for_member_arrival(self, page) -> None:
        page.wait_for_url(re.compile(r"^https://peerslate\\.com/app(?:[/?#]|$)"), timeout=60000)

    @staticmethod
    def _assert_expected_identity_host(page, auth_issuer: SealedValue) -> None:
        expected_host = urlparse(auth_issuer.reveal()).hostname
        actual_host = urlparse(str(page.url)).hostname
        if not expected_host or actual_host != expected_host:
            raise BrokerRefusal("unexpected_identity_host")

    def _sign_in(self, page, identity: SealedIdentity, auth_issuer: SealedValue) -> None:
        page.goto(
            f"{ALLOWED_SITE_ORIGIN}/.auth/login/aad?post_login_redirect_uri=%2Fapp",
            wait_until="domcontentloaded",
        )
        self._assert_expected_identity_host(page, auth_issuer)
        page.locator("input[type='email']").fill(identity.login_identifier.reveal())
        page.locator("input[type='submit']").click()
        page.locator("input[type='password']").fill(identity.password.reveal())
        page.locator("input[type='submit']").click()
        self._wait_for_member_arrival(page)

    def _sign_out(self, page) -> None:
        page.goto(
            f"{ALLOWED_SITE_ORIGIN}/.auth/logout?post_logout_redirect_uri=%2F",
            wait_until="domcontentloaded",
        )

    @staticmethod
    def _close_contexts(contexts: list[object]) -> bool:
        close_failed = False
        while contexts:
            try:
                contexts.pop().close()
            except Exception:
                close_failed = True
        return close_failed

    def exercise_sign_in_and_switch(
        self, identities: Sequence[SealedIdentity], *, auth_issuer: SealedValue
    ) -> BrowserOutcome:
        if len(identities) != 2 or tuple(item.alias for item in identities) != ALLOWED_ALIASES:
            raise BrokerRefusal("exact_alias_pair_required")
        self.preflight()

        contexts: list[object] = []
        browser = None
        playwright = None
        workspace: Path | None = None
        cleanup_failed = False
        try:
            workspace = Path(
                tempfile.mkdtemp(prefix=BROWSER_TEMP_PREFIX, dir=str(self._workspace_root))
            )
            child_environment = self._browser_environment(workspace)
            # Playwright's driver and Chromium receive only this run-scoped
            # environment. Its unavoidable engine/profile/temp files remain in
            # the one workspace and are deleted and rechecked before success.
            with _isolated_child_environment(child_environment):
                playwright = self._playwright_factory()
                browser = playwright.chromium.launch(
                    headless=False,
                    downloads_path=str(workspace),
                    env=child_environment,
                )
            member_a, member_b = identities
            for identity in (member_a, member_b):
                context = browser.new_context(accept_downloads=False)
                contexts.append(context)
                self._sign_in(context.new_page(), identity, auth_issuer)
            switch_context = browser.new_context(accept_downloads=False)
            contexts.append(switch_context)
            switch_page = switch_context.new_page()
            self._sign_in(switch_page, member_a, auth_issuer)
            self._sign_out(switch_page)
            self._sign_in(switch_page, member_b, auth_issuer)
            self._sign_out(switch_page)
            self._sign_in(switch_page, member_a, auth_issuer)
            if self._close_contexts(contexts):
                raise BrokerIndeterminate("sealed_browser_cleanup_indeterminate")
            browser.close()
            browser = None
            playwright.stop()
            playwright = None
            return BrowserOutcome(arrivals=2, switches=2, destroyed_contexts=3)
        except (BrokerRefusal, BrokerIndeterminate):
            raise
        except Exception:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
        finally:
            cleanup_failed = self._close_contexts(contexts) or cleanup_failed
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
            if workspace is not None:
                try:
                    shutil.rmtree(workspace)
                    if workspace.exists():
                        cleanup_failed = True
                except OSError:
                    cleanup_failed = True
            if cleanup_failed:
                raise BrokerIndeterminate("sealed_browser_cleanup_indeterminate")


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


def _require_interactive(stdin_isatty: Callable[[], bool]) -> None:
    if not stdin_isatty():
        raise BrokerRefusal("interactive_terminal_required")


def _read_secret(reader: Callable[[str], str], prompt: str, *, code: str) -> SealedValue:
    try:
        value = reader(prompt)
    except Exception:
        raise BrokerRefusal(code) from None
    return SealedValue(value)


def _validate_mailbox(value: SealedValue) -> None:
    if not SAFE_MAILBOX.fullmatch(value.reveal()):
        raise BrokerRefusal("sealed_mailbox_invalid")


def _validate_graph_issuer(value: SealedValue) -> None:
    if not SAFE_GRAPH_ISSUER.fullmatch(value.reveal()) or not value.reveal().lower().endswith(
        ".onmicrosoft.com"
    ):
        raise BrokerRefusal("graph_issuer_invalid")


def _derive_login_identifier(mailbox: SealedValue, *, run_id: str, alias: str) -> SealedValue:
    local, separator, domain = mailbox.reveal().partition("@")
    if not separator or not domain:
        raise BrokerRefusal("sealed_mailbox_invalid")
    local = local.split("+", 1)[0]
    return SealedValue(f"{local}+psqa-{run_id}-{alias}@{domain}")


def _generate_password(choice: Callable[[str], str] = secrets.choice) -> SealedValue:
    # Each required category is present before the remaining random characters.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*"
    required = "Aa1!"
    value = required + "".join(choice(alphabet) for _ in range(28))
    return SealedValue(value)


def _generate_identities(
    mailbox: SealedValue,
    *,
    run_id: str,
    choice: Callable[[str], str] = secrets.choice,
) -> tuple[SealedIdentity, SealedIdentity]:
    _validate_mailbox(mailbox)
    generated = []
    for alias in ALLOWED_ALIASES:
        generated.append(
            SealedIdentity(
                alias=alias,
                login_identifier=_derive_login_identifier(mailbox, run_id=run_id, alias=alias),
                password=_generate_password(choice),
                mail_nickname=SealedValue(f"psqa-{run_id}-{alias}"),
            )
        )
    return generated[0], generated[1]


def _require_auth_issuer(value: SealedValue) -> SealedValue:
    issuer = value.reveal().strip().rstrip("/")
    parsed = urlparse(issuer)
    if (
        not issuer
        or len(issuer) > MAX_SECRET_LENGTH
        or parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise BrokerRefusal("approved_auth_issuer_required")
    value.clear()
    return SealedValue(issuer)


def _validate_browser_outcome(outcome: BrowserOutcome) -> None:
    if outcome != BrowserOutcome(arrivals=2, switches=2, destroyed_contexts=3):
        raise BrokerIndeterminate("sealed_browser_operation_indeterminate")


def run_broker(
    *,
    run_id: str,
    cutoff: datetime,
    graph_issuer: SealedValue,
    mailbox: SealedValue,
    auth_issuer: SealedValue,
    graph: GraphAdapter,
    browser: BrowserAdapter,
    retirement_adapter: RetirementAdapter,
    choice: Callable[[str], str] = secrets.choice,
) -> Mapping[str, object]:
    """Execute one exact-two sealed lifecycle and return an allowlisted report."""

    _require_run_id(run_id)
    _validate_graph_issuer(graph_issuer)
    identities = _generate_identities(mailbox, run_id=run_id, choice=choice)
    created = 0
    phase = "preflight"
    try:
        browser.preflight()
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
        phase = "browser"
        _validate_browser_outcome(
            browser.exercise_sign_in_and_switch(identities, auth_issuer=auth_issuer)
        )
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
            "result": "pass",
            "state": "retired_pending_external_deletion",
            "counts": {
                "requested_identities": 2,
                "provisioned_identities": 2,
                "member_arrivals": 2,
                "account_switches": 2,
                "retired_members": 2,
            },
        }
    except BrokerRefusal as error:
        if phase == "preflight" or (phase == "graph" and not created):
            raise error
        if phase == "graph":
            raise BrokerIndeterminate("graph_creation_indeterminate") from None
        if phase == "browser":
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
        raise BrokerIndeterminate("retirement_indeterminate") from None
    except BrokerIndeterminate:
        raise
    except Exception:
        raise BrokerIndeterminate(
            "graph_creation_indeterminate" if created else "sealed_broker_operation_failed"
        ) from None
    finally:
        for identity in identities:
            identity.clear()
        mailbox.clear()
        graph_issuer.clear()
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
    secret_reader: Callable[[str], str] = getpass.getpass,
    stdin_isatty: Callable[[], bool] = sys.stdin.isatty,
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
                "counts": {"customer_identities": 2, "switches": 2},
                "external_deletion": "withheld",
            }
        )
        return 0

    report: Mapping[str, object] = {
        "result": "refused",
        "reason_code": "sealed_broker_operation_failed",
    }
    auth_issuer: SealedValue | None = None
    graph_issuer: SealedValue | None = None
    mailbox: SealedValue | None = None
    authorization_ref: SealedValue | None = None
    try:
        _require_confirmations(args)
        cutoff = retirement.parse_cutoff(args.created_after_utc, clock())
        _require_interactive(stdin_isatty)
        authorization_ref = _read_secret(
            secret_reader,
            "Current operation authorization reference: ",
            code="authorization_reference_required",
        )
        retirement.validate_authorization_ref(authorization_ref.reveal())
        authorization_ref.clear()
        authorization_ref = None
        auth_issuer = _require_auth_issuer(
            _read_secret(secret_reader, "Approved PeerSlate auth issuer: ", code="auth_issuer_required")
        )
        graph_issuer = _read_secret(secret_reader, "External ID tenant issuer: ", code="graph_issuer_required")
        mailbox = _read_secret(secret_reader, "Run-scoped QA mailbox: ", code="sealed_mailbox_required")
        report = run_broker(
            run_id=args.run_id,
            cutoff=cutoff,
            graph_issuer=graph_issuer,
            mailbox=mailbox,
            auth_issuer=auth_issuer,
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
        for value in (authorization_ref, mailbox, graph_issuer, auth_issuer):
            if value is not None:
                value.clear()
        _emit(report)
    return return_code


__all__ = [
    "ALLOWED_ALIASES",
    "ALLOWED_GRAPH_ENDPOINT",
    "ALLOWED_SITE_ORIGIN",
    "AzureCliGraphTokenProvider",
    "BrokerIndeterminate",
    "BrokerRefusal",
    "BrowserOutcome",
    "DirectRetirementAdapter",
    "MicrosoftGraphAdapter",
    "PlaywrightBrowserAdapter",
    "SealedIdentity",
    "SealedValue",
    "main",
    "run_broker",
]

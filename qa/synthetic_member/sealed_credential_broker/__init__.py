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
import importlib
import importlib.metadata
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

from qa.synthetic_member import identity_retirement as retirement
from qa.synthetic_member.contracts import JOURNEY_BY_ID, JOURNEYS, NOTE_CODES


ALLOWED_SITE_ORIGIN = "https://peerslate.com"
ALLOWED_SIGN_IN_ENDPOINT = (
    f"{ALLOWED_SITE_ORIGIN}/.auth/login/aad?post_login_redirect_uri=%2Fapp"
)
OWNER_AUTHORIZATION_REF = (
    "session:01a04348-7e3e-7a11-a443-752498be91b5/"
    "owner-authorization:2026-08-28/workshop-fg-sealed-private-proof-complete-lifecycle"
)
AZURE_SUBSCRIPTION_ID = "bd0ecf48-6940-4fd3-9687-3eaf72469d67"
AZURE_RESOURCE_GROUP = "peerslate"
AZURE_WEBAPP_NAME = "peerslate-pete"
ALLOWED_GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0/users"
ALLOWED_GRAPH_ORGANIZATION_ENDPOINT = (
    "https://graph.microsoft.com/v1.0/organization?$select=id,verifiedDomains"
)
ALLOWED_GRAPH_DELETED_ITEMS_ENDPOINT = (
    "https://graph.microsoft.com/v1.0/directory/deletedItems"
)
GRAPH_CUSTOMER_SHAPE_SELECT = (
    "id,accountEnabled,userType,creationType,displayName,mailNickname,"
    "identities,createdDateTime,passwordPolicies"
)
ALLOWED_ALIASES = ("member_a", "member_b")
REQUIRED_CONDITIONAL_OUTCOMES = {
    "member_a_cannot_update_member_b": "neutral_denial_not_distinguishable",
    "member_b_cannot_update_member_a": "neutral_denial_not_distinguishable",
    "member_a_cannot_delete_member_b": "neutral_denial_not_distinguishable",
    "member_b_cannot_delete_member_a": "neutral_denial_not_distinguishable",
    "member_a_forged_reference_denied": "feature_surface_unavailable",
    "member_b_forged_reference_denied": "feature_surface_unavailable",
    "member_a_cannot_export_member_b": "feature_surface_unavailable",
    "member_b_cannot_export_member_a": "feature_surface_unavailable",
    "member_a_expired_session_safe": "session_expiry_not_controllable",
    "member_b_expired_session_safe": "session_expiry_not_controllable",
}
SAFE_RUN_ID = re.compile(r"^[a-z0-9][a-z0-9-]{7,63}$")
SAFE_GRAPH_ISSUER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{2,253}$")
SAFE_GRAPH_MAIL_NICKNAME = re.compile(r"^[a-z0-9-]{1,64}$")
MAX_SECRET_LENGTH = 512
MAX_TOKEN_LENGTH = 32768
ALLOWED_AUTH_HOST_SUFFIXES = (".ciamlogin.com",)
SAFE_TENANT_LABEL = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
AUTHENTICATED_WORKSHOP_CONTROL = (
    "div.platform-account[data-ps-auth-control='authenticated']:not([hidden])"
)
GRAPH_AUDIENCES = {
    "00000003-0000-0000-c000-000000000000",
    "https://graph.microsoft.com",
    "https://graph.microsoft.com/",
}
REQUIRED_GRAPH_SCOPES = frozenset(
    {"User.Read", "User.ReadWrite.All", "User.DeleteRestore.All"}
)
ELIGIBLE_GRAPH_ROLE_TEMPLATE_IDS = frozenset(
    {
        # User Administrator is the least role with the complete
        # create + active-delete + deleted-item-purge action intersection.
        "fe930be7-5e62-47db-91af-98c3a49a38b1",
    }
)
BROWSER_TEMP_PREFIX = "peerslate-sealed-browser-"
BROWSER_PROBE_PREFIX = "peerslate-sealed-browser-probe-"
PLAYWRIGHT_LOCK_PATH = Path(__file__).with_name("playwright-runtime.lock.json")
WORKSHOP_HISTORY_NOTE = (
    "Some older AI-assisted versions may show refined wording under "
    "\u201cSource wording on record\u201d because the original wording was not "
    "retained at the time. PeerSlate does not infer or backfill wording it cannot prove."
)
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

    def __init__(self, value: str, *, max_length: int = MAX_SECRET_LENGTH):
        if (
            not isinstance(value, str)
            or not value
            or not isinstance(max_length, int)
            or max_length < 1
            or len(value) > max_length
        ):
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


@dataclass
class AuthorityBinding:
    """Validated production routing values held only in worker memory."""

    oidc_issuer: SealedValue
    authorization_origin: SealedValue
    tenant_id: SealedValue
    tenant_label: SealedValue

    def clear(self) -> None:
        self.oidc_issuer.clear()
        self.authorization_origin.clear()
        self.tenant_id.clear()
        self.tenant_label.clear()

    def __repr__(self) -> str:
        return "AuthorityBinding(material=<sealed>)"


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
    edit_counts: Mapping[str, int]
    retained_version_counts: Mapping[str, int]
    retained_source_proof_counts: Mapping[str, int]
    downstream_disclosure_counts: Mapping[str, int]
    active_residue_counts: Mapping[str, int]
    archived_residue_counts: Mapping[str, int]
    clean_start_confirmed: bool


@dataclass(frozen=True)
class BrowserPreflight:
    locked_runtime: bool
    probe_launch_closed: bool
    probe_root_removed: bool
    prepared_contexts: int
    signed_out_private_baseline: bool


@dataclass(frozen=True)
class BrowserCleanup:
    destroyed_contexts: int
    temporary_root_removed: bool


EXPECTED_BROWSER_CLEANUP = BrowserCleanup(
    destroyed_contexts=4,
    temporary_root_removed=True,
)


@dataclass(frozen=True)
class GraphDeletionOutcome:
    soft_deleted: int
    soft_state_proofs: int
    permanently_deleted: int
    final_absence_proofs: int


@dataclass
class GraphCreationOutcome:
    """Finite, non-reflective result of one and only one customer POST."""

    state: str
    attempted_after: datetime
    subject: SealedValue | None = None

    def __post_init__(self) -> None:
        if self.state not in {
            "known_created",
            "ambiguous_maybe_created",
            "known_not_created",
        }:
            raise BrokerRefusal("graph_creation_outcome_invalid")
        if (
            not isinstance(self.attempted_after, datetime)
            or self.attempted_after.tzinfo is None
            or self.attempted_after.utcoffset() is None
        ):
            raise BrokerRefusal("graph_creation_outcome_invalid")
        if (self.state == "known_created") != (self.subject is not None):
            raise BrokerRefusal("graph_creation_outcome_invalid")
        if self.subject is not None and not isinstance(self.subject, SealedValue):
            raise BrokerRefusal("graph_creation_outcome_invalid")

    def clear(self) -> None:
        if self.subject is not None:
            self.subject.clear()

    def __repr__(self) -> str:
        return (
            "GraphCreationOutcome("
            f"state={self.state!r}, attempted_after=<structural>, subject=<sealed>)"
        )


@dataclass
class _GraphLifecycleLedgerEntry:
    """Finite, worker-local mutation ledger for one exact generated alias."""

    alias: str
    create: str = "not_attempted"
    soft: str = "not_attempted"
    active_probe: str = "not_attempted"
    deleted_probe: str = "not_attempted"
    purge: str = "not_attempted"
    final_active_probe: str = "not_attempted"
    final_deleted_probe: str = "not_attempted"


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


class AuthorityAdapter(Protocol):
    def resolve(self) -> AuthorityBinding:
        """Bind the fixed App Service, live OIDC metadata, and exact tenant."""


class GraphAdapter(Protocol):
    def prepare(self, authority: AuthorityBinding) -> SealedValue:
        """Preflight exact tenant, delegated privileges, role, organization, and domain."""

    def create_customer(
        self,
        identity: SealedIdentity,
        *,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> GraphCreationOutcome:
        """Attempt one customer POST and return its finite sealed ledger state."""

    def prove_customer_absence(
        self,
        identities: Sequence[SealedIdentity],
        *,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> int:
        """Run four bounded exact-filter zero-result reads before either POST."""

    def contain_partial_creation(
        self,
        identities: Sequence[SealedIdentity],
        *,
        creation_states: Mapping[str, str],
        attempted_after: Mapping[str, datetime],
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> None:
        """Best-effort one-pass containment after an ambiguous create attempt."""

    def delete_exact_pair(
        self,
        subjects: Sequence[SealedValue],
        *,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> GraphDeletionOutcome:
        """Soft-delete, prove, permanently delete, and prove exact-pair absence."""

    def clear(self) -> None:
        """Clear any worker-local delegated caller binding."""


class AttendedBrowserSession(Protocol):
    def pre_graph_proof(self) -> BrowserPreflight:
        """Return the closed structural runtime/baseline proof."""

    def exercise_canonical_journeys(
        self, identities: Sequence[SealedIdentity]
    ) -> BrowserOutcome:
        """Complete the fixed journey matrix and application item lifecycle."""

    def destroy_and_verify(self) -> BrowserCleanup:
        """Destroy every context and the disposable root before retirement."""


class BrowserAdapter(Protocol):
    def prepare_attended_session(self, authority: AuthorityBinding) -> AttendedBrowserSession:
        """Launch and prove the no-capture browser baseline before Graph mutation."""


class RetirementAdapter(Protocol):
    def retire(
        self,
        subjects: Sequence[SealedValue],
        *,
        oidc_issuer: SealedValue,
        cutoff: datetime,
    ) -> Mapping[str, object]:
        """Run the accepted exact-two retirement core without echoing subjects."""


class _NoRedirectHandler(HTTPRedirectHandler):
    """Refuse every redirect, including redirects on nominally read-only calls."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        del req, fp, code, msg, headers, newurl
        return None


def _open_without_redirect(request: Request, *, timeout: int):
    return build_opener(_NoRedirectHandler()).open(request, timeout=timeout)


def _azure_child_environment(
    environment: Mapping[str, str] | None,
) -> dict[str, str]:
    source = environment if environment is not None else os.environ
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
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
    )
    child = {name: str(source[name]) for name in allowed if source.get(name)}
    azure_config = source.get("AZURE_CONFIG_DIR")
    if not azure_config and environment is None:
        azure_config = str(Path.home() / ".azure")
    if azure_config:
        child["AZURE_CONFIG_DIR"] = str(azure_config)
    child.update(
        {
            "AZURE_CORE_COLLECT_TELEMETRY": "false",
            "AZURE_CORE_ONLY_SHOW_ERRORS": "true",
            "AZURE_EXTENSION_USE_DYNAMIC_INSTALL": "no",
        }
    )
    return child


@dataclass(frozen=True)
class AzureCliRuntime:
    """One validated Azure CLI Python runtime; the discovered .cmd is never run."""

    python_executable: Path

    def command(self, arguments: Sequence[str]) -> tuple[str, ...]:
        return (
            str(self.python_executable),
            "-I",
            "-B",
            "-m",
            "azure.cli",
            *arguments,
        )


def _resolve_azure_cli_runtime(
    resolver: Callable[[str], str | None],
) -> AzureCliRuntime:
    """Bind the installed CLI2 Python executable before any Azure child starts."""

    try:
        discovered = resolver("az")
        if not isinstance(discovered, str) or not discovered:
            raise ValueError("Azure CLI discovery unavailable")
        az_command = Path(discovered).resolve(strict=True)
        if (
            not az_command.is_file()
            or az_command.name.lower() != "az.cmd"
            or az_command.parent.name.lower() != "wbin"
        ):
            raise ValueError("unexpected Azure CLI launcher")
        runtime_root = az_command.parent.parent.resolve(strict=True)
        expected_launcher = (runtime_root / "wbin" / "az.cmd").resolve(strict=True)
        if runtime_root.name.lower() != "cli2" or expected_launcher != az_command:
            raise ValueError("unexpected Azure CLI layout")
        python_executable = (runtime_root / "python.exe").resolve(strict=True)
        if (
            not python_executable.is_file()
            or python_executable.name.lower() != "python.exe"
        ):
            raise ValueError("Azure CLI Python unavailable")
        python_executable.relative_to(runtime_root)
    except (OSError, TypeError, ValueError):
        raise BrokerRefusal("production_authority_unavailable") from None
    return AzureCliRuntime(python_executable=python_executable)


def _run_azure_json(
    runner: Callable[..., object],
    command: Sequence[str],
    *,
    environment: Mapping[str, str] | None,
) -> object:
    try:
        result = runner(
            tuple(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
            env=_azure_child_environment(environment),
        )
    except (OSError, subprocess.SubprocessError):
        raise BrokerRefusal("production_authority_unavailable") from None
    raw = str(getattr(result, "stdout", "") or "")
    if getattr(result, "returncode", 1) != 0 or not raw or len(raw) > 65536:
        raise BrokerRefusal("production_authority_unavailable")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise BrokerRefusal("production_authority_unavailable") from None


def _validated_https_url(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_SECRET_LENGTH:
        raise BrokerRefusal(code)
    try:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or not host
            or parsed.port is not None
            or parsed.username
            or parsed.password
            or parsed.netloc != host
            or parsed.query
            or parsed.fragment
            or not any(host.endswith(suffix) for suffix in ALLOWED_AUTH_HOST_SUFFIXES)
        ):
            raise ValueError("unapproved authority")
    except (TypeError, ValueError):
        raise BrokerRefusal(code) from None
    return value


def _tenant_from_oidc_authority(value: str, *, require_uuid_host: bool) -> str:
    parsed = urlparse(value)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or parts[1] != "v2.0":
        raise BrokerRefusal("production_oidc_authority_mismatch")
    try:
        tenant_id = str(UUID(parts[0]))
    except (TypeError, ValueError, AttributeError):
        raise BrokerRefusal("production_oidc_authority_mismatch") from None
    if parts[0] != tenant_id or parsed.path != f"/{tenant_id}/v2.0":
        raise BrokerRefusal("production_oidc_authority_mismatch")
    host = (parsed.hostname or "").lower()
    if require_uuid_host and host != f"{tenant_id}.ciamlogin.com":
        raise BrokerRefusal("production_oidc_authority_mismatch")
    return tenant_id


class AzureAppAuthorityResolver:
    """Read and bind only the fixed production App Service authentication authority."""

    auth_command = (
        "webapp",
        "auth",
        "show",
        "--subscription",
        AZURE_SUBSCRIPTION_ID,
        "--resource-group",
        AZURE_RESOURCE_GROUP,
        "--name",
        AZURE_WEBAPP_NAME,
        "--query",
        "{enabled:enabled,issuer:issuer}",
        "--output",
        "json",
        "--only-show-errors",
    )
    settings_command = (
        "webapp",
        "config",
        "appsettings",
        "list",
        "--subscription",
        AZURE_SUBSCRIPTION_ID,
        "--resource-group",
        AZURE_RESOURCE_GROUP,
        "--name",
        AZURE_WEBAPP_NAME,
        "--query",
        "[?name=='PEERSLATE_AUTH_ISSUER'].{name:name,value:value}",
        "--output",
        "json",
        "--only-show-errors",
    )

    def __init__(
        self,
        runner: Callable[..., object] | None = None,
        opener: Callable[..., object] | None = None,
        *,
        environment: Mapping[str, str] | None = None,
        launcher_resolver: Callable[[str], str | None] | None = None,
    ):
        self._runner = runner or subprocess.run
        self._opener = opener or _open_without_redirect
        self._environment = environment
        self._launcher_resolver = launcher_resolver or shutil.which

    @staticmethod
    def _metadata_endpoint(open_id_issuer: str) -> str:
        _validated_https_url(
            open_id_issuer, code="production_oidc_authority_mismatch"
        )
        _tenant_from_oidc_authority(open_id_issuer, require_uuid_host=False)
        if open_id_issuer.endswith("/"):
            raise BrokerRefusal("production_oidc_authority_mismatch")
        return f"{open_id_issuer}/.well-known/openid-configuration"

    def _metadata(self, endpoint: str) -> Mapping[str, object]:
        request = Request(endpoint, headers={"Accept": "application/json"}, method="GET")
        try:
            with self._opener(request, timeout=60) as response:
                final_url = str(response.geturl())
                status = getattr(response, "status", None)
                if status is None and hasattr(response, "getcode"):
                    status = response.getcode()
                raw = response.read(65537)
        except HTTPError as error:
            error.close()
            raise BrokerRefusal("production_oidc_metadata_unavailable") from None
        except (URLError, OSError, ValueError, AttributeError):
            raise BrokerRefusal("production_oidc_metadata_unavailable") from None
        if (
            status != 200
            or final_url != endpoint
            or not isinstance(raw, bytes)
            or len(raw) > 65536
        ):
            raise BrokerRefusal("production_oidc_metadata_unavailable")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise BrokerRefusal("production_oidc_metadata_unavailable") from None
        if not isinstance(payload, Mapping):
            raise BrokerRefusal("production_oidc_metadata_unavailable")
        return payload

    @staticmethod
    def _authorization_origin(
        endpoint: object, tenant_id: str, discovery_issuer: str
    ) -> str:
        value = _validated_https_url(
            endpoint, code="production_oidc_authority_mismatch"
        )
        parsed = urlparse(value)
        parts = [part for part in parsed.path.split("/") if part]
        if (
            len(parts) != 4
            or parts[0] != tenant_id
            or parts[1:] != ["oauth2", "v2.0", "authorize"]
            or parsed.path != f"/{tenant_id}/oauth2/v2.0/authorize"
            or parsed.hostname != urlparse(discovery_issuer).hostname
        ):
            raise BrokerRefusal("production_oidc_authority_mismatch")
        return f"https://{parsed.hostname.lower()}"

    def resolve(self) -> AuthorityBinding:
        if OWNER_AUTHORIZATION_REF != (
            "session:01a04348-7e3e-7a11-a443-752498be91b5/"
            "owner-authorization:2026-08-28/workshop-fg-sealed-private-proof-complete-lifecycle"
        ):
            raise BrokerRefusal("owner_authorization_mismatch")
        cli_runtime = _resolve_azure_cli_runtime(self._launcher_resolver)
        raw_auth_settings = _run_azure_json(
            self._runner,
            cli_runtime.command(self.auth_command),
            environment=self._environment,
        )
        if (
            not isinstance(raw_auth_settings, Mapping)
            or set(raw_auth_settings) != {"enabled", "issuer"}
            or raw_auth_settings.get("enabled") is not True
        ):
            raise BrokerRefusal("production_oidc_authority_mismatch")
        auth_settings = {
            "platformEnabled": raw_auth_settings["enabled"],
            "openIdIssuer": raw_auth_settings["issuer"],
        }
        open_id_issuer = auth_settings["openIdIssuer"]
        endpoint = self._metadata_endpoint(str(open_id_issuer or ""))
        discovery_tenant = _tenant_from_oidc_authority(
            str(open_id_issuer), require_uuid_host=False
        )
        metadata = self._metadata(endpoint)
        oidc_issuer = _validated_https_url(
            metadata.get("issuer"), code="production_oidc_authority_mismatch"
        )
        if oidc_issuer.endswith("/"):
            raise BrokerRefusal("production_oidc_authority_mismatch")
        tenant_id = _tenant_from_oidc_authority(
            oidc_issuer, require_uuid_host=True
        )
        if tenant_id != discovery_tenant:
            raise BrokerRefusal("production_oidc_authority_mismatch")
        discovery_host = (urlparse(str(open_id_issuer)).hostname or "").lower()
        tenant_label = ""
        for suffix in ALLOWED_AUTH_HOST_SUFFIXES:
            if discovery_host.endswith(suffix):
                tenant_label = discovery_host[: -len(suffix)]
                break
        if not SAFE_TENANT_LABEL.fullmatch(tenant_label):
            raise BrokerRefusal("production_oidc_authority_mismatch")
        authorization_origin = self._authorization_origin(
            metadata.get("authorization_endpoint"), tenant_id, str(open_id_issuer)
        )
        settings = _run_azure_json(
            self._runner,
            cli_runtime.command(self.settings_command),
            environment=self._environment,
        )
        if (
            not isinstance(settings, list)
            or len(settings) != 1
            or not isinstance(settings[0], Mapping)
            or settings[0].get("name") != "PEERSLATE_AUTH_ISSUER"
            or settings[0].get("value") != oidc_issuer
        ):
            raise BrokerRefusal("production_oidc_setting_mismatch")
        return AuthorityBinding(
            oidc_issuer=SealedValue(oidc_issuer),
            authorization_origin=SealedValue(authorization_origin),
            tenant_id=SealedValue(tenant_id),
            tenant_label=SealedValue(tenant_label),
        )


class AzureCliGraphTokenProvider:
    """Acquire the active pre-authorized Graph token inside the local worker."""

    command_arguments = (
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
        launcher_resolver: Callable[[str], str | None] | None = None,
    ):
        self._runner = runner or subprocess.run
        self._environment = environment
        self._launcher_resolver = launcher_resolver or shutil.which

    def acquire(self, tenant_id: SealedValue) -> SealedValue:
        try:
            exact_tenant = str(UUID(tenant_id.reveal()))
        except (TypeError, ValueError, AttributeError):
            raise BrokerRefusal("graph_token_tenant_unverified") from None
        cli_runtime = _resolve_azure_cli_runtime(self._launcher_resolver)
        command = cli_runtime.command(
            (*self.command_arguments, "--tenant", exact_tenant)
        )
        try:
            result = self._runner(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
                stdin=subprocess.DEVNULL,
                env=_azure_child_environment(self._environment),
            )
        except (OSError, subprocess.SubprocessError):
            raise BrokerRefusal("graph_authorization_unavailable") from None
        if getattr(result, "returncode", 1) != 0:
            raise BrokerRefusal("graph_authorization_unavailable")
        token = str(getattr(result, "stdout", "") or "").strip()
        if len(token) < 16 or len(token) > MAX_TOKEN_LENGTH:
            raise BrokerRefusal("graph_authorization_unavailable")
        return SealedValue(token, max_length=MAX_TOKEN_LENGTH)


class MicrosoftGraphAdapter:
    """Exact-tenant Graph lifecycle with closed, non-reflective outcomes."""

    def __init__(
        self,
        token_provider: AzureCliGraphTokenProvider | None = None,
        opener: Callable[..., object] | None = None,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self._token_provider = token_provider or AzureCliGraphTokenProvider()
        self._opener = opener or _open_without_redirect
        self._clock = clock
        self._operator_id: SealedValue | None = None

    def _token_claims(self, token: SealedValue) -> Mapping[str, object]:
        try:
            header, encoded_payload, signature = token.reveal().split(".")
            if not header or not signature:
                raise ValueError("incomplete token")
            padding = "=" * (-len(encoded_payload) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode((encoded_payload + padding).encode("ascii"))
            )
            if not isinstance(payload, Mapping):
                raise ValueError("unexpected token payload")
            tenant_id = str(UUID(str(payload.get("tid") or "")))
            operator_id = str(UUID(str(payload.get("oid") or "")))
            if payload.get("aud") not in GRAPH_AUDIENCES:
                raise ValueError("unexpected audience")
            scopes = set(str(payload.get("scp") or "").split())
            if not REQUIRED_GRAPH_SCOPES.issubset(scopes):
                raise ValueError("missing delegated scope")
            raw_roles = payload.get("wids")
            if not isinstance(raw_roles, list):
                raise ValueError("missing directory role")
            roles = {str(UUID(str(role))) for role in raw_roles}
            if not roles.intersection(ELIGIBLE_GRAPH_ROLE_TEMPLATE_IDS):
                raise ValueError("ineligible directory role")
            expires = payload.get("exp")
            now = int(self._clock().timestamp())
            if isinstance(expires, bool) or not isinstance(expires, int) or expires <= now + 120:
                raise ValueError("token lifetime unavailable")
            return {"tenant_id": tenant_id, "operator_id": operator_id}
        except (
            AttributeError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            binascii.Error,
            json.JSONDecodeError,
        ):
            raise BrokerRefusal("graph_delegated_authority_unverified") from None

    def _token_tenant_id(self, token: SealedValue) -> str:
        return str(self._token_claims(token)["tenant_id"])

    @staticmethod
    def _response_status(response: object) -> int:
        value = getattr(response, "status", None)
        if value is None and hasattr(response, "getcode"):
            value = response.getcode()
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("missing status")
        return value

    @staticmethod
    def _read_json_response(
        response: object,
        *,
        expected_url: str,
        expected_status: int,
    ) -> Mapping[str, object]:
        if (
            MicrosoftGraphAdapter._response_status(response) != expected_status
            or str(response.geturl()) != expected_url
        ):
            raise ValueError("unexpected response")
        raw = response.read(65537)
        if not isinstance(raw, bytes) or len(raw) > 65536:
            raise ValueError("unexpected response")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("unexpected response")
        return payload

    def _verified_organization(
        self,
        token: SealedValue,
        *,
        authority: AuthorityBinding,
    ) -> Mapping[str, object]:
        tenant_id = self._token_tenant_id(token)
        if tenant_id != authority.tenant_id.reveal():
            raise BrokerRefusal("graph_tenant_issuer_mismatch")
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
                payload = self._read_json_response(
                    response,
                    expected_url=ALLOWED_GRAPH_ORGANIZATION_ENDPOINT,
                    expected_status=200,
                )
        except HTTPError as error:
            error.close()
            raise BrokerRefusal("graph_tenant_verification_unavailable") from None
        except (
            URLError,
            OSError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
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

    def prepare(self, authority: AuthorityBinding) -> SealedValue:
        """Perform the complete delegated authority preflight before mutation."""

        token = self._token_provider.acquire(authority.tenant_id)
        try:
            if self._operator_id is not None:
                raise BrokerRefusal("graph_delegated_authority_unverified")
            claims = self._token_claims(token)
            graph_issuer = self._initial_verified_issuer(
                self._verified_organization(token, authority=authority)
            )
            if graph_issuer.reveal().lower() != (
                f"{authority.tenant_label.reveal().lower()}.onmicrosoft.com"
            ):
                graph_issuer.clear()
                raise BrokerRefusal("graph_tenant_issuer_mismatch")
            self._operator_id = SealedValue(str(claims["operator_id"]))
            return graph_issuer
        finally:
            token.clear()

    def _bound_token(
        self,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> SealedValue:
        token = self._token_provider.acquire(authority.tenant_id)
        try:
            claims = self._token_claims(token)
            if (
                self._operator_id is None
                or str(claims["operator_id"]) != self._operator_id.reveal()
            ):
                raise BrokerRefusal("graph_delegated_authority_unverified")
            organization = self._verified_organization(token, authority=authority)
        except Exception:
            token.clear()
            raise
        verified_domains = organization.get("verifiedDomains")
        try:
            initial = self._initial_verified_issuer(organization)
            matches = initial.reveal() == graph_issuer.reveal()
            initial.clear()
        except Exception:
            token.clear()
            raise
        if not isinstance(verified_domains, list) or not matches:
            token.clear()
            raise BrokerRefusal("graph_tenant_issuer_mismatch")
        return token

    def prove_customer_absence(
        self,
        identities: Sequence[SealedIdentity],
        *,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> int:
        if (
            len(identities) != 2
            or tuple(identity.alias for identity in identities) != ALLOWED_ALIASES
        ):
            raise BrokerRefusal("exact_alias_pair_required")
        _validate_graph_issuer(graph_issuer)
        observed: set[str] = set()
        proofs = 0
        for identity in identities:
            login = identity.login_identifier.reveal()
            if (
                len(login) > 64
                or login in observed
                or not login.lower().endswith(
                    f"@{graph_issuer.reveal().lower()}"
                )
            ):
                raise BrokerRefusal("generated_identity_invalid")
            observed.add(login)
            try:
                active, deleted = self._exact_identity_matches(
                    identity,
                    authority=authority,
                    graph_issuer=graph_issuer,
                )
                if active or deleted:
                    raise ValueError("pre-existing exact identity")
            except (
                BrokerRefusal,
                HTTPError,
                URLError,
                OSError,
                ValueError,
                AttributeError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ):
                raise BrokerRefusal("graph_customer_absence_unverified") from None
            proofs += 2
        return proofs

    @staticmethod
    def _odata_literal(value: str) -> str:
        return value.replace("'", "''")

    def _exact_identity_endpoints(
        self,
        identity: SealedIdentity,
        graph_issuer: SealedValue,
    ) -> tuple[str, str]:
        login = identity.login_identifier.reveal()
        issuer = graph_issuer.reveal()
        if (
            len(login) > 64
            or not login.lower().endswith(f"@{issuer.lower()}")
        ):
            raise BrokerRefusal("generated_identity_invalid")
        exact_filter = (
            "identities/any(c:c/issuerAssignedId eq "
            f"'{self._odata_literal(login)}' and c/issuer eq "
            f"'{self._odata_literal(issuer)}')"
        )
        query = urlencode(
            {
                "$select": "id,identities,createdDateTime",
                "$top": "2",
                "$filter": exact_filter,
            },
            quote_via=quote,
        )
        return (
            f"{ALLOWED_GRAPH_ENDPOINT}?{query}",
            f"{ALLOWED_GRAPH_DELETED_ITEMS_ENDPOINT}/microsoft.graph.user?{query}",
        )

    def _exact_identity_matches(
        self,
        identity: SealedIdentity,
        *,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> tuple[list[object], list[object]]:
        results: list[list[object]] = []
        for endpoint in self._exact_identity_endpoints(identity, graph_issuer):
            token: SealedValue | None = None
            try:
                token = self._bound_token(authority, graph_issuer)
                request = Request(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {token.reveal()}",
                        "Accept": "application/json",
                    },
                    method="GET",
                )
                with self._opener(request, timeout=60) as response:
                    payload = self._read_json_response(
                        response, expected_url=endpoint, expected_status=200
                    )
                values = payload.get("value")
                if (
                    not isinstance(values, list)
                    or len(values) > 2
                    or "@odata.nextLink" in payload
                ):
                    raise ValueError("unbounded exact identity lookup")
                results.append(values)
            except HTTPError as error:
                error.close()
                raise
            finally:
                if token is not None:
                    token.clear()
        return results[0], results[1]

    @staticmethod
    def _parse_graph_datetime(value: object) -> datetime:
        if not isinstance(value, str) or not value:
            raise ValueError("missing Graph creation time")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("unbounded Graph creation time")
        return parsed.astimezone(timezone.utc)

    def _clock_utc(self) -> datetime:
        try:
            observed = self._clock()
            if (
                not isinstance(observed, datetime)
                or observed.tzinfo is None
                or observed.utcoffset() is None
            ):
                raise ValueError("unbounded operation clock")
            return observed.astimezone(timezone.utc)
        except (TypeError, ValueError, AttributeError, OverflowError):
            raise BrokerRefusal("graph_operation_clock_unavailable") from None

    @staticmethod
    def _customer_display_name(identity: SealedIdentity) -> str:
        return f"PeerSlate synthetic QA {identity.alias}"

    @staticmethod
    def _customer_shape_endpoint(subject: str, *, deleted: bool) -> str:
        exact_subject = str(UUID(subject))
        base = (
            ALLOWED_GRAPH_DELETED_ITEMS_ENDPOINT
            if deleted
            else ALLOWED_GRAPH_ENDPOINT
        )
        return f"{base}/{exact_subject}?$select={GRAPH_CUSTOMER_SHAPE_SELECT}"

    def _read_exact_customer_shape(
        self,
        identity: SealedIdentity,
        subject: str,
        *,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
        attempted_after: datetime,
        deleted: bool,
        token: SealedValue | None = None,
    ) -> None:
        try:
            bounded_attempt = attempted_after.astimezone(timezone.utc)
            if attempted_after.tzinfo is None or bounded_attempt.microsecond != 0:
                raise ValueError("unbounded creation attempt")
            endpoint = self._customer_shape_endpoint(subject, deleted=deleted)
        except (TypeError, ValueError, AttributeError, OverflowError):
            raise BrokerIndeterminate("graph_creation_indeterminate") from None
        owned_token = token is None
        exact_token = token
        try:
            if exact_token is None:
                exact_token = self._bound_token(authority, graph_issuer)
            request = Request(
                endpoint,
                headers={
                    "Authorization": f"Bearer {exact_token.reveal()}",
                    "Accept": "application/json",
                },
                method="GET",
            )
            try:
                with self._opener(request, timeout=60) as response:
                    payload = self._read_json_response(
                        response, expected_url=endpoint, expected_status=200
                    )
            except HTTPError as error:
                error.close()
                raise
            created = self._parse_graph_datetime(payload.get("createdDateTime"))
            observed_at = self._clock_utc()
            expected_identity = {
                "signInType": "emailAddress",
                "issuer": graph_issuer.reveal(),
                "issuerAssignedId": identity.login_identifier.reveal(),
            }
            if (
                str(payload.get("id") or "") != subject
                or payload.get("accountEnabled") is not True
                or payload.get("userType") != "Member"
                or payload.get("creationType") != "LocalAccount"
                or payload.get("displayName") != self._customer_display_name(identity)
                or payload.get("mailNickname") != identity.mail_nickname.reveal()
                or payload.get("identities") != [expected_identity]
                or payload.get("passwordPolicies") != "DisablePasswordExpiration"
                or created < bounded_attempt
                or created > observed_at + timedelta(minutes=2)
            ):
                raise ValueError("unbound customer shape")
        finally:
            if owned_token and exact_token is not None:
                exact_token.clear()

    def _reconcile_attempted_creation(
        self,
        identity: SealedIdentity,
        *,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
        attempted_after: datetime,
    ) -> str:
        active, deleted = self._exact_identity_matches(
            identity, authority=authority, graph_issuer=graph_issuer
        )
        if len(active) + len(deleted) != 1:
            raise BrokerIndeterminate("graph_creation_indeterminate")
        result = (active + deleted)[0]
        if not isinstance(result, Mapping):
            raise BrokerIndeterminate("graph_creation_indeterminate")
        try:
            bounded_attempt = attempted_after.astimezone(timezone.utc)
            if attempted_after.tzinfo is None or bounded_attempt.microsecond != 0:
                raise ValueError("unbounded creation attempt")
            subject = str(UUID(str(result.get("id") or "")))
            created = self._parse_graph_datetime(result.get("createdDateTime"))
            observed_at = self._clock_utc()
            raw_identities = result.get("identities")
            exact_identity = any(
                isinstance(candidate, Mapping)
                and candidate.get("signInType") == "emailAddress"
                and candidate.get("issuer") == graph_issuer.reveal()
                and candidate.get("issuerAssignedId")
                == identity.login_identifier.reveal()
                for candidate in raw_identities or []
            )
            if (
                not isinstance(raw_identities, list)
                or not exact_identity
                or created < bounded_attempt
                or created > observed_at + timedelta(minutes=2)
            ):
                raise ValueError("unbounded Graph identity")
            if identity.subject is not None and identity.subject.reveal() != subject:
                raise ValueError("subject changed during reconciliation")
            self._read_exact_customer_shape(
                identity,
                subject,
                authority=authority,
                graph_issuer=graph_issuer,
                attempted_after=bounded_attempt,
                deleted=bool(deleted),
            )
        except (TypeError, ValueError, AttributeError, OverflowError):
            raise BrokerIndeterminate("graph_creation_indeterminate") from None
        if identity.subject is None:
            identity.subject = SealedValue(subject)
        return "active_known" if active else "deleted_known"

    def create_customer(
        self,
        identity: SealedIdentity,
        *,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> GraphCreationOutcome:
        _validate_graph_issuer(graph_issuer)
        if (
            identity.alias not in ALLOWED_ALIASES
            or len(identity.login_identifier.reveal()) > 64
            or not identity.login_identifier.reveal().lower().endswith(
                f"@{graph_issuer.reveal().lower()}"
            )
        ):
            raise BrokerRefusal("generated_identity_invalid")
        token = self._bound_token(authority, graph_issuer)
        try:
            body = {
                "accountEnabled": True,
                "userType": "Member",
                "creationType": "LocalAccount",
                "displayName": self._customer_display_name(identity),
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
            attempted_after = self._clock_utc().replace(microsecond=0)
            try:
                with self._opener(request, timeout=60) as response:
                    payload = self._read_json_response(
                        response,
                        expected_url=ALLOWED_GRAPH_ENDPOINT,
                        expected_status=201,
                    )
            except HTTPError as error:
                try:
                    status = error.code
                finally:
                    error.close()
                state = (
                    "known_not_created"
                    if isinstance(status, int)
                    and not isinstance(status, bool)
                    and 400 <= status < 500
                    and status != 408
                    else "ambiguous_maybe_created"
                )
                return GraphCreationOutcome(state, attempted_after)
            except (
                URLError,
                OSError,
                ValueError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ):
                return GraphCreationOutcome(
                    "ambiguous_maybe_created", attempted_after
                )
            try:
                subject = str(UUID(str(payload.get("id") or "")))
                self._read_exact_customer_shape(
                    identity,
                    subject,
                    authority=authority,
                    graph_issuer=graph_issuer,
                    attempted_after=attempted_after,
                    deleted=False,
                    token=token,
                )
            except Exception:
                return GraphCreationOutcome(
                    "ambiguous_maybe_created", attempted_after
                )
            return GraphCreationOutcome(
                "known_created", attempted_after, SealedValue(subject)
            )
        finally:
            token.clear()

    def _expect_status(
        self,
        *,
        method: str,
        endpoint: str,
        expected_status: int,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> None:
        token: SealedValue | None = None
        try:
            token = self._bound_token(authority, graph_issuer)
            request = Request(
                endpoint,
                headers={
                    "Authorization": f"Bearer {token.reveal()}",
                    "Accept": "application/json",
                },
                method=method,
            )
            with self._opener(request, timeout=60) as response:
                if (
                    self._response_status(response) != expected_status
                    or str(response.geturl()) != endpoint
                    or response.read(1) != b""
                ):
                    raise ValueError("unexpected status")
        except HTTPError as error:
            error.close()
            raise BrokerIndeterminate("graph_deletion_indeterminate") from None
        except (URLError, OSError, ValueError, AttributeError):
            raise BrokerIndeterminate("graph_deletion_indeterminate") from None
        finally:
            if token is not None:
                token.clear()

    def _direct_probe(
        self,
        endpoint: str,
        *,
        subject: str,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> str:
        token: SealedValue | None = None
        try:
            token = self._bound_token(authority, graph_issuer)
            request = Request(
                endpoint,
                headers={
                    "Authorization": f"Bearer {token.reveal()}",
                    "Accept": "application/json",
                },
                method="GET",
            )
            try:
                with self._opener(request, timeout=60) as response:
                    payload = self._read_json_response(
                        response, expected_url=endpoint, expected_status=200
                    )
                if str(payload.get("id") or "") != subject:
                    raise ValueError("unexpected Graph object")
                return "present"
            except HTTPError as error:
                try:
                    if error.code != 404 or str(error.geturl()) != endpoint:
                        raise ValueError("unexpected Graph probe response")
                    return "absent"
                finally:
                    error.close()
        except (
            BrokerRefusal,
            URLError,
            OSError,
            ValueError,
            AttributeError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            raise BrokerIndeterminate("graph_deletion_indeterminate") from None
        finally:
            if token is not None:
                token.clear()

    @staticmethod
    def _probe_endpoints(subject: str) -> tuple[str, str]:
        return (
            f"{ALLOWED_GRAPH_ENDPOINT}/{subject}?$select=id",
            f"{ALLOWED_GRAPH_DELETED_ITEMS_ENDPOINT}/{subject}?$select=id",
        )

    def _capture_direct_state(
        self,
        ledger: _GraphLifecycleLedgerEntry,
        subject: str,
        *,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
        final: bool = False,
    ) -> None:
        active_endpoint, deleted_endpoint = self._probe_endpoints(subject)
        active_field = "final_active_probe" if final else "active_probe"
        deleted_field = "final_deleted_probe" if final else "deleted_probe"
        try:
            setattr(
                ledger,
                active_field,
                self._direct_probe(
                    active_endpoint,
                    subject=subject,
                    authority=authority,
                    graph_issuer=graph_issuer,
                ),
            )
        except Exception:
            setattr(ledger, active_field, "unknown")
        try:
            setattr(
                ledger,
                deleted_field,
                self._direct_probe(
                    deleted_endpoint,
                    subject=subject,
                    authority=authority,
                    graph_issuer=graph_issuer,
                ),
            )
        except Exception:
            setattr(ledger, deleted_field, "unknown")

    def contain_partial_creation(
        self,
        identities: Sequence[SealedIdentity],
        *,
        creation_states: Mapping[str, str],
        attempted_after: Mapping[str, datetime],
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> None:
        """One bounded reconciliation and containment pass; never retry POST."""

        allowed_states = {
            "not_attempted",
            "known_created",
            "ambiguous_maybe_created",
            "known_not_created",
        }
        attempted = {
            alias
            for alias, state in creation_states.items()
            if state != "not_attempted"
        }
        if (
            len(identities) != 2
            or tuple(identity.alias for identity in identities) != ALLOWED_ALIASES
            or set(creation_states) != set(ALLOWED_ALIASES)
            or any(state not in allowed_states for state in creation_states.values())
            or set(attempted_after) != attempted
        ):
            return
        ledgers = {
            identity.alias: _GraphLifecycleLedgerEntry(identity.alias)
            for identity in identities
        }
        known: dict[str, tuple[SealedIdentity, str]] = {}
        for identity in identities:
            ledger = ledgers[identity.alias]
            ledger.create = creation_states[identity.alias]
            if ledger.create in {"not_attempted", "known_not_created"}:
                continue
            try:
                ledger.create = self._reconcile_attempted_creation(
                    identity,
                    authority=authority,
                    graph_issuer=graph_issuer,
                    attempted_after=attempted_after[identity.alias],
                )
            except Exception:
                continue
            known[identity.alias] = (identity, ledger.create)

        for alias, (identity, create_state) in known.items():
            ledger = ledgers[alias]
            if identity.subject is None:
                continue
            try:
                subject = str(UUID(identity.subject.reveal()))
            except (TypeError, ValueError, AttributeError):
                continue
            if create_state == "active_known":
                ledger.soft = "attempted_unknown"
                try:
                    self._expect_status(
                        method="DELETE",
                        endpoint=f"{ALLOWED_GRAPH_ENDPOINT}/{subject}",
                        expected_status=204,
                        authority=authority,
                        graph_issuer=graph_issuer,
                    )
                    ledger.soft = "exact_204"
                except Exception:
                    pass
                self._capture_direct_state(
                    ledger,
                    subject,
                    authority=authority,
                    graph_issuer=graph_issuer,
                )
                # Partial creation occurs before browser journeys and the
                # exact-two SQL retirement gate. Soft deletion is the
                # recoverable containment boundary; irreversible purge is
                # forbidden here even for an exactly reconciled subject.
            elif create_state == "deleted_known":
                ledger.active_probe = "absent"
                ledger.deleted_probe = "present"

    def delete_exact_pair(
        self,
        subjects: Sequence[SealedValue],
        *,
        authority: AuthorityBinding,
        graph_issuer: SealedValue,
    ) -> GraphDeletionOutcome:
        if len(subjects) != 2:
            raise BrokerRefusal("exact_subject_pair_required")
        try:
            exact = tuple(str(UUID(subject.reveal())) for subject in subjects)
        except (TypeError, ValueError, AttributeError):
            raise BrokerRefusal("exact_subject_pair_required") from None
        if len(set(exact)) != 2:
            raise BrokerRefusal("exact_subject_pair_required")
        ledgers = [
            _GraphLifecycleLedgerEntry(alias)
            for alias in ALLOWED_ALIASES
        ]
        for ledger, subject in zip(ledgers, exact, strict=True):
            ledger.soft = "attempted_unknown"
            try:
                self._expect_status(
                    method="DELETE",
                    endpoint=f"{ALLOWED_GRAPH_ENDPOINT}/{subject}",
                    expected_status=204,
                    authority=authority,
                    graph_issuer=graph_issuer,
                )
                ledger.soft = "exact_204"
            except Exception:
                pass
        for ledger, subject in zip(ledgers, exact, strict=True):
            self._capture_direct_state(
                ledger,
                subject,
                authority=authority,
                graph_issuer=graph_issuer,
            )
        if not all(
            ledger.soft == "exact_204"
            and ledger.active_probe == "absent"
            and ledger.deleted_probe == "present"
            for ledger in ledgers
        ):
            raise BrokerIndeterminate("graph_deletion_indeterminate")

        for ledger, subject in zip(ledgers, exact, strict=True):
            ledger.purge = "attempted_unknown"
            try:
                self._expect_status(
                    method="DELETE",
                    endpoint=f"{ALLOWED_GRAPH_DELETED_ITEMS_ENDPOINT}/{subject}",
                    expected_status=204,
                    authority=authority,
                    graph_issuer=graph_issuer,
                )
                ledger.purge = "exact_204"
            except Exception:
                pass
        for ledger, subject in zip(ledgers, exact, strict=True):
            self._capture_direct_state(
                ledger,
                subject,
                authority=authority,
                graph_issuer=graph_issuer,
                final=True,
            )
        if not all(
            ledger.purge == "exact_204"
            and ledger.final_active_probe == "absent"
            and ledger.final_deleted_probe == "absent"
            for ledger in ledgers
        ):
            raise BrokerIndeterminate("graph_deletion_indeterminate")
        return GraphDeletionOutcome(
            soft_deleted=2,
            soft_state_proofs=4,
            permanently_deleted=2,
            final_absence_proofs=4,
        )

    def clear(self) -> None:
        if self._operator_id is not None:
            self._operator_id.clear()
            self._operator_id = None


@dataclass(frozen=True)
class StartedPlaywrightRuntime:
    """One started pinned driver and its already-validated Chromium executable."""

    playwright: object
    chromium_executable: Path


class PlaywrightRuntimeProvider(Protocol):
    expected_browser_version: str

    def start(
        self, workspace: Path, environment: Mapping[str, str]
    ) -> StartedPlaywrightRuntime:
        """Provision, validate, and start the exact locked runtime binding."""

    def release(self) -> None:
        """Release worker-local import routing before root removal."""


class PinnedPlaywrightRuntime:
    """Provision the reviewed Playwright closure into one disposable operation root."""

    requirements_path = PLAYWRIGHT_LOCK_PATH.with_name("playwright-requirements.lock")

    def __init__(
        self,
        runner: Callable[..., object] | None = None,
        *,
        lock_path: Path = PLAYWRIGHT_LOCK_PATH,
    ):
        self._runner = runner or subprocess.run
        self._lock_path = lock_path
        self._site_packages: Path | None = None
        self._runtime_module_names: set[str] = set()
        self.expected_browser_version = ""

    def _lock(self) -> Mapping[str, object]:
        try:
            lock_path = self._lock_path.resolve(strict=True)
            requirements_path = self.requirements_path.resolve(strict=True)
            if (
                not lock_path.is_file()
                or not requirements_path.is_file()
                or lock_path.parent != Path(__file__).resolve().parent
                or requirements_path.parent != lock_path.parent
            ):
                raise ValueError("unapproved lock path")
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            requirement_bytes = requirements_path.read_bytes()
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            raise BrokerRefusal("sealed_browser_lock_invalid") from None
        if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
            raise BrokerRefusal("sealed_browser_lock_invalid")
        targets = payload.get("targets")
        requirements = payload.get("requirements")
        chromium = payload.get("chromium")
        expected_targets = [
            {
                "system": "Darwin",
                "machine": "arm64",
                "python": "3.14",
                "venv_python": ["bin", "python"],
                "site_packages": ["lib", "python3.14", "site-packages"],
            },
            {
                "system": "Windows",
                "machine": "AMD64",
                "python": "3.13",
                "venv_python": ["Scripts", "python.exe"],
                "site_packages": ["Lib", "site-packages"],
            },
        ]
        if (
            not isinstance(targets, list)
            or targets != expected_targets
            or not isinstance(requirements, Mapping)
            or requirements.get("path") != requirements_path.name
            or requirements.get("sha256")
            != hashlib.sha256(requirement_bytes).hexdigest()
            or requirements.get("packages")
            != {
                "greenlet": "3.5.5",
                "playwright": "1.62.0",
                "pyee": "13.0.1",
                "typing-extensions": "4.16.0",
            }
            or not isinstance(chromium, Mapping)
            or chromium
            != {
                "name": "chromium",
                "revision": "1234",
                "browser_version": "151.0.7922.34",
                "title": "Chrome for Testing",
                "install_args": ["chromium", "--no-shell"],
            }
        ):
            raise BrokerRefusal("sealed_browser_lock_invalid")
        active_target = next(
            (
                target
                for target in expected_targets
                if (
                    platform.system() == target["system"]
                    and platform.machine() == target["machine"]
                    and f"{sys.version_info.major}.{sys.version_info.minor}"
                    == target["python"]
                )
            ),
            None,
        )
        if active_target is None:
            raise BrokerRefusal("sealed_browser_lock_invalid")
        self.expected_browser_version = str(chromium["browser_version"])
        return {**payload, "active_target": active_target}

    def _run(self, command: Sequence[str], *, environment: Mapping[str, str], timeout: int) -> None:
        try:
            result = self._runner(
                tuple(command),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                env=dict(environment),
            )
        except (OSError, subprocess.SubprocessError):
            raise BrokerRefusal("sealed_browser_runtime_unavailable") from None
        if getattr(result, "returncode", 1) != 0:
            raise BrokerRefusal("sealed_browser_runtime_unavailable")

    @staticmethod
    def _runtime_environment(
        workspace: Path, source: Mapping[str, str], browsers: Path
    ) -> dict[str, str]:
        environment = {
            "HOME": str(workspace),
            "USERPROFILE": str(workspace),
            "APPDATA": str(workspace),
            "LOCALAPPDATA": str(workspace),
            "TEMP": str(workspace),
            "TMP": str(workspace),
            "TMPDIR": str(workspace),
            "PLAYWRIGHT_BROWSERS_PATH": str(browsers),
            "PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT": "120000",
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
        for name in (
            "SystemRoot",
            "WINDIR",
            "COMSPEC",
            "PATH",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        ):
            if source.get(name):
                environment[name] = str(source[name])
        return environment

    @staticmethod
    def _distribution_versions(site_packages: Path) -> Mapping[str, str]:
        versions: dict[str, str] = {}
        for distribution in importlib.metadata.distributions(path=[str(site_packages)]):
            name = (
                str(distribution.metadata.get("Name") or "")
                .lower()
                .replace("_", "-")
                .replace(".", "-")
            )
            if name:
                versions[name] = distribution.version
        return versions

    def _capture_runtime_modules(self, site_packages: Path) -> None:
        for name, module in tuple(sys.modules.items()):
            module_file = getattr(module, "__file__", None)
            if not module_file:
                continue
            try:
                Path(module_file).resolve().relative_to(site_packages.resolve())
            except (OSError, ValueError):
                continue
            self._runtime_module_names.add(name)

    def _load_started_playwright(
        self,
        site_packages: Path,
        browsers: Path,
        runtime_environment: Mapping[str, str],
    ) -> StartedPlaywrightRuntime:
        if any(
            name == "playwright" or name.startswith("playwright.")
            for name in sys.modules
        ):
            raise BrokerRefusal("sealed_browser_runtime_contaminated")
        sys.path.insert(0, str(site_packages))
        self._site_packages = site_packages
        playwright = None
        try:
            with _isolated_child_environment(runtime_environment):
                sync_api = importlib.import_module("playwright.sync_api")
                playwright = sync_api.sync_playwright().start()
            executable = Path(playwright.chromium.executable_path).resolve(strict=True)
            executable.relative_to(browsers.resolve(strict=True))
            if not executable.is_file():
                raise ValueError("Chromium executable is not a file")
            self._capture_runtime_modules(site_packages)
            return StartedPlaywrightRuntime(
                playwright=playwright,
                chromium_executable=executable,
            )
        except Exception:
            cleanup_failed = False
            if playwright is not None:
                try:
                    playwright.stop()
                except Exception:
                    cleanup_failed = True
            try:
                self._capture_runtime_modules(site_packages)
            except Exception:
                cleanup_failed = True
            try:
                self.release()
            except Exception:
                cleanup_failed = True
            if cleanup_failed:
                raise BrokerIndeterminate(
                    "sealed_browser_cleanup_indeterminate"
                ) from None
            raise BrokerRefusal("sealed_browser_runtime_unavailable") from None

    def start(
        self, workspace: Path, environment: Mapping[str, str]
    ) -> StartedPlaywrightRuntime:
        lock = self._lock()
        runtime_root = workspace / "runtime"
        venv_root = runtime_root / "venv"
        browsers = runtime_root / "browsers"
        try:
            runtime_root.mkdir(mode=0o700)
            browsers.mkdir(mode=0o700)
        except OSError:
            raise BrokerRefusal("sealed_browser_runtime_unavailable") from None
        runtime_environment = self._runtime_environment(workspace, environment, browsers)
        self._run(
            (sys.executable, "-I", "-m", "venv", "--copies", str(venv_root)),
            environment=runtime_environment,
            timeout=120,
        )
        target = lock["active_target"]
        if not isinstance(target, Mapping):
            raise BrokerRefusal("sealed_browser_lock_invalid")
        venv_python_parts = target.get("venv_python")
        site_packages_parts = target.get("site_packages")
        if (
            not isinstance(venv_python_parts, list)
            or not isinstance(site_packages_parts, list)
            or not all(isinstance(part, str) and part for part in venv_python_parts)
            or not all(isinstance(part, str) and part for part in site_packages_parts)
        ):
            raise BrokerRefusal("sealed_browser_lock_invalid")
        venv_python = venv_root.joinpath(*venv_python_parts)
        site_packages = venv_root.joinpath(*site_packages_parts)
        self._run(
            (
                str(venv_python),
                "-I",
                "-m",
                "pip",
                "install",
                "--isolated",
                "--no-input",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "--only-binary=:all:",
                "--require-hashes",
                "-r",
                str(self.requirements_path),
            ),
            environment=runtime_environment,
            timeout=300,
        )
        expected_packages = lock["requirements"]["packages"]
        installed_packages = self._distribution_versions(site_packages)
        runtime_packages = {
            name: installed_packages.get(name) for name in expected_packages
        }
        unexpected = set(installed_packages).difference(
            set(expected_packages), {"pip", "setuptools", "wheel"}
        )
        if runtime_packages != expected_packages or unexpected:
            raise BrokerRefusal("sealed_browser_lock_invalid")
        browsers_json = site_packages / "playwright" / "driver" / "package" / "browsers.json"
        try:
            browser_payload = json.loads(browsers_json.read_text(encoding="utf-8"))
            entries = [
                entry
                for entry in browser_payload.get("browsers", [])
                if isinstance(entry, Mapping) and entry.get("name") == "chromium"
            ]
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            raise BrokerRefusal("sealed_browser_lock_invalid") from None
        chromium = lock["chromium"]
        if (
            len(entries) != 1
            or entries[0].get("revision") != chromium["revision"]
            or entries[0].get("browserVersion") != chromium["browser_version"]
            or entries[0].get("title") != chromium["title"]
        ):
            raise BrokerRefusal("sealed_browser_lock_invalid")
        self._run(
            (
                str(venv_python),
                "-I",
                "-m",
                "playwright",
                "install",
                *chromium["install_args"],
            ),
            environment=runtime_environment,
            timeout=900,
        )
        return self._load_started_playwright(
            site_packages, browsers, runtime_environment
        )

    def release(self) -> None:
        if self._site_packages is None:
            return
        try:
            sys.path.remove(str(self._site_packages))
        except ValueError:
            pass
        for name in sorted(self._runtime_module_names, reverse=True):
            sys.modules.pop(name, None)
        self._runtime_module_names.clear()
        self._site_packages = None


WORKSHOP_EXACT_DESCRIPTION_EVALUATOR = r"""
(rows, payload) => {
    const location = new URL(window.location.href);
    const rawHref = String(window.location.href);
    const authority = rawHref
        .slice("https://".length)
        .split(/[/?#]/, 1)[0];
    if (
        window.top !== window ||
        document.defaultView !== window ||
        location.protocol !== "https:" ||
        location.origin !== payload.expectedOrigin ||
        location.hostname !== "peerslate.com" ||
        location.port !== "" ||
        location.username !== "" ||
        location.password !== "" ||
        location.host !== "peerslate.com" ||
        authority !== "peerslate.com"
    ) {
        throw new Error("Workshop disclosure refused");
    }
    const matchingRows = [];
    for (const row of rows) {
        if (
            !row.isConnected ||
            row.ownerDocument !== document ||
            row.ownerDocument.defaultView !== window
        ) {
            throw new Error("Workshop disclosure refused");
        }
        const terms = Array.from(row.children).filter(
            (child) => child.tagName === "DT"
        );
        if (
            terms.length === 1 &&
            terms[0].textContent.trim() === payload.term
        ) {
            matchingRows.push(row);
        }
    }
    if (matchingRows.length !== 1) {
        throw new Error("Workshop disclosure refused");
    }
    const descriptions = Array.from(matchingRows[0].children).filter(
        (child) => child.tagName === "DD"
    );
    if (
        descriptions.length !== 1 ||
        descriptions[0].textContent.trim() !== payload.description
    ) {
        throw new Error("Workshop disclosure refused");
    }
    return true;
}
"""


class WorkshopEvaluator:
    """Bind every private Workshop interaction to one canonical document.

    Playwright locators may resolve after a navigation.  This evaluator keeps
    the locator operation and its document/origin proof in the same browser
    task, so a page from a hostile owner document, a non-canonical authority,
    or a redirect race cannot be credited as a Workshop proof or receive a
    generated value.
    """

    def __init__(self, page: object):
        self._page = page

    @staticmethod
    def _canonical_url(value: object) -> bool:
        try:
            parsed = urlparse(str(value))
            return (
                parsed.scheme == "https"
                and parsed.netloc == "peerslate.com"
                and parsed.hostname == "peerslate.com"
                and parsed.port is None
                and parsed.username is None
                and parsed.password is None
            )
        except (TypeError, ValueError):
            return False

    @classmethod
    def _require_canonical_target(cls, value: object) -> str:
        if not cls._canonical_url(value):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        return str(value)

    def _assert_document(self) -> None:
        if not self._canonical_url(getattr(self._page, "url", "")):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        try:
            result = self._page.evaluate(
                """
                (payload) => {
                    const location = new URL(window.location.href);
                    if (
                        window.top !== window ||
                        document.defaultView !== window ||
                        location.href !== window.location.href ||
                        location.protocol !== "https:" ||
                        location.origin !== payload.expectedOrigin ||
                        location.hostname !== "peerslate.com" ||
                        location.port !== "" ||
                        location.username !== "" ||
                        location.password !== "" ||
                        location.host !== "peerslate.com"
                    ) {
                        throw new Error("Workshop document refused");
                    }
                    return true;
                }
                """,
                {"expectedOrigin": ALLOWED_SITE_ORIGIN},
            )
        except Exception:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
        if result is not True:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")

    def navigate(self, target: object) -> None:
        target_url = self._require_canonical_target(target)
        try:
            self._page.goto(target_url, wait_until="domcontentloaded")
        except Exception:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
        self._assert_document()

    def reload(self) -> None:
        self._assert_document()
        try:
            self._page.reload(wait_until="domcontentloaded")
        except Exception:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
        self._assert_document()

    def _read(self, locator: object, operation: str, **extra: object) -> object:
        payload = {
            "operation": operation,
            "expectedOrigin": ALLOWED_SITE_ORIGIN,
            **extra,
        }
        try:
            return locator.evaluate_all(
                """
                (elements, payload) => {
                    const location = new URL(window.location.href);
                    if (
                        window.top !== window ||
                        document.defaultView !== window ||
                        location.protocol !== "https:" ||
                        location.origin !== payload.expectedOrigin ||
                        location.hostname !== "peerslate.com" ||
                        location.port !== "" ||
                        location.username !== "" ||
                        location.password !== "" ||
                        location.host !== "peerslate.com" ||
                        !elements.every(
                            (element) =>
                                element.isConnected &&
                                element.ownerDocument === document &&
                                element.ownerDocument.defaultView === window
                        )
                    ) {
                        throw new Error("Workshop document refused");
                    }
                    if (payload.operation === "count") {
                        return elements.length;
                    }
                    if (elements.length !== 1) {
                        throw new Error("Workshop target cardinality refused");
                    }
                    const element = elements[0];
                    if (payload.operation === "text") {
                        return element.textContent;
                    }
                    if (payload.operation === "input_value") {
                        if (!(element instanceof window.HTMLInputElement)) {
                            throw new Error("Workshop input refused");
                        }
                        return element.value;
                    }
                    if (payload.operation === "attribute") {
                        return element.getAttribute(payload.name);
                    }
                    throw new Error("Workshop read refused");
                }
                """,
                payload,
            )
        except Exception:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None

    def count(self, locator: object) -> int:
        result = self._read(locator, "count")
        if isinstance(result, bool) or not isinstance(result, int) or result < 0:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        return result

    def text(self, locator: object) -> str:
        result = self._read(locator, "text")
        if not isinstance(result, str):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        return result

    def input_value(self, locator: object) -> str:
        result = self._read(locator, "input_value")
        if not isinstance(result, str):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        return result

    def attribute(self, locator: object, name: str) -> str | None:
        result = self._read(locator, "attribute", name=name)
        if result is not None and not isinstance(result, str):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        return result

    def _write(self, locator: object, operation: str, **extra: object) -> None:
        payload = {
            "operation": operation,
            "expectedOrigin": ALLOWED_SITE_ORIGIN,
            **extra,
        }
        handle = None
        try:
            handle = locator.element_handle()
            if handle is None:
                raise ValueError("Workshop target unavailable")
            result = handle.evaluate(
                """
                (element, payload) => {
                    const location = new URL(window.location.href);
                    if (
                        window.top !== window ||
                        document.defaultView !== window ||
                        location.protocol !== "https:" ||
                        location.origin !== payload.expectedOrigin ||
                        location.hostname !== "peerslate.com" ||
                        location.port !== "" ||
                        location.username !== "" ||
                        location.password !== "" ||
                        location.host !== "peerslate.com" ||
                        !element.isConnected ||
                        element.ownerDocument !== document ||
                        element.ownerDocument.defaultView !== window
                    ) {
                        throw new Error("Workshop target refused");
                    }
                    if (payload.operation === "fill") {
                        if (
                            !(
                                element instanceof window.HTMLInputElement ||
                                element instanceof window.HTMLTextAreaElement
                            ) ||
                            typeof payload.value !== "string"
                        ) {
                            throw new Error("Workshop field refused");
                        }
                        const prototype =
                            element instanceof window.HTMLInputElement
                                ? window.HTMLInputElement.prototype
                                : window.HTMLTextAreaElement.prototype;
                        const descriptor = Object.getOwnPropertyDescriptor(
                            prototype,
                            "value"
                        );
                        if (!descriptor || typeof descriptor.set !== "function") {
                            throw new Error("Workshop field refused");
                        }
                        descriptor.set.call(element, payload.value);
                        element.dispatchEvent(
                            new window.Event("input", { bubbles: true })
                        );
                        element.dispatchEvent(
                            new window.Event("change", { bubbles: true })
                        );
                    } else if (payload.operation === "check") {
                        if (
                            !(element instanceof window.HTMLInputElement) ||
                            !["checkbox", "radio"].includes(element.type)
                        ) {
                            throw new Error("Workshop check refused");
                        }
                        if (!element.checked) {
                            element.click();
                        }
                    } else if (payload.operation === "click") {
                        if (!(element instanceof window.HTMLElement)) {
                            throw new Error("Workshop click refused");
                        }
                        element.click();
                    } else {
                        throw new Error("Workshop write refused");
                    }
                    return true;
                }
                """,
                payload,
            )
            if result is not True:
                raise ValueError("Workshop write refused")
        except Exception:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
        finally:
            if handle is not None:
                try:
                    handle.dispose()
                except Exception:
                    raise BrokerIndeterminate(
                        "sealed_browser_cleanup_indeterminate"
                    ) from None
        # A click may initiate navigation after the in-document operation.
        # Rebind the resulting page before any later proof can use it.
        self._assert_document()

    def fill(self, locator: object, value: str) -> None:
        self._write(locator, "fill", value=value)

    def check(self, locator: object) -> None:
        self._write(locator, "check")

    def click(self, locator: object) -> None:
        self._write(locator, "click")

    def exact_description(
        self, locator: object, *, term: str, description: str
    ) -> None:
        try:
            result = locator.evaluate_all(
                WORKSHOP_EXACT_DESCRIPTION_EVALUATOR,
                {
                    "expectedOrigin": ALLOWED_SITE_ORIGIN,
                    "term": term,
                    "description": description,
                },
            )
        except Exception:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
        if result is not True:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")


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
        runtime_provider_factory: Callable[[], PlaywrightRuntimeProvider] | None = None,
    ):
        self._environment = environment
        self._workspace_root = (
            Path(workspace_root) if workspace_root is not None else Path(tempfile.gettempdir())
        )
        self._runtime_provider_factory = runtime_provider_factory or PinnedPlaywrightRuntime

    def _source_environment(self) -> Mapping[str, str]:
        return self._environment if self._environment is not None else os.environ

    def _browser_environment(
        self, workspace: Path, *, browsers: Path | None = None
    ) -> dict[str, str]:
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
        if browsers is not None:
            child_environment["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers)
        return child_environment

    def preflight(self) -> None:
        source = self._source_environment()
        if any(source.get(name) for name in REJECTED_BROWSER_ENV_NAMES):
            raise BrokerRefusal("sealed_browser_environment_refused")
        try:
            workspace_root = self._workspace_root.resolve(strict=True)
            has_residue = any(workspace_root.glob(f"{BROWSER_TEMP_PREFIX}*")) or any(
                workspace_root.glob(f"{BROWSER_PROBE_PREFIX}*")
            )
        except OSError:
            raise BrokerRefusal("sealed_browser_workspace_unavailable") from None
        if not workspace_root.is_dir() or has_residue:
            raise BrokerRefusal("sealed_browser_workspace_residue")

    @staticmethod
    def _assert_site_page(page) -> None:
        if not WorkshopEvaluator._canonical_url(getattr(page, "url", "")):
            raise BrokerRefusal("signed_out_private_baseline_failed")

    def _assert_signed_out_private_baseline(self, page) -> None:
        evaluator = WorkshopEvaluator(page)
        try:
            evaluator.navigate(f"{ALLOWED_SITE_ORIGIN}/app/workshop")
        except BrokerIndeterminate:
            raise BrokerRefusal("signed_out_private_baseline_failed") from None
        # A structural selector is permitted; it intentionally reads neither
        # user text nor browser storage and is never emitted from the worker.
        if evaluator.count(page.locator(".wk-status-banner--preview")) != 1:
            raise BrokerRefusal("signed_out_private_baseline_failed")

    @staticmethod
    def _validated_chromium_executable(
        runtime: StartedPlaywrightRuntime, workspace: Path
    ) -> Path:
        """Bind launch to the provider-validated file before child-env entry."""

        try:
            executable = Path(runtime.chromium_executable).resolve(strict=True)
            browsers = (workspace / "runtime" / "browsers").resolve(strict=True)
            if not executable.is_file():
                raise ValueError("Chromium executable is not a file")
            executable.relative_to(browsers)
        except (AttributeError, OSError, TypeError, ValueError):
            raise BrokerRefusal("sealed_browser_runtime_unavailable") from None
        return executable

    @staticmethod
    def _close_resources(
        contexts: Sequence[object],
        browser: object | None,
        playwright: object | None,
        runtime_provider: PlaywrightRuntimeProvider | None,
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
        if runtime_provider is not None:
            try:
                runtime_provider.release()
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

    @staticmethod
    def _close_probe(
        page: object | None,
        context: object | None,
        browser: object | None,
        root: Path | None,
    ) -> None:
        cleanup_failed = False
        for resource in (page, context, browser):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    cleanup_failed = True
        if root is not None:
            try:
                shutil.rmtree(root)
                if root.exists():
                    cleanup_failed = True
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise BrokerIndeterminate("sealed_browser_cleanup_indeterminate")

    @classmethod
    def _cleanup_partial_session(
        cls,
        *,
        probe_page: object | None,
        probe_context: object | None,
        probe_browser: object | None,
        probe_root: Path | None,
        contexts: Sequence[object],
        browser: object | None,
        playwright: object | None,
        runtime_provider: PlaywrightRuntimeProvider | None,
        workspace: Path | None,
    ) -> None:
        cleanup_failed = False
        try:
            cls._close_probe(probe_page, probe_context, probe_browser, probe_root)
        except BrokerIndeterminate:
            cleanup_failed = True
        try:
            cls._close_resources(
                contexts,
                browser,
                playwright,
                runtime_provider,
                workspace,
                expected_contexts=len(contexts),
            )
        except BrokerIndeterminate:
            cleanup_failed = True
        if cleanup_failed:
            raise BrokerIndeterminate("sealed_browser_cleanup_indeterminate")

    @staticmethod
    def _assert_expected_identity_origin(page, authorization_origin: SealedValue) -> None:
        try:
            parsed = urlparse(str(page.url))
            actual = f"{parsed.scheme}://{parsed.hostname.lower()}"
            if (
                parsed.scheme != "https"
                or parsed.port is not None
                or parsed.username
                or parsed.password
                or actual != authorization_origin.reveal()
            ):
                raise ValueError("unexpected identity origin")
        except (TypeError, ValueError, AttributeError):
            raise BrokerRefusal("unexpected_identity_host") from None

    @staticmethod
    def _fill_password_at_expected_identity_origin(
        page, identity: SealedIdentity, authorization_origin: SealedValue
    ) -> None:
        """Bind one element handle, then origin-check and write in one task."""

        password_handle = None
        try:
            password_handle = page.locator(
                "input[type='password']"
            ).element_handle()
            if password_handle is None:
                raise ValueError("credential target unavailable")
            # Locator waiting and navigation happen before any secret crosses
            # this boundary. A handle is document-bound, so later navigation
            # detaches it instead of resolving the secret against a new page.
            PlaywrightBrowserAdapter._assert_expected_identity_origin(
                page, authorization_origin
            )
            password_handle.evaluate(
                """
                (element, payload) => {
                    if (
                        window.location.origin !== payload.expectedOrigin ||
                        !(element instanceof window.HTMLInputElement) ||
                        element.type !== "password" ||
                        !element.isConnected ||
                        element.ownerDocument.defaultView !== window
                    ) {
                        throw new Error("credential target refused");
                    }
                    const descriptor = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype,
                        "value"
                    );
                    if (!descriptor || typeof descriptor.set !== "function") {
                        throw new Error("credential target refused");
                    }
                    descriptor.set.call(element, payload.secret);
                    element.dispatchEvent(
                        new window.Event("input", { bubbles: true })
                    );
                    element.dispatchEvent(
                        new window.Event("change", { bubbles: true })
                    );
                }
                """,
                {
                    "expectedOrigin": authorization_origin.reveal(),
                    "secret": identity.password.reveal(),
                },
            )
        except Exception:
            raise BrokerRefusal("unexpected_identity_host") from None
        finally:
            if password_handle is not None:
                try:
                    password_handle.dispose()
                except Exception:
                    raise BrokerIndeterminate(
                        "sealed_browser_cleanup_indeterminate"
                    ) from None
        PlaywrightBrowserAdapter._assert_expected_identity_origin(
            page, authorization_origin
        )

    def prepare_attended_session(
        self, authority: AuthorityBinding
    ) -> AttendedBrowserSession:
        self.preflight()
        workspace: Path | None = None
        probe_root: Path | None = None
        probe_browser = None
        probe_context = None
        probe_page = None
        browser = None
        playwright = None
        chromium_executable: Path | None = None
        runtime_provider: PlaywrightRuntimeProvider | None = None
        contexts: dict[str, object] = {}
        try:
            workspace = Path(tempfile.mkdtemp(prefix=BROWSER_TEMP_PREFIX, dir=str(self._workspace_root)))
            runtime_provider = self._runtime_provider_factory()
            runtime = runtime_provider.start(workspace, self._source_environment())
            playwright = runtime.playwright
            chromium_executable = self._validated_chromium_executable(runtime, workspace)
            browser_root = workspace / "runtime" / "browsers"
            probe_root = Path(
                tempfile.mkdtemp(prefix=BROWSER_PROBE_PREFIX, dir=str(self._workspace_root))
            )
            probe_environment = self._browser_environment(
                probe_root, browsers=browser_root
            )
            with _isolated_child_environment(probe_environment):
                probe_browser = playwright.chromium.launch(
                    headless=False,
                    executable_path=str(chromium_executable),
                    downloads_path=str(probe_root),
                    env=probe_environment,
                )
            if probe_browser.version != runtime_provider.expected_browser_version:
                raise BrokerRefusal("sealed_browser_lock_invalid")
            probe_context = probe_browser.new_context(accept_downloads=False)
            probe_page = probe_context.new_page()
            probe_page.goto("about:blank", wait_until="domcontentloaded")
            self._close_probe(probe_page, probe_context, probe_browser, probe_root)
            probe_page = probe_context = probe_browser = None
            probe_root = None

            child_environment = self._browser_environment(
                workspace, browsers=browser_root
            )
            with _isolated_child_environment(child_environment):
                browser = playwright.chromium.launch(
                    headless=False,
                    executable_path=str(chromium_executable),
                    downloads_path=str(workspace),
                    env=child_environment,
                )
            if browser.version != runtime_provider.expected_browser_version:
                raise BrokerRefusal("sealed_browser_lock_invalid")
            for name in ("member_a", "member_b", "signed_out", "switch"):
                contexts[name] = browser.new_context(accept_downloads=False)
            signed_out_page = contexts["signed_out"].new_page()
            self._assert_signed_out_private_baseline(signed_out_page)
            signed_out_page.goto(ALLOWED_SIGN_IN_ENDPOINT, wait_until="domcontentloaded")
            self._assert_expected_identity_origin(
                signed_out_page, authority.authorization_origin
            )
            if signed_out_page.locator("input[type='email']").count() != 1:
                raise BrokerRefusal("unexpected_identity_host")
            return _PlaywrightAttendedSession(
                adapter=self,
                contexts=contexts,
                browser=browser,
                playwright=playwright,
                runtime_provider=runtime_provider,
                workspace=workspace,
                authorization_origin=SealedValue(
                    authority.authorization_origin.reveal()
                ),
                signed_out_page=signed_out_page,
                preflight=BrowserPreflight(
                    locked_runtime=True,
                    probe_launch_closed=True,
                    probe_root_removed=True,
                    prepared_contexts=4,
                    signed_out_private_baseline=True,
                ),
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
            self._cleanup_partial_session(
                probe_page=probe_page,
                probe_context=probe_context,
                probe_browser=probe_browser,
                probe_root=probe_root,
                contexts=tuple(contexts.values()),
                browser=browser,
                playwright=playwright,
                runtime_provider=runtime_provider,
                workspace=workspace,
            )
            raise
        except BrokerRefusal:
            try:
                self._cleanup_partial_session(
                    probe_page=probe_page,
                    probe_context=probe_context,
                    probe_browser=probe_browser,
                    probe_root=probe_root,
                    contexts=tuple(contexts.values()),
                    browser=browser,
                    playwright=playwright,
                    runtime_provider=runtime_provider,
                    workspace=workspace,
                )
            except BrokerIndeterminate:
                raise
            raise
        except Exception:
            try:
                self._cleanup_partial_session(
                    probe_page=probe_page,
                    probe_context=probe_context,
                    probe_browser=probe_browser,
                    probe_root=probe_root,
                    contexts=tuple(contexts.values()),
                    browser=browser,
                    playwright=playwright,
                    runtime_provider=runtime_provider,
                    workspace=workspace,
                )
            except BrokerIndeterminate:
                raise
            raise BrokerRefusal("sealed_browser_runtime_unavailable") from None

    def _wait_for_member_arrival(self, page) -> None:
        page.wait_for_url(re.compile(r"^https://peerslate\.com/app(?:[/?#]|$)"), timeout=60000)

    def _sign_in(
        self, page, identity: SealedIdentity, authorization_origin: SealedValue
    ) -> None:
        page.goto(ALLOWED_SIGN_IN_ENDPOINT, wait_until="domcontentloaded")
        self._assert_expected_identity_origin(page, authorization_origin)
        page.locator("input[type='email']").fill(identity.login_identifier.reveal())
        page.locator("input[type='submit']").click()
        self._assert_expected_identity_origin(page, authorization_origin)
        self._fill_password_at_expected_identity_origin(
            page, identity, authorization_origin
        )
        page.locator("input[type='submit']").click()
        self._wait_for_member_arrival(page)
        # The configured sign-in return is the generic /app landing.  Move to
        # Workshop deliberately, then let the caller prove the private shell;
        # never treat the auth callback or a generic app landing as Workshop.
        arrival = urlparse(str(page.url))
        if (
            arrival.scheme != "https"
            or arrival.netloc != "peerslate.com"
            or arrival.hostname != "peerslate.com"
            or arrival.port is not None
            or arrival.username is not None
            or arrival.password is not None
            or arrival.path != "/app"
        ):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        WorkshopEvaluator(page).navigate(f"{ALLOWED_SITE_ORIGIN}/app/workshop")

    @staticmethod
    def _sign_out(page) -> None:
        WorkshopEvaluator(page).navigate(
            f"{ALLOWED_SITE_ORIGIN}/.auth/logout?post_logout_redirect_uri=%2F",
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
        runtime_provider: PlaywrightRuntimeProvider,
        workspace: Path,
        authorization_origin: SealedValue,
        signed_out_page: object,
        preflight: BrowserPreflight,
        preflight_outcomes: Mapping[str, JourneyObservation],
    ):
        self._adapter = adapter
        self._contexts = dict(contexts)
        self._browser = browser
        self._playwright = playwright
        self._runtime_provider = runtime_provider
        self._workspace = workspace
        self._authorization_origin = authorization_origin
        self._signed_out_page = signed_out_page
        self._preflight = preflight
        self._preflight_outcomes = dict(preflight_outcomes)
        self._cleanup: BrowserCleanup | None = None

    def pre_graph_proof(self) -> BrowserPreflight:
        if self._cleanup is not None:
            raise BrokerRefusal("sealed_browser_session_closed")
        return self._preflight

    @staticmethod
    def _workshop(page) -> WorkshopEvaluator:
        return WorkshopEvaluator(page)

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
        evaluator = WorkshopEvaluator(page)
        if evaluator.count(page.get_by_text(marker, exact=True)) != 0:
            raise BrokerRefusal("private_peer_content_exposed")

    @staticmethod
    def _assert_marker_present(page, marker: str) -> None:
        evaluator = WorkshopEvaluator(page)
        if evaluator.count(page.get_by_text(marker, exact=True)) < 1:
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

        evaluator = WorkshopEvaluator(page)
        evaluator._assert_document()
        if (
            urlparse(str(page.url)).path != "/app/workshop"
            or evaluator.count(page.locator(".wk-status-banner--preview")) != 0
            or evaluator.count(page.locator(AUTHENTICATED_WORKSHOP_CONTROL)) != 1
        ):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")

    @staticmethod
    def _version_from_current_item(page) -> SealedValue:
        evaluator = WorkshopEvaluator(page)
        locator = page.locator("input[name='expected_row_version']")
        if evaluator.count(locator) != 1:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        return SealedValue(evaluator.input_value(locator))

    def _assert_owner_item(
        self,
        page,
        handle: _SealedItemHandle,
        marker: str,
        *,
        require_unchanged: bool = False,
    ) -> None:
        self._workshop(page).navigate(self._item_url(handle.key.reveal()))
        self._assert_authenticated_private_workshop(page)
        self._assert_marker_present(page, marker)
        refreshed = self._version_from_current_item(page)
        if require_unchanged and refreshed.reveal() != handle.version.reveal():
            refreshed.clear()
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        handle.version.clear()
        handle.version = refreshed

    def _create_item(self, page, *, marker: str) -> _SealedItemHandle:
        evaluator = self._workshop(page)
        evaluator.navigate(f"{ALLOWED_SITE_ORIGIN}/app/workshop/add")
        evaluator.fill(page.locator("#wk-title"), marker)
        evaluator.fill(page.locator("#wk-wording"), self._wordings(marker)[0])
        evaluator.check(
            page.locator("input[name='classification'][value='unclassified']")
        )
        evaluator.click(page.get_by_role("button", name="Continue"))
        evaluator.click(page.locator("button[name='save_action'][value='confirm']"))
        href = evaluator.attribute(
            page.get_by_role("link", name="View in My Information"), "href"
        )
        item_values = parse_qs(urlparse(str(href or "")).query).get("item", [])
        if len(item_values) != 1 or not item_values[0]:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        handle = _SealedItemHandle(key=SealedValue(item_values[0]), version=SealedValue("pending"))
        self._assert_owner_item(page, handle, marker)
        return handle

    @staticmethod
    def _wordings(marker: str) -> tuple[str, str, str]:
        return (
            f"{marker}-source  byte & stable",
            f"{marker}-edit-one",
            f"{marker}-edit-two",
        )

    def _record_foreign_mutation_conditional(
        self,
        page,
        owner_page,
        *,
        peer_handle: _SealedItemHandle,
        peer_marker: str,
    ) -> None:
        """Do not send a foreign write without one atomic owner binding.

        ``APIRequestContext`` is not tied to the visible page document: a
        redirect or hostile document can make an otherwise same-origin URL
        appear trustworthy while a mutation is in flight.  Workshop currently
        has no atomically provable foreign-owner form control, so retain the
        honest Conditional rather than manufacture an update or delete probe.
        """
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
        peer: str,
        peer_handle: _SealedItemHandle,
        peer_marker: str,
        outcomes: dict[str, JourneyObservation],
    ) -> None:
        peer_key = peer_handle.key.reveal()
        self._workshop(page).navigate(f"{ALLOWED_SITE_ORIGIN}/app/workshop")
        self._assert_authenticated_private_workshop(page)
        self._assert_marker_absent(page, peer_marker)
        self._assert_authenticated_private_workshop(page)
        self._record_pass(outcomes, f"{actor}_cannot_list_{peer}")

        self._workshop(page).navigate(self._item_url(peer_key))
        self._assert_authenticated_private_workshop(page)
        self._assert_marker_absent(page, peer_marker)
        self._assert_authenticated_private_workshop(page)
        self._record_pass(outcomes, f"{actor}_cannot_read_{peer}")

        self._workshop(page).navigate(f"{ALLOWED_SITE_ORIGIN}/app/workshop")
        self._assert_authenticated_private_workshop(page)
        self._record_foreign_mutation_conditional(
            page,
            owner_page,
            peer_handle=peer_handle,
            peer_marker=peer_marker,
        )
        self._record_conditional(
            outcomes,
            f"{actor}_cannot_update_{peer}",
            "neutral_denial_not_distinguishable",
        )

        self._workshop(page).navigate(f"{ALLOWED_SITE_ORIGIN}/app/workshop")
        self._assert_authenticated_private_workshop(page)
        self._record_foreign_mutation_conditional(
            page,
            owner_page,
            peer_handle=peer_handle,
            peer_marker=peer_marker,
        )
        self._record_conditional(
            outcomes,
            f"{actor}_cannot_delete_{peer}",
            "neutral_denial_not_distinguishable",
        )

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

    def _update_item(
        self,
        page,
        handle: _SealedItemHandle,
        marker: str,
        wording: str,
    ) -> None:
        item_key = handle.key.reveal()
        evaluator = self._workshop(page)
        evaluator.navigate(
            f"{ALLOWED_SITE_ORIGIN}/app/workshop/items/{quote(item_key, safe='')}/edit"
        )
        evaluator.fill(page.locator("#wk-wording"), wording)
        evaluator.click(page.get_by_role("button", name="Continue"))
        evaluator.click(page.locator("button[name='save_action'][value='confirm']"))
        self._assert_owner_item(page, handle, marker)

    def _assert_history_and_disclosure(
        self, page, handle: _SealedItemHandle, marker: str
    ) -> tuple[int, int, int]:
        self._assert_owner_item(page, handle, marker)
        evaluator = self._workshop(page)
        history = page.locator("details.wk-wording-history")
        if evaluator.count(history) != 1:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        count_text = evaluator.text(history.locator(".wk-wording-history__count"))
        note_text = evaluator.text(history.locator(".wk-wording-history__note"))
        versions = history.locator(".wk-wording-history__version")
        if (
            " ".join(str(count_text or "").split()) != "3 retained"
            or " ".join(str(note_text or "").split()) != WORKSHOP_HISTORY_NOTE
            or evaluator.count(history.locator(".wk-wording-history__window")) != 0
            or evaluator.count(versions) != 3
        ):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        expected = tuple(reversed(self._wordings(marker)))
        source = self._wordings(marker)[0].encode("utf-8")
        source_proofs = 0
        for index, approved in enumerate(expected):
            row = versions.nth(index)
            if evaluator.count(row.get_by_text(f"Version {3 - index}", exact=True)) != 1:
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
            wording = row.locator(".wk-wording-history__wording")
            if evaluator.count(wording) != 2:
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
            approved_text = evaluator.text(wording.nth(0))
            source_text = evaluator.text(wording.nth(1))
            if (
                not isinstance(approved_text, str)
                or not isinstance(source_text, str)
                or approved_text.encode("utf-8") != approved.encode("utf-8")
                or source_text.encode("utf-8") != source
            ):
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
            source_proofs += 1
        evaluator.exact_description(
            page.locator(".wk-detail__meta-row"),
            term="Downstream use",
            description="Not used elsewhere",
        )
        return 3, source_proofs, 1

    def _archive_and_restore_item(self, page, handle: _SealedItemHandle, marker: str) -> None:
        item_key = handle.key.reveal()
        evaluator = self._workshop(page)
        evaluator.navigate(self._item_url(item_key))
        evaluator.click(page.get_by_role("button", name="Archive"))
        evaluator.navigate(self._archived_item_url(item_key))
        self._assert_marker_present(page, marker)
        refreshed = self._version_from_current_item(page)
        handle.version.clear()
        handle.version = refreshed
        evaluator.click(page.get_by_role("button", name="Restore"))
        self._assert_owner_item(page, handle, marker)

    def _exercise_session_continuity(self, context, page, *, marker: str) -> None:
        evaluator = self._workshop(page)
        evaluator.reload()
        self._assert_marker_present(page, marker)
        second_tab = context.new_page()
        try:
            self._workshop(second_tab).navigate(f"{ALLOWED_SITE_ORIGIN}/app/workshop")
            self._assert_marker_present(second_tab, marker)
        finally:
            second_tab.close()
        evaluator.navigate(ALLOWED_SITE_ORIGIN)
        evaluator.navigate(f"{ALLOWED_SITE_ORIGIN}/app/workshop")
        self._assert_marker_present(page, marker)

    def _delete_item(self, page, handle: _SealedItemHandle) -> None:
        item_key = handle.key.reveal()
        evaluator = self._workshop(page)
        evaluator.navigate(
            f"{ALLOWED_SITE_ORIGIN}/app/workshop/items/{quote(item_key, safe='')}/delete"
        )
        if (
            evaluator.count(page.get_by_text("Permanent deletion", exact=True)) != 1
            or evaluator.count(
                page.get_by_text("could not check just now", exact=False)
            ) != 0
            or evaluator.count(
                page.get_by_text(
                    "Your saved Opportunity Slate cites this item", exact=False
                )
            )
            != 0
        ):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        evaluator.check(page.locator("input[name='confirm_delete']"))
        evaluator.click(page.get_by_role("button", name="Delete permanently"))

    def _observe_item_residue(
        self, page, handle: _SealedItemHandle, marker: str
    ) -> tuple[int, int]:
        evaluator = self._workshop(page)
        evaluator.navigate(self._item_url(handle.key.reveal()))
        self._assert_authenticated_private_workshop(page)
        active = evaluator.count(page.get_by_text(marker, exact=True))
        active_detail = evaluator.count(page.locator("article.wk-detail"))
        evaluator.navigate(self._archived_item_url(handle.key.reveal()))
        self._assert_authenticated_private_workshop(page)
        archived = evaluator.count(page.get_by_text(marker, exact=True))
        archived_detail = evaluator.count(page.locator("article.wk-detail"))
        if active_detail != 0 or archived_detail != 0:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        return active, archived

    def _sign_out_safely(self, context, page) -> None:
        second_tab = context.new_page()
        try:
            self._workshop(second_tab).navigate(f"{ALLOWED_SITE_ORIGIN}/app/workshop")
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
        markers: dict[str, str] = {}
        delete_attempted: set[str] = set()
        edit_counts: dict[str, int] = {}
        retained_version_counts: dict[str, int] = {}
        retained_source_proof_counts: dict[str, int] = {}
        downstream_disclosure_counts: dict[str, int] = {}
        try:
            if set(outcomes) != {
                "clean_client_a_start",
                "clean_client_b_start",
                "clean_signed_out_control_start",
                "signed_out_private_baseline",
            }:
                raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
            self._adapter._sign_in(
                pages["member_a"], member_a, self._authorization_origin
            )
            self._assert_authenticated_private_workshop(pages["member_a"])
            self._record_pass(outcomes, "member_a_first_arrival")
            self._adapter._sign_in(
                pages["member_b"], member_b, self._authorization_origin
            )
            self._assert_authenticated_private_workshop(pages["member_b"])
            self._record_pass(outcomes, "member_b_first_arrival")

            member_a_marker = member_a.mail_nickname.reveal()
            member_b_marker = member_b.mail_nickname.reveal()
            markers.update(
                {"member_a": member_a_marker, "member_b": member_b_marker}
            )
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
                pages["member_a"], pages["member_b"], actor="member_a",
                peer="member_b", peer_handle=handles["member_b"], peer_marker=member_b_marker, outcomes=outcomes,
            )
            self._exercise_peer_denials(
                pages["member_b"], pages["member_a"], actor="member_b",
                peer="member_a", peer_handle=handles["member_a"], peer_marker=member_a_marker, outcomes=outcomes,
            )

            self._adapter._sign_in(
                pages["switch"], member_a, self._authorization_origin
            )
            self._assert_authenticated_private_workshop(pages["switch"])
            self._assert_marker_present(pages["switch"], member_a_marker)
            self._adapter._sign_out(pages["switch"])
            self._adapter._sign_in(
                pages["switch"], member_b, self._authorization_origin
            )
            self._assert_authenticated_private_workshop(pages["switch"])
            self._assert_marker_present(pages["switch"], member_b_marker)
            self._assert_marker_absent(pages["switch"], member_a_marker)
            self._record_pass(outcomes, "account_switch_member_a_to_member_b")
            self._adapter._sign_out(pages["switch"])
            self._adapter._sign_in(
                pages["switch"], member_a, self._authorization_origin
            )
            self._assert_authenticated_private_workshop(pages["switch"])
            self._assert_marker_present(pages["switch"], member_a_marker)
            self._assert_marker_absent(pages["switch"], member_b_marker)
            self._record_pass(outcomes, "account_switch_member_b_to_member_a")

            for alias, marker in (
                ("member_a", member_a_marker),
                ("member_b", member_b_marker),
            ):
                for wording in self._wordings(marker)[1:]:
                    self._update_item(
                        pages[alias], handles[alias], marker, wording
                    )
                edit_counts[alias] = 2
                (
                    retained_version_counts[alias],
                    retained_source_proof_counts[alias],
                    downstream_disclosure_counts[alias],
                ) = self._assert_history_and_disclosure(
                    pages[alias], handles[alias], marker
                )
            self._archive_and_restore_item(pages["member_a"], handles["member_a"], member_a_marker)
            self._archive_and_restore_item(pages["member_b"], handles["member_b"], member_b_marker)
            for alias, marker in (
                ("member_a", member_a_marker),
                ("member_b", member_b_marker),
            ):
                restored_proof = self._assert_history_and_disclosure(
                    pages[alias], handles[alias], marker
                )
                if restored_proof != (
                    retained_version_counts[alias],
                    retained_source_proof_counts[alias],
                    downstream_disclosure_counts[alias],
                ):
                    raise BrokerIndeterminate(
                        "sealed_browser_operation_indeterminate"
                    )
            self._exercise_session_continuity(self._contexts["member_a"], pages["member_a"], marker=member_a_marker)
            self._record_pass(outcomes, "member_a_refresh_owner_only")
            self._record_pass(outcomes, "member_a_second_tab_owner_only")
            self._record_pass(outcomes, "member_a_public_return_owner_only")
            self._exercise_session_continuity(self._contexts["member_b"], pages["member_b"], marker=member_b_marker)
            self._record_pass(outcomes, "member_b_refresh_owner_only")
            self._record_pass(outcomes, "member_b_second_tab_owner_only")
            self._record_pass(outcomes, "member_b_public_return_owner_only")

            delete_attempted.add("member_a")
            self._delete_item(pages["member_a"], handles["member_a"])
            delete_attempted.add("member_b")
            self._delete_item(pages["member_b"], handles["member_b"])
            active_a, archived_a = self._observe_item_residue(
                pages["member_a"], handles["member_a"], member_a_marker
            )
            active_b, archived_b = self._observe_item_residue(
                pages["member_b"], handles["member_b"], member_b_marker
            )

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
                edit_counts=edit_counts,
                retained_version_counts=retained_version_counts,
                retained_source_proof_counts=retained_source_proof_counts,
                downstream_disclosure_counts=downstream_disclosure_counts,
                active_residue_counts={"member_a": active_a, "member_b": active_b},
                archived_residue_counts={"member_a": archived_a, "member_b": archived_b},
                clean_start_confirmed=True,
            )
        except Exception as error:
            # Once an exact item handle exists, attempt its permanent removal
            # at most once even if a later history, disclosure, peer, or
            # session proof fails.  Process both aliases independently; never
            # let one cleanup error strand the other item or trigger a retry.
            for alias in ALLOWED_ALIASES:
                if alias not in handles or alias in delete_attempted:
                    continue
                delete_attempted.add(alias)
                try:
                    self._delete_item(pages[alias], handles[alias])
                except Exception:
                    pass
            for alias in ALLOWED_ALIASES:
                if alias not in handles or alias not in markers:
                    continue
                try:
                    self._observe_item_residue(
                        pages[alias], handles[alias], markers[alias]
                    )
                except Exception:
                    pass
            if isinstance(error, (BrokerRefusal, BrokerIndeterminate)):
                raise error
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
            self._runtime_provider,
            self._workspace,
            expected_contexts=4,
        )
        self._contexts.clear()
        self._browser = None
        self._playwright = None
        self._runtime_provider = None
        self._authorization_origin.clear()
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
        oidc_issuer: SealedValue,
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
                issuer=oidc_issuer.reveal(),
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
        and args.confirm_permanent_exact_two_deletion
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
    run_fingerprint = hashlib.sha256(run_id.encode("ascii")).hexdigest()[:16]
    generated = []
    for alias in ALLOWED_ALIASES:
        local_part = f"psqa-{run_fingerprint}-{alias}"
        # The cryptographically random, Graph-valid marker makes an ambiguous
        # exact-identity reconciliation attributable to this POST attempt rather
        # than merely to the public run id. It is never emitted or retained.
        creation_marker = "".join(
            choice("abcdefghijkmnopqrstuvwxyz23456789") for _ in range(12)
        )
        mail_nickname = f"{local_part.replace('_', '-')}-{creation_marker}"
        login_identifier = f"{local_part}@{graph_issuer.reveal().lower()}"
        if (
            len(login_identifier) > 64
            or not SAFE_GRAPH_MAIL_NICKNAME.fullmatch(mail_nickname)
        ):
            raise BrokerRefusal("generated_identity_invalid")
        generated.append(
            SealedIdentity(
                alias=alias,
                login_identifier=SealedValue(login_identifier),
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
        or outcome.edit_counts != {"member_a": 2, "member_b": 2}
        or outcome.retained_version_counts != {"member_a": 3, "member_b": 3}
        or outcome.retained_source_proof_counts != {"member_a": 3, "member_b": 3}
        or outcome.downstream_disclosure_counts != {"member_a": 1, "member_b": 1}
        or outcome.active_residue_counts != {"member_a": 0, "member_b": 0}
        or outcome.archived_residue_counts != {"member_a": 0, "member_b": 0}
        or not outcome.clean_start_confirmed
        or cleanup != EXPECTED_BROWSER_CLEANUP
    ):
        raise BrokerIndeterminate("sealed_browser_operation_indeterminate")


def _require_exact_browser_cleanup(cleanup: BrowserCleanup | None) -> None:
    if cleanup != EXPECTED_BROWSER_CLEANUP:
        raise BrokerIndeterminate("sealed_browser_cleanup_indeterminate")


def _validate_browser_preflight(preflight: BrowserPreflight) -> None:
    if preflight != BrowserPreflight(
        locked_runtime=True,
        probe_launch_closed=True,
        probe_root_removed=True,
        prepared_contexts=4,
        signed_out_private_baseline=True,
    ):
        raise BrokerRefusal("sealed_browser_preflight_failed")


def run_broker(
    *,
    run_id: str,
    cutoff: datetime,
    authority_adapter: AuthorityAdapter,
    graph: GraphAdapter,
    browser: BrowserAdapter,
    retirement_adapter: RetirementAdapter,
    choice: Callable[[str], str] = secrets.choice,
    owner_authorization_ref: str = OWNER_AUTHORIZATION_REF,
) -> Mapping[str, object]:
    """Execute one exact-two sealed lifecycle and return an allowlisted report."""

    _require_run_id(run_id)
    if owner_authorization_ref != OWNER_AUTHORIZATION_REF:
        raise BrokerRefusal("owner_authorization_mismatch")
    identities: tuple[SealedIdentity, SealedIdentity] = ()
    authority: AuthorityBinding | None = None
    graph_issuer: SealedValue | None = None
    session: AttendedBrowserSession | None = None
    created = 0
    creation_states = {alias: "not_attempted" for alias in ALLOWED_ALIASES}
    attempted_after: dict[str, datetime] = {}
    mutation_started = False
    phase = "production_authority"
    try:
        authority = authority_adapter.resolve()
        phase = "browser_preflight"
        session = browser.prepare_attended_session(authority)
        _validate_browser_preflight(session.pre_graph_proof())
        phase = "graph_preflight"
        graph_issuer = graph.prepare(authority)
        identities = _generate_identities(graph_issuer, run_id=run_id, choice=choice)
        absence_proofs = graph.prove_customer_absence(
            identities,
            authority=authority,
            graph_issuer=graph_issuer,
        )
        if absence_proofs != 4:
            raise BrokerRefusal("graph_customer_absence_unverified")
        phase = "graph_creation"
        try:
            for identity in identities:
                mutation_started = True
                creation_outcome = graph.create_customer(
                    identity,
                    authority=authority,
                    graph_issuer=graph_issuer,
                )
                try:
                    if not isinstance(creation_outcome, GraphCreationOutcome):
                        raise ValueError("untyped creation outcome")
                    creation_states[identity.alias] = creation_outcome.state
                    attempted_after[identity.alias] = (
                        creation_outcome.attempted_after.astimezone(timezone.utc)
                    )
                    if (
                        creation_outcome.state != "known_created"
                        or creation_outcome.subject is None
                        or attempted_after[identity.alias].microsecond != 0
                    ):
                        raise BrokerIndeterminate("graph_creation_indeterminate")
                    identity.subject = SealedValue(
                        str(UUID(creation_outcome.subject.reveal()))
                    )
                except (TypeError, ValueError, AttributeError, OverflowError):
                    raise BrokerIndeterminate("graph_creation_indeterminate") from None
                finally:
                    if isinstance(creation_outcome, GraphCreationOutcome):
                        creation_outcome.clear()
                created += 1
        except Exception:
            try:
                graph.contain_partial_creation(
                    identities,
                    creation_states=creation_states,
                    attempted_after=attempted_after,
                    authority=authority,
                    graph_issuer=graph_issuer,
                )
            except Exception:
                pass
            raise BrokerIndeterminate("graph_creation_indeterminate") from None
        if created != 2 or identities[0].subject is None or identities[1].subject is None:
            raise BrokerIndeterminate("graph_creation_indeterminate")
        if identities[0].subject.reveal() == identities[1].subject.reveal():
            raise BrokerIndeterminate("graph_creation_indeterminate")
        browser_failure: BrokerIndeterminate | None = None
        browser_cleanup_failed = False
        browser_outcome: BrowserOutcome | None = None
        browser_cleanup: BrowserCleanup | None = None
        phase = "browser_journeys"
        try:
            browser_outcome = session.exercise_canonical_journeys(identities)
        except Exception:
            browser_failure = BrokerIndeterminate(
                "sealed_browser_operation_indeterminate"
            )
        phase = "browser_cleanup"
        try:
            browser_cleanup = session.destroy_and_verify()
        except Exception:
            browser_cleanup_failed = True
            browser_failure = BrokerIndeterminate(
                "sealed_browser_cleanup_indeterminate"
            )
        if browser_failure is None:
            try:
                if browser_outcome is None or browser_cleanup is None:
                    raise BrokerIndeterminate(
                        "sealed_browser_operation_indeterminate"
                    )
                _validate_browser_outcome(browser_outcome, browser_cleanup)
            except Exception:
                browser_failure = BrokerIndeterminate(
                    "sealed_browser_operation_indeterminate"
                )
        # SQL retirement is gated on a structurally exact closed browser and
        # removed runtime root. A failed journey with successful cleanup may
        # still enter exact containment; an unproved cleanup may not bypass
        # this boundary merely to make later residue look smaller.
        if browser_cleanup_failed:
            raise BrokerIndeterminate("sealed_browser_cleanup_indeterminate")
        _require_exact_browser_cleanup(browser_cleanup)
        phase = "retirement"
        retirement_report = retirement_adapter.retire(
            [identities[0].subject, identities[1].subject],
            oidc_issuer=authority.oidc_issuer,
            cutoff=cutoff,
        )
        if (
            retirement_report.get("result") != "pass"
            or retirement_report.get("state") != "retired"
            or retirement_report.get("counts") != {"retired_members": 2}
        ):
            raise BrokerIndeterminate("retirement_indeterminate")
        phase = "graph_deletion"
        deletion_outcome = graph.delete_exact_pair(
            [identities[0].subject, identities[1].subject],
            authority=authority,
            graph_issuer=graph_issuer,
        )
        if deletion_outcome != GraphDeletionOutcome(
            soft_deleted=2,
            soft_state_proofs=4,
            permanently_deleted=2,
            final_absence_proofs=4,
        ):
            raise BrokerIndeterminate("graph_deletion_indeterminate")
        if browser_failure is not None:
            raise browser_failure
        if browser_outcome is None or browser_cleanup is None:
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate")
        return {
            "result": "conditional",
            "state": "retired_and_permanently_deleted",
            "counts": {
                "requested_identities": 2,
                "precreation_absence_proofs": absence_proofs,
                "provisioned_identities": 2,
                "member_arrivals": 2,
                "account_switches": 2,
                "canonical_journeys": len(browser_outcome.journey_outcomes),
                "conditional_journeys": len(REQUIRED_CONDITIONAL_OUTCOMES),
                "created_items": sum(browser_outcome.created_item_counts.values()),
                "item_edits": sum(browser_outcome.edit_counts.values()),
                "retained_versions": sum(
                    browser_outcome.retained_version_counts.values()
                ),
                "retained_source_proofs": sum(
                    browser_outcome.retained_source_proof_counts.values()
                ),
                "downstream_disclosures": sum(
                    browser_outcome.downstream_disclosure_counts.values()
                ),
                "active_residue": sum(browser_outcome.active_residue_counts.values()),
                "archived_residue": sum(
                    browser_outcome.archived_residue_counts.values()
                ),
                "destroyed_contexts": browser_cleanup.destroyed_contexts,
                "retired_members": 2,
                "soft_deleted_identities": deletion_outcome.soft_deleted,
                "soft_state_proofs": deletion_outcome.soft_state_proofs,
                "permanently_deleted_identities": deletion_outcome.permanently_deleted,
                "final_absence_proofs": deletion_outcome.final_absence_proofs,
            },
        }
    except BrokerRefusal as error:
        if not mutation_started:
            raise error
        if phase == "graph_creation":
            raise BrokerIndeterminate("graph_creation_indeterminate") from None
        if phase.startswith("browser"):
            raise BrokerIndeterminate("sealed_browser_operation_indeterminate") from None
        if phase == "retirement":
            raise BrokerIndeterminate("retirement_indeterminate") from None
        raise BrokerIndeterminate("graph_deletion_indeterminate") from None
    except BrokerIndeterminate:
        raise
    except Exception:
        if not mutation_started:
            raise BrokerRefusal("sealed_broker_operation_failed") from None
        reason = {
            "graph_creation": "graph_creation_indeterminate",
            "browser_journeys": "sealed_browser_operation_indeterminate",
            "browser_cleanup": "sealed_browser_cleanup_indeterminate",
            "retirement": "retirement_indeterminate",
            "graph_deletion": "graph_deletion_indeterminate",
        }.get(phase, "sealed_broker_operation_indeterminate")
        raise BrokerIndeterminate(reason) from None
    finally:
        cleanup_error: BrokerIndeterminate | BrokerRefusal | None = None
        if session is not None:
            try:
                session.destroy_and_verify()
            except Exception:
                cleanup_error = BrokerIndeterminate(
                    "sealed_browser_cleanup_indeterminate"
                )
        for identity in identities:
            identity.clear()
        if graph_issuer is not None:
            graph_issuer.clear()
        try:
            graph.clear()
        except Exception:
            if mutation_started:
                cleanup_error = BrokerIndeterminate(
                    "sealed_broker_cleanup_indeterminate"
                )
            else:
                cleanup_error = BrokerRefusal("sealed_broker_cleanup_failed")
        if authority is not None:
            authority.clear()
        if cleanup_error is not None:
            raise cleanup_error


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
    run.add_argument("--confirm-permanent-exact-two-deletion", action="store_true")
    return parser


def _emit(report: Mapping[str, object]) -> None:
    print(json.dumps(report, sort_keys=True))


def main(
    argv: Sequence[str] | None = None,
    *,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    authority_factory: Callable[[], AuthorityAdapter] = AzureAppAuthorityResolver,
    graph_factory: Callable[[], GraphAdapter] = MicrosoftGraphAdapter,
    browser_factory: Callable[[], BrowserAdapter] = PlaywrightBrowserAdapter,
    retirement_factory: Callable[[], RetirementAdapter] = DirectRetirementAdapter,
) -> int:
    args = _parser().parse_args(argv)
    if args.mode == "plan":
        _emit(
            {
                "result": "planned",
                "counts": {
                    "customer_identities": 2,
                    "precreation_collision_reads": 4,
                    "contexts": 4,
                    "journeys": len(JOURNEYS),
                    "item_edits": 4,
                    "retained_versions": 6,
                },
                "graph_deletion": (
                    "soft_and_permanent_exact_two_after_verified_retirement"
                ),
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
            authority_adapter=authority_factory(),
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
    "AuthorityBinding",
    "AzureAppAuthorityResolver",
    "AzureCliGraphTokenProvider",
    "BrokerIndeterminate",
    "BrokerRefusal",
    "BrowserCleanup",
    "BrowserOutcome",
    "BrowserPreflight",
    "DirectRetirementAdapter",
    "GraphCreationOutcome",
    "GraphDeletionOutcome",
    "MicrosoftGraphAdapter",
    "PlaywrightBrowserAdapter",
    "PinnedPlaywrightRuntime",
    "REQUIRED_CONDITIONAL_OUTCOMES",
    "SealedIdentity",
    "SealedValue",
    "main",
    "run_broker",
]

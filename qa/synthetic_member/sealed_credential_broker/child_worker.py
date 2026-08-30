"""Exact locked-venv entrypoint for one sealed browser child.

The parent invokes this file with no arguments under ``python -I -B``.  All
operation material enters through the inherited anonymous stdin pipe, and the
only stdout frames are the broker module's fixed structural protocol.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import sys
from typing import BinaryIO, Callable, Mapping


_SCRIPT = Path(__file__).resolve(strict=True)
_REPOSITORY_ROOT = _SCRIPT.parents[3]
_EXPECTED_SCRIPT = (
    _REPOSITORY_ROOT
    / "qa"
    / "synthetic_member"
    / "sealed_credential_broker"
    / "child_worker.py"
).resolve(strict=True)
if _SCRIPT != _EXPECTED_SCRIPT or not (_REPOSITORY_ROOT / "qa").is_dir():
    raise SystemExit(3)
sys.path.insert(0, str(_REPOSITORY_ROOT))

from qa.synthetic_member.sealed_credential_broker import (
    ALLOWED_ALIASES,
    ALLOWED_BROWSER_CHILD_ENV_NAMES,
    AuthorityBinding,
    BROWSER_CHILD_PROTOCOL_SCHEMA,
    BROWSER_TEMP_PREFIX,
    BrokerIndeterminate,
    BrokerRefusal,
    BrowserCleanup,
    CHILD_PASSWORD_ALPHABET,
    PinnedPlaywrightRuntime,
    SAFE_CHILD_LOGIN_IDENTIFIER,
    SAFE_GRAPH_MAIL_NICKNAME,
    SealedIdentity,
    SealedValue,
    StartedPlaywrightRuntime,
    ProvisionedPlaywrightRuntime,
    AttendedBrowserSession,
    BrowserOutcome,
    PlaywrightRuntimeProvider,
    REJECTED_BROWSER_ENV_NAMES,
    _NativePlaywrightBrowserAdapter,
    _canonical_windows_environment_is_exact,
    _authorization_origin_for_child,
    _exact_protocol_mapping,
    _read_child_message,
    _validate_browser_preflight,
    _validate_browser_outcome,
    _write_child_message,
)


def _browser_preflight_payload(preflight: object) -> Mapping[str, object]:
    return {
        "locked_runtime": preflight.locked_runtime,
        "probe_launch_closed": preflight.probe_launch_closed,
        "probe_root_removed": preflight.probe_root_removed,
        "prepared_contexts": preflight.prepared_contexts,
        "signed_out_private_baseline": preflight.signed_out_private_baseline,
    }


def _browser_outcome_payload(outcome: BrowserOutcome) -> Mapping[str, object]:
    return {
        "journey_outcomes": {
            journey_id: {
                "status": observation.status,
                "observed_outcome": observation.observed_outcome,
                "note_code": observation.note_code,
            }
            for journey_id, observation in outcome.journey_outcomes.items()
        },
        "created_item_counts": dict(outcome.created_item_counts),
        "edit_counts": dict(outcome.edit_counts),
        "retained_version_counts": dict(outcome.retained_version_counts),
        "retained_source_proof_counts": dict(
            outcome.retained_source_proof_counts
        ),
        "downstream_disclosure_counts": dict(
            outcome.downstream_disclosure_counts
        ),
        "active_residue_counts": dict(outcome.active_residue_counts),
        "archived_residue_counts": dict(outcome.archived_residue_counts),
        "clean_start_confirmed": outcome.clean_start_confirmed,
    }


def _cleanup_payload(*, destroyed_contexts: int, complete: bool) -> Mapping[str, object]:
    return {"destroyed_contexts": destroyed_contexts, "complete": complete}


def _parse_child_identities(
    value: object, *, tenant_label: str
) -> tuple[SealedIdentity, SealedIdentity]:
    if type(value) is not list or len(value) != 2:
        raise BrokerRefusal("sealed_browser_protocol_refused")
    identities: list[SealedIdentity] = []
    fingerprints: list[str] = []
    try:
        for index, raw_value in enumerate(value):
            raw = _exact_protocol_mapping(
                raw_value,
                {"alias", "login_identifier", "password", "mail_nickname"},
            )
            alias = raw["alias"]
            login_identifier = raw["login_identifier"]
            password = raw["password"]
            mail_nickname = raw["mail_nickname"]
            login_match = (
                re.fullmatch(
                    r"psqa-([0-9a-f]{16})-(member_[ab])@([a-z0-9][a-z0-9.-]+)",
                    login_identifier,
                )
                if isinstance(login_identifier, str)
                else None
            )
            expected_local = (
                f"psqa-{login_match.group(1)}-{alias}"
                if login_match is not None
                else ""
            )
            if (
                alias != ALLOWED_ALIASES[index]
                or not isinstance(login_identifier, str)
                or len(login_identifier) > 64
                or not SAFE_CHILD_LOGIN_IDENTIFIER.fullmatch(login_identifier)
                or login_match is None
                or login_match.group(2) != alias
                or login_match.group(3) != f"{tenant_label}.onmicrosoft.com"
                or not isinstance(password, str)
                or len(password) != 32
                or not password.startswith("Aa1!")
                or any(
                    character not in CHILD_PASSWORD_ALPHABET
                    for character in password[4:]
                )
                or not isinstance(mail_nickname, str)
                or not SAFE_GRAPH_MAIL_NICKNAME.fullmatch(mail_nickname)
                or re.fullmatch(
                    re.escape(expected_local.replace("_", "-"))
                    + r"-[abcdefghijkmnopqrstuvwxyz23456789]{12}",
                    mail_nickname,
                )
                is None
            ):
                raise BrokerRefusal("sealed_browser_protocol_refused")
            fingerprints.append(login_match.group(1))
            identities.append(
                SealedIdentity(
                    alias=alias,
                    login_identifier=SealedValue(login_identifier),
                    password=SealedValue(password),
                    mail_nickname=SealedValue(mail_nickname),
                )
            )
        if (
            fingerprints[0] != fingerprints[1]
            or identities[0].login_identifier.reveal()
            == identities[1].login_identifier.reveal()
            or identities[0].mail_nickname.reveal()
            == identities[1].mail_nickname.reveal()
        ):
            raise BrokerRefusal("sealed_browser_protocol_refused")
    except Exception:
        for identity in identities:
            identity.clear()
        raise
    return identities[0], identities[1]


class _ExistingChildRuntimeProvider:
    """Child-only native import bound to the already provisioned exact venv."""

    def __init__(
        self,
        *,
        workspace: Path,
        site_packages: Path,
        browsers: Path,
        environment: Mapping[str, str],
        expected_browser_version: str,
    ):
        self._workspace = workspace
        self._site_packages = site_packages
        self._browsers = browsers
        self._environment = dict(environment)
        self._loader = PinnedPlaywrightRuntime()
        self.expected_browser_version = expected_browser_version

    def provision(
        self, workspace: Path, environment: Mapping[str, str]
    ) -> ProvisionedPlaywrightRuntime:
        del workspace, environment
        raise BrokerRefusal("sealed_browser_runtime_unavailable")

    def start(
        self, workspace: Path, environment: Mapping[str, str]
    ) -> StartedPlaywrightRuntime:
        try:
            if (
                workspace.resolve(strict=True) != self._workspace
                or dict(environment) != self._environment
            ):
                raise ValueError("runtime binding changed")
        except (OSError, ValueError):
            raise BrokerRefusal("sealed_browser_runtime_unavailable") from None
        return self._loader._load_started_playwright(
            self._site_packages,
            self._browsers,
            self._environment,
        )

    def release(self) -> None:
        self._loader.release()


def _native_child_runtime_provider() -> tuple[Path, _ExistingChildRuntimeProvider]:
    environment = dict(os.environ)
    if (
        set(environment).difference(ALLOWED_BROWSER_CHILD_ENV_NAMES)
        or any(environment.get(name) for name in REJECTED_BROWSER_ENV_NAMES)
        or any(
            name in environment
            for name in ("AUTHORIZATION_REF", "PEERSLATE_AUTH_ISSUER", "PYTHONPATH")
        )
        or not _canonical_windows_environment_is_exact(environment)
    ):
        raise BrokerRefusal("sealed_browser_environment_refused")
    try:
        workspace = Path(environment["HOME"]).resolve(strict=True)
        if not workspace.is_dir() or not workspace.name.startswith(BROWSER_TEMP_PREFIX):
            raise ValueError("unexpected workspace")
        for name in (
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "TEMP",
            "TMP",
            "TMPDIR",
        ):
            if Path(environment[name]).resolve(strict=True) != workspace:
                raise ValueError("workspace environment changed")
        browsers = Path(environment["PLAYWRIGHT_BROWSERS_PATH"]).resolve(strict=True)
        if browsers != (workspace / "runtime" / "browsers").resolve(strict=True):
            raise ValueError("browser root changed")
    except (KeyError, OSError, ValueError):
        raise BrokerRefusal("sealed_browser_environment_refused") from None
    runtime = PinnedPlaywrightRuntime()
    lock = runtime._lock()
    target = lock.get("active_target")
    if not isinstance(target, Mapping):
        raise BrokerRefusal("sealed_browser_lock_invalid")
    try:
        venv_root = (workspace / "runtime" / "venv").resolve(strict=True)
        venv_python = venv_root.joinpath(*target["venv_python"]).resolve(strict=True)
        site_packages = venv_root.joinpath(*target["site_packages"]).resolve(strict=True)
        if (
            Path(sys.executable).resolve(strict=True) != venv_python
            or not venv_python.is_file()
            or not site_packages.is_dir()
            or not browsers.is_dir()
        ):
            raise ValueError("child is not the exact locked venv")
        venv_python.relative_to(venv_root)
        site_packages.relative_to(venv_root)
    except (KeyError, OSError, TypeError, ValueError):
        raise BrokerRefusal("sealed_browser_runtime_unavailable") from None
    return workspace, _ExistingChildRuntimeProvider(
        workspace=workspace,
        site_packages=site_packages,
        browsers=browsers,
        environment=environment,
        expected_browser_version=str(lock["chromium"]["browser_version"]),
    )


def _prepare_native_child_session(
    authorization_origin: SealedValue,
) -> AttendedBrowserSession:
    workspace, runtime_provider = _native_child_runtime_provider()
    adapter = _NativePlaywrightBrowserAdapter(
        environment=dict(os.environ),
        workspace_root=workspace.parent,
        runtime_provider_factory=lambda: runtime_provider,
        fixed_workspace=workspace,
        remove_workspace_on_cleanup=False,
    )
    authority = AuthorityBinding(
        oidc_issuer=SealedValue("child-only"),
        authorization_origin=SealedValue(authorization_origin.reveal()),
        tenant_id=SealedValue("child-only"),
        tenant_label=SealedValue("child-only"),
    )
    try:
        return adapter.prepare_attended_session(authority)
    finally:
        authority.clear()


def _read_child_command(stream: BinaryIO) -> dict[str, object]:
    command = _read_child_message(stream)
    try:
        trailing = stream.read(1)
    except OSError:
        raise BrokerIndeterminate("sealed_browser_protocol_indeterminate") from None
    if trailing != b"":
        raise BrokerIndeterminate("sealed_browser_protocol_indeterminate")
    return command


def _browser_child_main(
    stdin: BinaryIO | None = None,
    stdout: BinaryIO | None = None,
    *,
    session_factory: Callable[[SealedValue], AttendedBrowserSession] = (
        _prepare_native_child_session
    ),
) -> int:
    """Run one exact prepare/identity-or-abort exchange inside the locked venv."""

    input_stream = stdin if stdin is not None else sys.stdin.buffer
    output_stream = stdout if stdout is not None else sys.stdout.buffer
    session: AttendedBrowserSession | None = None
    authorization_origin: SealedValue | None = None
    identities: tuple[SealedIdentity, SealedIdentity] = ()
    ready_sent = False
    action = "none"
    outcome: BrowserOutcome | None = None
    failure: Exception | None = None
    cleanup = _cleanup_payload(destroyed_contexts=0, complete=True)
    try:
        prepare = _exact_protocol_mapping(
            _read_child_message(input_stream),
            {"schema_version", "type", "authorization_origin"},
        )
        if (
            type(prepare["schema_version"]) is not int
            or prepare["schema_version"] != BROWSER_CHILD_PROTOCOL_SCHEMA
            or prepare["type"] != "prepare"
            or not isinstance(prepare["authorization_origin"], str)
        ):
            raise BrokerRefusal("sealed_browser_protocol_refused")
        authorization_origin = SealedValue(
            _authorization_origin_for_child(prepare["authorization_origin"])
        )
        session = session_factory(authorization_origin)
        preflight = session.pre_graph_proof()
        _validate_browser_preflight(preflight)
        _write_child_message(
            output_stream,
            {
                "schema_version": BROWSER_CHILD_PROTOCOL_SCHEMA,
                "type": "ready",
                "preflight": _browser_preflight_payload(preflight),
            },
        )
        ready_sent = True
        command = _read_child_command(input_stream)
        if command.get("type") == "abort":
            payload = _exact_protocol_mapping(
                command, {"schema_version", "type"}
            )
            if (
                type(payload["schema_version"]) is not int
                or payload["schema_version"] != BROWSER_CHILD_PROTOCOL_SCHEMA
            ):
                raise BrokerIndeterminate("sealed_browser_protocol_indeterminate")
            action = "abort"
        elif command.get("type") == "identities":
            payload = _exact_protocol_mapping(
                command, {"schema_version", "type", "identities"}
            )
            if (
                type(payload["schema_version"]) is not int
                or payload["schema_version"] != BROWSER_CHILD_PROTOCOL_SCHEMA
            ):
                raise BrokerIndeterminate("sealed_browser_protocol_indeterminate")
            action = "identities"
            tenant_label = authorization_origin.reveal().removeprefix(
                "https://"
            ).split(".", 1)[0]
            identities = _parse_child_identities(
                payload["identities"], tenant_label=tenant_label
            )
            outcome = session.exercise_canonical_journeys(identities)
        else:
            raise BrokerIndeterminate("sealed_browser_protocol_indeterminate")
    except Exception as error:
        failure = error
    finally:
        if session is not None:
            try:
                closed = session.destroy_and_verify()
                if closed != BrowserCleanup(
                    destroyed_contexts=4,
                    temporary_root_removed=False,
                ):
                    raise BrokerIndeterminate(
                        "sealed_browser_cleanup_indeterminate"
                    )
                cleanup = _cleanup_payload(destroyed_contexts=4, complete=True)
            except Exception:
                cleanup = _cleanup_payload(destroyed_contexts=0, complete=False)
                failure = BrokerIndeterminate("sealed_browser_cleanup_indeterminate")
        elif isinstance(failure, BrokerIndeterminate):
            cleanup = _cleanup_payload(destroyed_contexts=0, complete=False)
        for identity in identities:
            identity.clear()
        if authorization_origin is not None:
            authorization_origin.clear()

    if failure is None and action == "identities":
        try:
            if outcome is None:
                raise ValueError("missing browser outcome")
            _validate_browser_outcome(
                outcome,
                BrowserCleanup(
                    destroyed_contexts=4,
                    temporary_root_removed=True,
                ),
            )
        except Exception:
            failure = BrokerIndeterminate(
                "sealed_browser_operation_indeterminate"
            )

    try:
        if not ready_sent:
            result = "indeterminate" if isinstance(failure, BrokerIndeterminate) else "refused"
            reason_code = (
                "sealed_browser_cleanup_indeterminate"
                if isinstance(failure, BrokerIndeterminate)
                else "sealed_browser_runtime_unavailable"
            )
            if isinstance(failure, BrokerRefusal) and failure.code in {
                "sealed_browser_environment_refused",
                "sealed_browser_lock_invalid",
                "sealed_browser_runtime_unavailable",
                "sealed_browser_workspace_residue",
                "sealed_browser_protocol_refused",
            }:
                reason_code = (
                    "sealed_browser_protocol_refused"
                    if failure.code == "sealed_browser_protocol_refused"
                    else "sealed_browser_runtime_unavailable"
                )
            _write_child_message(
                output_stream,
                {
                    "schema_version": BROWSER_CHILD_PROTOCOL_SCHEMA,
                    "type": "ready_error",
                    "result": result,
                    "reason_code": reason_code,
                    "cleanup": cleanup,
                },
            )
            return 0
        if failure is None and action == "abort":
            response: Mapping[str, object] = {
                "schema_version": BROWSER_CHILD_PROTOCOL_SCHEMA,
                "type": "complete",
                "result": "aborted",
                "cleanup": cleanup,
            }
        elif failure is None and action == "identities" and outcome is not None:
            response = {
                "schema_version": BROWSER_CHILD_PROTOCOL_SCHEMA,
                "type": "complete",
                "result": "ok",
                "outcome": _browser_outcome_payload(outcome),
                "cleanup": cleanup,
            }
        else:
            response = {
                "schema_version": BROWSER_CHILD_PROTOCOL_SCHEMA,
                "type": "complete",
                "result": "indeterminate",
                "reason_code": (
                    "sealed_browser_cleanup_indeterminate"
                    if cleanup["complete"] is not True
                    else "sealed_browser_operation_indeterminate"
                ),
                "cleanup": cleanup,
            }
        _write_child_message(output_stream, response)
        return 0
    except Exception:
        return 3




def main() -> int:
    if len(sys.argv) != 1:
        return 3
    return _browser_child_main()


if __name__ == "__main__":
    raise SystemExit(main())

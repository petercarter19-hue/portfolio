#!/usr/bin/env python3
"""Fail closed before a PeerSlate production or schema operation.

The pipeline passes queue-time values as process arguments and the Azure OAuth
token as an environment variable. The token is used only to read build state;
it is never printed or written.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MIGRATION_ID_RE = re.compile(r"^PS-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
AUTHORIZATION_REFERENCE_RE = re.compile(r"^[ -~]{8,240}$")
ACTIVE_STATUSES = {"notStarted", "inProgress", "cancelling", "postponed"}
AUTOMATIC_REASONS = {"individualCI", "batchedCI"}
# BuildReason values returned by Azure DevOps REST 7.1. The `none` and `all`
# filter sentinels are not unambiguous reasons for an individual build.
SUPPORTED_RUN_REASONS = AUTOMATIC_REASONS | {
    "manual", "schedule", "scheduleForced", "userCreated",
    "validateShelveset", "checkInShelveset", "pullRequest",
    "buildCompletion", "resourceTrigger", "triggered",
}
MAX_BUILD_PAGES = 20
# Azure BuildStatus flags: inProgress=1, cancelling=4, postponed=8,
# notStarted=32. Filter on the server before bounded pagination; the API has
# no sourceVersion filter, so exact-SHA matching remains client-side.
ACTIVE_STATUS_FILTER = "45"


class PreflightError(ValueError):
    """An unsafe or ambiguous production-operation request."""


@dataclass(frozen=True)
class Operation:
    deploy_application: bool
    schema_action: str
    source_version: str
    authorization_reference: str


def parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise PreflightError(f"expected true or false, found {value!r}")


def validate_request(
    *,
    build_reason: str,
    source_branch: str,
    source_version: str,
    force_production_deploy: bool,
    manual_source_version: str,
    production_authorization_reference: str,
    schema_action: str,
    schema_migration_id: str,
    schema_rollback_confirm: str,
) -> Operation:
    if source_branch != "refs/heads/main":
        raise PreflightError("production operations require refs/heads/main")
    if not SHA_RE.fullmatch(source_version):
        raise PreflightError("Build.SourceVersion must be a 40-character SHA")
    if schema_action not in {"none", "report", "apply", "rollback"}:
        raise PreflightError(f"unknown schema action {schema_action!r}")

    deploy_application = force_production_deploy

    if force_production_deploy and schema_action != "none":
        raise PreflightError(
            "application deployment and schema action cannot share one run"
        )
    if force_production_deploy:
        if build_reason != "Manual":
            raise PreflightError("production deployment is manual-only")
        if manual_source_version != source_version:
            raise PreflightError(
                "manualProductionSourceVersion must exactly match "
                "Build.SourceVersion"
            )
        if (
            production_authorization_reference
            != production_authorization_reference.strip()
            or not AUTHORIZATION_REFERENCE_RE.fullmatch(
                production_authorization_reference
            )
        ):
            raise PreflightError(
                "productionAuthorizationReference must be a trimmed, printable "
                "8-240 character reference to Pete's explicit authorization"
            )
    elif manual_source_version or production_authorization_reference:
        raise PreflightError(
            "manualProductionSourceVersion and productionAuthorizationReference "
            "are allowed only with an authorized manual deployment"
        )

    if schema_action != "none":
        if build_reason != "Manual":
            raise PreflightError("schema actions are manual-only")
        if force_production_deploy:
            raise PreflightError("schema actions cannot force a web deploy")

    if schema_action in {"apply", "rollback"}:
        if not MIGRATION_ID_RE.fullmatch(schema_migration_id):
            raise PreflightError(
                "apply and rollback require one valid schema migration id"
            )
    elif schema_migration_id:
        raise PreflightError(
            "schemaMigrationId must be empty unless action is apply or rollback"
        )

    if schema_action == "rollback":
        if schema_rollback_confirm != schema_migration_id:
            raise PreflightError(
                "schemaRollbackConfirm must exactly repeat schemaMigrationId"
            )
    elif schema_rollback_confirm:
        raise PreflightError(
            "schemaRollbackConfirm must be empty unless action is rollback"
        )

    return Operation(
        deploy_application=deploy_application,
        schema_action=schema_action,
        source_version=source_version,
        authorization_reference=production_authorization_reference,
    )


def read_exact_sha_runs(
    *,
    collection_uri: str,
    project_id: str,
    definition_id: str,
    source_version: str,
    token: str,
    opener=urllib.request.urlopen,
) -> list[dict]:
    if not collection_uri.startswith("https://dev.azure.com/"):
        raise PreflightError("unexpected Azure DevOps collection URI")
    if not project_id or not definition_id or not token:
        raise PreflightError(
            "Azure build identity and System.AccessToken are required for a "
            "manual production operation"
        )

    base = collection_uri.rstrip("/") + "/"
    matching = []
    continuation_token = ""
    seen_tokens = set()
    for _page in range(MAX_BUILD_PAGES):
        parameters = {
            "definitions": definition_id,
            # Azure DevOps' build-list API does not support sourceVersion as
            # a server-side filter. Unknown query parameters are silently
            # ignored, so exact-SHA matching must happen on every response
            # page.
            "branchName": "refs/heads/main",
            "statusFilter": ACTIVE_STATUS_FILTER,
            "queryOrder": "queueTimeDescending",
            "$top": "50",
            "api-version": "7.1",
        }
        if continuation_token:
            parameters["continuationToken"] = continuation_token
        query = urllib.parse.urlencode(parameters)
        url = (
            f"{base}{urllib.parse.quote(project_id, safe='')}/"
            f"_apis/build/builds?{query}"
        )
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        try:
            with opener(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
                headers = getattr(response, "headers", {}) or {}
                next_token = str(
                    headers.get("x-ms-continuationtoken", "") or ""
                ).strip()
        except Exception as exc:  # fail closed without exposing token or URL query
            raise PreflightError(
                f"could not read exact-SHA Azure run state: {type(exc).__name__}"
            ) from exc
        if not isinstance(payload, dict):
            raise PreflightError("Azure build-state response has an invalid shape")
        values = payload.get("value")
        if not isinstance(values, list):
            raise PreflightError("Azure build-state response has an invalid shape")
        for item in values:
            if (
                not isinstance(item, dict)
                or type(item.get("id")) is not int
                or item["id"] <= 0
                or not isinstance(item.get("sourceVersion"), str)
                or not SHA_RE.fullmatch(item["sourceVersion"])
                or not isinstance(item.get("reason"), str)
                or item["reason"] not in SUPPORTED_RUN_REASONS
                or not isinstance(item.get("status"), str)
                or item.get("status") not in ACTIVE_STATUSES
            ):
                raise PreflightError("Azure build-state response has an invalid run")
            if item["sourceVersion"] == source_version:
                matching.append(item)
        if not next_token:
            return matching
        if next_token in seen_tokens:
            raise PreflightError("Azure build-state pagination repeated a token")
        seen_tokens.add(next_token)
        continuation_token = next_token
    raise PreflightError("Azure build-state pagination exceeded its safe bound")


def reject_overlapping_exact_sha_run(
    runs: list[dict], *, current_build_id: str
) -> None:
    automatic = [
        run
        for run in runs
        if str(run.get("id")) != str(current_build_id)
        and run.get("reason") in AUTOMATIC_REASONS
    ]
    active = [run for run in automatic if run.get("status") in ACTIVE_STATUSES]
    if active:
        ids = ", ".join(str(run.get("id")) for run in active)
        raise PreflightError(
            f"automatic exact-SHA CI run still active ({ids}); production "
            "operation refused until it finishes"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-reason", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--force-production-deploy", required=True)
    parser.add_argument("--manual-source-version", default="")
    parser.add_argument("--production-authorization-reference", default="")
    parser.add_argument("--schema-action", required=True)
    parser.add_argument("--schema-migration-id", default="")
    parser.add_argument("--schema-rollback-confirm", default="")
    parser.add_argument("--collection-uri", default="")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--definition-id", default="")
    parser.add_argument("--build-id", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        force = parse_boolean(args.force_production_deploy)
        operation = validate_request(
            build_reason=args.build_reason,
            source_branch=args.source_branch,
            source_version=args.source_version,
            force_production_deploy=force,
            manual_source_version=args.manual_source_version,
            production_authorization_reference=(
                args.production_authorization_reference
            ),
            schema_action=args.schema_action,
            schema_migration_id=args.schema_migration_id,
            schema_rollback_confirm=args.schema_rollback_confirm,
        )
        if force:
            runs = read_exact_sha_runs(
                collection_uri=args.collection_uri,
                project_id=args.project_id,
                definition_id=args.definition_id,
                source_version=args.source_version,
                token=os.environ.get("SYSTEM_ACCESSTOKEN", ""),
            )
            reject_overlapping_exact_sha_run(
                runs, current_build_id=args.build_id
            )
    except PreflightError as exc:
        print(json.dumps({"result": "fail", "error": str(exc)}, indent=2))
        return 2

    print(
        json.dumps(
            {
                "result": "pass",
                "source_version": operation.source_version,
                "deploy_application": operation.deploy_application,
                "schema_action": operation.schema_action,
                "authorization_reference": operation.authorization_reference,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

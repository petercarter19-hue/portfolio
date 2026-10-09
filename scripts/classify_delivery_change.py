"""Fail-closed, repository-only PR classification for the two real Build jobs.

The fast disposition is an optimization, never delivery authority.  Azure's
synthetic PR merge commit supplies immutable S and T; the current target ref is
read separately from Azure.  An unknown proof takes the full test route.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import types
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(os.environ.get("BUILD_SOURCESDIRECTORY") or Path(__file__).resolve().parents[1]).resolve()
SHA = re.compile(r"[0-9a-f]{40}\Z")
REPOSITORY_ID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z"
)
PR_REF = re.compile(r"refs/pull/([1-9][0-9]*)/merge\Z")
CLAIMS = "docs/governance/lane_claims"
TRUSTED_BLOBS = (
    "scripts/classify_delivery_change.py",
    "scripts/delivery_preflight.py",
    "scripts/worktree_lifecycle.py",
    "azure-pipelines.yml",
    ".gitleaks.toml",
    "docs/governance/CURRENT_LANES.json",
)
JOBS = ("BuildJob", "InterviewStudioBrowserCI")
SCHEMA = 1
CLAIM_FIELDS = {
    "schema_version", "package", "state", "outcome", "assignment", "writer_ref",
    "branch", "delivery_path", "repository_authority", "production_authority",
    "activated_from_main", "owner_outcome_ref", "surfaces", "evidence_surfaces",
    "domains", "review_requirement", "handoff", "checkpoint_sha", "merged_sha",
    "closed_at",
}
OPTIONAL_CLAIM_FIELDS = {"scope_release", "supersession", "superseded_at"}


class InvalidChange(ValueError):
    """A proven PR has an illegal claim-set or transition, not just unknown scope."""


class UnknownProvenance(ValueError):
    """A proof was unavailable; run all tests instead of granting a shortcut."""


@dataclass(frozen=True)
class Context:
    reason: str
    source_branch: str
    merge: str
    source: str
    target_branch: str
    fork: str
    pr_id: str
    source_repo_uri: str
    build_repo_uri: str
    collection_uri: str
    project_id: str
    repository_id: str
    access_token: str = ""

    @classmethod
    def environment(cls) -> Context:
        names = (
            "BUILD_REASON", "BUILD_SOURCEBRANCH", "BUILD_SOURCEVERSION",
            "SYSTEM_PULLREQUEST_SOURCECOMMITID",
            "SYSTEM_PULLREQUEST_TARGETBRANCH", "SYSTEM_PULLREQUEST_ISFORK",
            "SYSTEM_PULLREQUEST_PULLREQUESTID",
            "SYSTEM_PULLREQUEST_SOURCEREPOSITORYURI", "BUILD_REPOSITORY_URI",
            "SYSTEM_COLLECTIONURI", "SYSTEM_TEAMPROJECTID",
            "BUILD_REPOSITORY_ID", "SYSTEM_ACCESSTOKEN",
        )
        return cls(*(os.environ.get(name, "") for name in names))


@dataclass(frozen=True)
class Decision:
    disposition: str
    reason: str
    source: str = ""
    target: str = ""
    merge: str = ""
    classifier_sha256: str = ""

    def record(self, job: str) -> dict:
        if job not in JOBS and job != "FinalValidation":
            raise ValueError("unknown required validation job")
        result = {
            "schema_version": SCHEMA,
            "job": job,
            "disposition": self.disposition,
            "reason": self.reason,
            "source": self.source,
            "target": self.target,
            "merge": self.merge,
            "classifier_sha256": self.classifier_sha256,
        }
        result["record_sha256"] = hashlib.sha256(
            json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return result


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    if result.returncode:
        raise UnknownProvenance("required Git object or full history is unavailable")
    return result.stdout


def git_text(root: Path, *args: str) -> str:
    return git(root, *args).decode("utf-8", "strict").strip()


def blob(root: Path, commit: str, path: str) -> tuple[str, bytes] | None:
    raw = git(root, "ls-tree", "-z", commit, "--", path)
    records = [record for record in raw.split(b"\0") if record]
    if not records:
        return None
    if len(records) != 1:
        raise InvalidChange("ambiguous tracked path")
    try:
        metadata, actual = records[0].split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidChange("malformed tracked path") from exc
    if actual.decode("utf-8", "strict") != path or kind != "blob":
        raise InvalidChange("tracked path does not resolve to its exact blob")
    return mode, git(root, "cat-file", "blob", oid)


def strict_json(payload: bytes) -> dict:
    if len(payload) > 128_000:
        raise InvalidChange("oversized control JSON")

    def pairs(items: list[tuple[str, object]]) -> dict:
        value: dict = {}
        for key, item in items:
            if key in value:
                raise InvalidChange("duplicate JSON member")
            value[key] = item
        return value

    try:
        parsed = json.loads(payload.decode("utf-8", "strict"), object_pairs_hook=pairs)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidChange("malformed control JSON") from exc
    if not isinstance(parsed, dict):
        raise InvalidChange("control JSON must be an object")
    return parsed


def repository_uri(value: str) -> tuple[str, str, str | None, str]:
    """Accept Azure's project-qualified and documented org-level Git URIs.

    Repository ID and non-fork PR metadata are the server identity anchors;
    the two URIs must additionally agree on organization, repository name,
    and project whenever both URI forms include it.
    """
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "https" or parsed.hostname != "dev.azure.com"
        or parsed.port is not None or parsed.password is not None
        or parsed.query or parsed.fragment):
        raise UnknownProvenance("untrusted source repository URI")
    parts = [urllib.parse.unquote(part) for part in parsed.path.strip("/").split("/")]
    if (len(parts) not in {3, 4} or parts[-2] != "_git"
        or any(not part or part in {".", ".."} or "/" in part or "\\" in part for part in parts)):
        raise UnknownProvenance("unsupported Azure repository URI")
    organization, repository = parts[0].casefold(), parts[-1].casefold()
    if parsed.username and parsed.username.casefold() != organization:
        raise UnknownProvenance("repository URI organization differs from its userinfo")
    project = parts[1].casefold() if len(parts) == 4 else None
    return parsed.hostname, organization, project, repository


def same_repository(ctx: Context) -> bool:
    if not REPOSITORY_ID.fullmatch(ctx.repository_id):
        raise UnknownProvenance("build repository identity is unavailable")
    source = repository_uri(ctx.source_repo_uri)
    build = repository_uri(ctx.build_repo_uri)
    collection = urllib.parse.urlsplit(ctx.collection_uri)
    if (collection.scheme != "https" or collection.hostname != "dev.azure.com"
        or collection.query or collection.fragment or collection.port is not None):
        raise UnknownProvenance("Azure collection identity is unavailable")
    collection_parts = collection.path.strip("/").split("/")
    if len(collection_parts) != 1 or not collection_parts[0]:
        raise UnknownProvenance("Azure collection organization is ambiguous")
    organization = collection_parts[0].casefold()
    return (source[1] == build[1] == organization
            and source[3] == build[3]
            and (source[2] is None or build[2] is None or source[2] == build[2]))


def azure_branch_tip(ctx: Context, branch: str) -> str:
    """Read one exact Azure ref; never trust an S-controlled SHA argument."""
    if not ctx.access_token or not ctx.collection_uri.startswith("https://"):
        raise UnknownProvenance("Azure target-ref read is unavailable")
    if not REPOSITORY_ID.fullmatch(ctx.repository_id):
        raise UnknownProvenance("repository identity is unavailable")
    if not re.fullmatch(r"(?:main|(?:work|codex)/[A-Za-z0-9._/-]+)", branch):
        raise UnknownProvenance("requested Azure ref is not a supported branch")
    ref = "refs/heads/" + branch
    url = (
        ctx.collection_uri.rstrip("/")
        + "/"
        + urllib.parse.quote(ctx.project_id, safe="")
        + "/_apis/git/repositories/"
        + urllib.parse.quote(ctx.repository_id, safe="")
        + "/refs?filter="
        + urllib.parse.quote("heads/" + branch, safe="")
        + "&api-version=7.1"
    )
    request = urllib.request.Request(
        url, headers={"Authorization": "Bearer " + ctx.access_token, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200:
                raise UnknownProvenance("Azure target-ref read failed")
            document = strict_json(response.read(128_001))
    except (OSError, urllib.error.HTTPError, ValueError) as exc:
        raise UnknownProvenance("Azure target-ref read failed") from exc
    values = document.get("value")
    exact = [item for item in values if isinstance(item, dict) and item.get("name") == ref] if isinstance(values, list) else []
    if (
        type(document.get("count")) is not int
        or document["count"] < 1
        or not isinstance(values, list)
        or document["count"] != len(values)
        or len(exact) != 1
        or not isinstance(exact[0].get("objectId"), str)
        or not SHA.fullmatch(exact[0]["objectId"])
    ):
        raise UnknownProvenance("Azure branch ref is missing or ambiguous")
    return exact[0]["objectId"]


def azure_main_tip(ctx: Context) -> str:
    return azure_branch_tip(ctx, "main")


def changed_paths(root: Path, target: str, merge: str) -> list[tuple[str, str]]:
    raw = git(root, "diff", "--name-status", "-z", "--no-renames", target, merge)
    fields = raw.split(b"\0")
    if fields[-1:] == [b""]:
        fields.pop()
    if len(fields) % 2:
        raise UnknownProvenance("malformed complete PR delta")
    try:
        return [(fields[i].decode("ascii"), fields[i + 1].decode("utf-8", "strict"))
                for i in range(0, len(fields), 2)]
    except UnicodeDecodeError as exc:
        raise UnknownProvenance("unrepresentable PR path") from exc


@contextlib.contextmanager
def target_validator(root: Path, target: str):
    """Execute only the accepted validator and lifecycle bytes from T.

    The accepted preflight imports ``scripts.worktree_lifecycle``.  An empty,
    in-memory package and exact T modules satisfy that import without adding
    the PR checkout to Python's search path or executing candidate __init__.
    Restore the caller's module cache so unit tests remain isolated.
    """
    names = ("scripts", "scripts.worktree_lifecycle", "scripts.delivery_preflight")
    previous = {name: sys.modules.get(name) for name in names}
    package = types.ModuleType("scripts")
    package.__path__ = []
    package.__package__ = "scripts"
    sys.modules["scripts"] = package
    try:
        for short in ("worktree_lifecycle", "delivery_preflight"):
            path = f"scripts/{short}.py"
            item = blob(root, target, path)
            if item is None or item[0] != "100644":
                raise UnknownProvenance("trusted target validator is unavailable")
            name = f"scripts.{short}"
            module = types.ModuleType(name)
            module.__file__ = str(root / path)
            module.__package__ = "scripts"
            sys.modules[name] = module
            setattr(package, short, module)
            exec(compile(item[1], module.__file__, "exec"), module.__dict__)
        yield sys.modules["scripts.delivery_preflight"]
    finally:
        for name, prior in previous.items():
            if prior is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prior


def claim_set(root: Path, commit: str, validator: types.ModuleType) -> dict[str, dict]:

    entries = git(root, "ls-tree", "-r", "-z", commit, "--", CLAIMS)
    result: dict[str, dict] = {}
    for entry in (item for item in entries.split(b"\0") if item):
        try:
            metadata, raw_path = entry.split(b"\t", 1)
            mode, kind, _oid = metadata.decode("ascii").split()
            path = raw_path.decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError) as exc:
            raise InvalidChange("malformed claim-tree entry") from exc
        if not (path.startswith(CLAIMS + "/") and path.endswith(".json")):
            continue
        if "/" in path[len(CLAIMS) + 1:]:
            continue  # Fixed evidence/receipt directories are not claim records.
        if mode != "100644" or kind != "blob" or not Path(path).name.startswith("PS-"):
            raise InvalidChange("claim entry is not an ordinary canonical JSON file")
        item = blob(root, commit, path)
        if item is None:
            raise InvalidChange("claim disappeared from immutable tree")
        claim = strict_json(item[1])
        if (type(claim.get("schema_version")) is not int
            or set(claim) - OPTIONAL_CLAIM_FIELDS != CLAIM_FIELDS):
            raise InvalidChange("claim JSON has missing, unknown or non-integer schema fields")
        package = claim.get("package")
        key = package.casefold() if isinstance(package, str) else path.casefold()
        if key in result:
            raise InvalidChange("duplicate package claim")
        claim["_relative_path"] = path
        result[key] = claim
    errors = validator.validate_claim_set(result)
    if errors:
        raise InvalidChange("claim-set invariants failed: " + errors[0])
    return result


def _transition(
    target: str, path: str, before: dict | None, after: dict,
    root: Path, validator: types.ModuleType,
) -> str:

    old = {key: value for key, value in before.items() if key != "_relative_path"} if before else None
    new = {key: value for key, value in after.items() if key != "_relative_path"}
    if old is None:
        if (new.get("state") == "active"
            and new.get("activated_from_main") == target
            and all(new.get(key) is None for key in ("checkpoint_sha", "merged_sha", "closed_at", "handoff"))):
            return "activation"
        raise InvalidChange("illegal ordinary activation")
    changed = {key for key in set(old) | set(new) if old.get(key) != new.get(key)}
    old_state, new_state = old.get("state"), new.get("state")
    if old_state == "active" and new_state == "active":
        if (changed == {"repository_authority", "owner_outcome_ref"}
            and old.get("repository_authority") == "write_only"
            and new.get("repository_authority") == "through_merge"
            and old.get("owner_outcome_ref") != new.get("owner_outcome_ref")
            and validator.REF_RE.fullmatch(str(new.get("owner_outcome_ref", "")))):
            return "authorize"
        if changed == {"surfaces"}:
            prior, current = old.get("surfaces"), new.get("surfaces")
            if not isinstance(prior, list) or not isinstance(current, list) or current[:len(prior)] != prior or len(current) <= len(prior):
                raise InvalidChange("extension must append only exact paths")
            for added in current[len(prior):]:
                item = blob(root, target, added)
                if item is None or item[0] != "100644" or validator.extension_surface_is_broad(root, target, added):
                    raise InvalidChange("extension must append tracked ordinary files")
            return "extend-surfaces"
    if old_state == "active" and new_state == "paused" and changed == {"state", "checkpoint_sha"}:
        return "pause"
    if old_state == "paused" and new_state == "active" and changed == {"state"}:
        return "resume"
    if old_state in {"active", "paused"} and new_state == "closed" and changed == {"state", "merged_sha", "closed_at"}:
        return "close"
    # Protected recovery/transfer/scope-release transitions need their own
    # machine-local proofs. Never mistake unrelated field tampering for one.
    exceptional = (
        changed <= {"surfaces", "domains", "scope_release"}
        and "scope_release" in changed and old_state == new_state == "active"
    ) or (
        changed == {"writer_ref", "handoff"}
        and old_state == new_state == "active"
    ) or (
        changed == {"writer_ref", "branch", "handoff"}
        and old_state == new_state == "active"
    ) or (
        changed == {"state", "checkpoint_sha", "superseded_at", "supersession"}
        and new_state == "superseded"
    )
    if exceptional:
        return "unsupported"
    raise InvalidChange("illegal or unexplained claim transition")


def validate_repair_activation(
    root: Path, target: str, merge: str,
    delta: list[tuple[str, str]], claim_changes: list[str],
) -> None:
    """Validate structural full-CI routing, never external repair authority.

    Only the immutable target supplies validators and the repair boundary.
    Owner authorization and hash-bound independent reviews remain separate
    local admission proofs; candidate code cannot attest to itself here.
    """
    if len(claim_changes) != 1:
        raise InvalidChange("repair activation must add exactly one claim")
    path = claim_changes[0]
    with target_validator(root, target) as validator:
        index_blob = blob(root, target, "docs/governance/CURRENT_LANES.json")
        if index_blob is None or index_blob[0] != "100644":
            raise UnknownProvenance("authoritative claim index is missing")
        index = strict_json(index_blob[1])
        if index.get("schema_version") != 4 or validator.validate_index(index):
            raise UnknownProvenance("authoritative claim index schema is unsupported")
        before_set = claim_set(root, target, validator)
        after_set = claim_set(root, merge, validator)
        after = next((claim for claim in after_set.values()
                      if claim["_relative_path"] == path), None)
        if (after is None or after["package"].casefold() in before_set
            or path != validator.claim_relative_path(after["package"])
            or blob(root, target, path) is not None
            or ("A", path) not in delta):
            raise InvalidChange("repair requires a fresh canonical activation claim")
        if (_transition(target, path, None, after, root, validator) != "activation"
            or any(field in after for field in OPTIONAL_CLAIM_FIELDS)
            or after["delivery_path"] != "Protected"
            or after["review_requirement"] != "independent"
            or after["repository_authority"] not in {"through_merge", "write_only"}
            or after["production_authority"] != "withheld"
            or not validator.REF_RE.fullmatch(after["owner_outcome_ref"])
            or after["owner_outcome_ref"] == after["writer_ref"]):
            raise InvalidChange("repair requires an owner-selected Protected independent activation")
        repair_paths = {changed for _status, changed in delta} - {path}
        allowed = getattr(validator, "REPAIR_SURFACES", None)
        if allowed is None:
            raise UnknownProvenance("target repair boundary is unavailable")
        if not repair_paths or repair_paths - allowed:
            raise InvalidChange("repair contains unsupported files or no gate correction")
        expected_surfaces = repair_paths | set(validator.control_relative_paths(after["package"]))
        if set(after["surfaces"]) != expected_surfaces:
            raise InvalidChange("repair must reserve exactly changed files and fixed controls")
        for status, changed in delta:
            try:
                canonical = validator.normalize_path(changed)
            except ValueError as exc:
                raise InvalidChange("repair path is not canonical") from exc
            old, new = blob(root, target, changed), blob(root, merge, changed)
            if (canonical != changed or status not in {"A", "M"}
                or new is None or new[0] != "100644"
                or (status == "A" and old is not None)
                or (status == "M" and (old is None or old[0] != "100644"))):
                raise InvalidChange("repair permits only added or modified regular files without mode changes")


def classify(
    root: Path, ctx: Context, *, target_tip: Callable[[Context], str] = azure_main_tip,
    branch_tip: Callable[[Context, str], str] = azure_branch_tip,
) -> Decision:
    if ctx.reason != "PullRequest":
        return Decision("full", "not a branch-policy PR build")
    try:
        match = PR_REF.fullmatch(ctx.source_branch)
        if (match is None or ctx.pr_id != match.group(1)
            or ctx.target_branch != "refs/heads/main" or ctx.fork != "False"
            or not SHA.fullmatch(ctx.merge) or not SHA.fullmatch(ctx.source)
            or not same_repository(ctx)):
            raise UnknownProvenance("PR source, target or fork provenance is uncertain")
        if git_text(root, "rev-parse", "HEAD") != ctx.merge:
            raise UnknownProvenance("checkout is not the exact Azure merge commit")
        parents = git_text(root, "show", "-s", "--format=%P", ctx.merge).split()
        if len(parents) != 2 or parents[1] != ctx.source:
            raise UnknownProvenance("Azure merge/source ancestry is uncertain")
        target = parents[0]
        if target_tip(ctx) != target:
            raise UnknownProvenance("main moved since the Azure PR merge was computed")
        for commit in (target, ctx.source, ctx.merge):
            if git_text(root, "cat-file", "-t", commit) != "commit":
                raise UnknownProvenance("full PR commit history is unavailable")
        if git_text(root, "rev-parse", "--is-shallow-repository") != "false":
            raise UnknownProvenance("full Git history is required for control-only validation")
        classifier = blob(root, target, TRUSTED_BLOBS[0])
        if classifier is None or classifier[0] != "100644":
            raise UnknownProvenance("classifier is not yet installed on main")
        digest = hashlib.sha256(classifier[1]).hexdigest()
        result = Decision("full", "unclassified PR delta", ctx.source, target, ctx.merge, digest)
        trusted = True
        for path in TRUSTED_BLOBS:
            expected = blob(root, target, path)
            if expected is None or expected[0] != "100644":
                trusted = False
                break
            if blob(root, ctx.source, path) != expected or blob(root, ctx.merge, path) != expected:
                trusted = False
                break
        # All template guard blobs at T are also immutable for this candidate.
        template_paths = git_text(root, "ls-tree", "-r", "--name-only", target, "--", "pipelines/templates").splitlines()
        for path in template_paths:
            expected = blob(root, target, path)
            if expected is None or blob(root, ctx.source, path) != expected or blob(root, ctx.merge, path) != expected:
                trusted = False
                break
        delta = changed_paths(root, target, ctx.merge)
        claim_changes = [path for _status, path in delta if path.startswith(CLAIMS + "/") and path.endswith(".json") and "/" not in path[len(CLAIMS) + 1:]]
        if claim_changes and len(delta) > 1:
            validate_repair_activation(root, target, ctx.merge, delta, claim_changes)
            return Decision("full", "bounded required-check repair activation",
                            ctx.source, target, ctx.merge, digest)
        if not trusted:
            if claim_changes:
                raise InvalidChange("claim transition cannot certify altered validation guards")
            return Decision("full", "trusted guard changed", ctx.source, target, ctx.merge, digest)
        if not claim_changes:
            return result
        if len(claim_changes) != 1 or len(delta) != 1:
            raise InvalidChange("claim control PR must change exactly one claim")
        with target_validator(root, target) as validator:
            index_blob = blob(root, target, "docs/governance/CURRENT_LANES.json")
            if index_blob is None:
                raise UnknownProvenance("authoritative claim index is missing")
            index = strict_json(index_blob[1])
            if index.get("schema_version") != 4 or validator.validate_index(index):
                raise UnknownProvenance("authoritative claim index schema is unsupported")
            before_set = claim_set(root, target, validator)
            after_set = claim_set(root, ctx.merge, validator)
            for key in set(before_set) & set(after_set):
                if before_set[key].get("package") != after_set[key].get("package"):
                    raise InvalidChange("claim package identity changed")
            path = claim_changes[0]
            status, _ = next((pair for pair in delta if pair[1] == path))
            if status not in {"A", "M"}:
                raise InvalidChange("claim deletion, rename or mode transition is illegal")
            item = blob(root, ctx.merge, path)
            if item is None or item[0] != "100644":
                raise InvalidChange("claim must be a plain tracked JSON file")
            after = next((value for value in after_set.values() if value["_relative_path"] == path), None)
            before = next((value for value in before_set.values() if value["_relative_path"] == path), None)
            if after is None or (before is None and status != "A") or (before is not None and status != "M"):
                raise InvalidChange("claim change has ambiguous identity")
            transition = _transition(target, path, before, after, root, validator)
            if transition == "unsupported":
                return Decision("full", "exceptional control transition", ctx.source, target, ctx.merge, digest)
            if transition in {"pause", "resume"}:
                checkpoint = after.get("checkpoint_sha") if transition == "pause" else before.get("checkpoint_sha")
                if branch_tip(ctx, str(after["branch"])) != checkpoint:
                    raise UnknownProvenance("preserved implementation checkpoint moved")
            if transition == "close":
                # Close has additional accepted-candidate/receipt and product
                # introduction proofs. Unless each is independently available,
                # leave it on the full path and the owner's ordinary preflight.
                return Decision("full", "close introduction proof requires normal delivery", ctx.source, target, ctx.merge, digest)
            return Decision("control_only_validated", transition, ctx.source, target, ctx.merge, digest)
    except InvalidChange:
        raise
    except (UnknownProvenance, OSError, UnicodeDecodeError, ValueError) as exc:
        return Decision("full", str(exc))


def _read_record(path: Path) -> dict:
    record = strict_json(path.read_bytes())
    required = {"schema_version", "job", "disposition", "reason", "source", "target", "merge", "classifier_sha256", "record_sha256"}
    if set(record) != required or type(record["schema_version"]) is not int or record["schema_version"] != SCHEMA:
        raise InvalidChange("disposition artifact has an unknown schema")
    digest = record.pop("record_sha256")
    expected = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != expected:
        raise InvalidChange("disposition artifact digest differs")
    record["record_sha256"] = digest
    return record


def verify_coherence(left: dict, right: dict, final: Decision) -> None:
    if left.get("job") != JOBS[0] or right.get("job") != JOBS[1]:
        raise InvalidChange("one or both required executed jobs are missing")
    expected = final.record("FinalValidation")
    for field in ("disposition", "reason", "source", "target", "merge", "classifier_sha256"):
        if left.get(field) != right.get(field) or left.get(field) != expected[field]:
            raise InvalidChange("required job dispositions disagree or target drifted")
    if final.disposition not in {"full", "control_only_validated"}:
        raise InvalidChange("unknown final disposition")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    classify_args = sub.add_parser("classify")
    classify_args.add_argument("--job", choices=JOBS, required=True)
    classify_args.add_argument("--output", type=Path, required=True)
    classify_args.add_argument("--force-full", action="store_true",
                               help="bootstrap when main does not yet contain this classifier")
    classify_args.add_argument("--no-vso", action="store_true",
                               help="bootstrap full artifact after YAML fixed the output to false")
    verify_args = sub.add_parser("verify")
    verify_args.add_argument("--build", type=Path, required=True)
    verify_args.add_argument("--browser", type=Path, required=True)
    verify_args.add_argument("--bootstrap-full", action="store_true",
                             help="match the fixed full-only rollout branch")
    args = parser.parse_args(argv)
    try:
        context = Context.environment()
        decision = (
            Decision("full", "not a branch-policy PR build" if context.reason != "PullRequest"
                     else "classifier is not yet installed on main")
            if (args.mode == "classify" and args.force_full)
            or (args.mode == "verify" and args.bootstrap_full)
            else classify(ROOT, context)
        )
        if args.mode == "classify":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(decision.record(args.job), sort_keys=True) + "\n", encoding="utf-8")
            if not args.no_vso:
                print("##vso[task.setvariable variable=deliveryControlOnly;isOutput=true;isReadOnly=true]" + ("true" if decision.disposition == "control_only_validated" else "false"))
            print(f"Delivery CI disposition: {decision.disposition} ({decision.reason})")
        else:
            verify_coherence(_read_record(args.build), _read_record(args.browser), decision)
            print("Both required jobs executed with the same immutable source/target disposition")
        return 0
    except (InvalidChange, OSError) as exc:
        print("Delivery CI provenance/claim validation failed: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

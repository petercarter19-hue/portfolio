"""The guarded-change version tripwire (correction B1).

The §2 tripwire rule: any change to guarded behaviour — a guarded
repository blob, an external implementation digest, the manifest builder,
or the digest algorithm itself — must arrive with the responsible
version change (`contracts_version` or `guardian_set_version`), or CI
fails.

The control anchors against an IMMUTABLE PRIOR VERSION RECORD, not
against files the mutable builder regenerates:
`prompts/interview/contracts/version-anchors.json` is append-only, is
written only by an explicit, separate anchoring command (never by the
ordinary build), is excluded from the guarded manifest it anchors (an
anchor cannot live inside the identity it pins), and is tamper-evidenced
by a hash chain over its entries. The anchoring command itself refuses to
append while the guarded identity has drifted under unchanged versions —
so the only way to move the anchor is to change the responsible version,
which is exactly the reviewable act the tripwire exists to force.

Everything here is pure computation over explicit inputs (prior anchor
identity, candidate identity, both version pairs, and the classified
changes), so the required proof matrix runs as ordinary unit tests
without scratch mutations.
"""

import hashlib
import re

from services.interview_ai.identity import (
    canonical_json_bytes,
    runtime_core_digest,
)

ANCHOR_DOMAIN = b"peerslate.interview.anchor.v1\x00"
ANCHOR_SCHEMA = "interview-version-anchors@1"

# Consolidated correction B1: the candidate-local chain is bound to an
# EXTERNAL trust root — the manager's consolidated-review record, which
# names a preserved candidate SHA. The trust-root file pins (a) that SHA,
# (b) the exact anchors-file blob hash committed at it, (c) the anchor
# count, latest chain value, and a domain-framed digest of the anchor
# PREFIX as of that record. A fresh replacement chain, a truncated
# prefix, a deleted/rebootstrapped file, or a coordinated rewrite of
# guarded code + derived files + the local chain all fail against the
# pinned prefix; the pin itself is one manager-auditable record that can
# be checked against the review text and against git history.
TRUST_ROOT_SCHEMA = "interview-anchor-trust-root@1"
TRUST_ROOT_DOMAIN = b"peerslate.interview.anchor-trust-root.v1\x00"

# B1 second round: the five reviewed values are ALSO embedded here, in the
# guarded tripwire code, so a trust record that was rewritten to bless a
# different chain fails against these constants even where git history is
# unavailable (a deployed artifact). The record file still carries the
# values (it is the manager's auditable custody record outside the
# writer's surfaces); verification requires the file and this embedded
# copy to AGREE and the live chain prefix to hash to the reviewed digest,
# so a local rewrite of one without the other is rejected. These values
# were dictated verbatim by the manager's 2026-08-21 review packet.
REVIEWED_TRUST_ROOT = {
    "manager_review_sha": "a0402d33d066baa18e446bad2f632a48e2f84380",
    "trusted_anchor_count": 5,
    "trusted_blob_sha256":
        "a0aa1302245022abad2780d791f9a7adc28ade989a389fb389ea2f4437172b0d",
    "trusted_latest_chain":
        "670927cb7b1fe26f7200d816201a05a9b8522439fd5372bc0b87028c70a0163c",
    "trusted_prefix_sha256":
        "37f66fc7caf43e07aec9ced203a79f7a5246e16e02937ea713cd9f5f041b4fdb",
}

_VERSION_PATTERN = re.compile(r"^([a-z](?:[a-z-]*[a-z])?)@([1-9][0-9]*)$")


class TripwireViolation(ValueError):
    """A guarded change arrived without the responsible version change."""


def identity_snapshot(entries, external_artifacts, guardian_set_version,
                      contracts_version):
    """One comparable identity record, digest included."""
    return {
        "entries": [
            {"path": entry["path"], "sha256": entry["sha256"]}
            for entry in entries
        ],
        "external_artifacts": [
            {
                "name": artifact["name"],
                "coordinate": artifact["coordinate"],
                "artifacts": [
                    {"filename": item["filename"], "sha256": item["sha256"]}
                    for item in artifact["artifacts"]
                ],
            }
            for artifact in external_artifacts
        ],
        "guardian_set_version": guardian_set_version,
        "contracts_version": contracts_version,
        "runtime_core_digest": runtime_core_digest(
            entries, external_artifacts
        ),
    }


def classify_identity_changes(prior, candidate):
    """Name exactly which guarded paths and external artifacts changed."""
    prior_paths = {e["path"]: e["sha256"] for e in prior["entries"]}
    candidate_paths = {e["path"]: e["sha256"] for e in candidate["entries"]}
    repository_paths = sorted(
        set(prior_paths) ^ set(candidate_paths)
        | {
            path for path in set(prior_paths) & set(candidate_paths)
            if prior_paths[path] != candidate_paths[path]
        }
    )

    def _external_map(snapshot):
        return {
            artifact["name"]: canonical_json_bytes(artifact)
            for artifact in snapshot["external_artifacts"]
        }

    prior_externals = _external_map(prior)
    candidate_externals = _external_map(candidate)
    external_artifacts = sorted(
        set(prior_externals) ^ set(candidate_externals)
        | {
            name
            for name in set(prior_externals) & set(candidate_externals)
            if prior_externals[name] != candidate_externals[name]
        }
    )
    return {
        "repository_paths": repository_paths,
        "external_artifacts": external_artifacts,
    }


def evaluate_version_tripwire(prior, candidate):
    """Return the violation list; empty means the change is lawful.

    ``prior`` is the immutable anchor's identity snapshot; ``candidate``
    is the working tree's. Rejects, mechanically:
    - a guarded repository path changing without a version change;
    - an external implementation digest changing without a version change;
    - the manifest builder or digest algorithm changing without a version
      change (both are guarded repository paths, so they classify above —
      and an algorithm swap that survives regeneration still moves those
      blobs relative to the anchor);
    - regeneration of manifest/registry under unchanged versions after any
      such change (regeneration cannot move this anchor);
    - a candidate identity whose recorded digest does not recompute from
      its own members under the current algorithm.
    """
    violations = []
    recomputed = runtime_core_digest(
        candidate["entries"], candidate["external_artifacts"]
    )
    if recomputed != candidate["runtime_core_digest"]:
        violations.append(
            "candidate identity does not recompute from its own members "
            "(digest-algorithm or manifest regeneration mismatch)"
        )
    versions_changed = (
        prior["guardian_set_version"] != candidate["guardian_set_version"]
        or prior["contracts_version"] != candidate["contracts_version"]
    )
    changes = classify_identity_changes(prior, candidate)
    digest_moved = (
        prior["runtime_core_digest"] != candidate["runtime_core_digest"]
    )
    if not versions_changed:
        for path in changes["repository_paths"]:
            violations.append(
                "guarded path changed without the responsible version "
                "change: %s" % path
            )
        for name in changes["external_artifacts"]:
            violations.append(
                "external implementation digest changed without the "
                "responsible version change: %s" % name
            )
        if digest_moved and not (
            changes["repository_paths"] or changes["external_artifacts"]
        ):
            violations.append(
                "runtime core digest changed without the responsible "
                "version change"
            )
    return violations


def parse_governed_version(version):
    """Parse ``name@N`` strictly; return (name, N) or raise.

    Consolidated B1: versions are PARSED and compared numerically, so
    monotonic advancement is enforced mechanically rather than by string
    inequality.
    """
    if not isinstance(version, str):
        raise TripwireViolation("governed version must be a string")
    match = _VERSION_PATTERN.match(version)
    if not match:
        raise TripwireViolation(
            "governed version %r is not name@N with N >= 1" % version
        )
    return match.group(1), int(match.group(2))


def verify_monotonic_versions(anchors, candidate_contracts_version,
                              candidate_guardian_version):
    """Reject version regression and reuse along the chain and into the
    candidate.

    Rules, per governed version family (contracts and guardian):
    - the lineage name never changes within the chain;
    - numbers are non-decreasing along the chain (no regression);
    - a number that has been advanced past is never reused;
    - EVERY adjacent anchor pair strictly advances at least one governed
      version (B1 second round: an anchor exists precisely to record an
      identity-changing, version-bumped act, and the appending command
      refuses a no-op — so two adjacent anchors under identical versions
      are always a hand-forged same-version identity change, which the
      reviewers proved could previously verify);
    - the candidate's number is >= the latest anchored number.
    """
    for index in range(1, len(anchors)):
        contracts_gain = (
            parse_governed_version(anchors[index]["contracts_version"])[1]
            - parse_governed_version(anchors[index - 1]["contracts_version"])[1]
        )
        guardian_gain = (
            parse_governed_version(anchors[index]["guardian_set_version"])[1]
            - parse_governed_version(
                anchors[index - 1]["guardian_set_version"]
            )[1]
        )
        if contracts_gain <= 0 and guardian_gain <= 0:
            raise TripwireViolation(
                "adjacent anchors %d and %d do not strictly advance any "
                "governed version: a same-version appended anchor is a "
                "forged identity change" % (index - 1, index)
            )

    def walk(field, candidate_version):
        previous = None
        for index, anchor in enumerate(anchors):
            name, number = parse_governed_version(anchor[field])
            if previous is not None:
                previous_name, previous_number = previous
                if name != previous_name:
                    raise TripwireViolation(
                        "%s lineage changed mid-chain at entry %d"
                        % (field, index)
                    )
                if number < previous_number:
                    raise TripwireViolation(
                        "%s regressed at entry %d: %d after %d"
                        % (field, index, number, previous_number)
                    )
            previous = (name, number)
        if previous is not None:
            candidate_name, candidate_number = parse_governed_version(
                candidate_version
            )
            latest_name, latest_number = previous
            if candidate_name != latest_name:
                raise TripwireViolation(
                    "candidate %s lineage %r does not extend the anchored "
                    "lineage %r" % (field, candidate_name, latest_name)
                )
            if candidate_number < latest_number:
                raise TripwireViolation(
                    "candidate %s regressed below the anchored version: "
                    "%d < %d" % (field, candidate_number, latest_number)
                )

    walk("contracts_version", candidate_contracts_version)
    walk("guardian_set_version", candidate_guardian_version)
    return True


def trust_root_prefix_digest(anchors_prefix):
    """The domain-framed digest the trust root pins over the prefix."""
    return hashlib.sha256(
        TRUST_ROOT_DOMAIN + canonical_json_bytes(anchors_prefix)
    ).hexdigest()


def verify_anchor_trust_root(document, trust_root, committed_blob=None):
    """Bind the local chain to the external manager-review trust root.

    ``committed_blob``, when available, is the anchors file's exact bytes
    as committed at the manager-named SHA (read from git history by the
    caller); it proves the pin itself matches the preserved record.
    """
    if trust_root.get("schema") != TRUST_ROOT_SCHEMA:
        raise TripwireViolation("unknown anchor trust-root schema")
    # B1 second round: the record file must carry the reviewed values
    # verbatim — a rewritten local record that blesses a different chain
    # differs from this embedded copy and is rejected here, before any
    # of its own (attacker-chosen) fields are trusted.
    for field, expected in REVIEWED_TRUST_ROOT.items():
        if trust_root.get(field) != expected:
            raise TripwireViolation(
                "trust record field %r does not match the reviewed value: "
                "the record was rewritten" % field
            )
    count = trust_root.get("trusted_anchor_count")
    if not isinstance(count, int) or count < 1:
        raise TripwireViolation("trust root anchor count is malformed")
    anchors = document.get("anchors", [])
    if len(anchors) < count:
        raise TripwireViolation(
            "anchor chain is shorter than the trusted prefix: the chain "
            "has been truncated, deleted, or rebootstrapped"
        )
    prefix = anchors[:count]
    if trust_root_prefix_digest(prefix) != trust_root.get(
        "trusted_prefix_sha256"
    ):
        raise TripwireViolation(
            "anchor prefix does not match the external trust root: a "
            "replacement chain cannot impersonate the reviewed lineage"
        )
    if prefix[-1].get("chain") != trust_root.get("trusted_latest_chain"):
        raise TripwireViolation(
            "trusted latest chain value does not match the prefix"
        )
    if committed_blob is not None:
        if hashlib.sha256(committed_blob).hexdigest() != trust_root.get(
            "trusted_blob_sha256"
        ):
            raise TripwireViolation(
                "the trust root's pinned blob hash does not match the "
                "anchors file committed at the manager-reviewed SHA"
            )
        # The committed prefix and the pinned prefix must be the same
        # record, not merely both internally consistent.
        import json as _json
        committed_anchors = _json.loads(committed_blob).get("anchors", [])
        if committed_anchors[:count] != prefix:
            raise TripwireViolation(
                "current anchor prefix diverges from the committed record "
                "at the manager-reviewed SHA"
            )
    verify_anchor_chain(document)
    return True


def _chain_digest(previous_chain, anchor_without_chain):
    digest = hashlib.sha256()
    digest.update(ANCHOR_DOMAIN)
    if previous_chain is not None:
        digest.update(previous_chain.encode("ascii"))
    digest.update(canonical_json_bytes(anchor_without_chain))
    return digest.hexdigest()


def verify_anchor_chain(document):
    """Recompute the tamper-evidence chain over every anchor entry."""
    if document.get("schema") != ANCHOR_SCHEMA:
        raise TripwireViolation("unknown anchor schema")
    previous_chain = None
    for index, anchor in enumerate(document.get("anchors", [])):
        without_chain = {
            key: value for key, value in anchor.items() if key != "chain"
        }
        expected = _chain_digest(previous_chain, without_chain)
        if anchor.get("chain") != expected:
            raise TripwireViolation(
                "anchor chain broken at entry %d" % index
            )
        previous_chain = anchor["chain"]
    return True


def append_anchor(document, snapshot, anchored_at, anchored_by):
    """Append one anchor entry, enforcing append-only version discipline.

    Refuses when the guarded identity has drifted while both versions are
    unchanged — anchoring is never a way around the tripwire, only the
    record of a lawful, version-bumped change (or the very first
    baseline).
    """
    verify_anchor_chain(document)
    anchors = document.setdefault("anchors", [])
    if anchors:
        top = anchors[-1]
        same_versions = (
            top["guardian_set_version"] == snapshot["guardian_set_version"]
            and top["contracts_version"] == snapshot["contracts_version"]
        )
        if same_versions:
            if top["runtime_core_digest"] == snapshot["runtime_core_digest"]:
                return False  # already anchored; nothing to record
            raise TripwireViolation(
                "guarded identity changed under unchanged versions; bump "
                "the responsible contracts_version or guardian_set_version "
                "before anchoring"
            )
        # Consolidated B1: an appended anchor may only ADVANCE governed
        # versions — parsing them numerically rejects both regression and
        # reuse of an already-superseded version.
        verify_monotonic_versions(
            anchors + [
                {
                    "contracts_version": snapshot["contracts_version"],
                    "guardian_set_version": snapshot["guardian_set_version"],
                }
            ],
            snapshot["contracts_version"],
            snapshot["guardian_set_version"],
        )
        top_contracts = parse_governed_version(top["contracts_version"])[1]
        top_guardian = parse_governed_version(top["guardian_set_version"])[1]
        new_contracts = parse_governed_version(
            snapshot["contracts_version"]
        )[1]
        new_guardian = parse_governed_version(
            snapshot["guardian_set_version"]
        )[1]
        if new_contracts <= top_contracts and new_guardian <= top_guardian:
            raise TripwireViolation(
                "a version change must strictly advance at least one "
                "governed version"
            )
    entry = dict(snapshot)
    entry["anchored_at"] = anchored_at
    entry["anchored_by"] = anchored_by
    entry["chain"] = _chain_digest(
        anchors[-1]["chain"] if anchors else None, entry,
    )
    anchors.append(entry)
    return True

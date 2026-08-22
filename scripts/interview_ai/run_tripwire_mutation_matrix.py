"""Execute the B1/B2 tripwire mutation matrix in disposable scratch trees.

Each case copies the guarded universe into a scratch directory, applies
one mutation, then runs the REAL production flow — regenerate everything
with ``build_release_identity.py`` (the reviewers' defeat step) and then
``--verify`` (which evaluates the version tripwire against the immutable
anchor). Expected outcomes:

  fail          verification must fail (tripwire or fail-closed builder);
  pass          verification must pass (version-bumped change, unrelated
                edits, anchor-regeneration control);
  anchor_refuse the deliberate re-anchoring command must refuse.

The report is content-free JSON: per case, the mutation label, the exact
commands, their exit codes, the decisive output lines, and whether the
outcome matched. Nothing here touches the repository itself.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

COPY_TREES = (
    "services/interview_ai",
    "prompts/interview",
    "tests/interview_ai/fixtures/parity",
    "docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001",
)
COPY_FILES = (
    "services/__init__.py",
    "services/database_service.py",
    "db.py",
    "requirements.txt",
    "app.py",
    # Consolidated B2: the guarded application closure files.
    "identity.py",
    "owner_authorization.py",
    "static/data/resume_data.json",
    "templates/error.html",
    # B1 second round: the manager trust record (external to the writer's
    # surfaces and to the guarded identity).
    "docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/ANCHOR_TRUST_ROOT.json",
    "scripts/interview_ai/build_release_identity.py",
    "scripts/interview_ai/build_runtime_lock.py",
    "scripts/interview_ai/verify_staged_runtime.py",
)


def _tripwire():
    """The real tripwire module, for constructing chain-forgery attacks."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from services.interview_ai import tripwire
    return tripwire


def _scratch_snapshot(scratch):
    """The scratch tree's current identity snapshot, via ITS builder."""
    completed = subprocess.run(
        [sys.executable, "-c",
         "import json, sys; sys.path.insert(0, '.');"
         "import importlib.util;"
         "spec = importlib.util.spec_from_file_location("
         "'brl', 'scripts/interview_ai/build_release_identity.py');"
         "brl = importlib.util.module_from_spec(spec);"
         "spec.loader.exec_module(brl);"
         "print(json.dumps(brl._current_snapshot()))"],
        capture_output=True, text=True, cwd=str(scratch),
    )
    if completed.returncode != 0:
        raise SystemExit(
            "scratch snapshot failed: %s" % completed.stderr[-400:]
        )
    return json.loads(completed.stdout)


def _forge_fresh_chain(scratch):
    """The replacement-chain attack: a brand-new, internally consistent,
    correctly hash-chained single-anchor document over the scratch
    tree's CURRENT identity. The per-chain checks all pass; only the
    external trust root can reject it."""
    tripwire = _tripwire()
    document = {"schema": tripwire.ANCHOR_SCHEMA, "anchors": []}
    tripwire.append_anchor(
        document, _scratch_snapshot(scratch), "2026-08-21",
        "forged replacement chain (matrix attack)",
    )
    anchors_path = (
        scratch / "prompts" / "interview" / "contracts"
        / "version-anchors.json"
    )
    anchors_path.write_text(
        json.dumps(document, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _truncate_chain(scratch, keep):
    """Trailing truncation keeps the hash chain internally valid."""
    anchors_path = (
        scratch / "prompts" / "interview" / "contracts"
        / "version-anchors.json"
    )
    document = json.loads(anchors_path.read_text(encoding="utf-8"))
    document["anchors"] = document["anchors"][:keep]
    anchors_path.write_text(
        json.dumps(document, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _repoint_root_and_append_same_version(scratch):
    """The reviewers' second-round bypass, executed: a writer forges a
    trust record blessing the CURRENT chain wholesale (posing as a fresh
    manager review at a writer-created SHA), then hand-appends a
    correctly chained anchor recording a changed identity under
    UNCHANGED governed versions."""
    tripwire = _tripwire()
    import hashlib
    anchors_path = (
        scratch / "prompts" / "interview" / "contracts"
        / "version-anchors.json"
    )
    document = json.loads(anchors_path.read_text(encoding="utf-8"))
    root_path = (
        scratch / "docs" / "initiatives"
        / "PS-INTERVIEW-AI-ARCHITECTURE-001" / "ANCHOR_TRUST_ROOT.json"
    )
    forged_root = {
        "custody": "forged",
        "manager_review": "writer-created intermediate commit posing as a review",
        "manager_review_sha": "deadbeef" * 5,
        "schema": "interview-anchor-trust-root@1",
        "trusted_anchor_count": len(document["anchors"]),
        "trusted_blob_sha256": hashlib.sha256(
            anchors_path.read_bytes()
        ).hexdigest(),
        "trusted_latest_chain": document["anchors"][-1]["chain"],
        "trusted_prefix_sha256": tripwire.trust_root_prefix_digest(
            document["anchors"]
        ),
    }
    root_path.write_text(
        json.dumps(forged_root, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    # Hand-append the same-version changed identity (valid chain digest,
    # bypassing append_anchor's own refusal).
    entry = _scratch_snapshot(scratch)
    entry["anchored_at"] = "2026-08-21"
    entry["anchored_by"] = "same-version forged append (matrix attack)"
    entry["chain"] = tripwire._chain_digest(
        document["anchors"][-1]["chain"], entry,
    )
    document["anchors"].append(entry)
    anchors_path.write_text(
        json.dumps(document, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _append_regressed_anchor(scratch):
    """A correctly chained anchor whose contracts version moves BACKWARD."""
    tripwire = _tripwire()
    anchors_path = (
        scratch / "prompts" / "interview" / "contracts"
        / "version-anchors.json"
    )
    document = json.loads(anchors_path.read_text(encoding="utf-8"))
    entry = dict(document["anchors"][-1])
    entry.pop("chain")
    entry["contracts_version"] = "interview-contracts@4"
    entry["anchored_by"] = "regressed anchor (matrix attack)"
    entry["chain"] = tripwire._chain_digest(
        document["anchors"][-1]["chain"], entry,
    )
    document["anchors"].append(entry)
    anchors_path.write_text(
        json.dumps(document, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def make_scratch(base):
    scratch = Path(tempfile.mkdtemp(prefix="tripwire-", dir=base))
    for tree in COPY_TREES:
        shutil.copytree(ROOT / tree, scratch / tree)
    for file in COPY_FILES:
        target = scratch / file
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / file, target)
    return scratch


def edit(scratch, relative, old, new, count=1):
    path = scratch / relative
    text = path.read_text(encoding="utf-8")
    occurrences = text.count(old)
    if occurrences < count:
        raise SystemExit(
            "mutation anchor missing in %s (%r)" % (relative, old[:60])
        )
    text = text.replace(old, new, count)
    path.write_text(text, encoding="utf-8", newline="")


def append(scratch, relative, suffix):
    path = scratch / relative
    path.write_bytes(path.read_bytes() + suffix.encode("utf-8"))


def run(scratch, *arguments):
    completed = subprocess.run(
        [sys.executable,
         str(scratch / "scripts" / "interview_ai"
             / "build_release_identity.py")] + list(arguments),
        capture_output=True, text=True, cwd=str(scratch),
    )
    output = (completed.stdout + completed.stderr).strip().splitlines()
    return completed.returncode, output[-3:]


def build_then_verify(scratch):
    build_rc, build_tail = run(scratch)
    verify_rc, verify_tail = run(scratch, "--verify")
    return {
        "build_rc": build_rc,
        "build_tail": build_tail,
        "verify_rc": verify_rc,
        "verify_tail": verify_tail,
    }


CASES = [
    # -- B1 required proof matrix ------------------------------------
    ("b1_1_unchanged_identity_and_versions", "pass",
     "no mutation (control)", lambda s: None),
    ("b1_2_validator_guardian_change", "fail",
     "append a byte to services/interview_ai/validation.py",
     lambda s: append(s, "services/interview_ai/validation.py",
                      "\n# drifted guardian behaviour\n")),
    # The contracts JSON files are builder-derived: a scratch edit that is
    # followed by regeneration is simply overwritten from the guarded
    # builder constants (their true source, itself guarded — see b1_3d).
    # The honest attack on the committed file is tampering WITHOUT
    # regeneration, which direct verification must catch:
    ("b1_3a_contracts_file_tamper_no_rebuild", "fail_verify_only",
     "mutate prompts/interview/contracts/dimension-registry-1.json and run "
     "verification without rebuilding",
     lambda s: edit(s, "prompts/interview/contracts/dimension-registry-1.json",
                    "interview-dimension-registry@1",
                    "interview-dimension-registry@1-drift")),
    ("b1_3b_contracts_module_change", "fail",
     "append a byte to services/interview_ai/contracts.py",
     lambda s: append(s, "services/interview_ai/contracts.py",
                      "\n# drifted contracts\n")),
    ("b1_3c_provider_adapter_change", "fail",
     "append a byte to services/interview_ai/jobs.py",
     lambda s: append(s, "services/interview_ai/jobs.py",
                      "\n# drifted adapter\n")),
    ("b1_3d_manifest_builder_change", "fail",
     "append a byte to scripts/interview_ai/build_release_identity.py",
     lambda s: append(s, "scripts/interview_ai/build_release_identity.py",
                      "\n# drifted builder\n")),
    ("b1_4_external_artifact_change", "fail",
     "alter the recorded anthropic wheel sha256 in the external runtime "
     "manifest",
     lambda s: edit(s, "prompts/interview/contracts/external-runtime-1.json",
                    "bcc6268612c716dbb77133dd60fc41d26016d1b81dee9a52",
                    "0000000012c716dbb77133dd60fc41d26016d1b81dee9a52")),
    # B3 proof case 11: the lock, manifest, and verifier are inside the
    # guarded closure - editing any of them without the responsible
    # version transition triggers B1.
    ("b3_11a_lock_edit_trips_b1", "fail",
     "append a byte to interview-runtime-lock.txt",
     lambda s: append(s, "prompts/interview/control/interview-runtime-lock.txt",
                      "# drifted lock\n")),
    ("b3_11b_verifier_edit_trips_b1", "fail",
     "append a byte to services/interview_ai/runtime_lock.py",
     lambda s: append(s, "services/interview_ai/runtime_lock.py",
                      "\n# drifted verifier\n")),
    ("b3_11c_vendor_args_edit_trips_b1", "fail",
     "append a byte to interview-runtime-vendor-args.txt",
     lambda s: append(s, "prompts/interview/control/interview-runtime-vendor-args.txt",
                      "--drifted\n")),
    ("b1_5_version_bumped_change_passes", "pass",
     "validator drift + contracts_version bump + deliberate re-anchor",
     lambda s: (
         append(s, "services/interview_ai/validation.py",
                "\n# lawful, version-bumped change\n"),
         edit(s, "services/interview_ai/constants.py",
              'CONTRACTS_VERSION = "interview-contracts@7"',
              'CONTRACTS_VERSION = "interview-contracts@8"'),
     )),
    ("b1_6a_unrelated_app_edit_outside_fragments", "pass",
     "append a comment to app.py outside every guarded fragment",
     lambda s: append(s, "app.py",
                      "\n# unrelated PeerSlate change outside Interview\n")),
    ("b1_6b_unrelated_documentation_edit", "pass",
     "add an unrelated documentation file",
     lambda s: (s / "docs" / "UNRELATED_NOTE.md").write_text(
         "unrelated documentation change\n", encoding="utf-8")),
    ("b1_7_regenerate_everything_defeat", "fail",
     "edit telemetry.py, then regenerate every derived manifest, digest, "
     "and release record with the real builder, versions unchanged "
     "(the reviewers' defeat sequence)",
     lambda s: append(s, "services/interview_ai/telemetry.py",
                      "\n# silent behaviour drift\n")),
    # -- B1 external-trust-root attacks (consolidated review) ---------
    ("b1_8_replacement_chain", "fail",
     "replace version-anchors.json with a fresh, internally consistent, "
     "correctly hash-chained single-anchor document over the current "
     "identity (every per-chain check passes; only the external trust "
     "root can reject it)",
     _forge_fresh_chain),
    ("b1_9_prefix_truncation", "fail",
     "truncate the chain to its first three anchors (trailing truncation "
     "keeps the hash chain valid; the trusted prefix count rejects it)",
     lambda s: _truncate_chain(s, 3)),
    ("b1_10_chain_deletion", "fail",
     "delete version-anchors.json entirely (deletion/rebootstrap)",
     lambda s: (s / "prompts" / "interview" / "contracts"
                / "version-anchors.json").unlink()),
    ("b1_11_trust_root_deletion", "fail",
     "delete the manager trust record (removing the external binding is "
     "itself a verification failure)",
     lambda s: (s / "docs" / "initiatives"
                / "PS-INTERVIEW-AI-ARCHITECTURE-001"
                / "ANCHOR_TRUST_ROOT.json").unlink()),
    ("b1_12_coordinated_rewrite", "fail",
     "the coordinated attack: drift guarded code, regenerate every "
     "derived manifest/digest/record, AND forge a fresh consistent "
     "anchor chain over the drifted identity, versions unchanged",
     lambda s: (
         append(s, "services/interview_ai/validation.py",
                "\n# coordinated silent drift\n"),
         _forge_fresh_chain(s),
     )),
    ("b1_13_version_regression", "fail",
     "regress CONTRACTS_VERSION below the latest anchored version",
     lambda s: edit(s, "services/interview_ai/constants.py",
                    'CONTRACTS_VERSION = "interview-contracts@7"',
                    'CONTRACTS_VERSION = "interview-contracts@4"')),
    ("b1_14_version_reuse", "fail",
     "append a correctly chained anchor that REUSES a superseded "
     "contracts version (monotonic parsing rejects the regression)",
     _append_regressed_anchor),
    ("b1_15_trust_root_tamper", "fail",
     "tamper the pinned prefix digest inside the manager trust record "
     "(the pin is load-bearing, not decorative)",
     lambda s: edit(s,
                    "docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/"
                    "ANCHOR_TRUST_ROOT.json",
                    '"trusted_prefix_sha256": "37f66fc7',
                    '"trusted_prefix_sha256": "00000000')),
    ("b1_16_repointed_root_same_version_append", "fail",
     "the reviewers' second-round bypass: repoint the trust record at a "
     "writer-created intermediate 'review' (pinning the current chain "
     "wholesale), then drift guarded code, regenerate, and hand-append a "
     "correctly chained anchor under the UNCHANGED governed versions — "
     "the adjacency rule (every appended anchor strictly advances a "
     "governed version) must reject it",
     lambda s: (
         append(s, "services/interview_ai/validation.py",
                "\n# same-version silent drift\n"),
         _repoint_root_and_append_same_version(s),
     )),
    # -- anchor mechanism proofs -------------------------------------
    ("anchor_regeneration_cannot_advance_it", "pass",
     "ordinary regeneration; version-anchors.json must be byte-identical",
     lambda s: None),
    ("anchor_refuses_drift_under_same_versions", "anchor_refuse",
     "validator drift, then attempt the deliberate re-anchor command",
     lambda s: append(s, "services/interview_ai/validation.py",
                      "\n# drift before unlawful re-anchor\n")),
    # -- B2 required mutation proof ----------------------------------
    ("b2_serializer_salt", "fail",
     "change the signing salt inside the guarded fragment",
     lambda s: edit(s, "app.py",
                    "salt='peerslate-interview-model-answer-v1'",
                    "salt='peerslate-interview-model-answer-v2'")),
    ("b2_rate_limit_review", "fail",
     "change the review route rate limit",
     lambda s: edit(s, "app.py",
                    "@limiter.limit('6 per minute')\ndef interview_review",
                    "@limiter.limit('9 per minute')\ndef interview_review")),
    ("b2_rate_limit_improve", "fail",
     "change the improve route rate limit",
     lambda s: edit(s, "app.py",
                    "@limiter.limit('6 per minute')\ndef interview_improve",
                    "@limiter.limit('9 per minute')\ndef interview_improve")),
    ("b2_rate_limit_nudge", "fail",
     "change the nudge route rate limit",
     lambda s: edit(s, "app.py",
                    "@limiter.limit('8 per minute')",
                    "@limiter.limit('9 per minute')")),
    ("b2_rate_limit_model_answer", "fail",
     "change the model-answer route rate limit",
     lambda s: edit(s, "app.py",
                    "@limiter.limit('6 per minute')\ndef interview_model_answer",
                    "@limiter.limit('9 per minute')\ndef interview_model_answer")),
    ("b2_refusal_copy", "fail",
     "change one refusal copy string inside the boundary",
     lambda s: edit(s, "app.py",
                    "'Send interview requests as JSON.'",
                    "'Send interview requests as JSON!'")),
    ("b2_provider_client_fragment", "fail",
     "change bytes inside the provider-client fragment",
     lambda s: edit(s, "app.py",
                    "client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)",
                    "client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)"
                    "  # option drift")),
    ("b2_provider_client_option", "fail",
     "alter the provider client construction itself (pinned executed "
     "symbol -> the builder refuses the stale fragment outright)",
     lambda s: edit(s, "app.py",
                    "client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)",
                    "client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, max_retries=0)")),
    ("b2_default_public_profile_slug", "fail",
     "change the default public profile slug (pinned executed symbol -> "
     "builder refusal)",
     lambda s: edit(s, "app.py",
                    "default_public_profile_slug='petec'",
                    "default_public_profile_slug='member'")),
    ("b2_jobdeps_callback_binding", "fail",
     "rebind a JobDeps callback",
     lambda s: edit(s, "app.py",
                    "resolve_public_context=_interview_page_context,",
                    "resolve_public_context=_interview_identity_evidence_context,")),
    ("b2_response_serialization", "fail",
     "change the response serialization inside the boundary",
     lambda s: edit(s, "app.py",
                    "    payload, status = interview_ai.jobs.run_review(",
                    "    payload, status = interview_ai.jobs.run_review(  # drift")),
    # -- B2 follow-up: the retired legacy coach contract ---------------
    ("b2_retired_coach_rate", "fail",
     "change the retired coach endpoint's rate limit",
     lambda s: edit(s, "app.py",
                    "@limiter.limit('10 per minute')\ndef interview_coach",
                    "@limiter.limit('60 per minute')\ndef interview_coach")),
    ("b2_retired_coach_body", "fail",
     "change the retired coach endpoint's refusal body",
     lambda s: edit(s, "app.py",
                    "This legacy coach endpoint has retired.",
                    "This legacy coach endpoint is back.")),
    ("b2_retired_coach_status", "fail",
     "resurrect the retired coach endpoint (410 -> 200; the pinned "
     "executed symbol makes the builder refuse the stale fragment)",
     lambda s: edit(s, "app.py",
                    "    }), 410\n# <<< END-INTERVIEW-GUARDED-FRAGMENT: "
                    "interview_retired_coach_contract",
                    "    }), 200\n# <<< END-INTERVIEW-GUARDED-FRAGMENT: "
                    "interview_retired_coach_contract")),
]


def main():
    report = {"cases": [], "result": "pass"}
    with tempfile.TemporaryDirectory() as base:
        for name, expected, description, mutate in CASES:
            scratch = make_scratch(base)
            mutate(scratch)
            record = {"case": name, "expected": expected,
                      "mutation": description}
            if expected == "fail_verify_only":
                verify_rc, verify_tail = run(scratch, "--verify")
                record.update({
                    "verify_rc": verify_rc,
                    "verify_tail": verify_tail,
                })
                record["ok"] = verify_rc != 0
            elif expected == "anchor_refuse":
                build_rc, build_tail = run(scratch)
                anchor_rc, anchor_tail = run(
                    scratch, "--write-anchor",
                    "--anchored-at", "2026-08-21",
                    "--anchored-by", "unlawful re-anchor attempt",
                )
                record.update({
                    "build_rc": build_rc,
                    "anchor_rc": anchor_rc,
                    "anchor_tail": anchor_tail,
                })
                record["ok"] = anchor_rc != 0 and any(
                    "bump the responsible" in line for line in anchor_tail
                )
            else:
                if name == "b1_5_version_bumped_change_passes":
                    build_rc, _ = run(scratch)
                    anchor_rc, anchor_tail = run(
                        scratch, "--write-anchor",
                        "--anchored-at", "2026-08-21",
                        "--anchored-by",
                        "lawful version-bumped change (matrix case b1_5)",
                    )
                    record["anchor_rc"] = anchor_rc
                    record["anchor_tail"] = anchor_tail
                anchors_path = (
                    scratch / "prompts" / "interview" / "contracts"
                    / "version-anchors.json"
                )
                # b1_10 deletes the file outright; "unchanged" then means
                # regeneration did not RECREATE it.
                anchors_before = (
                    anchors_path.read_bytes() if anchors_path.is_file()
                    else None
                )
                record.update(build_then_verify(scratch))
                anchors_after = (
                    anchors_path.read_bytes() if anchors_path.is_file()
                    else None
                )
                record["anchor_file_unchanged_by_regeneration"] = (
                    anchors_before == anchors_after
                )
                if expected == "pass":
                    record["ok"] = (
                        record["verify_rc"] == 0
                        and record["anchor_file_unchanged_by_regeneration"]
                    )
                else:
                    record["ok"] = (
                        record["build_rc"] != 0 or record["verify_rc"] != 0
                    ) and record["anchor_file_unchanged_by_regeneration"]
            if not record["ok"]:
                report["result"] = "FAIL"
            report["cases"].append(record)
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

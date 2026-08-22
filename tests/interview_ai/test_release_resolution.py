"""Fail-closed active-release resolution and the frozen 503 posture."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import app as app_module
from services import database_service as database_service_module
from services import interview_ai
from services.interview_ai import release as release_module

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = json.loads(
    (ROOT / "prompts" / "interview" / "control" / "registry.json").read_text(
        encoding="utf-8"
    )
)
RELEASE_ID = REGISTRY["active_release_set"]["interview_release_set_id"]

REVIEW_PAYLOAD = {
    "question": "Tell me about a project.",
    "answer": "I led one.",
    "profile_slug": "petec",
}


def _scratch_release_root(scratch):
    """A complete copy of everything resolution verifies, for tampering."""
    scratch_root = Path(scratch)
    shutil.copytree(ROOT / "prompts", scratch_root / "prompts")
    shutil.copytree(
        ROOT / "services" / "interview_ai",
        scratch_root / "services" / "interview_ai",
    )
    shutil.copy2(
        ROOT / "services" / "database_service.py",
        scratch_root / "services" / "database_service.py",
    )
    shutil.copy2(ROOT / "db.py", scratch_root / "db.py")
    shutil.copy2(ROOT / "requirements.txt", scratch_root / "requirements.txt")
    # Consolidated B2: the guarded application closure files.
    shutil.copy2(ROOT / "identity.py", scratch_root / "identity.py")
    shutil.copy2(
        ROOT / "owner_authorization.py",
        scratch_root / "owner_authorization.py",
    )
    (scratch_root / "static" / "data").mkdir(parents=True)
    shutil.copy2(
        ROOT / "static" / "data" / "resume_data.json",
        scratch_root / "static" / "data" / "resume_data.json",
    )
    (scratch_root / "templates").mkdir()
    shutil.copy2(
        ROOT / "templates" / "error.html",
        scratch_root / "templates" / "error.html",
    )
    (scratch_root / "scripts" / "interview_ai").mkdir(parents=True)
    for guarded_script in ("build_release_identity.py",
                           "build_runtime_lock.py",
                           "verify_staged_runtime.py"):
        shutil.copy2(
            ROOT / "scripts" / "interview_ai" / guarded_script,
            scratch_root / "scripts" / "interview_ai" / guarded_script,
        )
    shutil.copy2(ROOT / "app.py", scratch_root / "app.py")
    return scratch_root


def _recomputed_record(record, **overrides):
    """Mutate a registry record and recompute its identities so it is
    internally CONSISTENT — every hash checks out — while being
    incompatible with the running system (correction C2's exploit shape).
    """
    from services.interview_ai.identity import (
        candidate_system_digest,
        release_set_id,
    )

    mutated = json.loads(json.dumps(record))
    mutated.update(overrides)
    slots = [
        {
            "specialist": ref["specialist"],
            "bundle_content_sha256": ref["bundle_content_sha256"],
        }
        for ref in mutated["bundle_refs"]
    ]
    mutated["candidate_system_digest"] = candidate_system_digest(
        mutated["runtime_core_digest"],
        slots,
        mutated["guardian_set_version"],
        mutated["contracts_version"],
        mutated["evaluation_set_hash"],
    )
    mutated["interview_release_set_id"] = release_set_id(
        mutated["candidate_system_digest"],
        mutated["accepted_run_digests"],
        mutated["threshold_set_id"],
        mutated["threshold_set_version"],
    )
    return mutated


def _write_adversarial_registry(scratch_root, mutated_record):
    registry_path = (
        scratch_root / "prompts" / "interview" / "control" / "registry.json"
    )
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["active_release_set"] = mutated_record
    registry_path.write_text(
        json.dumps(registry, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return mutated_record["interview_release_set_id"]


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        interview_ai.reset_resolution_cache()
        self.addCleanup(interview_ai.reset_resolution_cache)

    def test_recorded_release_resolves_and_reverifies(self):
        release = interview_ai.resolve_active_release(RELEASE_ID)
        self.assertIsNotNone(release)
        self.assertEqual(release.release_set_id, RELEASE_ID)
        self.assertEqual(
            sorted(release.bundles), sorted(interview_ai.BUNDLE_SLOT_ORDER)
        )

    def test_unset_config_is_unresolved(self):
        self.assertIsNone(interview_ai.resolve_active_release(None))

    def test_non_hex_config_is_unresolved(self):
        self.assertIsNone(interview_ai.resolve_active_release("not-a-hash"))

    def test_unknown_id_is_unresolved(self):
        self.assertIsNone(interview_ai.resolve_active_release("a" * 64))

    def test_tampered_bundle_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            bundle_dir = next(
                (scratch_root / "prompts" / "interview" / "bundles"
                 / "coach").iterdir()
            )
            instruction = bundle_dir / "instruction.md"
            instruction.write_bytes(
                instruction.read_bytes().replace(b"coach", b"c0ach", 1)
            )
            self.assertIsNone(
                release_module._resolve_uncached(RELEASE_ID, scratch_root)
            )

    def test_tampered_guarded_runtime_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            target = scratch_root / "services" / "interview_ai" / "release.py"
            target.write_bytes(target.read_bytes() + b"\n# drifted\n")
            self.assertIsNone(
                release_module._resolve_uncached(RELEASE_ID, scratch_root)
            )


class AdversarialCompatibilityTests(unittest.TestCase):
    """C2: internally consistent but incompatible records must fail closed.

    Every case below recomputes candidate and release identities from its
    mutated fields, so hash recomputation alone would accept it — exactly
    the reviewer's `incompatible-guardian@999` exploit. The control case
    proves the scratch harness resolves the genuine record, so each
    refusal is attributable to the intended incompatibility and nothing
    environmental.
    """

    def setUp(self):
        interview_ai.reset_resolution_cache()
        self.addCleanup(interview_ai.reset_resolution_cache)
        self.record = REGISTRY["active_release_set"]

    def _resolve_mutated(self, **overrides):
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            mutated = _recomputed_record(self.record, **overrides)
            adversarial_id = _write_adversarial_registry(scratch_root, mutated)
            return release_module._resolve_uncached(
                adversarial_id, scratch_root
            )

    def test_control_the_genuine_record_resolves_in_the_scratch_harness(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            release = release_module._resolve_uncached(
                RELEASE_ID, scratch_root
            )
            self.assertIsNotNone(release)

    def test_incompatible_guardian_version_fails_closed(self):
        self.assertIsNone(
            self._resolve_mutated(
                guardian_set_version="incompatible-guardian@999",
            )
        )

    def test_incompatible_contracts_version_fails_closed(self):
        self.assertIsNone(
            self._resolve_mutated(
                contracts_version="interview-contracts@999",
            )
        )

    def test_sentinel_reuse_by_a_non_initial_release_fails_closed(self):
        self.assertIsNone(
            self._resolve_mutated(initial_extraction=False)
        )

    def test_non_initial_release_without_accepted_runs_fails_closed(self):
        self.assertIsNone(
            self._resolve_mutated(
                initial_extraction=False,
                threshold_set_id="wave-one-thresholds",
                threshold_set_version="1",
                accepted_run_digests=[],
            )
        )

    def test_initial_release_with_a_fabricated_run_fails_closed(self):
        self.assertIsNone(
            self._resolve_mutated(accepted_run_digests=["a" * 64])
        )

    def test_swapped_bundle_slot_order_fails_closed(self):
        swapped = json.loads(json.dumps(self.record["bundle_refs"]))
        swapped[0], swapped[1] = swapped[1], swapped[0]
        self.assertIsNone(self._resolve_mutated(bundle_refs=swapped))

    def test_configuration_only_rollback_compatibility_is_enforced(self):
        """D8: a prior entry is selectable only when its runtime core,
        guardian version, and contracts version match the running system —
        which resolution enforces against current constants and recomputed
        bytes, so an incompatible prior entry is unreachable by
        construction. Prove it with a prior entry whose core digest
        differs but whose identities recompute."""
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            prior = _recomputed_record(
                self.record, runtime_core_digest="b" * 64,
            )
            registry_path = (
                scratch_root / "prompts" / "interview" / "control"
                / "registry.json"
            )
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            prior["deactivated_at"] = "2026-08-19"
            registry["prior_release_sets"] = [prior]
            registry_path.write_text(
                json.dumps(registry, indent=1, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.assertIsNone(
                release_module._resolve_uncached(
                    prior["interview_release_set_id"], scratch_root
                )
            )

    def test_b5_deployment_shape_resolves_without_evaluation_files(self):
        """B5: the scratch harness deliberately carries NO tests/** and no
        golden docs — the deployment shape — and the genuine record still
        resolves, because the evaluation identity derives from the
        guarded, deployable manifest rather than the source files."""
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            self.assertFalse((scratch_root / "tests").exists())
            self.assertFalse(
                (scratch_root / "docs" / "initiatives"
                 / "PS-AI-AGENT-QUALITY-ROUND-2-001").exists()
            )
            self.assertIsNotNone(
                release_module._resolve_uncached(RELEASE_ID, scratch_root)
            )

    def test_b5_the_fail_open_defect_is_dead(self):
        """The reviewers' exact defect: evaluation files absent + an
        internally consistent record carrying a WRONG evaluation hash.
        The old resolver trusted the recorded hash and resolved; the
        manifest-derived recomputation must refuse it."""
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            self.assertFalse((scratch_root / "tests").exists())
            mutated = _recomputed_record(
                self.record, evaluation_set_hash="e" * 64,
            )
            adversarial_id = _write_adversarial_registry(scratch_root, mutated)
            self.assertIsNone(
                release_module._resolve_uncached(adversarial_id, scratch_root)
            )

    def test_b5_present_but_tampered_evaluation_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            fixture_relative = Path(
                "tests/interview_ai/fixtures/parity/coach_success_minimal.json"
            )
            target = scratch_root / fixture_relative
            target.parent.mkdir(parents=True)
            content = (ROOT / fixture_relative).read_bytes()
            target.write_bytes(content.replace(b"coach", b"c0ach", 1))
            self.assertIsNone(
                release_module._resolve_uncached(RELEASE_ID, scratch_root)
            )
            # Control: the same file, untampered, resolves.
            target.write_bytes(content)
            self.assertIsNotNone(
                release_module._resolve_uncached(RELEASE_ID, scratch_root)
            )

    def test_b5_missing_evaluation_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            (scratch_root / "prompts" / "interview" / "contracts"
             / "evaluation-set-1.json").unlink()
            self.assertIsNone(
                release_module._resolve_uncached(RELEASE_ID, scratch_root)
            )

    def test_b5_tampered_evaluation_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            manifest_path = (
                scratch_root / "prompts" / "interview" / "contracts"
                / "evaluation-set-1.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"][0]["sha256"] = "f" * 64
            manifest_path.write_text(
                json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.assertIsNone(
                release_module._resolve_uncached(RELEASE_ID, scratch_root)
            )

    def test_tampered_runtime_lock_manifest_fails_closed(self):
        """B3: resolution gates on the runtime lock — a tampered external
        runtime manifest is service_not_configured, never a served
        release."""
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            manifest_path = (
                scratch_root / "prompts" / "interview" / "contracts"
                / "external-runtime-1.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            target = next(record for record in manifest["distributions"]
                          if record["name"] == "anthropic")
            target["version"] = "0.999.0"
            manifest_path.write_text(
                json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.assertIsNone(
                release_module._resolve_uncached(RELEASE_ID, scratch_root)
            )

    def test_adversarial_record_yields_the_frozen_route_refusal(self):
        """Route-level proof: service_not_configured, zero dispatch."""
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            mutated = _recomputed_record(
                self.record,
                guardian_set_version="incompatible-guardian@999",
            )
            adversarial_id = _write_adversarial_registry(scratch_root, mutated)
            previous = app_module.app.config.get(
                interview_ai.ACTIVE_RELEASE_CONFIG_KEY
            )
            limiter_was_enabled = app_module.limiter.enabled
            app_module.limiter.enabled = False
            app_module.app.config[interview_ai.ACTIVE_RELEASE_CONFIG_KEY] = (
                adversarial_id
            )
            interview_ai.reset_resolution_cache()
            appended = []

            def record_append(procedure_name, parameters=None):
                appended.append(dict(parameters))
                return []

            try:
                with patch.object(
                    release_module, "ROOT", scratch_root,
                ), patch.object(
                    app_module.client.messages, "create",
                ) as provider_call, patch.object(
                    database_service_module.database_service,
                    "execute_procedure",
                    new=record_append,
                ):
                    response = app_module.app.test_client().post(
                        "/api/interview/review",
                        json=REVIEW_PAYLOAD,
                        base_url="http://localhost",
                    )
                provider_call.assert_not_called()
                self.assertEqual(response.status_code, 503)
                self.assertEqual(
                    response.get_json(),
                    {"error": interview_ai.SERVICE_NOT_CONFIGURED_COPY},
                )
                self.assertEqual(len(appended), 1)
                self.assertEqual(
                    appended[0]["@FailureReason"], "active_release_unresolved"
                )
            finally:
                app_module.app.config[
                    interview_ai.ACTIVE_RELEASE_CONFIG_KEY
                ] = previous
                app_module.limiter.enabled = limiter_was_enabled
                interview_ai.reset_resolution_cache()


class UnconfiguredRouteTests(unittest.TestCase):
    """The frozen Interview-only 503: zero dispatch, one telemetry row."""

    def setUp(self):
        self.previous = app_module.app.config.get(
            interview_ai.ACTIVE_RELEASE_CONFIG_KEY
        )
        app_module.app.config[interview_ai.ACTIVE_RELEASE_CONFIG_KEY] = None
        interview_ai.reset_resolution_cache()
        self.limiter_was_enabled = app_module.limiter.enabled
        app_module.limiter.enabled = False

    def tearDown(self):
        app_module.app.config[interview_ai.ACTIVE_RELEASE_CONFIG_KEY] = (
            self.previous
        )
        interview_ai.reset_resolution_cache()
        app_module.limiter.enabled = self.limiter_was_enabled

    def _post(self, path, payload, appended):
        def record_append(procedure_name, parameters=None):
            appended.append((procedure_name, dict(parameters)))
            return []

        with patch.object(
            app_module.client.messages, "create"
        ) as provider_call, patch.object(
            database_service_module.database_service,
            "execute_procedure",
            new=record_append,
        ):
            response = app_module.app.test_client().post(
                path, json=payload, base_url="http://localhost"
            )
        provider_call.assert_not_called()
        return response

    def test_review_unconfigured_is_interview_only_503(self):
        appended = []
        response = self._post("/api/interview/review", REVIEW_PAYLOAD, appended)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {"error": interview_ai.SERVICE_NOT_CONFIGURED_COPY},
        )
        self.assertEqual(len(appended), 1)
        _, row = appended[0]
        self.assertEqual(row["@Outcome"], "failed")
        self.assertEqual(row["@FailureState"], "service_not_configured")
        self.assertEqual(row["@FailureReason"], "active_release_unresolved")
        self.assertEqual(row["@Specialist"], "coach")
        self.assertIsNone(row["@BundleLabel"])
        self.assertIsNone(row["@BundleContentSha256"])
        self.assertIsNone(row["@ReleaseSetId"])
        self.assertEqual(row["@ValidationResult"], "not_applicable")

    def test_compare_unconfigured_writes_a_parent_row_with_no_children(self):
        appended = []
        response = self._post(
            "/api/interview/model-answer",
            {"question": "Q?", "mode": "compare", "profile_slug": "petec"},
            appended,
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(appended), 1)
        _, row = appended[0]
        self.assertEqual(row["@EventKind"], "composition_parent")
        self.assertEqual(row["@Composition"], "compare")
        self.assertIsNone(row["@Specialist"])
        self.assertIsNone(row["@ParentAttemptUuid"])

    def test_the_rest_of_peerslate_stays_operational(self):
        response = app_module.app.test_client().get(
            "/", base_url="http://localhost"
        )
        self.assertLess(response.status_code, 500)

    def test_pre_provider_refusals_still_precede_release_resolution(self):
        appended = []
        response = self._post(
            "/api/interview/review",
            {"question": "Q?", "profile_slug": "petec"},
            appended,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(appended, [])


if __name__ == "__main__":
    unittest.main()

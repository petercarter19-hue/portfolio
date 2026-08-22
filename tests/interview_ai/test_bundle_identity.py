"""Bundle and release identity: framing vectors, byte-lock, loader rules."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from services.interview_ai import identity
from services.interview_ai.bundles import (
    BundleError,
    load_bundle,
    parse_instruction_segments,
)

ROOT = Path(__file__).resolve().parents[2]
BUNDLES_ROOT = ROOT / "prompts" / "interview" / "bundles"


class CanonicalJsonTests(unittest.TestCase):
    def test_sorted_compact_utf8(self):
        payload = {"b": 1, "a": ["x", {"d": 2, "c": 3}]}
        self.assertEqual(
            identity.canonical_json_bytes(payload),
            b'{"a":["x",{"c":3,"d":2}],"b":1}',
        )

    def test_floats_are_rejected_not_canonicalized(self):
        with self.assertRaises(ValueError):
            identity.canonical_json_bytes({"a": 1.5})

    def test_non_string_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            identity.canonical_json_bytes({1: "a"})


class BundleHashTests(unittest.TestCase):
    def test_known_answer_framing_vector(self):
        files = {
            "constitution.md": b"",
            "instruction.md": b"I",
            "schema.json": b"{}",
            "provider.json": b"{}",
        }
        expected = hashlib.sha256()
        expected.update(b"peerslate.interview.bundle.v1\x00")
        for name in ("constitution.md", "instruction.md", "schema.json",
                     "provider.json"):
            name_bytes = name.encode()
            expected.update(len(name_bytes).to_bytes(8, "big") + name_bytes)
            expected.update(
                len(files[name]).to_bytes(8, "big") + files[name]
            )
        self.assertEqual(
            identity.bundle_content_sha256(files), expected.hexdigest()
        )

    def test_missing_identity_file_is_rejected(self):
        with self.assertRaises(ValueError):
            identity.bundle_content_sha256({"instruction.md": b"x"})

    def test_content_moves_between_files_change_the_hash(self):
        base = {
            "constitution.md": b"", "instruction.md": b"AB",
            "schema.json": b"", "provider.json": b"",
        }
        moved = {
            "constitution.md": b"", "instruction.md": b"A",
            "schema.json": b"B", "provider.json": b"",
        }
        self.assertNotEqual(
            identity.bundle_content_sha256(base),
            identity.bundle_content_sha256(moved),
        )


class InstructionSegmentTests(unittest.TestCase):
    def test_exact_bytes_no_normalization(self):
        raw = (
            b"<<<SEGMENT system_template>>>\nLine one\r\nno trailing newline"
            b"\n<<<END system_template>>>\n"
        )
        segments = parse_instruction_segments(raw)
        self.assertEqual(
            segments, {"system_template": "Line one\r\nno trailing newline"}
        )

    def test_unterminated_segment_is_rejected(self):
        with self.assertRaises(BundleError):
            parse_instruction_segments(b"<<<SEGMENT system_template>>>\nX")


class CatalogByteLockTests(unittest.TestCase):
    def test_committed_catalog_and_registry_recompute_exactly(self):
        """The CI byte-lock: regenerate everything and demand zero drift."""
        completed = subprocess.run(
            [sys.executable,
             str(ROOT / "scripts" / "interview_ai"
                 / "build_release_identity.py"),
             "--verify"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(
            completed.returncode, 0,
            "release identity drifted:\n%s%s"
            % (completed.stdout, completed.stderr),
        )

    def test_every_committed_bundle_loads_and_verifies(self):
        loaded = 0
        for specialist_dir in sorted(BUNDLES_ROOT.iterdir()):
            for bundle_dir in sorted(specialist_dir.iterdir()):
                bundle = load_bundle(
                    bundle_dir, expected_specialist=specialist_dir.name
                )
                self.assertEqual(bundle.semver, "1.0.0")
                self.assertEqual(bundle.model, "claude-haiku-4-5-20251001")
                loaded += 1
        self.assertEqual(loaded, 5)

    def test_tampered_bundle_byte_fails_verification(self):
        with tempfile.TemporaryDirectory() as scratch:
            source = next((BUNDLES_ROOT / "coach").iterdir())
            target = Path(scratch) / source.name
            shutil.copytree(source, target)
            instruction = target / "instruction.md"
            instruction.write_bytes(
                instruction.read_bytes().replace(b"coach", b"C0ach", 1)
            )
            with self.assertRaises(BundleError):
                load_bundle(target, expected_specialist="coach")

    def test_registry_identities_recompute_from_parts(self):
        registry = json.loads(
            (ROOT / "prompts" / "interview" / "control" / "registry.json")
            .read_text(encoding="utf-8")
        )
        record = registry["active_release_set"]
        recomputed = identity.release_set_id(
            record["candidate_system_digest"],
            record["accepted_run_digests"],
            record["threshold_set_id"],
            record["threshold_set_version"],
        )
        self.assertEqual(recomputed, record["interview_release_set_id"])
        self.assertEqual(record["accepted_run_digests"], [])
        self.assertIs(record["initial_extraction"], True)
        self.assertIsNone(record["activated_at"])
        self.assertEqual(record["threshold_set_id"],
                         "initial-extraction-parity")
        self.assertEqual(record["threshold_set_version"], "1")


if __name__ == "__main__":
    unittest.main()

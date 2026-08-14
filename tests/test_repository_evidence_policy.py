import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_repository_evidence_policy.py"
SPEC = importlib.util.spec_from_file_location("evidence_policy", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RepositoryEvidencePolicyTests(unittest.TestCase):
    def test_large_exact_duplicates_are_reviewed(self):
        self.assertEqual(MODULE.validate_policy(), [])

    def test_allowlist_has_only_complete_existing_groups(self):
        allowlist = MODULE.load_allowlist()
        actual = MODULE.collect_large_duplicate_groups(
            allowlist["threshold_bytes"]
        )
        self.assertEqual(set(actual), {entry["sha256"] for entry in allowlist["entries"]})


if __name__ == "__main__":
    unittest.main()

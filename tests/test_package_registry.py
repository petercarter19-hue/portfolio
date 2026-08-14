import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageRegistryTests(unittest.TestCase):
    def test_registry_accounts_for_every_initiative_once(self):
        registry = json.loads(
            (ROOT / "docs" / "governance" / "PACKAGE_REGISTRY.json").read_text(
                encoding="utf-8"
            )
        )
        categories = registry["categories"]
        expected_categories = {
            "current_protect",
            "future_finish",
            "reconcile",
            "historical_evidence",
            "retire_supersede",
        }
        self.assertEqual(set(categories), expected_categories)

        assigned = [package for values in categories.values() for package in values]
        self.assertEqual(len(assigned), len(set(assigned)))

        actual = sorted(
            path.name
            for path in (ROOT / "docs" / "initiatives").iterdir()
            if path.is_dir()
        )
        self.assertEqual(sorted(assigned), actual)
        self.assertEqual(registry["counts"]["total"], len(actual))
        for category, values in categories.items():
            self.assertEqual(registry["counts"][category], len(values))

    def test_registry_does_not_claim_lifecycle_authority(self):
        registry = json.loads(
            (ROOT / "docs" / "governance" / "PACKAGE_REGISTRY.json").read_text(
                encoding="utf-8"
            )
        )
        note = registry["authority_note"]
        self.assertIn("CURRENT_LANES.json", note)
        self.assertIn("CURRENT_BASELINE.yaml", note)


if __name__ == "__main__":
    unittest.main()

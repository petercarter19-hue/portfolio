import json
import unittest
from pathlib import Path

from scripts.delivery_preflight import evaluate_policy, load_ledger


ROOT = Path(__file__).resolve().parents[1]


def facts(**overrides):
    value = {
        "branch": "work/2026-08-04-delivery-reset-001",
        "ahead": 0,
        "behind": 0,
        "tracked_changes": 0,
        "untracked_changes": 0,
        "origin_is_azure": True,
    }
    value.update(overrides)
    return value


class DeliveryPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "docs" / "governance" / "CURRENT_LANES.json"
        cls.ledger = load_ledger(cls.path)

    def test_lane_ledger_is_valid_and_reset_is_single_writer(self):
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(1, parsed["schema_version"])
        self.assertEqual(
            "owner_directed_delivery_reset",
            parsed["operating_mode"]["state"],
        )
        self.assertEqual(
            ["PS-DELIVERY-RESET-001"],
            parsed["operating_mode"]["writes_allowed_for"],
        )
        self.assertEqual(
            ["PS-DELIVERY-RESET-001"],
            parsed["operating_mode"]["merge_allowed_for"],
        )
        self.assertEqual(
            ["PS-DELIVERY-RESET-001"],
            parsed["operating_mode"]["cleanup_allowed_for"],
        )
        self.assertEqual([], parsed["operating_mode"]["release_allowed_for"])
        self.assertTrue(parsed["workspace_snapshot"]["cleanup_authorized"])

    def test_reset_lane_write_passes_on_exact_branch(self):
        errors, _ = evaluate_policy(
            self.ledger,
            facts(),
            "PS-DELIVERY-RESET-001",
            "write",
            require_clean=True,
        )
        self.assertEqual([], errors)

    def test_other_lane_write_is_blocked_but_read_is_allowed(self):
        errors, _ = evaluate_policy(
            self.ledger,
            facts(branch="work/other"),
            "PS-OPPORTUNITY-SLATE-001",
            "write",
        )
        self.assertTrue(any("blocked" in error for error in errors))

        read_errors, _ = evaluate_policy(
            self.ledger,
            facts(branch="work/other", behind=40),
            "PS-OPPORTUNITY-SLATE-001",
            "read",
        )
        self.assertTrue(any("behind" in error for error in read_errors))

        current_read_errors, _ = evaluate_policy(
            self.ledger,
            facts(branch="work/other"),
            "PS-OPPORTUNITY-SLATE-001",
            "read",
        )
        self.assertEqual([], current_read_errors)

    def test_release_and_direct_main_writes_are_blocked(self):
        merge_errors, _ = evaluate_policy(
            self.ledger,
            facts(),
            "PS-DELIVERY-RESET-001",
            "merge",
        )
        self.assertEqual([], merge_errors)

        cleanup_errors, _ = evaluate_policy(
            self.ledger,
            facts(),
            "PS-DELIVERY-RESET-001",
            "cleanup",
        )
        self.assertEqual([], cleanup_errors)

        release_errors, _ = evaluate_policy(
            self.ledger,
            facts(),
            "PS-DELIVERY-RESET-001",
            "release",
        )
        self.assertTrue(any("release is blocked" in error for error in release_errors))

        main_errors, _ = evaluate_policy(
            self.ledger,
            facts(branch="main"),
            "PS-DELIVERY-RESET-001",
            "write",
        )
        self.assertTrue(any("directly from main" in error for error in main_errors))

    def test_clean_and_azure_requirements_fail_closed(self):
        dirty_errors, _ = evaluate_policy(
            self.ledger,
            facts(untracked_changes=1),
            "PS-DELIVERY-RESET-001",
            "write",
            require_clean=True,
        )
        self.assertIn("checkout is not clean", dirty_errors)

        remote_errors, _ = evaluate_policy(
            self.ledger,
            facts(origin_is_azure=False),
            "PS-DELIVERY-RESET-001",
            "write",
        )
        self.assertTrue(any("Azure DevOps" in error for error in remote_errors))


if __name__ == "__main__":
    unittest.main()

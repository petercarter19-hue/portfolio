import copy
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
        "changed_paths": [],
        "origin_is_azure": True,
    }
    value.update(overrides)
    return value


class DeliveryPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "docs" / "governance" / "CURRENT_LANES.json"
        cls.ledger = load_ledger(cls.path)

    def test_lane_ledger_is_valid_and_controlled_idle(self):
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(1, parsed["schema_version"])
        self.assertEqual(
            "controlled_idle",
            parsed["operating_mode"]["state"],
        )
        self.assertEqual([], parsed["operating_mode"]["writes_allowed_for"])
        self.assertEqual(
            ["PS-DELIVERY-RESET-001"],
            parsed["operating_mode"]["merge_allowed_for"],
        )
        self.assertEqual(
            ["PS-DELIVERY-RESET-001"],
            parsed["operating_mode"]["cleanup_allowed_for"],
        )
        self.assertEqual([], parsed["operating_mode"]["release_allowed_for"])
        self.assertEqual([], parsed["active_lanes"])
        self.assertTrue(parsed["activation_policy"]["enabled"])
        self.assertTrue(parsed["workspace_snapshot"]["cleanup_authorized"])

    def test_reset_lane_is_merge_and_cleanup_only(self):
        write_errors, _ = evaluate_policy(
            self.ledger,
            facts(),
            "PS-DELIVERY-RESET-001",
            "write",
        )
        self.assertTrue(
            any("write is blocked" in error for error in write_errors)
        )

        merge_errors, _ = evaluate_policy(
            self.ledger,
            facts(),
            "PS-DELIVERY-RESET-001",
            "merge",
            require_clean=True,
        )
        self.assertEqual([], merge_errors)

        cleanup_errors, _ = evaluate_policy(
            self.ledger,
            facts(),
            "PS-DELIVERY-RESET-001",
            "cleanup",
        )
        self.assertEqual([], cleanup_errors)

    def test_controlled_activation_requires_exact_package_and_branch(self):
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        errors, _ = evaluate_policy(
            self.ledger,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
        )
        self.assertEqual([], errors)

        wrong_package, _ = evaluate_policy(
            self.ledger,
            activation_facts,
            "PS-OPPORTUNITY-SLATE-001",
            "activate",
        )
        self.assertTrue(
            any("standing control package" in error for error in wrong_package)
        )

        wrong_branch, _ = evaluate_policy(
            self.ledger,
            facts(branch="work/feature-direct"),
            "PS-DELIVERY-CONTROL-001",
            "activate",
        )
        self.assertTrue(
            any("branch does not match" in error for error in wrong_branch)
        )

        busy = copy.deepcopy(self.ledger)
        busy["active_lanes"] = [
            {"package": "PS-EXISTING-001"},
            {"package": "PS-EXISTING-002"},
        ]
        busy_errors, _ = evaluate_policy(
            busy,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
        )
        self.assertIn(
            "activation refused because the lane limit is full",
            busy_errors,
        )

        product_change, _ = evaluate_policy(
            self.ledger,
            facts(
                branch=(
                    "work/2026-08-05-delivery-activation-opportunity-slate"
                ),
                changed_paths=["app.py"],
            ),
            "PS-DELIVERY-CONTROL-001",
            "activate",
        )
        self.assertTrue(
            any("non-control paths" in error for error in product_change)
        )

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

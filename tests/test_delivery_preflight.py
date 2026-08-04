import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.delivery_preflight import collect_facts, evaluate_policy, load_ledger


ROOT = Path(__file__).resolve().parents[1]


def facts(**overrides):
    value = {
        "branch": "work/2026-08-04-delivery-reset-001",
        "ahead": 0,
        "behind": 0,
        "tracked_changes": 0,
        "untracked_changes": 0,
        "changed_paths": [],
        "origin_main": "b86053df749287d9dc4cdece0dbf4ad9a682283a",
        "origin_is_azure": True,
    }
    value.update(overrides)
    return value


class DeliveryPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "docs" / "governance" / "CURRENT_LANES.json"
        cls.ledger = load_ledger(cls.path)

    def test_lane_ledger_has_a_valid_operating_state(self):
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(1, parsed["schema_version"])
        mode = parsed["operating_mode"]
        active = parsed["active_lanes"]
        closing = parsed["closing_lanes"]
        active_packages = {lane["package"] for lane in active}
        closable_packages = active_packages | {
            lane["package"] for lane in closing
        }
        self.assertIn(mode["state"], {"controlled_idle", "active_delivery"})
        self.assertLessEqual(len(active), 2)
        self.assertEqual(set(mode["writes_allowed_for"]), active_packages)
        self.assertLessEqual(set(mode["merge_allowed_for"]), closable_packages)
        self.assertLessEqual(set(mode["cleanup_allowed_for"]), closable_packages)
        release_packages = set(mode["release_allowed_for"])
        self.assertLessEqual(release_packages, active_packages)
        self.assertLessEqual(len(release_packages), 1)
        if mode["state"] == "controlled_idle":
            self.assertEqual([], active)
            self.assertEqual([], mode["writes_allowed_for"])
            self.assertEqual(set(), release_packages)
        else:
            self.assertTrue(active)
        self.assertTrue(parsed["activation_policy"]["enabled"])
        self.assertTrue(parsed["workspace_snapshot"]["cleanup_authorized"])

    def test_closing_lanes_are_merge_and_cleanup_only(self):
        for lane in self.ledger["closing_lanes"]:
            lane_facts = facts(branch=lane["branch"])
            write_errors, _ = evaluate_policy(
                self.ledger, lane_facts, lane["package"], "write"
            )
            self.assertTrue(
                any("write is blocked" in error for error in write_errors)
            )
            merge_errors, _ = evaluate_policy(
                self.ledger,
                lane_facts,
                lane["package"],
                "merge",
                require_clean=True,
            )
            self.assertEqual([], merge_errors)
            cleanup_errors, _ = evaluate_policy(
                self.ledger, lane_facts, lane["package"], "cleanup"
            )
            self.assertEqual([], cleanup_errors)

    def test_controlled_activation_requires_exact_package_and_branch(self):
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        activation_ledger = copy.deepcopy(self.ledger)
        activation_ledger["operating_mode"]["state"] = "controlled_idle"
        activation_ledger["active_lanes"] = []
        errors, _ = evaluate_policy(
            activation_ledger,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
        )
        self.assertEqual([], errors)

        wrong_package, _ = evaluate_policy(
            activation_ledger,
            activation_facts,
            "PS-OPPORTUNITY-SLATE-001",
            "activate",
        )
        self.assertTrue(
            any("standing control package" in error for error in wrong_package)
        )

        wrong_branch, _ = evaluate_policy(
            activation_ledger,
            facts(branch="work/feature-direct"),
            "PS-DELIVERY-CONTROL-001",
            "activate",
        )
        self.assertTrue(
            any("branch does not match" in error for error in wrong_branch)
        )

        busy = copy.deepcopy(activation_ledger)
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
            activation_ledger,
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

    def test_ordinary_fact_collection_skips_changed_path_inventory(self):
        def fake_git(*args, **_kwargs):
            command = tuple(args)
            outputs = {
                ("status", "--porcelain=v1"): "?? output/",
                ("remote", "get-url", "origin"): (
                    "https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site"
                ),
                ("branch", "--show-current"): "main",
                ("rev-parse", "HEAD"): "abc",
                ("rev-parse", "origin/main"): "abc",
                ("rev-list", "--count", "origin/main..HEAD"): "0",
                ("rev-list", "--count", "HEAD..origin/main"): "0",
            }
            if command not in outputs:
                raise AssertionError(f"unexpected changed-path command: {command}")
            return outputs[command]

        with patch("scripts.delivery_preflight._git", side_effect=fake_git):
            collected = collect_facts()

        self.assertNotIn("changed_paths", collected)
        self.assertEqual(1, collected["untracked_changes"])

    def test_activation_fact_collection_includes_changed_paths(self):
        def fake_git(*args, **_kwargs):
            outputs = {
                ("status", "--porcelain=v1"): " M scripts/delivery_preflight.py",
                ("remote", "get-url", "origin"): (
                    "https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site"
                ),
                ("branch", "--show-current"): (
                    "work/2026-08-04-delivery-activation-preflight-output"
                ),
                ("rev-parse", "HEAD"): "abc",
                ("rev-parse", "origin/main"): "abc",
                ("rev-list", "--count", "origin/main..HEAD"): "0",
                ("rev-list", "--count", "HEAD..origin/main"): "0",
                ("diff", "--name-only", "origin/main...HEAD"): "",
                ("diff", "--name-only"): "scripts/delivery_preflight.py",
                ("diff", "--cached", "--name-only"): "",
                ("ls-files", "--others", "--exclude-standard"): "output/note.txt",
            }
            return outputs[tuple(args)]

        with patch("scripts.delivery_preflight._git", side_effect=fake_git):
            collected = collect_facts(include_changed_paths=True)

        self.assertEqual(
            ["output/note.txt", "scripts/delivery_preflight.py"],
            collected["changed_paths"],
        )

    def test_bootstrap_control_repair_is_exact_and_one_time(self):
        exact = facts(
            branch="work/2026-08-04-delivery-activation-preflight-output",
            changed_paths=["scripts/delivery_preflight.py"],
        )
        exact_errors, exact_warnings = evaluate_policy(
            self.ledger,
            exact,
            "PS-DELIVERY-CONTROL-001",
            "activate",
        )
        self.assertEqual([], exact_errors)
        self.assertTrue(any("one-time" in warning for warning in exact_warnings))

        stale_errors, _ = evaluate_policy(
            self.ledger,
            {**exact, "origin_main": "new-main-after-merge"},
            "PS-DELIVERY-CONTROL-001",
            "activate",
        )
        self.assertTrue(
            any("non-control paths" in error for error in stale_errors)
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

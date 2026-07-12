import unittest
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations"
VERIFY = ROOT / "SQL FIles" / "Verification" / "peerslate_platform_foundation_verify.sql"
RUNNER = ROOT / "scripts" / "apply_sql_migrations.py"


class SqlFoundationTests(unittest.TestCase):
    def setUp(self):
        self.forward = sorted(
            path
            for path in MIGRATIONS.glob("PS-PLAT-*.sql")
            if not path.name.endswith("_rollback.sql")
        )
        self.rollbacks = sorted(MIGRATIONS.glob("PS-PLAT-*_rollback.sql"))

    def test_six_ordered_forward_and_rollback_migrations_exist(self):
        self.assertEqual(
            [path.name.split("_")[0] for path in self.forward],
            [
                "PS-PLAT-001",
                "PS-PLAT-002",
                "PS-PLAT-003",
                "PS-PLAT-004",
                "PS-PLAT-005",
                "PS-PLAT-006",
            ],
        )
        self.assertEqual(len(self.rollbacks), 6)

    def test_forward_migrations_are_transactional_and_recorded(self):
        for path in self.forward:
            sql = path.read_text(encoding="utf-8")
            migration_id = path.name.split("_")[0]
            with self.subTest(path=path.name):
                self.assertIn("SET XACT_ABORT ON", sql)
                self.assertIn("BEGIN TRANSACTION", sql)
                self.assertIn("COMMIT TRANSACTION", sql)
                self.assertIn("ROLLBACK TRANSACTION", sql)
                self.assertIn(migration_id, sql)

    def test_new_member_content_defaults_private_and_ai_stays_proposed(self):
        profiles = (MIGRATIONS / "PS-PLAT-002_profiles_entities_access.sql").read_text(encoding="utf-8")
        ai = (MIGRATIONS / "PS-PLAT-003_evidence_ai.sql").read_text(encoding="utf-8")
        connections = (MIGRATIONS / "PS-PLAT-004_connections_notifications.sql").read_text(encoding="utf-8")
        self.assertGreaterEqual(profiles.count("DEFAULT N'private'"), 3)
        self.assertIn("DEFAULT N'proposed'", ai)
        self.assertIn("DEFAULT 0", connections)
        self.assertIn("blocker_user_id <> blocked_user_id", connections)

    def test_audit_table_is_immutable(self):
        governance = (MIGRATIONS / "PS-PLAT-001_platform_governance.sql").read_text(encoding="utf-8")
        self.assertIn("AFTER UPDATE, DELETE", governance)
        self.assertIn("Audit events are immutable", governance)

    def test_tenant_integrity_uses_composite_owner_constraints(self):
        sql = (MIGRATIONS / "PS-PLAT-005_tenant_integrity.sql").read_text(encoding="utf-8")
        self.assertIn("FOREIGN KEY (from_entity_id, owner_profile_id)", sql)
        self.assertIn("FOREIGN KEY (evidence_item_id, owner_profile_id)", sql)
        self.assertIn("FOREIGN KEY (target_entity_id, owner_profile_id)", sql)

    def test_living_resume_domain_is_private_tenant_owned_and_reviewable(self):
        sql = (MIGRATIONS / "PS-PLAT-006_living_resume_domain.sql").read_text(
            encoding="utf-8"
        )
        rollback = (
            MIGRATIONS / "PS-PLAT-006_living_resume_domain_rollback.sql"
        ).read_text(encoding="utf-8")

        self.assertGreaterEqual(sql.count("DEFAULT N'private'"), 5)
        self.assertGreaterEqual(sql.count("DEFAULT N'draft'"), 4)
        self.assertIn("FOREIGN KEY (chapter_id, owner_profile_id)", sql)
        self.assertIn("FOREIGN KEY (skill_id, owner_profile_id)", sql)
        self.assertIn("FOREIGN KEY (ai_proposal_id, owner_profile_id)", sql)
        self.assertIn("Content approval events are immutable", sql)
        self.assertIn("contains member data", rollback)

    def test_verification_script_is_read_only(self):
        sql = VERIFY.read_text(encoding="utf-8").upper()
        for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "CREATE "):
            self.assertNotIn(forbidden, sql)

    def test_verification_validator_accepts_complete_safe_foundation(self):
        spec = importlib.util.spec_from_file_location("peerslate_migrations", RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        results = [
            [{"database_name": "test"}],
            [{"migration_id": item} for item in sorted(module.EXPECTED_MIGRATIONS)],
            [
                {"object_name": item, "exists_flag": 1}
                for item in sorted(module.EXPECTED_TABLES)
            ],
            [
                {"object_name": item, "exists_flag": 1}
                for item in sorted(module.EXPECTED_PROGRAMMABLE_OBJECTS)
            ],
            [],
            [],
            [],
            [{
                "user_count": 2,
                "profile_count": 2,
                "private_profile_count": 2,
                "discovery_off_count": 2,
            }],
        ]

        self.assertEqual(module.validate_verification_results(results), [])

    def test_verification_validator_rejects_public_backfill_or_opt_in(self):
        spec = importlib.util.spec_from_file_location("peerslate_migrations", RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        results = [
            [{"database_name": "test"}],
            [{"migration_id": item} for item in sorted(module.EXPECTED_MIGRATIONS)],
            [
                {"object_name": item, "exists_flag": 1}
                for item in sorted(module.EXPECTED_TABLES)
            ],
            [
                {"object_name": item, "exists_flag": 1}
                for item in sorted(module.EXPECTED_PROGRAMMABLE_OBJECTS)
            ],
            [],
            [],
            [],
            [{
                "user_count": 2,
                "profile_count": 2,
                "private_profile_count": 1,
                "discovery_off_count": 1,
            }],
        ]

        failures = module.validate_verification_results(results)
        self.assertEqual(len(failures), 2)


if __name__ == "__main__":
    unittest.main()

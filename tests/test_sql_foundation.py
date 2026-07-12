import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations"
VERIFY = ROOT / "SQL FIles" / "Verification" / "peerslate_platform_foundation_verify.sql"


class SqlFoundationTests(unittest.TestCase):
    def setUp(self):
        self.forward = sorted(
            path
            for path in MIGRATIONS.glob("PS-PLAT-*.sql")
            if not path.name.endswith("_rollback.sql")
        )
        self.rollbacks = sorted(MIGRATIONS.glob("PS-PLAT-*_rollback.sql"))

    def test_five_ordered_forward_and_rollback_migrations_exist(self):
        self.assertEqual(
            [path.name.split("_")[0] for path in self.forward],
            ["PS-PLAT-001", "PS-PLAT-002", "PS-PLAT-003", "PS-PLAT-004", "PS-PLAT-005"],
        )
        self.assertEqual(len(self.rollbacks), 5)

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

    def test_verification_script_is_read_only(self):
        sql = VERIFY.read_text(encoding="utf-8").upper()
        for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "CREATE "):
            self.assertNotIn(forbidden, sql)


if __name__ == "__main__":
    unittest.main()

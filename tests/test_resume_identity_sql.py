"""G migration source/rollback integrity. This is not SQL engine proof."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROPOSED = ROOT / "SQL FIles/Migrations/proposed"
NAME = "PS-RESUME-IDENTITY-001_publication_identity"


def definitions(source):
    found = {}
    for match in re.finditer(r"EXEC\s*(?:sys\.sp_executesql\s+|\(\s*)N?'((?:''|[^'])*)'", source):
        statement = match.group(1).replace("''", "'").strip()
        header = re.match(r"CREATE OR ALTER PROCEDURE dbo\.(\w+)\b", statement)
        if header:
            name = header.group(1)
            if name in found:
                raise AssertionError("Duplicate procedure definition: " + name)
            found[name] = statement
    return found


class ResumeIdentityMigrationSourceTests(unittest.TestCase):
    def test_forward_and_rollback_cover_the_same_procedures(self):
        forward = definitions((PROPOSED / (NAME + ".sql")).read_text(encoding="utf-8"))
        rollback = definitions((PROPOSED / (NAME + "_rollback.sql")).read_text(encoding="utf-8"))
        self.assertEqual(set(forward), set(rollback))
        self.assertEqual(len(forward), 14)
        self.assertIn("usp_MemberVisitorAiSnapshotInternal", forward)
        self.assertIn("usp_CommitResumeDraftCommandForOwner", forward)

    def test_rollback_restores_exact_dependency_definitions(self):
        from scripts.run_mvp1_acceptance_sql_proof import migration_closure
        originals = {}
        # Later migrations wrap earlier public mutators. Resolve the same ordered
        # closure as the engine, never a manually reordered dependency list.
        for migration in migration_closure(ROOT)[:-1]:
            originals.update(definitions((ROOT / migration['forward']).read_text(encoding="utf-8")))
        rollback = definitions((PROPOSED / (NAME + "_rollback.sql")).read_text(encoding="utf-8"))
        for name, definition in rollback.items():
            with self.subTest(procedure=name):
                self.assertEqual(definition, originals[name])

    def test_rollback_refuses_retained_references_before_replacing_procedures(self):
        sql = (PROPOSED / (NAME + "_rollback.sql")).read_text(encoding="utf-8")
        before = sql.split("CREATE OR ALTER PROCEDURE", 1)[0]
        for retained in ("profile_identity_json IS NOT NULL", "$.candidate", "N'bind_story'", "record_type=N'knowledge'", "catalog_source_bound=1", "source_kind=N'generated_illustration'"):
            self.assertIn(retained, before)
        self.assertNotRegex(sql, r"(?i)\bDELETE\s+(?:FROM\s+)?dbo\.(knowledge|resume_publication_revisions|resume_draft_command_receipts)")

    def test_prerequisites_are_registered_and_runtime_gate_remains_unqualified(self):
        registry = json.loads((ROOT / "SQL FIles/Migrations/registry.json").read_text(encoding="utf-8"))
        rows = registry["migrations"]
        migration = next(row for row in rows if row["id"] == "PS-RESUME-IDENTITY-001")
        self.assertIsNone(migration["gate"])
        self.assertEqual(set(migration["requires"]), {
            "PS-RESUME-PUBLICATION-001", "PS-PROFILE-002", "PS-WORKSHOP-004", "PS-VISITOR-AI-001"})
        self.assertTrue(set(migration["requires"]) <= {row["id"] for row in rows})


if __name__ == "__main__":
    unittest.main()

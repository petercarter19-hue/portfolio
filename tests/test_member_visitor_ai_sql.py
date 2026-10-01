"""Source admission checks, not SQL Server acceptance."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class SqlSourceTests(unittest.TestCase):
    def test_registered_dependency_and_reader_only_rollback_preserve_E(self):
        registry=json.loads((ROOT/'SQL FIles/Migrations/registry.json').read_text(encoding='utf-8'))
        entry=next(x for x in registry['migrations'] if x['id']=='PS-VISITOR-AI-001')
        self.assertEqual(entry['requires'],['PS-RESUME-PUBLICATION-001'])
        # Honest null until actual proof; imported proofs must match unchanged SQL.
        if entry["gate"] is not None:
            from scripts.migration_registry import GateProof, executable_sha256
            proof = GateProof.from_json(entry["id"], entry["gate"])
            self.assertEqual(proof.executable_sha256, executable_sha256(ROOT / entry["forward"]))
        rollback=(ROOT/entry['rollback']).read_text(encoding='utf-8')
        self.assertNotIn('DROP TABLE',rollback.upper())
        self.assertNotIn('DELETE dbo.resume_',rollback)
        self.assertEqual(rollback.count('DROP PROCEDURE'),3)

    def test_guest_wrapper_cannot_take_owner_or_client_manifest(self):
        source=(ROOT/'SQL FIles/Migrations/proposed/PS-VISITOR-AI-001_readers.sql').read_text(encoding='utf-8')
        guest=source.split('CREATE OR ALTER PROCEDURE dbo.usp_GetMemberVisitorAiBySlug',1)[1].split("END;'",1)[0]
        self.assertNotIn('@UserKey',guest)
        self.assertNotIn('@Manifest',guest)
        self.assertIn('@OwnerPreview=0',guest)
        self.assertIn('DENY EXECUTE ON dbo.usp_MemberVisitorAiSnapshotInternal TO PUBLIC',source)

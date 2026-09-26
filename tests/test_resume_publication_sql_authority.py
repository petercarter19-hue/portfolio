"""Publication SQL authority helper stays plan-only."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "configure_resume_publication_sql_authority.py"


class ResumePublicationSqlAuthorityTests(unittest.TestCase):
    def test_plan_lists_grants_and_denies_without_connecting(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--plan"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["production_apply"])
        self.assertIn("usp_CommitResumePublicationCommandForOwner", payload["grant_execute"])
        self.assertIn("usp_ResumePublicationEncodeSourceInternal", payload["deny_execute"])

    def test_apply_is_refused(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--apply"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("refused", completed.stderr)


if __name__ == "__main__":
    unittest.main()

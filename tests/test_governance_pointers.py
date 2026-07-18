"""PS-GOV-001 — guardrails for the repository authority chain.

These checks FAIL THE BUILD (requirement PS-GOV-001-R02) when the mandatory
startup system is missing or when its document pointers go stale. That is what
keeps every delivery lane — Cowork/Claude, Claude Code, Codex, and humans —
starting from the same authority instead of relying on a verbal handoff.

Deliberately dependency-free (standard library only) so it runs anywhere the
existing suite runs, with no new package in requirements.txt.
"""

import os
import re
import unittest

# Repo root = one directory up from tests/ (same pattern as test_site_rules.py).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def _exists(*parts):
    return os.path.exists(os.path.join(ROOT, *parts))


class StartHereEntryPointTests(unittest.TestCase):
    """PS-GOV-001-R01 — one mandatory entry point for every lane."""

    def test_start_here_exists(self):
        self.assertTrue(
            _exists('START_HERE.md'),
            'START_HERE.md must exist at the repository root',
        )

    def test_claude_md_requires_start_here(self):
        body = _read('CLAUDE.md')
        self.assertIn('START_HERE', body,
                      'CLAUDE.md must point every session at START_HERE.md')
        self.assertIn('MANDATORY PRE-WORK GATE', body,
                      'CLAUDE.md must carry the mandatory pre-work gate block')

    def test_agents_md_requires_start_here(self):
        body = _read('AGENTS.md')
        self.assertIn('START_HERE', body,
                      'AGENTS.md must point every session at START_HERE.md')
        self.assertIn('MANDATORY PRE-WORK GATE', body,
                      'AGENTS.md must carry the mandatory pre-work gate block')


class GovernanceRecordsTests(unittest.TestCase):
    """PS-GOV-001-R02 — the required state/template records exist."""

    REQUIRED = (
        ('docs', 'governance', 'CURRENT_BASELINE.yaml'),
        ('docs', 'governance', 'CURRENT_STATE.md'),
        ('docs', 'governance', 'ACTIVE_INITIATIVES.md'),
        ('docs', 'governance', 'AGENT_STARTUP_CHECKLIST.md'),
        ('docs', 'templates', 'OWNER_TECHNICAL_COMPLETION_REPORT.md'),
        ('docs', 'initiatives', 'PS-GOV-001', 'README.md'),
    )

    def test_required_records_exist(self):
        missing = [os.path.join(*p) for p in self.REQUIRED if not _exists(*p)]
        self.assertEqual([], missing,
                         f'Missing required governance records: {missing}')


class NoStalePointersTests(unittest.TestCase):
    """PS-GOV-001-R02 — every path named in the baseline must resolve."""

    def _baseline_paths(self):
        text = _read('docs', 'governance', 'CURRENT_BASELINE.yaml')
        # Every  path: "..."  entry (bible, roadmap, sync_standard, design_baseline).
        return re.findall(r'path:\s*"([^"]+)"', text)

    def test_baseline_pointers_resolve(self):
        stale = []
        for rel in self._baseline_paths():
            parts = rel.rstrip('/').split('/')  # tolerate trailing slash on dirs
            if not _exists(*parts):
                stale.append(rel)
        self.assertEqual([], stale,
                         f'CURRENT_BASELINE.yaml points at missing paths: {stale}')

    def test_baseline_names_the_adopted_versions(self):
        text = _read('docs', 'governance', 'CURRENT_BASELINE.yaml')
        self.assertIn('Bible_v2.3', text, 'Baseline must name the adopted Bible v2.3')
        self.assertIn('Roadmap_v2.3', text, 'Baseline must name the adopted Roadmap v2.3')


if __name__ == '__main__':
    unittest.main()

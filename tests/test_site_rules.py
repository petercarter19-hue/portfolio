"""PS-RULES-001 — automated guardrails for the v1.2 site rules.

Pragmatic static checks (rules doc §12 / implementation instructions §5):
they target production behavior and UI surfaces, not internal migration
notes or documentation. Checks for Evidence-in-navigation and About-in-nav
land together with PS-BRAND-NAV-001, which removes those labels.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


class DeploymentPolicyTests(unittest.TestCase):
    def test_no_github_workflow_can_deploy_automatically(self):
        """Azure Pipelines is the only production deployment path."""
        workflows = os.path.join(ROOT, '.github', 'workflows')
        if not os.path.isdir(workflows):
            return
        for name in os.listdir(workflows):
            content = _read(os.path.join(workflows, name))
            for trigger in ('push:', 'schedule:', 'pull_request:'):
                self.assertNotIn(
                    '\n  ' + trigger, '\n' + content.split('jobs:')[0],
                    f'{name} has an automatic trigger ({trigger.strip(":")})'
                    ' — GitHub Actions must not deploy PeerSlate')


class OwnershipGuardrailTests(unittest.TestCase):
    REUSABLE_CODE = ('services', 'db.py', 'identity.py',
                     'peerslate_api.py', 'people_interests_api.py')

    def test_no_hardcoded_owner_identifiers_in_reusable_code(self):
        pattern = re.compile(r"['\"](petec|danielle[a-z]*)['\"]", re.I)
        offenders = []
        for entry in self.REUSABLE_CODE:
            path = os.path.join(ROOT, entry)
            files = []
            if os.path.isdir(path):
                for base, _, names in os.walk(path):
                    files += [os.path.join(base, n) for n in names
                              if n.endswith('.py')]
            elif os.path.isfile(path):
                files = [path]
            for f in files:
                for i, line in enumerate(_read(f).splitlines(), 1):
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        continue
                    if pattern.search(line):
                        offenders.append(f'{f}:{i}')
        self.assertEqual(offenders, [],
                         'hardcoded owner identifiers in reusable code')


class ProductBoundaryTests(unittest.TestCase):
    def test_no_job_listing_routes(self):
        """Rule 34: no job posts, listings, feeds, or marketplace — ever."""
        from app import app
        banned = ('job', 'jobs', 'hiring', 'listing')
        for rule in app.url_map.iter_rules():
            path = rule.rule.lower()
            for term in banned:
                self.assertNotIn(f'/{term}', path,
                                 f'route {rule.rule} looks like a job surface')

    def test_no_secret_names_in_client_javascript(self):
        js_dir = os.path.join(ROOT, 'static', 'js')
        secret_names = ('ANTHROPIC_API_KEY', 'AZURE_CLIENT_SECRET',
                        'CONNECTION_STRING', 'PUBLISH_PROFILE',
                        'SECRET_KEY')
        for base, _, names in os.walk(js_dir):
            for name in names:
                if not name.endswith('.js'):
                    continue
                content = _read(os.path.join(base, name))
                for secret in secret_names:
                    self.assertNotIn(secret, content,
                                     f'{name} references {secret}')


class GovernanceDocsTests(unittest.TestCase):
    def test_authoritative_documents_are_in_the_repository(self):
        for rel in ('docs/PEERSLATE_SITE_RULES.md',
                    'docs/PEERSLATE_V12_IMPLEMENTATION_INSTRUCTIONS.md',
                    'PeerSlate_Company_and_Product_Bible_v1.2.docx',
                    'docs/INITIATIVE_CHECKLIST.md'):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_claude_md_points_to_v12_governance(self):
        content = _read(os.path.join(ROOT, 'CLAUDE.md'))
        self.assertIn('PEERSLATE_SITE_RULES.md', content)
        self.assertIn('PeerSlate_Company_and_Product_Bible_v1.2.docx',
                      content)


if __name__ == '__main__':
    unittest.main()

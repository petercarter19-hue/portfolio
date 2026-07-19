"""PS-RULES-001 — automated guardrails for the governing site rules.

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
        for rel in (
                'docs/governance/CURRENT_BASELINE.yaml',
                'docs/governance/DOCUMENT_CONTROL.md',
                'docs/governance/PeerSlate_Company_and_Product_Bible_v2.4.docx',
                'docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.3.docx',
                'docs/PEERSLATE_SITE_RULES.md'):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_claude_md_points_to_current_governance(self):
        content = _read(os.path.join(ROOT, 'CLAUDE.md'))
        self.assertIn('PEERSLATE_SITE_RULES.md', content)
        self.assertIn('CURRENT_BASELINE.yaml', content)
        self.assertIn('DOCUMENT_CONTROL.md', content)
        self.assertIn('Bible v2.4 / Roadmap v2.3', content)


class NavigationLanguageTests(unittest.TestCase):
    """PS-BRAND-NAV-001: Evidence and About stay out of the navigation."""

    def test_no_evidence_label_in_navigation_templates(self):
        for rel in ('templates/base.html',
                    'templates/partials/profile_tabs.html'):
            content = _read(os.path.join(ROOT, rel))
            for line in content.splitlines():
                if '>Evidence<' in line.replace(' ', ''):
                    self.fail(f'Evidence nav label found in {rel}: {line.strip()}')

    def test_about_peerslate_not_in_header_nav(self):
        content = _read(os.path.join(ROOT, 'templates/base.html'))
        nav = content.split('platform-nav__links')[1].split('</ul>')[0]
        self.assertNotIn('About PeerSlate', nav)
        self.assertIn('footer-why-link', content)


if __name__ == '__main__':
    unittest.main()

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


class DeploymentPackageTests(unittest.TestCase):
    """The deployment package must keep everything the running site reads.

    The disabled GitHub workflow shows how this goes wrong: it excludes
    static/images/Mockups/ and static/images/background-templates/ wholesale,
    but resume2.css references Mockups/resume2/ and three stylesheets
    reference background-templates. Because that workflow never runs, the
    mistake was never caught. Pin the live pipeline against the same error.
    """

    REQUIRED_AT_RUNTIME = (
        'docs',                              # Control Room + chatbot knowledge
        'docs/knowledge',
        'docs/governance',
        'docs/initiatives',
        'static/data',                       # resume/story/feed JSON
        'static/css',
        'static/js',
        'static/images/Mockups',             # resume2.css uses Mockups/resume2/
        'static/images/background-templates',
        'templates',
        'services',
        'SQL FIles',
    )

    def test_pipeline_never_excludes_a_runtime_required_path(self):
        pipeline = _read(os.path.join(ROOT, 'azure-pipelines.yml'))
        excluded = re.findall(r'^\s*!(\S+)', pipeline, re.MULTILINE)
        for pattern in excluded:
            base = pattern.split('/*')[0].rstrip('/')
            for required in self.REQUIRED_AT_RUNTIME:
                self.assertNotEqual(
                    base, required,
                    f'azure-pipelines.yml excludes {pattern!r}, but '
                    f'{required!r} is read by the running site')

    def test_pipeline_still_excludes_the_largest_non_runtime_folders(self):
        pipeline = _read(os.path.join(ROOT, 'azure-pipelines.yml'))
        for pattern in ('!artifacts/**', '!tests/**'):
            self.assertIn(
                pattern, pipeline,
                f'{pattern} keeps the deployment package from carrying '
                'evidence and test material onto the web server')


class DependencyPinTests(unittest.TestCase):
    def test_shared_pins_match_between_requirements_files(self):
        """requirements-sql.txt re-pins packages requirements.txt also pins.

        Two files pinning the same package can drift silently, so the local
        database tooling would resolve a different version than the deployed
        application. Keep the shared pins identical or remove the duplicate.
        """

        def pins(filename):
            found = {}
            for line in _read(os.path.join(ROOT, filename)).splitlines():
                line = line.split('#', 1)[0].strip()
                if '==' in line:
                    name, version = line.split('==', 1)
                    found[name.strip().lower()] = version.strip()
            return found

        app_pins = pins('requirements.txt')
        sql_pins = pins('requirements-sql.txt')
        shared = set(app_pins) & set(sql_pins)
        self.assertTrue(shared, 'expected requirements-sql.txt to share pins')
        for package in sorted(shared):
            self.assertEqual(
                sql_pins[package], app_pins[package],
                f'{package} is pinned to {sql_pins[package]} in '
                f'requirements-sql.txt but {app_pins[package]} in '
                'requirements.txt')


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
                'docs/governance/PeerSlate_Company_and_Product_Bible_v2.9.md',
                'docs/governance/PeerSlate_Company_and_Product_Bible_v2.9.docx',
                'docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.8.md',
                'docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.8.docx',
                'docs/PEERSLATE_SITE_RULES.md'):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_page_purpose_gate_preserves_truth_before_visual_creation(self):
        standard = _read(os.path.join(
            ROOT, 'docs', 'governance', 'OWNER_VISUAL_INTEGRITY_STANDARD.md'))
        template = _read(os.path.join(
            ROOT, 'docs', 'templates', 'PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md'))
        for expected in (
                'Before ChatGPT creates or materially revises a visual',
                'meaningful visible page item, card, control, and status',
                'Pete approves the page-purpose/non-redundancy inventory before the visual lock.',
                'The visual lock may not introduce a meaningful item'):
            self.assertIn(expected, standard)
        for expected in (
                'Member purpose',
                'Source / capability truth',
                'Privacy, audience, and lifecycle',
                'Keep / Change / Combine / Remove / Defer'):
            self.assertIn(expected, template)

    def test_claude_md_points_to_current_governance(self):
        content = _read(os.path.join(ROOT, 'CLAUDE.md'))
        self.assertIn('PEERSLATE_SITE_RULES.md', content)
        self.assertIn('CURRENT_BASELINE.yaml', content)
        self.assertIn('DOCUMENT_CONTROL.md', content)
        self.assertIn('Bible and\nRoadmap paths it names', content)
        self.assertNotIn('currently Bible', content)
        self.assertIn('self-manages its assigned branch', content)
        self.assertIn('Pass` self-certification', content)
        self.assertIn('Claude Co-Work', content)
        self.assertIn('designated session manager', content)

    def test_site_rules_encode_one_journal_and_open_navigation(self):
        content = _read(os.path.join(ROOT, 'docs', 'PEERSLATE_SITE_RULES.md'))
        for expected in (
                'Save Moment',
                'deterministic derived membership',
                'not a required destination',
                'final signed-in route map remains an explicit later decision',
                'Ask Slate AI',
                'Ashley AI is retired terminology',
                'My Story',
                'not necessarily daily'):
            self.assertIn(expected, content)
        for superseded_affirmative in (
                'Every Capture initially creates a private draft',
                'The user then explicitly chooses whether to add it to the Journal',
                'Capture is a primary destination'):
            self.assertNotIn(superseded_affirmative, content)
        self.assertIn('not another user-facing destination or an Add to Journal gate', content)

    def test_interview_demo_is_downstream_of_released_studio(self):
        package = os.path.join(
            ROOT,
            'docs',
            'initiatives',
            'PS-INTERVIEW-PUBLIC-GATE-001')
        convergence_path = os.path.join(
            package,
            '10_REAL_STUDIO_AND_HOMEPAGE_DEMO_CONVERGENCE.md')
        self.assertTrue(os.path.isfile(convergence_path), convergence_path)

        convergence = _read(convergence_path)
        normalized_convergence = ' '.join(convergence.split())
        readme = _read(os.path.join(package, 'README.md'))
        visual_standard = _read(os.path.join(
            ROOT, 'docs', 'governance',
            'OWNER_VISUAL_INTEGRITY_STANDARD.md'))

        self.assertIn(
            'The walkthrough is not a second visual authority',
            normalized_convergence)
        self.assertIn(
            'verified live before demo convergence begins',
            normalized_convergence)
        self.assertIn(
            'Written practice is primary in both real product and demo',
            normalized_convergence)
        self.assertIn(
            'no network, API, input, storage', normalized_convergence)
        self.assertIn(
            '10_REAL_STUDIO_AND_HOMEPAGE_DEMO_CONVERGENCE.md', readme)
        self.assertIn(
            'upstream authority for that walkthrough', visual_standard)

        baseline = _read(os.path.join(
            ROOT, 'docs', 'governance', 'CURRENT_BASELINE.yaml'))
        self.assertIn('interview_demo_convergence_pr: 83', baseline)
        self.assertIn('interview_demo_convergence_pipeline: 117', baseline)
        self.assertIn('homepage_interview_demo_pr: 86', baseline)
        self.assertIn('homepage_interview_demo_pipeline: 122', baseline)
        self.assertIn(
            'homepage_interview_demo_merge_commit: '
            '"a98cced519a1f853ad9f4462fd438efa67d6f260"',
            baseline)
        self.assertIn(
            'Current illustration live and verified; real 5A/5C Studio and '
            'converged projection not live',
            normalized_convergence)


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

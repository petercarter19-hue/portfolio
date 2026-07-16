import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKGROUND_NAME = '2509b8db-4281-468c-a2cf-dba20ac3268b.png'


class SiteBackgroundTests(unittest.TestCase):
    def test_shared_background_asset_is_present(self):
        asset = ROOT / 'static' / 'images' / 'background-templates' / BACKGROUND_NAME
        self.assertTrue(asset.is_file())
        self.assertGreater(asset.stat().st_size, 100_000)

    def test_shared_and_interview_surfaces_use_the_new_background(self):
        expected_url = f'../images/background-templates/{BACKGROUND_NAME}'
        for relative_path in (
            'static/css/sky-glass.css',
            'static/css/editorial-glass.css',
            'static/css/interview-studio.css',
        ):
            with self.subTest(relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding='utf-8')
                self.assertIn(expected_url, source)

    def test_editorial_background_no_longer_uses_retired_navy_field(self):
        source = (ROOT / 'static/css/editorial-glass.css').read_text(encoding='utf-8')
        self.assertNotIn('navy-background.png', source)
        self.assertNotIn('navy-background-mobile.jpg', source)

        interview_source = (ROOT / 'static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertNotIn('interview-workspace-bg', interview_source)


if __name__ == '__main__':
    unittest.main()

import re
import unittest

from app import app


class AtriumTests(unittest.TestCase):
    """The Atrium (Living Triptych 01-Arrival) experimental Overview.

    These lock in the slice-1 guarantees: the route renders, the header
    exposes the Atrium link, the three dimensions carry real fixture content
    with working destinations, the retired MICAP example never appears, and
    the page keeps the accessibility structure (one h1, labelled slabs, a
    reduced-motion path) — without the profile tab strip so it stays
    full-bleed.
    """

    def setUp(self):
        self.client = app.test_client()

    def _html(self, path='/atrium'):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_atrium_route_renders(self):
        html = self._html()
        self.assertIn('class="atrium"', html)

    def test_header_exposes_the_atrium_link(self):
        html = self._html('/')
        self.assertRegex(html, r'href="/atrium"[^>]*>\s*Atrium\s*<')

    def test_three_dimensions_link_to_real_destinations(self):
        html = self._html()
        # The shared identity is the single page heading.
        self.assertEqual(len(re.findall(r'<h1[^>]*>', html)), 1)
        self.assertIn('Pete Carter', html)
        self.assertIn('Person', html)
        self.assertIn('Builder', html)
        self.assertIn('Engineer', html)
        # Each slab is a labelled section with a real Enter destination.
        for title, href in [
            ('My Story', '/petec/my-story'),
            ('Projects', '/petec/work'),
            ('Living Résumé', '/petec/resume2'),
        ]:
            self.assertIn(title, html)
            self.assertIn(href, html)

    def test_resume_slab_uses_real_chapters_and_evidence(self):
        html = self._html()
        # Real, current career chapters — not the mockup's fictional data.
        self.assertIn('Northrop Grumman', html)
        self.assertIn('L3Harris', html)
        # At least one real, measured impact metric is surfaced.
        self.assertIn('$36M+', html)

    def test_atrium_omits_the_retired_micap_example(self):
        html = self._html()
        self.assertNotIn('MICAP', html.upper())

    def test_story_slab_uses_existing_photography_assets(self):
        html = self._html()
        self.assertIn('images/story/', html)

    def test_atrium_hides_the_profile_tab_strip(self):
        # The Atrium is full-bleed; it opts out of the profile sub-nav just
        # like the homepage does.
        html = self._html()
        self.assertNotIn('profile-tabs__list', html)

    def test_atrium_declares_reduced_motion_support(self):
        css = self.client.get('/static/css/atrium.css').get_data(as_text=True)
        self.assertIn('prefers-reduced-motion', css)
        self.assertIn('forced-colors', css)


if __name__ == '__main__':
    unittest.main()

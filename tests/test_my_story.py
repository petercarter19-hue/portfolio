import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import app


class StoryMarkupParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.act_sections = []
        self.collages = 0
        self.h1_count = 0
        self.card_depth = 0
        self.card_images = []
        self.chapter_controls = []
        self.expand_panels = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get('class', '').split()

        if tag == 'section' and 'story-act' in classes:
            self.act_sections.append(attributes)
        if tag == 'div' and 'story-collage' in classes:
            self.collages += 1
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'article' and 'st-card' in classes:
            self.card_depth += 1
        if tag == 'img' and self.card_depth:
            self.card_images.append(attributes)
        if tag == 'button' and 'data-sc-toggle' in attributes:
            self.chapter_controls.append(attributes)
        if tag == 'div' and 'sc-expand' in classes:
            self.expand_panels[attributes['id']] = attributes

    def handle_endtag(self, tag):
        if tag == 'article' and self.card_depth:
            self.card_depth -= 1


class MyStoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.story_data = json.loads(
            (cls.project_root / 'static' / 'data' / 'story_data.json').read_text(
                encoding='utf-8'
            )
        )

    def setUp(self):
        self.client = app.test_client()

    def render_story(self, path='/petec/my-story'):
        response = self.client.get(path, base_url='http://localhost')
        parser = StoryMarkupParser()
        parser.feed(response.get_data(as_text=True))
        return response, parser

    def test_both_story_routes_render_the_four_act_composition(self):
        expected_ids = [act['id'] for act in self.story_data['acts']]

        for path in ('/my-story', '/petec/my-story'):
            with self.subTest(path=path):
                response, parser = self.render_story(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [section['id'] for section in parser.act_sections],
                    expected_ids,
                )
                self.assertEqual(parser.collages, 4)
                self.assertIn(b'css/story-acts.css?v=story-acts-3', response.data)

    def test_story_has_one_page_heading_and_labelled_act_sections(self):
        response, parser = self.render_story()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(parser.h1_count, 1)
        for section in parser.act_sections:
            self.assertEqual(
                section['aria-labelledby'],
                f"{section['id']}-title",
            )

    def test_every_data_card_renders_in_semantic_order(self):
        response = self.client.get('/petec/my-story', base_url='http://localhost')
        markup = response.get_data(as_text=True)
        rendered_positions = []

        for act in self.story_data['acts']:
            for card in act['cards']:
                card_id = f"{act['id']}-{card['id']}"
                rendered_positions.append(markup.index(f'id="{card_id}"'))

        self.assertEqual(rendered_positions, sorted(rendered_positions))

    def test_story_images_are_accessible_and_use_existing_assets(self):
        _, parser = self.render_story()
        data_images = [
            card['image']
            for act in self.story_data['acts']
            for card in act['cards']
            if card['type'] == 'image'
        ]

        self.assertEqual(len(parser.card_images), len(data_images))
        self.assertEqual(
            sum(image.get('fetchpriority') == 'high' for image in parser.card_images),
            1,
        )
        self.assertTrue(all(image.get('alt', '').strip() for image in parser.card_images))

        for image in data_images:
            for source_key in ('src', 'mobile'):
                with self.subTest(asset=image[source_key]):
                    self.assertTrue(
                        (self.project_root / 'static' / image[source_key]).is_file()
                    )

    def test_chapter_disclosures_start_closed_and_have_valid_targets(self):
        _, parser = self.render_story()

        self.assertEqual(len(parser.chapter_controls), 7)
        for control in parser.chapter_controls:
            panel_id = control['aria-controls']
            self.assertEqual(control['aria-expanded'], 'false')
            self.assertIn(panel_id, parser.expand_panels)
            self.assertIn('hidden', parser.expand_panels[panel_id])

    def test_closing_values_and_truthful_goal_storage_copy_render(self):
        response = self.client.get('/petec/my-story', base_url='http://localhost')
        markup = response.get_data(as_text=True)

        for value in self.story_data['closing_values']:
            self.assertIn(value['label'], markup)
        self.assertIn('nothing is published or shared automatically', markup)
        self.assertNotIn('Ph.D. in Computer Science', markup)

    def test_act_four_trajectory_modules_render_from_story_data(self):
        response = self.client.get('/petec/my-story', base_url='http://localhost')
        markup = response.get_data(as_text=True)
        signal_cards = [
            card
            for act in self.story_data['acts']
            for card in act['cards']
            if card.get('signal')
        ]

        self.assertEqual(markup.count('class="sc-signal '), len(signal_cards))
        for card in signal_cards:
            signal = card['signal']
            self.assertIn(f'sc-signal--{signal["variant"]}', markup)
            self.assertIn(f'aria-label="{signal["title"]}"', markup)
            for step in signal['steps']:
                self.assertIn(f'<li>{step}</li>', markup)

    def test_mobile_progress_and_reduced_motion_avoid_fixed_overlap(self):
        css = (
            self.project_root / 'static' / 'css' / 'story-acts.css'
        ).read_text(encoding='utf-8')

        mobile_block = css[css.index('@media (max-width: 47.9rem)'):]
        reduced_motion_block = css[
            css.index('@media (prefers-reduced-motion: reduce)'):
        ]

        self.assertIn('position: relative;', mobile_block)
        self.assertIn('bottom: auto;', mobile_block)
        self.assertIn('body.sa-js .sa-reveal', reduced_motion_block)
        self.assertIn('transform: none;', reduced_motion_block)


if __name__ == '__main__':
    unittest.main()

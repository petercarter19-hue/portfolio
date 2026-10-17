"""Real-browser layout and interaction proof. AI responses are controlled fixtures.

The Flask page and its assets are real. These tests do not establish live provider,
private messaging, or physical-device proof. They skip if Chrome/Playwright is absent.
"""
import copy
import json
import os
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('ANTHROPIC_API_KEY', 'sage-mist-test-only')
import app as app_module
from werkzeug.serving import make_server
from tests.test_resume_sage_mist import public_projection, sparse_projection

try:
    from playwright.sync_api import sync_playwright
    from scripts.capture_ps_journal_j1_evidence import _resolve_chrome
    CHROME = _resolve_chrome()
except (ImportError, RuntimeError, FileNotFoundError):
    sync_playwright = None
    CHROME = None


def answer_fixture(record='northrop', summary=None):
    locator = {'section': 'experience', 'anchor': f'r2-exp-card-{record}', 'record_kind': 'career_role', 'record_id': record, 'highlight_key': f'career-{record}'}
    return {'schema_version': 'ask-pete-public-answer.v1', 'state': 'supported', 'purpose': 'evidence_finder',
            'summary': summary or 'A controlled public-answer fixture describes the work and its supporting record. ' * 6,
            'claims': [{'text': 'Controlled evidence fixture.', 'state': 'supported', 'kind': 'evidence', 'citations': [{'excerpt': 'Approved public record excerpt.', 'source_title': record, 'locator': locator}]}],
            'follow_up_questions': [], 'source_summary': {'label': 'Approved public information', 'show_all_on_resume': True},
            'sources_used': [{'title': record, 'locator': locator}], 'handoff': None}


@unittest.skipUnless(sync_playwright is not None and CHROME, 'Real Chrome and Playwright required')
class SageMistBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = dict(app_module.app.config)
        cls.old_limiter = app_module.limiter.enabled
        app_module.app.config.update(TESTING=True, PEERSLATE_ASK_PETE_GROUNDED_ENABLED=True)
        app_module.limiter.enabled = False
        # A cancelled/intercepted request may race browser route cleanup. Block
        # the application adapter too, so no test can reach a real AI provider.
        unavailable = answer_fixture(summary='The browser-test provider boundary is unavailable.')
        unavailable.update(state='unavailable', claims=[], sources_used=[])
        cls.api_boundary = patch.object(app_module, 'answer_public_question', return_value=SimpleNamespace(payload=unavailable))
        cls.api_boundary.start()
        cls.server = make_server('127.0.0.1', 0, app_module.app, threaded=True)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.runtime = sync_playwright().start()
        cls.browser = cls.runtime.chromium.launch(executable_path=CHROME, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()
        cls.server.shutdown()
        cls.server_thread.join(timeout=5)
        app_module.app.config.clear()
        app_module.app.config.update(cls.original)
        app_module.limiter.enabled = cls.old_limiter
        cls.api_boundary.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width': 1440, 'height': 900}, reduced_motion='reduce')
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.errors, [], 'No browser JavaScript errors')

    def open(self, width=1440, height=900, query=''):
        self.page.set_viewport_size({'width': width, 'height': height})
        self.page.goto(self.base + '/petec/resume' + query)
        self.page.wait_for_selector('[data-sage-ready]')

    def away(self, width):
        self.page.locator('#impact').evaluate("e => e.scrollIntoView({behavior:'instant'})")
        self.page.wait_for_function("document.querySelector('[data-ask-pete-companion]').dataset.sagePlacement !== 'inline'")
        if width <= 900:
            self.page.locator('.sage-ai-bubble').click()

    def assert_geometry(self):
        result = self.page.evaluate("""() => {
            const c=document.querySelector('[data-ask-pete-companion]'), input=c.querySelector('[data-ask-pete-input]');
            const r=input.getBoundingClientRect(), scroll=c.querySelector('.ask-pete-evidence-companion__scroll');
            return {overflow:document.documentElement.scrollWidth>innerWidth+1, count:document.querySelectorAll('[data-ask-pete-companion]').length,
                visible:r.height>0 && r.top>=0 && r.bottom<=innerHeight, bottom:c.getBoundingClientRect().bottom,
                scrollable:scroll.scrollHeight>scroll.clientHeight, inputFont:parseFloat(getComputedStyle(input).fontSize)};
        }""")
        self.assertFalse(result['overflow'])
        self.assertEqual(result['count'], 1)
        self.assertTrue(result['visible'])
        self.assertLessEqual(result['bottom'], self.page.viewport_size['height'] + 1)
        return result

    def respond(self, payload=None):
        payload = payload or answer_fixture()
        self.page.route('**/api/chat', lambda route: route.fulfill(status=200, json=payload))
        self.page.locator('[data-ask-pete-input]').fill('What public work supports this?')
        self.page.locator('[data-ask-pete-form] [data-ask-pete-submit]').click()
        self.page.wait_for_selector('.sage-ai-turn')

    def test_sizes_opening_rail_sheet_answer_and_evidence(self):
        for width, height in ((320,800),(390,844),(900,800),(1024,800),(1440,900),(2560,1440),(1024,500),(1280,500)):
            with self.subTest(width=width, height=height):
                self.open(width, height)
                self.assertEqual(self.page.locator('[data-ask-pete-starter]').count(), 2)
                self.assertEqual(self.page.locator('[data-ask-pete-companion]').get_attribute('data-sage-placement'), 'inline')
                self.assertEqual(self.page.evaluate("getComputedStyle(document.body).backgroundColor"), 'rgb(63, 106, 81)')  # the site theme green
                self.away(width)
                self.assert_geometry()
                self.respond()
                self.assert_geometry()
                self.page.locator('[data-ask-pete-fold-toggle]').click()
                self.page.locator('[data-ask-pete-claim-toggle]').click()
                self.assert_geometry()
                self.assertGreater(self.page.locator('[data-ask-pete-source]').count(), 0)
                self.page.unroute('**/api/chat')

    # A short desktop rail must show the latest answer, not just a composer.
    # Settled means the transcript has reached its compact size and two more
    # frames have rendered, so a late re-alignment cannot slip past the check.
    SHORT_RAIL_SETTLED = """() => {
        const c=document.querySelector('[data-ask-pete-companion]'), s=c.querySelector('.ask-pete-evidence-companion__scroll');
        return document.querySelector('[data-sage-mist]').dataset.sageTight==='true' && c.dataset.sagePlacement==='rail'
            && c.dataset.askPetePhase==='answered' && s.clientHeight<260;
    }"""
    SHORT_RAIL_READABLE = """() => {
        const c=document.querySelector('[data-ask-pete-companion]'), s=c.querySelector('.ask-pete-evidence-companion__scroll');
        const h=c.querySelector('.sage-ai-turn:last-child .ask-pete-evidence-answer__heading');
        const p=c.querySelector('.sage-ai-turn:last-child .ask-pete-evidence-answer__summary');
        const sr=s.getBoundingClientRect(), hr=h.getBoundingClientRect(), pr=p.getBoundingClientRect();
        const input=c.querySelector('[data-ask-pete-input]'), ir=input.getBoundingClientRect();
        return {transcript:s.clientHeight, headingInside:hr.top>=sr.top-1 && hr.bottom<=sr.bottom+1,
            summaryVisible:Math.min(pr.bottom,sr.bottom)-Math.max(pr.top,sr.top),
            inputVisible:ir.top>=0 && ir.bottom<=innerHeight, draftClipped:input.scrollHeight>input.clientHeight+1};
    }"""

    def settle_short_rail(self):
        self.page.wait_for_function(self.SHORT_RAIL_SETTLED)
        self.page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

    def assert_short_rail_readable(self):
        result = self.page.evaluate(self.SHORT_RAIL_READABLE)
        self.assertGreaterEqual(result['transcript'], 100, result)
        self.assertTrue(result['headingInside'], result)
        self.assertGreaterEqual(result['summaryVisible'], 40, result)  # At least two lines of the answer itself.
        self.assertTrue(result['inputVisible'], result)
        self.assertFalse(result['draftClipped'], result)

    def test_short_rail_keeps_current_answer_readable_after_resize(self):
        self.open()
        self.respond()
        self.page.locator('[data-ask-pete-input]').fill('Unsaved follow-up draft')
        self.away(1440)
        for width in (1024, 1280):
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': 500})
                self.settle_short_rail()
                self.assert_short_rail_readable()
                self.assert_geometry()
                self.assertEqual(self.page.locator('[data-ask-pete-input]').input_value(), 'Unsaved follow-up draft')
                status = self.page.locator('[data-ask-pete-status]')
                self.assertIn('Answer ready', status.text_content())
                self.assertEqual(status.get_attribute('aria-live'), 'polite')
                self.assertEqual(self.page.locator('[data-ask-pete-input]').get_attribute('aria-describedby'), 'ask-pete-evidence-help')
        self.page.set_viewport_size({'width': 1440, 'height': 900})
        self.page.wait_for_function("document.querySelector('[data-sage-mist]').dataset.sageTight === 'false'")
        self.assert_geometry()
        self.assertTrue(self.page.locator('#ask-pete-evidence-help').is_visible())
        self.assertEqual(self.page.locator('[data-ask-pete-input]').input_value(), 'Unsaved follow-up draft')

    def test_short_rail_opened_directly_shows_answer_asked_there(self):
        self.open(1024, 500)
        self.away(1024)
        self.respond()
        self.settle_short_rail()
        self.assert_short_rail_readable()
        self.assert_geometry()

    def test_short_rail_respects_reader_viewing_earlier_messages(self):
        self.open()
        self.page.route('**/api/chat', lambda route: route.fulfill(status=200, json=answer_fixture()))
        for count, question in enumerate(('First question', 'Second question'), start=1):
            self.page.locator('[data-ask-pete-input]').fill(question)
            self.page.locator('[data-ask-pete-form] [data-ask-pete-submit]').click()
            self.page.wait_for_function(f"document.querySelectorAll('.sage-ai-turn').length === {count}")
        self.away(1440)
        # The reader scrolls the transcript themselves to keep reading the first answer.
        first_turn = self.page.locator('.sage-ai-turn').first
        first_turn.locator('.ask-pete-evidence-answer__summary').hover()  # Waits for the relocated rail to be stable.
        scroll = "document.querySelector('[data-ask-pete-companion] .ask-pete-evidence-companion__scroll')"
        before = self.page.evaluate(f"{scroll}.scrollTop")
        self.page.mouse.wheel(0, 120)  # Returns before the browser scrolls; wait for the wheel itself.
        self.page.wait_for_function(f"{scroll}.scrollTop > {before} + 1")
        self.page.set_viewport_size({'width': 1024, 'height': 500})
        self.settle_short_rail()
        visible = self.page.evaluate("""() => {
            const s=document.querySelector('[data-ask-pete-companion] .ask-pete-evidence-companion__scroll').getBoundingClientRect();
            const [first, latest]=[...document.querySelectorAll('.sage-ai-turn')].map(t=>t.getBoundingClientRect());
            return {first: Math.min(first.bottom,s.bottom)-Math.max(first.top,s.top), latestTop: latest.top-s.top};
        }""")
        self.assertGreater(visible['first'], 40, visible)  # Still reading the first answer...
        self.assertGreater(visible['latestTop'], 40, visible)  # ...not pulled to the latest one.
        self.page.unroute('**/api/chat')

    def test_draft_transcript_focus_and_historical_sources_survive_relocation(self):
        self.open()
        seen = []
        def response(route):
            seen.append(route.request.post_data_json)
            route.fulfill(status=200, json=answer_fixture('northrop' if len(seen)==1 else 'l3harris'))
        self.page.route('**/api/chat', response)
        self.page.locator('[data-ask-pete-input]').fill('First question')
        self.page.locator('[data-ask-pete-form] [data-ask-pete-submit]').click()
        self.page.wait_for_selector('.sage-ai-turn')
        self.page.locator('[data-ask-pete-input]').fill('Second question')
        self.page.locator('[data-ask-pete-form] [data-ask-pete-submit]').click()
        self.page.wait_for_function("document.querySelectorAll('.sage-ai-turn').length === 2")
        self.assertEqual(self.page.locator('[data-ask-pete-back]').count(), 0)
        self.assertIn('follow-up', self.page.locator('[data-ask-pete-form] > label').inner_text())
        self.page.locator('[data-ask-pete-input]').fill('Unsaved draft')
        self.away(1440)
        self.page.set_viewport_size({'width':390,'height':844})
        self.page.wait_for_function("document.querySelector('[data-ask-pete-companion]').dataset.sagePlacement === 'sheet'")
        self.assertEqual(self.page.locator('[data-ask-pete-input]').input_value(), 'Unsaved draft')
        self.assertEqual(self.page.locator('.sage-ai-turn').count(), 2)
        self.page.locator('[data-ask-pete-close]').click()
        self.assertTrue(self.page.locator('[data-ask-pete-companion]').is_hidden())
        self.page.locator('.sage-ai-bubble').click()
        self.assert_geometry()
        self.page.set_viewport_size({'width':1440,'height':900})
        self.page.wait_for_function("document.querySelector('[data-ask-pete-companion]').dataset.sagePlacement === 'rail'")
        # Earlier evidence must use its own payload, not the latest answer's sources.
        self.page.locator('.sage-ai-turn').first.locator('[data-ask-pete-fold-toggle]').click()
        self.page.locator('.sage-ai-turn').first.locator('[data-ask-pete-show-all]').click()
        self.page.wait_for_function("document.getElementById('r2-exp-card-northrop').classList.contains('ask-pete-evidence-highlight')")
        self.assertTrue(self.page.locator('#r2-exp-card-northrop').evaluate("e=>e.classList.contains('ask-pete-evidence-highlight')"))
        self.assertFalse(self.page.locator('#r2-exp-card-l3harris').evaluate("e=>e.classList.contains('ask-pete-evidence-highlight')"))
        for request in seen:
            self.assertEqual(set(request), {'message','action','context_key'})

    def test_optional_groups_long_copy_and_balanced_skill_counts(self):
        with patch.object(app_module, 'build_public_overview_projection', return_value=sparse_projection()):
            self.open(390,844)
        self.assertEqual(self.page.locator('.overview-story').count(), 0)
        self.assertEqual(self.page.locator('.overview-hero-media').count(), 0)
        groups=self.page.locator('.overview-credentials > section')
        self.assertEqual(groups.count(), 1)
        inner_width=self.page.locator('.overview-credentials').evaluate("e=>e.clientWidth-parseFloat(getComputedStyle(e).paddingLeft)-parseFloat(getComputedStyle(e).paddingRight)")
        self.assertAlmostEqual(groups.first.bounding_box()['width'], inner_width, delta=2)
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth>innerWidth+1'))
        for width, count in ((1440,1),(1440,15),(1440,16),(1440,17),(320,16)):
            self.open(width,900)
            # Layout-only count variants use real rendered button nodes, without changing public records.
            self.page.evaluate("""count=>{const c=document.querySelector('[data-r2-skill-overview]');const original=c.querySelector('[data-r2-skill-toggle]'); const nodes=Array.from({length:count},(_,i)=>{const n=original.cloneNode(true);n.dataset.r2SkillToggle='layout-only-'+i;n.removeAttribute('aria-controls');return n;});c.replaceChildren(...nodes);delete c.dataset.sageRows;window.dispatchEvent(new Event('resize'));}""", count)
            self.page.wait_for_function("document.querySelector('[data-r2-skill-overview]').dataset.sageRows !== undefined")
            rows=self.page.locator('[data-r2-skill-overview] .sage-balanced-row')
            sizes=rows.evaluate_all('rows=>rows.map(r=>r.children.length)')
            self.assertEqual(sum(sizes), count)
            self.assertLessEqual(max(sizes)-min(sizes),1)
            self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth>innerWidth+1'))
            widths=rows.evaluate_all('rows=>rows.map(r=>r.getBoundingClientRect().width)')
            self.assertLessEqual(max(widths)-min(widths),1)

    def test_keyboard_contact_navigation_impact_and_reflow(self):
        self.open(1024,500)
        button=self.page.locator('[data-sage-impact-flip]').first
        button.focus()
        button.press('Enter')
        self.assertEqual(button.get_attribute('aria-expanded'),'true')
        self.assertTrue(self.page.locator('#'+button.get_attribute('aria-controls')).is_visible())
        button.press('Space')
        self.assertEqual(button.get_attribute('aria-expanded'),'false')
        self.away(1024)
        summary=self.page.locator('[data-sage-contact] summary')
        summary.focus()
        summary.press('Enter')
        self.assertTrue(self.page.locator('[data-sage-contact]').evaluate('e=>e.open'))
        self.assert_geometry()
        summary.press('Escape')
        self.assertFalse(self.page.locator('[data-sage-contact]').evaluate('e=>e.open'))
        self.page.locator('[data-sage-section-select]').select_option('overview-career')
        self.page.wait_for_function("location.hash==='#overview-career'")
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'overview-career')
        self.open(640,450)  # 1280px desktop at 200% effective viewport.
        self.away(640)
        self.assert_geometry()

    def test_small_gold_and_experience_footer_have_aa_contrast(self):
        self.open()
        samples=self.page.evaluate("""() => {
            const rgb=s=>{const a=s.match(/[\\d.]+/g).map(Number);return [a[0],a[1],a[2],a.length>3?a[3]:1];};
            const luminance=c=>c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
            return [...document.querySelectorAll('.overview-headline,.overview-career-quote figcaption,.r2-exp-card__footer > span')].map(e=>{
                const ancestors=[];for(let n=e;n;n=n.parentElement) ancestors.unshift(n);
                let bg=[255,255,255];for(const n of ancestors){const c=rgb(getComputedStyle(n).backgroundColor);bg=bg.map((v,i)=>c[i]*c[3]+v*(1-c[3]));}
                const fg=rgb(getComputedStyle(e).color),a=luminance(fg),b=luminance(bg);
                return {text:e.textContent.trim(),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
            });
        }""")
        self.assertEqual(len(samples),5)
        for sample in samples:
            with self.subTest(text=sample['text']):
                self.assertGreaterEqual(sample['ratio'],4.5)

    def test_working_cancellation_and_honest_recovery(self):
        self.open()
        pending=[]
        self.page.route('**/api/chat', lambda route: pending.append(route))
        self.page.locator('[data-ask-pete-input]').fill('Pending question')
        self.page.locator('[data-ask-pete-form] [data-ask-pete-submit]').click()
        self.page.wait_for_function("document.querySelector('[data-ask-pete-input]').getAttribute('aria-busy')==='true'")
        self.assertNotEqual(self.page.locator('[data-ask-pete-input]').evaluate('e=>getComputedStyle(e).boxShadow'),'none')
        self.page.locator('[data-ask-pete-cancel]').click()
        self.assertEqual(self.page.locator('[data-ask-pete-input]').input_value(),'Pending question')
        self.assertEqual(self.page.locator('[data-ask-pete-input]').get_attribute('aria-busy'),'false')
        for route in pending:
            try: route.abort()
            except Exception: pass  # Browser already cancelled the request.
        self.page.unroute('**/api/chat')
        payload=answer_fixture(summary='The shared public information does not establish this experience.')
        payload.update(state='not_established',claims=[],sources_used=[],handoff={'available':True,'label':'Contact Pete directly','question':'Would you like to add context?'})
        self.respond(payload)
        self.assertIn('does not establish',self.page.locator('.sage-ai-turn').inner_text())
        self.assertEqual(self.page.locator('.ask-pete-evidence-handoff a').get_attribute('href'),'/petec/contact')
        self.page.unroute('**/api/chat')
        self.page.route('**/api/chat', lambda route: route.fulfill(status=503,json={'error':'Unavailable'}))
        self.page.locator('[data-ask-pete-input]').fill('Another question')
        self.page.locator('[data-ask-pete-form] [data-ask-pete-submit]').click()
        self.page.wait_for_selector('[data-ask-pete-recovery]:visible')
        self.assertEqual(self.page.locator('.sage-ai-turn').count(),1)
        self.assertEqual(self.page.locator('[data-ask-pete-recovery] a').count(),2)


if __name__ == '__main__':
    unittest.main()

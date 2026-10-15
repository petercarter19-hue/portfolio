"""Guide component/API integration: real local HTTP, fictional stores, no interception.

The host is a plain same-origin document, not the full Guide app bootstrap.
"""
from copy import deepcopy
from pathlib import Path
import unittest
import json
from unittest.mock import patch
from uuid import uuid4

from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
from tests.test_resume_intake_browser import CHROME_EXECUTABLE, sync_playwright
from services.resume_intake_repository import ResumeIntakeStoreUnavailable

ROOT = Path(__file__).resolve().parents[1]
OWNER = "g-member-a"


@unittest.skipUnless(sync_playwright is not None and CHROME_EXECUTABLE,
                     "Playwright and Chrome are required for real Guide API proof")
class GuidePanelBrowserTests(unittest.TestCase):
    def test_opt_in_record_stop_transcribes_through_the_existing_owner_transport(self):
        from app import app
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}):
            context=self.browser.new_context(permissions=['microphone'])
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page=context.new_page()
            page.goto(self.server.url+'/app/resume')
            page.locator('#resume-intake-reopen').click()
            page.get_by_role('button',name='Type or paste',exact=True).click()
            page.wait_for_function("()=>!document.querySelector('.ps-guide-compose-send').closest('.ps-guide-compose-box').getAttribute('aria-busy') || document.querySelector('.ps-guide-compose-box').getAttribute('aria-busy')==='false'")
            page.locator('#resume-intake-text').fill('Newer fictional words before transcription. ')
            page.get_by_role('button',name='Record a message',exact=True).click()
            page.wait_for_function("()=>document.getElementById('resume-intake-mic').getAttribute('aria-pressed')==='true'")
            self.assertEqual(page.locator('.ps-guide-compose-talk').get_attribute('aria-label'),'Stop recording')
            self.assertEqual(page.locator('.ps-guide-compose-talk').get_attribute('aria-pressed'),'true')
            page.wait_for_timeout(350)
            page.get_by_role('button',name='Stop recording',exact=True).click()
            page.wait_for_function("()=>document.getElementById('resume-intake-text').value.includes('Synthetic spoken contribution about planning.')")
            self.assertTrue(page.locator('#resume-intake-text').input_value().startswith('Newer fictional words before transcription.'))
            self.assertEqual(page.locator('.ps-guide-compose-talk').get_attribute('aria-label'),'Record a message')
            self.assertEqual(len(self.server.transcriber.calls),1)
            self.assertEqual(self.server.shared.canonical.list_items(OWNER),[])
            self.assertTrue(all(set(row)=={'text','filenames'} for row in page.evaluate("()=>Object.keys(sessionStorage).filter(k=>k.startsWith('peerslate.guide.unsent.')).map(k=>JSON.parse(sessionStorage.getItem(k)))")))

    def test_opt_in_visual_zoom_keeps_the_dialog_inside_the_visible_viewport(self):
        from app import app
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}):
            context=self.browser.new_context(viewport={'width':1440,'height':1000})
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page=context.new_page()
            page.goto(self.server.url+'/app/resume')
            page.locator('#resume-intake-reopen').click()
            page.get_by_role('button',name='Type or paste',exact=True).wait_for()
            cdp=context.new_cdp_session(page)
            cdp.send('Emulation.setPageScaleFactor',{'pageScaleFactor':2})
            page.wait_for_timeout(100)
            measured=page.evaluate('''() => {
                const root=document.getElementById('resume-intake'),r=root.getBoundingClientRect(),v=visualViewport;
                return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,
                    x:v.offsetLeft,y:v.offsetTop,viewWidth:v.width,viewHeight:v.height,scale:v.scale};
            }''')
            self.assertEqual(measured['scale'],2)
            self.assertGreaterEqual(measured['left'],measured['x']-1,measured)
            self.assertLessEqual(measured['right'],measured['x']+measured['viewWidth']+1,measured)
            self.assertGreaterEqual(measured['top'],measured['y']-1,measured)
            self.assertLessEqual(measured['bottom'],measured['y']+measured['viewHeight']+1,measured)
            cdp.send('Emulation.setPageScaleFactor',{'pageScaleFactor':1})
            page.wait_for_function("() => document.getElementById('resume-intake').dataset.guideSheet==='false'")

    def test_opt_in_app_geometry_reflows_at_phone_short_window_and_double_text_size(self):
        from app import app
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}):
            for width,height,double in ((1440,1000,False),(390,844,False),(1200,420,False),(1440,1000,True)):
                with self.subTest(width=width,height=height,double=double):
                    context=self.browser.new_context(viewport={'width':width,'height':height})
                    self.addCleanup(context.close)
                    context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
                    page=context.new_page()
                    page.goto(self.server.url+'/app/resume')
                    page.locator('#resume-intake-reopen').click()
                    page.get_by_role('button',name='Type or paste',exact=True).wait_for()
                    if double:
                        page.evaluate('''() => {
                            const root=document.getElementById('resume-intake');
                            const nodes=[root,...root.querySelectorAll('h2,h3,p,b,button,span,textarea')];
                            const styles=nodes.map(node=>[node,parseFloat(getComputedStyle(node).fontSize),parseFloat(getComputedStyle(node).lineHeight)]);
                            styles.forEach(([node,font,line])=>{node.style.fontSize=(font*2)+'px';if(Number.isFinite(line))node.style.lineHeight=(line*2)+'px';});
                        }''')
                    page.wait_for_timeout(100)
                    measured=page.evaluate('''() => {
                        const root=document.getElementById('resume-intake'), rect=root.getBoundingClientRect();
                        const clipped=[...root.querySelectorAll('button,textarea')].filter(node=>node.getClientRects().length&&
                            (node.getBoundingClientRect().left<rect.left-1||node.getBoundingClientRect().right>rect.right+1));
                        return {left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom,width:rect.width,
                            sheet:root.dataset.guideSheet,bodyScroll:root.dataset.guideBodyScroll,
                            clipped:clipped.map(node=>node.getAttribute('aria-label')||node.textContent)};
                    }''')
                    self.assertGreaterEqual(measured['left'],-1,measured)
                    self.assertLessEqual(measured['right'],width+1,measured)
                    self.assertGreaterEqual(measured['top'],-1,measured)
                    self.assertLessEqual(measured['bottom'],height+1,measured)
                    self.assertEqual(measured['clipped'],[],measured)
                    if width<960:
                        self.assertEqual(measured['sheet'],'true')
                        self.assertAlmostEqual(measured['width'],width,delta=1)
                    if height<480:
                        self.assertEqual(measured['bodyScroll'],'true')

    def test_opt_in_delayed_upload_shows_actual_busy_state_and_keeps_newer_words_and_files(self):
        import threading
        from app import app
        from services.resume_intake_service import ResumeIntakeService
        from services.resume_intake_repository import InMemoryResumeIntakeRepository
        from services.resume_intake_policy import selected_policy_for_tests
        from services.resume_guide_service import ResumeGuideService
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter
        from tests.test_my_data_intake_sources import extracted_pipeline
        text='Experience\nEngineer at Fictional Orchard\n'
        entered,released=threading.Event(),threading.Event()
        self.addCleanup(released.set)
        adapter=DeterministicFakeExtractionAdapter([{'record_type':'role',
            'values':{'role_title':'Engineer','employer_name':'Fictional Orchard'},
            'quote':'Engineer at Fictional Orchard','outcome':'new','confidence':'certain'}])
        original=adapter._provider
        def delayed(request,**kwargs):
            entered.set()
            if not released.wait(10):
                raise RuntimeError('bounded fake organizer timeout')
            return original(request,**kwargs)
        adapter._provider=delayed
        service=ResumeIntakeService(repository=InMemoryResumeIntakeRepository(),draft_service=self.server.shared.draft,
            policy=selected_policy_for_tests(),document_pipeline=extracted_pipeline(text),extraction_adapter=adapter)
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True,'RESUME_INTAKE_SERVICE':service,
                'RESUME_GUIDE_SERVICE':ResumeGuideService(repository=service.repository)}):
            context=self.browser.new_context()
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page=context.new_page()
            page.goto(self.server.url+'/app/resume')
            page.locator('#resume-intake-reopen').click()
            requests=[]
            page.on('request',lambda request: requests.append(request.url) if request.method=='POST' else None)
            sent=[]
            real_submit=service.submit
            def observed_submit(member,payload,**kwargs):
                sent.append(payload.get('source_only'))
                return real_submit(member,payload,**kwargs)
            service.submit=observed_submit
            page.locator('#resume-intake-file').set_input_files({'name':'first-fictional.txt','mimeType':'text/plain','buffer':text.encode()})
            page.locator('.ps-guide-compose-send').click()
            self.assertTrue(entered.wait(5))
            page.wait_for_selector('.ps-guide-progress-current')
            self.assertEqual(page.locator('.ps-guide-body .ps-guide-screen-heading').inner_text(),'Organizing your file…')
            self.assertTrue(page.locator('.ps-guide-starters').is_hidden())
            # Approved two-step send (96c4fd1): a real receipt saved the file before organizing began.
            page.locator('.ps-guide-progress-done').filter(has_text='Your file is saved privately').wait_for()
            self.assertEqual(page.locator('.ps-guide-file-chip').filter(has_text='first-fictional.txt').count(),0)
            self.assertEqual(sent,[True],'One file alone is sent store-and-read only')
            self.assertEqual(sum(1 for url in requests if url.endswith('/api/resume-intake/me/sources/organize')),1)
            self.assertNotIn('Send them',page.locator('.ps-guide-composer').inner_text())
            page.locator('#resume-intake-text').fill('New exact words typed during organizing.')
            page.locator('#resume-intake-file').set_input_files({'name':'second-fictional.txt','mimeType':'text/plain',
                'buffer':b'New file, never sent with the first request.'})
            second=page.locator('.ps-guide-file-chip').filter(has_text='second-fictional.txt')
            self.assertIn('not sent yet',second.inner_text())
            released.set()
            page.wait_for_function("() => !document.querySelector('.ps-guide-progress-current')")
            self.assertEqual(page.locator('#resume-intake-text').input_value(),'New exact words typed during organizing.')
            self.assertEqual(page.locator('.ps-guide-file-chip').count(),1)
            self.assertIn('second-fictional.txt',page.locator('.ps-guide-file-chip').inner_text())
            self.assertEqual(len(adapter.calls),1)
            self.assertEqual(self.server.shared.canonical.list_items(OWNER),[])
            stored=next(iter(service.repository._owners.values()))
            self.assertEqual(sum(1 for row in stored['sources'].values() if row['kind']=='document'),1)

    def _two_step_service(self, *, busy_organize_once=False):
        import threading
        from services.resume_intake_service import ResumeIntakeService, ResumeIntakeBusyError
        from services.resume_intake_repository import InMemoryResumeIntakeRepository
        from services.resume_intake_policy import selected_policy_for_tests
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter
        from tests.test_my_data_intake_sources import extracted_pipeline
        text = 'Experience\nEngineer at Fictional Orchard\n'
        adapter = DeterministicFakeExtractionAdapter([{'record_type': 'role',
            'values': {'role_title': 'Engineer', 'employer_name': 'Fictional Orchard'},
            'quote': 'Engineer at Fictional Orchard', 'outcome': 'new', 'confidence': 'certain'}])
        service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(), draft_service=self.server.shared.draft,
            policy=selected_policy_for_tests(), document_pipeline=extracted_pipeline(text), extraction_adapter=adapter)
        organize_ids = []
        real = service.organize_source
        def organize(owner, payload, **kwargs):
            organize_ids.append(payload.get('request_id'))
            if busy_organize_once and len(organize_ids) == 1:
                raise ResumeIntakeBusyError(payload.get('request_id'))
            return real(owner, payload, **kwargs)
        service.organize_source = organize
        return service, adapter, organize_ids, text

    def _until(self, page, condition, seconds=20):
        import time
        end = time.monotonic() + seconds
        while time.monotonic() < end and not condition():
            page.wait_for_timeout(100)
        return condition()

    def _two_step_page(self, service, *, interview=False):
        from app import app
        from services.resume_guide_service import ResumeGuideService
        stack = patch.dict(app.config, {'PEERSLATE_GUIDE_REBUILD_ENABLED': True, 'RESUME_INTAKE_SERVICE': service,
            'RESUME_GUIDE_SERVICE': ResumeGuideService(repository=service.repository),
            'PEERSLATE_RESUME_INTERVIEW_ENABLED': interview})
        stack.start(); self.addCleanup(stack.stop)
        context = self.browser.new_context()
        self.addCleanup(context.close)
        context.add_cookies([{'name': 'mvp1-synthetic-owner', 'value': OWNER, 'url': self.server.url}])
        page = context.new_page()
        page.goto(self.server.url + '/app/resume')
        page.locator('#resume-intake-reopen').click()
        return context, page

    def test_opt_in_busy_organize_reply_keeps_the_same_request_and_organizes_once(self):
        service, adapter, organize_ids, text = self._two_step_service(busy_organize_once=True)
        _context, page = self._two_step_page(service)
        page.locator('#resume-intake-file').set_input_files({'name': 'busy-fictional.txt', 'mimeType': 'text/plain',
            'buffer': text.encode()})
        page.locator('.ps-guide-compose-send').click()
        self.assertTrue(self._until(page, lambda: len(adapter.calls) == 1 and len(organize_ids) >= 2),
                        (organize_ids, len(adapter.calls)))
        page.wait_for_timeout(500)
        self.assertGreaterEqual(len(organize_ids), 2)
        self.assertEqual(len(set(organize_ids)), 1, 'A busy reply must keep and retry the same organize request id')
        self.assertEqual(len(adapter.calls), 1)

    def test_opt_in_words_and_a_file_are_sent_one_at_a_time_and_nothing_is_sent_by_itself(self):
        import threading
        service, adapter, organize_ids, text = self._two_step_service()
        entered, released = threading.Event(), threading.Event()
        self.addCleanup(released.set)
        provider = adapter._provider
        def held(request, **kwargs):
            entered.set(); released.wait(30)
            return provider(request, **kwargs)
        adapter._provider = held
        _context, page = self._two_step_page(service, interview=True)
        posts = []
        page.on('request', lambda request: posts.append(request.url.rsplit('/api/', 1)[-1])
                if request.method == 'POST' and '/api/' in request.url else None)
        page.locator('#resume-intake-file').set_input_files({'name': 'words-fictional.txt', 'mimeType': 'text/plain',
            'buffer': text.encode()})
        page.locator('#resume-intake-text').fill('I also mentored two fictional interns.')
        send = page.locator('.ps-guide-compose-send')
        self.assertTrue(send.is_disabled())
        self.assertEqual(page.locator('.ps-guide-compose-notice').inner_text(), 'Send the file first, then your message.')
        page.locator('#resume-intake-text').press('Enter')
        page.wait_for_timeout(400)
        self.assertFalse([url for url in posts if url.startswith(('resume-intake/me/submissions', 'resume-interview/me/turn'))])
        # The file goes by itself. Words typed or edited while it organizes are never sent by themselves.
        page.locator('#resume-intake-text').fill('')
        send.click()
        self.assertTrue(entered.wait(10))
        page.locator('#resume-intake-text').fill('EDITED during organizing, never sent.')
        released.set()
        self.assertTrue(self._until(page, lambda: len(adapter.calls) == 1))
        page.wait_for_function("() => !document.querySelector('.ps-guide-progress-current')", timeout=20000)
        page.wait_for_timeout(1500)
        self.assertFalse([url for url in posts if url.startswith('resume-interview/me/turn')], posts)
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'EDITED during organizing, never sent.')

    def test_opt_in_a_message_over_the_limit_is_kept_whole_and_cannot_be_sent(self):
        service, adapter, organize_ids, text = self._two_step_service()
        _context, page = self._two_step_page(service, interview=True)
        page.wait_for_function("() => document.querySelector('.ps-guide-body') && "
                               "document.querySelector('.ps-guide-body').dataset.guideView !== 'unavailable'")
        page.locator('#resume-intake-text').fill('x' * 20001)
        self.assertEqual(len(page.locator('#resume-intake-text').input_value()), 20001, 'Nothing is cut')
        self.assertEqual(page.locator('.ps-guide-compose-notice').inner_text(),
                         'That’s longer than I can take in one message. Send it in parts, or attach it as a file.')
        self.assertTrue(page.locator('.ps-guide-compose-send').is_disabled())
        page.locator('#resume-intake-text').fill('x' * 20000)
        self.assertTrue(page.locator('.ps-guide-compose-notice').is_hidden())
        self.assertTrue(page.locator('.ps-guide-compose-send').is_enabled())

    def test_opt_in_the_phone_header_shortens_to_guide_without_an_ellipsis(self):
        from app import app
        with patch.dict(app.config, {'PEERSLATE_GUIDE_REBUILD_ENABLED': True}):
            for width, short in ((390, True), (1440, False)):
                with self.subTest(width=width):
                    context = self.browser.new_context(viewport={'width': width, 'height': 844})
                    self.addCleanup(context.close)
                    context.add_cookies([{'name': 'mvp1-synthetic-owner', 'value': OWNER, 'url': self.server.url}])
                    page = context.new_page(); page.goto(self.server.url + '/app/resume')
                    page.locator('#resume-intake-reopen').click()
                    page.wait_for_function("() => document.querySelector('.ps-guide-body') && "
                                           "document.querySelector('.ps-guide-body').dataset.guideView !== 'unavailable'")
                    page.wait_for_timeout(300)
                    title = page.locator('.ps-guide-title')
                    self.assertEqual(title.evaluate("(node) => node.classList.contains('is-short')"), short)
                    self.assertTrue(title.evaluate('(node) => node.scrollWidth <= node.clientWidth + 0.5'), 'No clipped title')
                    self.assertEqual(title.evaluate('(node) => getComputedStyle(node).textOverflow'), 'clip')
                    self.assertEqual(page.get_by_role('heading', name='PeerSlate Guide', exact=True).count(), 1)

    def test_opt_in_the_message_box_shows_the_guide_focus_ring_not_the_page_ring(self):
        service, adapter, organize_ids, text = self._two_step_service()
        _context, page = self._two_step_page(service, interview=True)
        page.wait_for_function("() => document.querySelector('.ps-guide-body') && "
                               "document.querySelector('.ps-guide-body').dataset.guideView !== 'unavailable'")
        page.locator('#resume-intake-text').focus()
        page.keyboard.type('Fictional words.')
        focus = page.evaluate("""() => { const field = document.getElementById('resume-intake-text');
            const box = field.closest('.ps-guide-compose-box'); const f = getComputedStyle(field), b = getComputedStyle(box);
            return {fieldOutline: f.outlineStyle, fieldWidth: f.outlineWidth, box: b.boxShadow}; }""")
        self.assertEqual(focus['fieldOutline'], 'none', focus)
        self.assertIn('rgb(21, 67, 42) 0px 0px 0px 2px', focus['box'], focus)
        # The notice above the box keeps the box's inset, never the window edge.
        page.locator('#resume-intake-text').fill('x' * 20001)
        inset = page.evaluate("""() => { const n = document.querySelector('.ps-guide-compose-notice').getBoundingClientRect();
            const box = document.querySelector('.ps-guide-compose-box').getBoundingClientRect();
            const win = document.getElementById('resume-intake').getBoundingClientRect();
            return {notice: n.left - win.left, box: box.left - win.left}; }""")
        self.assertGreaterEqual(inset['notice'], 24, inset)

    def test_opt_in_a_reload_names_only_what_was_lost(self):
        service, adapter, organize_ids, text = self._two_step_service()
        _context, page = self._two_step_page(service, interview=True)
        page.wait_for_function("() => document.querySelector('.ps-guide-body') && "
                               "document.querySelector('.ps-guide-body').dataset.guideView !== 'unavailable'")
        page.locator('#resume-intake-text').fill('Fictional words kept in this tab.')
        page.reload(); page.locator('#resume-intake-reopen').click()
        note = page.locator('.ps-guide-composer .resume-intake__hint')
        note.wait_for()
        self.assertEqual(note.inner_text(), 'Your message is back, not sent.')

    def test_opt_in_a_file_on_its_way_is_never_called_unsent_or_offered_again(self):
        import threading
        service, adapter, organize_ids, text = self._two_step_service()
        entered, released = threading.Event(), threading.Event()
        real_submit = service.submit
        def held_submit(member, payload, **kwargs):
            entered.set(); released.wait(30)
            return real_submit(member, payload, **kwargs)
        service.submit = held_submit
        self.addCleanup(released.set)
        _context, page = self._two_step_page(service)
        page.locator('#resume-intake-file').set_input_files({'name': 'on-its-way.txt', 'mimeType': 'text/plain',
            'buffer': text.encode()})
        page.locator('.ps-guide-compose-send').click()
        self.assertTrue(entered.wait(10))
        page.wait_for_selector('.ps-guide-progress-current')
        # The sent file leaves the box and the same-tab copy.
        self.assertEqual(page.locator('.ps-guide-file-chip').count(), 0)
        copies = page.evaluate("() => Object.keys(sessionStorage).filter(k => k.startsWith('peerslate.guide.unsent.')).map(k => sessionStorage.getItem(k))")
        self.assertFalse(any('on-its-way.txt' in (value or '') for value in copies), copies)
        # Leaving with new words lists only the words, and says organizing carries on.
        page.locator('#resume-intake-text').fill('Fictional words typed while the file is on its way.')
        page.get_by_role('button', name='Finish for now', exact=True).click()
        leave = page.locator('.ps-guide-leave-list')
        leave.wait_for()
        self.assertNotIn('on-its-way.txt', leave.inner_text())
        self.assertIn('Your message', leave.inner_text())
        self.assertIn('Organizing carries on without you.', page.locator('.ps-guide-body').inner_text())
        page.get_by_role('button', name='Stay', exact=True).click()
        # A reload while the file is on its way never offers it to choose again.
        page.reload(); page.locator('#resume-intake-reopen').click()
        page.wait_for_function("()=>document.querySelector('.ps-guide-body') && document.querySelector('.ps-guide-body').dataset.guideView!=='unavailable'")
        self.assertEqual(page.locator('.ps-guide-file-chip').filter(has_text='on-its-way.txt').count(), 0)
        self.assertNotIn('choose the file again', page.locator('#resume-intake').inner_text())
        released.set()
        # The stored file is organized exactly once when the Guide next loads.
        self.assertTrue(self._until(page, lambda: page.evaluate(
            "async () => { const r = await fetch('/api/resume-intake/me'); const d = await r.json();"
            " return ((d.review_overview||{}).batch||{}).organization ? d.review_overview.batch.organization.state : null; }") == 'not_started'))
        page.locator('.ps-guide-window-button[aria-label="Minimize the Guide"]').click()
        if page.get_by_role('button', name='Leave anyway', exact=True).count():
            page.get_by_role('button', name='Stay', exact=True).click()
            page.locator('#resume-intake-text').fill('')
            page.locator('.ps-guide-window-button[aria-label="Minimize the Guide"]').click()
        page.locator('#resume-intake-reopen').click()
        self.assertTrue(self._until(page, lambda: len(adapter.calls) >= 1))
        page.wait_for_timeout(1500)
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(len(set(organize_ids)), 1)

    def test_opt_in_reload_with_a_stored_file_waiting_organizes_it_once(self):
        service, adapter, organize_ids, text = self._two_step_service()
        _context, page = self._two_step_page(service)
        page.wait_for_timeout(300)
        status = page.evaluate("""async (text) => {
            const form = new FormData();
            form.append('request', JSON.stringify({request_id: crypto.randomUUID(), source_only: true,
                attachments: [{client_key: 'document', kind: 'document', declared_content_type: 'text/plain',
                               filename: 'waiting-fictional.txt'}]}));
            form.append('file:document', new Blob([text], {type: 'text/plain'}), 'waiting-fictional.txt');
            const response = await fetch('/api/resume-intake/me/submissions', {method: 'POST', body: form,
                headers: {'X-PeerSlate-Request': 'same-origin'}});
            return response.status;
        }""", text)
        self.assertEqual(status, 200)
        self.assertEqual(len(adapter.calls), 0, 'The stored-first send dispatches nothing')
        page.reload(); page.locator('#resume-intake-reopen').wait_for()
        self._until(page, lambda: len(adapter.calls) >= 1)
        page.wait_for_timeout(1500)
        self.assertEqual(len(adapter.calls), 1, 'A stored file waiting is organized exactly once after the reload')
        self.assertEqual(len(organize_ids), 1)

    def test_opt_in_browser_session_keeps_only_unsent_words_and_filenames_and_clears_for_another_member(self):
        from app import app
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}), patch.object(
                self.server.intake.repository,'load_owner',side_effect=ResumeIntakeStoreUnavailable('fictional unavailable')):
            context = self.browser.new_context()
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page = context.new_page()
            page.goto(self.server.url+'/app/resume')
            page.locator('#resume-intake-reopen').click()
            words='Exact fictional words recoverable when the server is unavailable.'
            page.locator('#resume-intake-text').fill(words)
            page.locator('#resume-intake-file').set_input_files({'name':'fictional-backup.txt','mimeType':'text/plain',
                'buffer':b'File bytes must never enter browser storage.'})
            page.reload()
            page.locator('#resume-intake-reopen').click()
            page.wait_for_function("text => document.getElementById('resume-intake-text').value===text",arg=words)
            self.assertIn('fictional-backup.txt',page.locator('.ps-guide-file-chip').inner_text())
            self.assertIn('choose the file again',page.locator('.ps-guide-file-chip').inner_text())
            copies=page.evaluate("() => Object.keys(sessionStorage).filter(k=>k.startsWith('peerslate.guide.unsent.')).map(k=>JSON.parse(sessionStorage.getItem(k)))")
            self.assertEqual(copies,[{'text':words,'filenames':['fictional-backup.txt']}])
            context.clear_cookies()
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':'g-member-b','url':self.server.url}])
            page.goto(self.server.url+'/app/resume')
            page.locator('#resume-intake-reopen').click()
            self.assertEqual(page.locator('#resume-intake-text').input_value(),'')
            self.assertEqual(page.locator('.ps-guide-file-chip').count(),0)
            self.assertEqual(page.evaluate("() => Object.keys(sessionStorage).filter(k=>k.startsWith('peerslate.guide.unsent.')).length"),0)

    def test_opt_in_failed_workspace_load_keeps_words_and_refuses_a_raw_extraction_fallback(self):
        from app import app
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}):
            context = self.browser.new_context()
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page = context.new_page()
            writes=[]
            page.on('request',lambda request:writes.append(request.url) if request.method=='POST' else None)
            with patch.object(self.server.intake.repository,'load_owner',side_effect=ResumeIntakeStoreUnavailable('fictional unavailable')):
                page.goto(self.server.url+'/app/resume')
                page.locator('#resume-intake-reopen').click()
                page.wait_for_selector('.ps-guide-body [role="status"]')
                page.locator('#resume-intake-text').fill('Exact fictional words while loading failed.')
                self.assertTrue(page.locator('.ps-guide-compose-send').is_disabled())
                page.evaluate("() => document.getElementById('resume-intake-composer').dispatchEvent(new Event('submit',{cancelable:true}))")
                self.assertEqual(page.locator('#resume-intake-text').input_value(),'Exact fictional words while loading failed.')
                self.assertFalse(any('/submissions' in url or '/interview' in url for url in writes))
                # Start Retry while the failure still holds. The incumbent's
                # bounded GET retry may recover immediately once it clears.
                page.locator('.ps-guide-body').get_by_role('button',name='Retry',exact=True).click()
            page.wait_for_function("() => !document.querySelector('.ps-guide-compose-send').disabled")
            self.assertEqual(page.locator('#resume-intake-text').input_value(),'Exact fictional words while loading failed.')
            self.assertEqual(self.server.shared.canonical.list_items(OWNER),[])

    def test_opt_in_finish_asks_first_and_never_checkpoints_unsent_box_words(self):
        from app import app
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}):
            context = self.browser.new_context()
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page = context.new_page()
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(self.server.url+'/app/resume')
            page.locator('#resume-intake-reopen').click()
            page.get_by_role('button',name='Type or paste',exact=True).click()
            words='Exact fictional words kept only in this tab.'
            page.locator('#resume-intake-text').fill(words)
            page.get_by_role('button',name='Finish for now',exact=True).click()
            page.get_by_role('button',name='Stay',exact=True).click()
            self.assertTrue(page.locator('#resume-intake').evaluate('(node)=>node.open'))
            self.assertEqual(page.locator('#resume-intake-text').input_value(),words)
            page.get_by_role('button',name='Finish for now',exact=True).click()
            page.get_by_role('button',name='Leave anyway',exact=True).click()
            page.wait_for_function("() => !document.getElementById('resume-intake').open")
            page.wait_for_function("async () => (await (await fetch('/api/resume-intake/me/guide')).json()).status==='paused'")
            draft=self.server.intake.get_draft(OWNER)['draft']
            self.assertNotIn(words,str(draft))
            self.assertEqual(self.server.shared.canonical.list_items(OWNER),[])
            page.reload()
            page.locator('#resume-intake-reopen').click()
            page.wait_for_function("() => document.getElementById('resume-intake-text').value === ''")
            self.assertEqual(page.evaluate("()=>Object.keys(sessionStorage).filter(k=>k.startsWith('peerslate.guide.unsent.')).length"),0)
            self.assertTrue(page.locator('.ps-guide-composer #resume-intake-text').is_visible())
            self.assertEqual(errors,[])

    def test_opt_in_preserves_older_server_box_draft_but_does_not_restore_it_into_a_new_tab(self):
        from app import app
        old_words='Historical private server draft, preserve exactly.'
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}):
            context=self.browser.new_context()
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page=context.new_page()
            page.goto(self.server.url+'/app/resume')
            # Seed through the real legacy draft contract, before R6q reads it.
            result=page.evaluate('''async words => {
                const existing=(await (await fetch('/api/resume-intake/me/draft')).json()).draft;
                return await (await fetch('/api/resume-intake/me/draft',{method:'PUT',headers:{'Content-Type':'application/json','X-PeerSlate-Request':'same-origin'},
                    body:JSON.stringify({request_id:crypto.randomUUID(),expected_version:existing?existing.version:null,
                        text:words,items:[],attachments:[{client_key:'historical-file',kind:'document',
                            filename:'historical-private.txt',declared_content_type:'text/plain'}]})})).json();
            }''',old_words)
            self.assertEqual(result['draft']['text'],old_words)
            page.reload()
            page.locator('#resume-intake-reopen').click()
            self.assertEqual(page.locator('#resume-intake-text').input_value(),'')
            page.locator('#resume-intake-text').fill('New transient words must never reach server autosave.')
            page.wait_for_timeout(1800)
            self.assertEqual(self.server.intake.get_draft(OWNER)['draft']['text'],old_words)
            self.assertEqual(self.server.intake.get_draft(OWNER)['draft']['attachments'][0]['filename'],'historical-private.txt')
            self.assertNotIn('New transient words',str(self.server.intake.get_draft(OWNER)))
            other=context.new_page()
            other.goto(self.server.url+'/app/resume')
            other.locator('#resume-intake-reopen').click()
            self.assertEqual(other.locator('#resume-intake-text').input_value(),'')

    def test_opt_in_failed_pause_status_keeps_visible_retry_and_the_unsent_message(self):
        from app import app
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}):
            context=self.browser.new_context()
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page=context.new_page()
            page.goto(self.server.url+'/app/resume')
            page.locator('#resume-intake-reopen').click()
            page.get_by_role('button',name='Type or paste',exact=True).click()
            page.locator('#resume-intake-text').fill('Exact unsent words during a failed pause.')
            with patch.object(self.server.intake.repository,'save_owner',side_effect=ResumeIntakeStoreUnavailable('fictional save failure')):
                page.get_by_role('button',name='Finish for now',exact=True).click()
                page.get_by_role('button',name='Leave anyway',exact=True).click()
                page.locator('#resume-intake-pause-notice').wait_for(state='visible')
                self.assertIn('Pausing wasn’t recorded',page.locator('#resume-intake-pause-notice').inner_text())
                self.assertEqual(page.locator('#resume-intake-text').input_value(),'')
            page.locator('#resume-intake-pause-notice').get_by_role('button',name='Retry',exact=True).click()
            page.wait_for_function("async ()=>(await (await fetch('/api/resume-intake/me/guide')).json()).status==='paused'")
            self.assertNotIn('Exact unsent words',str(self.server.intake.get_draft(OWNER)))
            self.assertEqual(self.server.shared.canonical.list_items(OWNER),[])

    def test_opt_in_storage_failure_warns_and_sign_out_intent_clears_without_reading(self):
        from app import app
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}):
            context=self.browser.new_context()
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page=context.new_page()
            page.goto(self.server.url+'/app/resume')
            page.locator('#resume-intake-reopen').click()
            page.locator('#resume-intake-text').fill('Fictional words before sign out.')
            self.assertEqual(page.evaluate("()=>Object.keys(sessionStorage).filter(k=>k.startsWith('peerslate.guide.unsent.')).length"),1)
            # Exercise the actual capture-phase sign-out hook without signing
            # a real account out or calling the identity provider.
            page.evaluate('''() => {
                const form=document.createElement('form');form.action='/auth/sign-out';form.method='post';
                form.addEventListener('submit',event=>event.preventDefault());
                document.getElementById('resume-intake').appendChild(form);
                const read=Storage.prototype.getItem;
                Storage.prototype.getItem=function(key){if(key.startsWith('peerslate.guide.unsent.'))throw new Error('must not read');return read.call(this,key);};
                form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
                document.getElementById('resume-intake-text').dispatchEvent(new Event('input',{bubbles:true}));
            }''')
            self.assertEqual(page.evaluate("()=>Object.keys(sessionStorage).filter(k=>k.startsWith('peerslate.guide.unsent.')).length"),0)
            blocked=self.browser.new_context()
            self.addCleanup(blocked.close)
            blocked.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            blocked.add_init_script("Storage.prototype.setItem=function(){throw new DOMException('fictional storage unavailable','QuotaExceededError');}")
            failed=blocked.new_page()
            failed.goto(self.server.url+'/app/resume')
            failed.locator('#resume-intake-reopen').click()
            failed.locator('#resume-intake-text').fill('Fictional unsent words when storage is unavailable.')
            self.assertIn('this browser can’t keep a copy',failed.locator('.ps-guide-composer .resume-intake__hint').inner_text())
            self.assertTrue(failed.get_by_role('button',name='Discard the message',exact=True).is_hidden())

    def test_opt_in_file_attachment_and_remove_use_the_incumbent_unsent_file_state(self):
        from app import app
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}):
            context = self.browser.new_context()
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page = context.new_page()
            writes=[]
            page.on('request',lambda request:writes.append(request.url) if request.method=='POST' else None)
            page.goto(self.server.url+'/app/resume')
            page.locator('#resume-intake-reopen').click()
            page.locator('#resume-intake-file').set_input_files({'name':'fictional-notes.txt','mimeType':'text/plain',
                'buffer':b'Fictional notes, still unsent.'})
            page.wait_for_selector('.ps-guide-file-chip')
            self.assertTrue(page.locator('.ps-guide-start-tiles').is_hidden())
            self.assertTrue(page.locator('.ps-guide-starters').is_hidden())
            self.assertEqual(page.locator('#resume-intake-text').get_attribute('placeholder'),'Add a note, or just send…')
            self.assertNotIn('choose Continue',page.locator('#resume-intake').inner_text())
            self.assertIn('fictional-notes.txt',page.locator('.ps-guide-file-chip').inner_text())
            page.get_by_role('button',name='Remove fictional-notes.txt',exact=True).click()
            page.wait_for_selector('.ps-guide-file-chip',state='detached')
            self.assertFalse(any('/submissions' in url or '/interview' in url or '/organize' in url for url in writes))
            self.assertEqual(self.server.shared.canonical.list_items(OWNER),[])

    def test_opt_in_app_bootstrap_is_manual_only_and_uses_the_incumbent_input(self):
        from app import app
        with patch.dict(app.config,{'PEERSLATE_GUIDE_REBUILD_ENABLED':True}):
            context = self.browser.new_context(viewport={'width':1440,'height':1000})
            self.addCleanup(context.close)
            context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
            page = context.new_page()
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(self.server.url+'/app/resume')
            page.wait_for_selector('#resume-intake.ps-guide-shell',state='attached')
            self.assertFalse(page.locator('#resume-intake').evaluate('(node)=>node.open'))
            page.locator('#resume-intake-reopen').click()
            page.wait_for_selector('#resume-intake[open] .ps-guide-title')
            self.assertEqual(page.locator('.ps-guide-title').inner_text(),'PeerSlate Guide')
            self.assertEqual(page.locator('[data-guide-view="welcome"] h3').inner_text(),'Let’s build your resume together.')
            typography=page.evaluate('''() => ({title:getComputedStyle(document.querySelector('.ps-guide-title')).fontSize,
                heading:getComputedStyle(document.querySelector('.ps-guide-screen-heading')).fontSize,
                family:getComputedStyle(document.querySelector('.ps-guide-title')).fontFamily,
                legacyLayer:getComputedStyle(document.getElementById('resume-intake'),'::before').display,
                cairnStroke:getComputedStyle(document.querySelector('.ps-guide-avatar svg')).stroke})''')
            self.assertEqual(typography['title'],'18px')
            self.assertEqual(typography['heading'],'21px')
            self.assertIn('Newsreader',typography['family'])
            self.assertEqual(typography['legacyLayer'],'none')
            self.assertEqual(typography['cairnStroke'],'none')
            tile_tops=page.locator('.ps-guide-start-tile b').evaluate_all('(nodes)=>nodes.map(node=>node.getBoundingClientRect().top)')
            self.assertLessEqual(max(tile_tops)-min(tile_tops),1)
            self.assertEqual(page.locator('#resume-intake-text').get_attribute('placeholder'),'Tell me about your work, or attach a file…')
            self.assertEqual(page.evaluate("()=>document.querySelector('.ps-guide-screen-heading').getBoundingClientRect().left-document.querySelector('.ps-guide-body').getBoundingClientRect().left"),68)
            page.get_by_role('button',name='Type or paste',exact=True).wait_for()
            self.assertEqual(page.locator('.ps-guide-starters button').count(),3)
            page.get_by_role('button',name='Start with my current job',exact=True).click()
            self.assertEqual(page.locator('#resume-intake-text').input_value(),'Start with my current job')
            self.assertEqual(self.server.shared.canonical.list_items(OWNER),[])
            page.locator('#resume-intake-text').fill('Exact fictional words, kept unsent.')
            self.assertTrue(page.locator('.ps-guide-composer #resume-intake-text').is_visible())
            self.assertEqual(page.locator('#resume-intake-text').count(),1)
            self.assertEqual(page.locator('#resume-intake-text').input_value(),'Exact fictional words, kept unsent.')
            self.assertEqual(errors,[])

    def _correction_page(self,width=1440,height=1000,interview=None):
        from app import app
        old=app.config.get('PEERSLATE_GUIDE_REBUILD_ENABLED')
        self.addCleanup(app.config.__setitem__,'PEERSLATE_GUIDE_REBUILD_ENABLED',old)
        app.config['PEERSLATE_GUIDE_REBUILD_ENABLED']=True
        if interview is not None:
            old_interview=app.config.get('PEERSLATE_RESUME_INTERVIEW_ENABLED')
            self.addCleanup(app.config.__setitem__,'PEERSLATE_RESUME_INTERVIEW_ENABLED',old_interview)
            app.config['PEERSLATE_RESUME_INTERVIEW_ENABLED']=interview
        context=self.browser.new_context(viewport={'width':width,'height':height})
        self.addCleanup(context.close)
        context.add_cookies([{'name':'mvp1-synthetic-owner','value':OWNER,'url':self.server.url}])
        page=context.new_page();page.set_default_timeout(7000)
        page.goto(self.server.url+'/app/resume')
        page.locator('#resume-intake-reopen').click()
        page.get_by_role('button',name='Type or paste',exact=True).wait_for()
        page.wait_for_function("()=>document.querySelector('.ps-guide-compose-box').getAttribute('aria-busy')==='false'")
        self._settled_panel(page)
        return page

    def _settled_panel(self,page):
        return page.evaluate('''async () => {
            await document.fonts.ready;
            const panel=document.getElementById('resume-intake');let previous=null,stable=0;
            for(let n=0;n<60;n++){
                await new Promise(resolve=>requestAnimationFrame(resolve));
                const rect=panel.getBoundingClientRect();const now=[rect.x,rect.y,rect.width,rect.height];
                stable=previous&&now.every((v,i)=>Math.abs(v-previous[i])<.1)?stable+1:0;previous=now;
                if(stable>=3)return {x:rect.x,y:rect.y,width:rect.width,height:rect.height};
            }
            throw Error('Guide geometry did not settle');
        }''')

    def _capture_settled_panel(self,page,label):
        import os
        folder=os.environ.get('PEERSLATE_GUIDE_PANEL_EVIDENCE_DIR')
        if folder:
            target=Path(folder).resolve();target.mkdir(parents=True,exist_ok=True)
            bounds=self._settled_panel(page)
            page.screenshot(path=str(target/(label+'.png')),animations='disabled')
            (target/(label+'-bounds.json')).write_text(json.dumps(bounds),encoding='utf-8')

    def test_opt_in_actual_header_and_settled_width_at_620_704_and_390(self):
        for width,height,panel_width in ((1536,1024,704),(1024,768,620),(1440,1000,704),(390,844,390)):
            with self.subTest(width=width):
                page=self._correction_page(width,height)
                bounds=self._settled_panel(page)
                self.assertAlmostEqual(bounds['width'],panel_width,delta=1)
                header=page.evaluate('''()=>{const nodes=[...document.querySelector('.ps-guide-head').children].filter(n=>n.getClientRects().length);
                    const boxes=nodes.map(n=>n.getBoundingClientRect());return {overlap:Math.max(...boxes.map(b=>b.top))<Math.min(...boxes.map(b=>b.bottom)),
                        right:Math.max(...boxes.map(b=>b.right)),panelRight:document.getElementById('resume-intake').getBoundingClientRect().right};}''')
                self.assertTrue(header['overlap'],header)
                self.assertLessEqual(header['right'],header['panelRight']+1,header)
                self._capture_settled_panel(page,'corrected-welcome-'+str(width))
                page.locator('#resume-intake-file').set_input_files({'name':'fictional-layout.txt','mimeType':'text/plain','buffer':b'Not sent.'})
                self.assertAlmostEqual(self._settled_panel(page)['width'],bounds['width'],delta=.1)
                self._capture_settled_panel(page,'corrected-attached-'+str(width))

    def test_opt_in_welcome_vertical_components_match_locked_704_dimensions(self):
        import os
        page=self._correction_page(1536,1024)
        metrics=page.evaluate('''()=>{
            const panel=document.getElementById('resume-intake'),base=panel.getBoundingClientRect();
            const rect=selector=>{const n=panel.querySelector(selector),r=n.getBoundingClientRect(),s=getComputedStyle(n);return {
                x:r.x-base.x,y:r.y-base.y,width:r.width,height:r.height,
                margin:s.margin,padding:s.padding,border:s.borderBottomWidth,lineHeight:s.lineHeight};};
            return {panel:{x:base.x,y:base.y,width:base.width,height:base.height},
                header:rect('.ps-guide-head'),body:rect('.ps-guide-body'),
                heading:rect('.ps-guide-screen-heading'),intro:rect('.ps-guide-screen-copy'),
                tiles:rect('.ps-guide-start-tiles'),box:rect('.ps-guide-compose-box'),
                starters:rect('.ps-guide-starters'),footer:rect('.ps-guide-footer')};
        }''')
        folder=os.environ.get('PEERSLATE_GUIDE_PANEL_EVIDENCE_DIR')
        if folder:
            target=Path(folder).resolve();target.mkdir(parents=True,exist_ok=True)
            (target/'welcome-704-vertical-metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
            page.screenshot(path=str(target/'welcome-704-vertical.png'),animations='disabled')
        # Locked R6q D02 measured at the actual app's 704px panel width.
        # Match region positions/heights, so an arbitrary total-height trim
        # cannot mask an incorrect internal gap or clipped body/composer.
        expected={'header':(0,0,704,52),'body':(0,52,704,153.5),
            'heading':(68,62,608,26.25),'intro':(68,90.25,608,17.25),
            'tiles':(28,117.5,648,86),'box':(28,213.5,648,46),
            'starters':(28,266.5,648,31),'footer':(28,301.5,648,30)}
        for region,values in expected.items():
            with self.subTest(region=region):
                for axis,value in zip(('x','y','width','height'),values):
                    self.assertAlmostEqual(metrics[region][axis],value,delta=.1,msg=str(metrics))
        self.assertAlmostEqual(metrics['panel']['width'],704,delta=.1)
        self.assertAlmostEqual(metrics['panel']['height'],337.5,delta=.1,msg=str(metrics))

    def test_opt_in_leave_prompt_focus_and_preview_follow_D88(self):
        page=self._correction_page()
        words='Fictional first words. '+('Exact later words. '*12)
        page.locator('#resume-intake-text').fill(words)
        page.get_by_role('button',name='Finish for now',exact=True).click()
        self.assertEqual(page.evaluate('document.activeElement.textContent'),'Stay')
        self.assertIn(words[:100]+'…',page.locator('.ps-guide-leave-list').inner_text())
        self.assertTrue(page.locator('.ps-guide-composer>.resume-intake__hint').is_hidden())
        page.get_by_role('button',name='Stay',exact=True).click()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),words)

    def test_opt_in_clear_position_on_close_minimize_and_reload(self):
        page=self._correction_page()
        initial=self._settled_panel(page)
        for button in ('Minimize the Guide','Close the Guide'):
            page.locator('.ps-guide-grip').focus();page.keyboard.press('ArrowRight');page.keyboard.press('ArrowDown')
            moved=self._settled_panel(page)
            self.assertGreater(moved['x'],initial['x'])
            page.get_by_role('button',name=button,exact=True).click()
            page.wait_for_function("()=>!document.getElementById('resume-intake').open")
            self.assertIsNone(page.evaluate("sessionStorage.getItem('peerslate.guide.position')"))
            page.locator('#resume-intake-reopen').click()
            reopened=self._settled_panel(page)
            self.assertAlmostEqual(reopened['x'],initial['x'],delta=1)
            self.assertAlmostEqual(reopened['y'],initial['y'],delta=1)
        page.reload();page.locator('#resume-intake-reopen').click()
        self.assertAlmostEqual(self._settled_panel(page)['x'],initial['x'],delta=1)

    def test_opt_in_empty_pause_does_not_invent_an_unsent_message(self):
        page=self._correction_page()
        page.get_by_role('button',name='Finish for now',exact=True).click()
        page.wait_for_function("()=>!document.getElementById('resume-intake').open")
        notice=page.locator('#resume-intake-pause-notice')
        notice.wait_for(state='visible')
        self.assertEqual(notice.inner_text(),'Paused.')
        self.assertNotIn('message',notice.inner_text().lower())

    def test_opt_in_local_note_is_absent_and_session_copy_recovers_below_text_cap(self):
        page=self._correction_page()
        page.locator('#resume-intake-text').fill('Local fictional words.')
        self.assertTrue(page.locator('.ps-guide-composer>.resume-intake__hint').is_hidden())
        page.locator('#resume-intake-text').fill('x'*20001)
        self.assertNotIn('this browser can’t keep a copy',page.locator('.ps-guide-composer').inner_text())
        page.locator('#resume-intake-text').fill('Back below the selected local copy cap.')
        copies=page.evaluate("()=>Object.keys(sessionStorage).filter(k=>k.startsWith('peerslate.guide.unsent.')).map(k=>JSON.parse(sessionStorage.getItem(k)))")
        self.assertEqual(copies,[{'text':'Back below the selected local copy cap.','filenames':[]}])

    def test_opt_in_exact_type_spacing_and_visible_short_window_body_track(self):
        page=self._correction_page(1536,1024)
        tile_edge=page.locator('.ps-guide-start-tiles').bounding_box()['x']
        box_edge=page.locator('.ps-guide-compose-box').bounding_box()['x']
        page.locator('#resume-intake-file').set_input_files({'name':'fictional.txt','mimeType':'text/plain','buffer':b'Not sent.'})
        values=page.evaluate('''()=>({sizes:[...document.querySelectorAll('.ps-guide-starters button,.ps-guide-file-chip b,.ps-guide-file-chip em')].map(n=>getComputedStyle(n).fontSize),
            bodyPadding:getComputedStyle(document.querySelector('.ps-guide-body')).paddingLeft,
            copyGap:getComputedStyle(document.querySelector('.ps-guide-screen-copy')).marginTop})''')
        self.assertTrue(all(size=='12.5px' for size in values['sizes']),values)
        self.assertEqual(values['bodyPadding'],'28px',values)
        self.assertEqual(values['copyGap'],'2px',values)
        self.assertAlmostEqual(tile_edge,box_edge,delta=1)
        page.get_by_role('button',name='Remove fictional.txt',exact=True).click()
        page.set_viewport_size({'width':1200,'height':350})
        self._settled_panel(page)
        scroll=page.evaluate('''()=>{const panel=document.getElementById('resume-intake'),body=panel.querySelector('.ps-guide-body');
            return {fallback:panel.dataset.guideBodyScroll,overflow:body.scrollHeight>body.clientHeight,
                reserved:body.offsetWidth-body.clientWidth,gutter:getComputedStyle(body).scrollbarGutter};}''')
        self.assertEqual(scroll['fallback'],'true',scroll)
        self.assertGreater(scroll['reserved'],0,scroll)
        self.assertEqual(scroll['gutter'],'stable',scroll)

    def test_opt_in_unavailable_retry_and_restored_discard_use_approved_control_scale(self):
        page=self._correction_page()
        page.locator('#resume-intake-text').fill('Fictional words restored for a reviewable discard.')
        page.route('**/api/resume-intake/me/guide/working-set',lambda route:route.fulfill(status=503,json={'success':False,'code':'unavailable'}))
        page.reload();page.locator('#resume-intake-reopen').click()
        retry=page.get_by_role('button',name='Retry',exact=True)
        retry.wait_for()
        discard=page.get_by_role('button',name='Discard the message',exact=True)
        discard.wait_for()
        self.assertAlmostEqual(retry.bounding_box()['height'],30,delta=1)
        self.assertAlmostEqual(discard.bounding_box()['height'],30,delta=1)
        self.assertAlmostEqual(discard.bounding_box()['x'],page.locator('.ps-guide-compose-box').bounding_box()['x'],delta=1)
        self.assertIn('Your message is back, not sent.',page.locator('.ps-guide-composer').inner_text())
        self.assertEqual(page.locator('.ps-guide-recovery-tag').inner_text(),'Not sent yet')
        discard.click()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'')

    def test_opt_in_reopen_defers_working_set_without_discarding_unknown_formdata(self):
        from email.parser import BytesParser
        from email.policy import default
        page=self._correction_page(interview=False)
        reads=[];held=[];payloads=[]
        page.on('request',lambda request:reads.append(request.url) if request.url.endswith('/guide/working-set') else None)
        def submission(route):
            request=route.request
            message=BytesParser(policy=default).parsebytes(('Content-Type: '+request.headers['content-type']+'\r\n\r\n').encode()+request.post_data_buffer)
            payload=json.loads(next(part.get_payload(decode=True) for part in message.walk() if part.get_param('name',header='content-disposition')=='request'))
            payloads.append(payload)
            if len(payloads)==1:held.append(route)
            else:route.fulfill(status=400,json={'success':False,'message':'Fictional terminal refusal; no save.'})
        page.route('**/api/resume-intake/me/submissions',submission)
        def release():
            for route in held:
                try:route.abort()
                except Exception:pass
        self.addCleanup(release)
        page.locator('#resume-intake-text').fill('Original immutable request words.')
        page.locator('#resume-intake-file').set_input_files({'name':'first-unknown.txt','mimeType':'text/plain','buffer':b'FIRST'})
        page.locator('.ps-guide-compose-send').click()
        page.locator('.ps-guide-progress-current').wait_for()
        page.locator('#resume-intake-text').fill('New truly unsent words.')
        page.locator('#resume-intake-file').set_input_files({'name':'second-unsent.txt','mimeType':'text/plain','buffer':b'SECOND'})
        before=len(reads)
        page.get_by_role('button',name='Finish for now',exact=True).click()
        page.get_by_role('button',name='Leave anyway',exact=True).click()
        page.wait_for_function("()=>!document.getElementById('resume-intake').open")
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'')
        self.assertEqual(page.evaluate("()=>Object.keys(sessionStorage).filter(k=>k.startsWith('peerslate.guide.unsent.')).length"),0)
        page.locator('#resume-intake-reopen').click()
        page.locator('.ps-guide-progress-current').wait_for()
        page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        self.assertEqual(len(reads),before,'No working-set read may overlap the unresolved request')
        self.assertNotIn('second-unsent.txt',page.locator('.ps-guide-attachment-row').inner_text())
        held.pop().abort()
        page.wait_for_function("()=>document.querySelector('#resume-intake-add-label').textContent === 'Retry submission'")
        page.locator('#resume-intake-composer').dispatch_event('submit')
        page.wait_for_function("()=>document.querySelector('#resume-intake-add-label').textContent === 'Continue'")
        self.assertEqual(len(payloads),2)
        self.assertEqual(payloads[1],payloads[0])
        self.assertEqual(payloads[1]['text'],'Original immutable request words.')
        self.assertEqual(len(payloads[1]['attachments']),1)


    @classmethod
    def setUpClass(cls):
        runtime = sync_playwright().start()
        cls.addClassCleanup(runtime.stop)
        cls.browser = runtime.chromium.launch(executable_path=CHROME_EXECUTABLE, headless=True,
            args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        self.server = Mvp1AcceptanceServer().__enter__()
        self.addCleanup(self.server.__exit__, None, None, None)

    def page(self, owner=OWNER):
        context = self.browser.new_context()
        self.addCleanup(context.close)
        context.add_cookies([{"name": "mvp1-synthetic-owner", "value": owner, "url": self.server.url}])
        page = context.new_page()
        # A real plain-text route supplies same-origin HTTP without booting unrelated UI.
        page.goto(self.server.url + "/robots.txt")
        for module in ("guide-state.js", "guide-api.js", "guide-view.js"):
            page.add_script_tag(path=str(ROOT / "static/js" / module))
        page.evaluate('''() => {
            const root = document.createElement('main'); root.id = 'guide-api-proof'; document.body.append(root);
            window.guideProof = {state: PeerSlateGuideState.create(), api: PeerSlateGuideApi.create()};
            guideProof.view = PeerSlateGuideView.create(root);
        }''')
        return page

    def read(self, page):
        return page.evaluate('''async () => {
            const accepted = await guideProof.api.refresh(guideProof.state);
            const rendered = guideProof.view.render(guideProof.state);
            return {accepted, rendered, loadState:guideProof.state.loadState(), data:guideProof.state.data()};
        }''')

    def role(self, owner=OWNER, title="Engineer"):
        return self.server.shared.canonical.create_private(owner, {"command_id": str(uuid4()),
            "record_type": "role", "values": {"role_title": title, "employer_name": "Fictional Acorn Works"}})

    def test_real_working_set_renders_card_counts_without_child_inflation_or_writes(self):
        role = self.role()
        bullet = self.server.shared.canonical.create_private(OWNER, {"command_id": str(uuid4()),
            "record_type": "accomplishment", "parent_key": role["record_key"],
            "values": {"wording": "Reviewed 12 fictional records."}})
        page = self.page()
        requests = []
        page.on("request", lambda request: requests.append((request.method, request.url)))
        before = deepcopy(self.server.intake.repository.load_owner(OWNER))
        with (patch.object(self.server.shared.policy.repository, "save_owner", wraps=self.server.shared.policy.repository.save_owner) as policy_save,
              patch.object(self.server.shared.draft.repository, "save_owner", wraps=self.server.shared.draft.repository.save_owner) as draft_save,
              patch.object(self.server.intake.repository, "save_owner", wraps=self.server.intake.repository.save_owner) as intake_save):
            result = self.read(page)
            self.assertTrue(result["accepted"] and result["rendered"])
            section = next(row for row in result["data"]["sections"] if row["key"] == "experience")
            self.assertEqual(section["counts"]["saved"], 1)
            self.assertEqual(section["child_counts"]["saved"], 1)
            self.assertEqual(section["items"][0]["item_ref"], role["record_key"])
            self.assertEqual(section["items"][0]["children"][0]["item_ref"], bullet["record_key"])
            tab = page.locator('#guide-api-proof button[data-section="experience"]')
            self.assertEqual(tab.inner_text(), "Experience (1)")
            tab.click()
            self.assertEqual(tab.get_attribute("aria-current"), "page")
            policy_save.assert_not_called(); draft_save.assert_not_called(); intake_save.assert_not_called()
        self.assertEqual(self.server.intake.repository.load_owner(OWNER), before)
        self.assertTrue(all(method == "GET" for method, _ in requests), requests)
        self.assertEqual([(method, url) for method, url in requests if "/api/" in url],
            [("GET", self.server.url + "/api/resume-intake/me/guide/working-set")])

    def test_real_unavailable_read_clears_authority_and_shows_unavailable(self):
        self.role()
        page = self.page()
        self.assertTrue(self.read(page)["accepted"])
        with patch.object(self.server.intake.repository, "load_owner", side_effect=ResumeIntakeStoreUnavailable()):
            result = self.read(page)
        self.assertEqual(result, {"accepted": False, "rendered": False, "loadState": "unavailable", "data": None})
        self.assertEqual(page.locator('#guide-api-proof [role="status"]').inner_text(),
            "The Guide is unavailable right now.")
        self.assertEqual(page.locator('#guide-api-proof button[data-section]').count(), 0)

    def test_real_owner_cookie_never_reads_the_other_members_working_set(self):
        first, second = self.role(title="Fictional Alpha Engineer"), self.role("g-member-b", "Fictional Beta Designer")
        for owner, expected, forbidden in ((OWNER, first, second), ("g-member-b", second, first)):
            with self.subTest(owner=owner):
                data = self.read(self.page(owner))["data"]
                refs = [item["item_ref"] for section in data["sections"] for item in section["items"]]
                self.assertIn(expected["record_key"], refs)
                self.assertNotIn(forbidden["record_key"], refs)


if __name__ == "__main__":
    unittest.main()

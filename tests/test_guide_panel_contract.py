"""Frozen B1 contract consumers in a real browser; no model or server writes."""
from copy import deepcopy
from pathlib import Path
import unittest

from tests.test_resume_intake_browser import CHROME_EXECUTABLE, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def working_set():
    keys = ["impact_statement", "skills", "experience", "projects", "education", "certifications", "awards"]
    counts = {"saved": 0, "waiting": 0, "hidden": 0, "skipped": 0, "updates_waiting": 0}
    item = {"item_ref": "pending-one", "identity_aliases": [], "origin": "pending", "state": "waiting",
            "record_type": "skill", "section": "skills", "values": {"name": "Python"}, "parent_ref": None,
            "saved_revision": None, "proposal_key": "proposal-one", "revision": 1,
            "proposals": [{"proposal_key": "proposal-one", "revision": 1}], "evidence": [], "children": []}
    sections = [{"key": k, "label": k, "items": [item] if k == "skills" else [],
                 "tab_visible": k == "skills", "counts": {**counts, "waiting": int(k == "skills")},
                 "child_counts": dict(counts)}
                for k in keys]
    return {"success": True, "schema_version": 1, "load_state": "loaded", "section_order": keys,
            "sections": sections, "unplaced": [], "non_tab_items": [], "legacy_outcomes": [], "active_sources": [],
            "draft_version": 0, "lifecycle_epoch": 0, "working_set_token": "opaque-fixture-token",
            "publication_state": "unknown", "counts": {**counts, "waiting": 1},
            "child_counts": dict(counts), "child_count": 0,
            "last_receipt": None}


@unittest.skipUnless(sync_playwright is not None and CHROME_EXECUTABLE,
                     "Playwright and Chrome are required for panel contract proof")
class GuidePanelContractTests(unittest.TestCase):
    def test_composer_adopts_the_existing_input_and_preserves_transport_and_voice_frontiers(self):
        page = self.page('guide-view.js','guide-conversation.js')
        result = page.evaluate('''() => {
            const form=document.createElement('form'), input=document.createElement('textarea');
            input.id='existing-private-input'; input.value='Original exact words.';
            form.append(input); document.body.append(form);
            const host=document.createElement('div'); document.body.append(host);
            let legacyInputs=0, sends=[];
            input.addEventListener('input',()=>legacyInputs++);
            form.addEventListener('submit',event=>{event.preventDefault();sends.push(input.value);});
            const composer=PeerSlateGuideConversation.createComposer(host,{input,
                onSend:()=>form.dispatchEvent(new Event('submit',{cancelable:true})),onAction:()=>{}});
            const adopted=host.querySelector('textarea')===input;
            const initial=composer.snapshot().text;
            input.value='New exact words.';input.dispatchEvent(new Event('input'));
            const frontier=composer.snapshot();
            input.value+=' Appended voice.';input.dispatchEvent(new Event('input'));
            const afterVoice=composer.snapshot();
            input.value+=' External restore.';
            const staleClear=composer.clear(afterVoice.revision);
            host.querySelector('[aria-label="Send"]').click();
            composer.dispose();
            input.value+=' After dispose.';input.dispatchEvent(new Event('input'));
            return {adopted,initial,staleClear,sends,legacyInputs,value:input.value,
                sameNode:document.getElementById('existing-private-input')===input};
        }''')
        self.assertEqual(result,{'adopted':True,'initial':'Original exact words.','staleClear':False,
            'sends':['New exact words. Appended voice. External restore.'],'legacyInputs':3,
            'value':'New exact words. Appended voice. External restore. After dispose.','sameNode':True})

    def test_composer_enter_shift_enter_and_ime_preserve_the_input_frontier(self):
        page = self.page('guide-view.js','guide-conversation.js')
        page.evaluate('''() => {
            const host=document.createElement('div');document.body.append(host);
            window.sent=[];window.input=document.createElement('textarea');input.value='First words';
            window.composer=PeerSlateGuideConversation.createComposer(host,{input,onSend:s=>sent.push(s.text),onAction:()=>{}});
            input.focus();input.setSelectionRange(input.value.length,input.value.length);
        }''')
        page.keyboard.press('Shift+Enter')
        self.assertEqual(page.evaluate('input.value'),'First words\n')
        page.keyboard.type('Second line')
        page.evaluate('''() => {
            input.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));
            input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',isComposing:true,bubbles:true,cancelable:true}));
        }''')
        self.assertEqual(page.evaluate('sent'),[])
        page.evaluate("input.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true}))")
        page.keyboard.press('Enter')
        self.assertEqual(page.evaluate('sent'),['First words\nSecond line'])
        self.assertEqual(page.evaluate('input.value'),'First words\nSecond line')
        page.evaluate('composer.dispose()')
        page.keyboard.press('Enter')
        self.assertEqual(len(page.evaluate('sent')),1)

    def test_header_uses_one_row_and_compact_privacy_at_real_panel_widths(self):
        page = self.page('guide-view.js','guide-shell.js')
        page.add_style_tag(path=str(ROOT/'static/css/resume-intake.css'))
        for width in (620,704,390):
            for state in ('unpublished','unknown'):
                with self.subTest(width=width,state=state):
                    result=page.evaluate('''([width,state]) => {
                        document.querySelectorAll('dialog').forEach(node=>node.remove());
                        const root=document.createElement('dialog');document.body.append(root);
                        const frame=PeerSlateGuideView.frame(root,{publicationState:state,onAction:()=>{}});
                        root.style.width=width+'px';root.style.left='0';root.style.top='0';
                        root.dataset.guideSheet=String(width===390);root.showModal();frame.publication(state);
                        const children=[...frame.header.children].filter(n=>n.getClientRects().length);
                        const boxes=children.map(n=>n.getBoundingClientRect());
                        return {header:frame.header.getBoundingClientRect().toJSON(),
                            boxes:boxes.map(b=>({top:b.top,bottom:b.bottom,left:b.left,right:b.right})),
                            titleLines:frame.header.querySelector('h2').getBoundingClientRect().height,
                            privacy:frame.privacy.textContent,full:frame.privacy.getAttribute('aria-label'),
                            nowrap:getComputedStyle(frame.header).flexWrap};
                    }''',[width,state])
                    self.assertEqual(result['nowrap'],'nowrap',result)
                    self.assertLess(max(box['top'] for box in result['boxes'])-min(box['bottom'] for box in result['boxes']),0,result)
                    self.assertLess(result['titleLines'],30,result)
                    self.assertEqual(result['privacy'],('Private draft. Nothing is published.' if width>700 else 'Private draft')
                        if state=='unpublished' else 'Changes stay private')
                    self.assertTrue(all(box['right']<=width+1 for box in result['boxes']),result)

    def test_flag_off_template_omits_feature_attributes_and_extra_script_whitespace(self):
        from jinja2 import Environment
        source=(ROOT/'templates/partials/resume/_intake_composer.html').read_text(encoding='utf-8')
        template=Environment(autoescape=True).from_string(source)
        options={'member':{'user_key':'opaque-fictional-member'},'url_for':lambda endpoint,**kw:'/url/'+endpoint+'/'+kw.get('filename','')}
        off=template.render(config={'PEERSLATE_GUIDE_REBUILD_ENABLED':False},**options)
        on=template.render(config={'PEERSLATE_GUIDE_REBUILD_ENABLED':True},**options)
        self.assertNotIn('data-guide-rebuild-enabled',off)
        self.assertNotIn('data-guide-member-key',off)
        self.assertNotIn('js/guide-state.js',off)
        self.assertIn('<dialog class="resume-intake" id="resume-intake"\n    data-intake-workspace-url=',off)
        self.assertIn('</details>\n</div>\n<div class="resume-intake__reopen">',off)
        self.assertIn('data-guide-rebuild-enabled="true"',on)
        self.assertIn('data-guide-member-key="opaque-fictional-member"',on)



    @classmethod
    def setUpClass(cls):
        runtime = sync_playwright().start()
        cls.addClassCleanup(runtime.stop)
        cls.browser = runtime.chromium.launch(executable_path=CHROME_EXECUTABLE, headless=True)
        cls.addClassCleanup(cls.browser.close)

    def page(self, *modules):
        context = self.browser.new_context()
        self.addCleanup(context.close)
        page = context.new_page()
        page.route("http://guide.test/**", lambda route: route.fulfill(body="<main>Contract fixture</main>", content_type="text/html"))
        page.goto("http://guide.test/")
        for module in modules:
            page.add_script_tag(path=str(ROOT / "static/js" / module))
        return page

    def test_unavailable_or_malformed_read_never_becomes_an_empty_resume(self):
        page = self.page("guide-state.js")
        payload = working_set()
        self.assertEqual(page.evaluate("p => { const s=PeerSlateGuideState.create(); s.accept(p); s.fail(); "
                                       "return [s.loadState(),s.data(),s.selected()]; }", payload),
                         ["unavailable", None, None])
        for changed in ({"success": False}, {"load_state": "unavailable"}, {"schema_version": 2},
                        {"sections": []}, {"counts": {"saved": -1, "waiting": 0, "hidden": 0, "skipped": 0}},
                        {"publication_state": "pretend-unpublished"}):
            with self.subTest(changed=changed):
                self.assertFalse(page.evaluate("p => PeerSlateGuideState.create().accept(p)", {**payload, **changed}))

    def test_saved_alias_keeps_selection_and_navigation_does_not_write(self):
        page = self.page("guide-state.js")
        before = working_set()
        after = deepcopy(before)
        item = after["sections"][1]["items"][0]
        item.update(item_ref="saved-record", identity_aliases=["pending-one"], origin="saved", state="saved",
                    saved_revision="actual-saved-revision", proposal_key=None, revision=None, proposals=[])
        after["sections"][1]["counts"].update(saved=1, waiting=0)
        after["counts"].update(saved=1, waiting=0)
        result = page.evaluate("([before,after]) => { const s=PeerSlateGuideState.create(); "
                               "let writes=0; window.fetch=()=>{writes++;throw Error('Unexpected write')}; "
                               "s.accept(before); s.select('pending-one'); s.accept(after); "
                               "return [s.selected().item_ref,s.select('foreign-ref'),s.selected().item_ref,writes]; }",
                               [before, after])
        self.assertEqual(result, ["saved-record", False, "saved-record", 0])

    def test_sources_publication_and_section_order_stay_server_truth(self):
        page = self.page("guide-state.js")
        payload = working_set()
        payload["active_sources"] = [{"source_key": "source-one", "source_version": 1, "kind": "document",
                                      "state": "active", "page_count": 3, "text_page_count": 1,
                                      "unit_count": 1, "complete": True, "organization": {"state": "failed"}}]
        result = page.evaluate("p => {const s=PeerSlateGuideState.create();s.accept(p); const d=s.data(); "
                               "return [d.section_order,d.publication_state,d.active_sources[0].page_count,"
                               "d.active_sources[0].organization.state,d.counts.waiting,Object.isFrozen(d.sections)];}", payload)
        self.assertEqual(result, [payload["section_order"], "unknown", 3, "failed", 1, True])

    def test_duplicate_or_ambiguous_item_references_fail_closed(self):
        page = self.page("guide-state.js")
        for as_alias in (False, True):
            payload = working_set()
            item = deepcopy(payload["sections"][1]["items"][0])
            if as_alias:
                item.update(item_ref="other", identity_aliases=["pending-one"])
            payload["sections"][1]["items"].append(item)
            self.assertFalse(page.evaluate("p=>PeerSlateGuideState.create().accept(p)", payload))

    def test_api_reads_only_owner_route_with_private_request_options(self):
        page = self.page("guide-state.js", "guide-api.js")
        payload = working_set()
        result = page.evaluate("async p=>{const calls=[]; const api=PeerSlateGuideApi.create({fetch:async(url,opts)=>{"
                               "calls.push([url,opts]);return {ok:true,json:async()=>p};}}); "
                               "const d=await api.readWorkingSet(); return [calls,d.publication_state];}", payload)
        calls, publication = result
        self.assertEqual(publication, "unknown")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "/api/resume-intake/me/guide/working-set")
        self.assertEqual({k: calls[0][1][k] for k in ("method", "credentials", "cache", "redirect")},
                         {"method": "GET", "credentials": "same-origin", "cache": "no-store", "redirect": "error"})
        self.assertNotIn("body", calls[0][1])

    def test_api_refusal_cannot_expose_failed_or_stale_payload(self):
        page = self.page("guide-state.js", "guide-api.js")
        result = page.evaluate("async()=>{const api=PeerSlateGuideApi.create({fetch:async()=>({ok:false,"
                               "json:async()=>({success:true,load_state:'loaded'})})}); "
                               "try{await api.readWorkingSet();return 'leaked';}catch(e){return e.code;}}")
        self.assertEqual(result, "guide_unavailable")

    def test_late_read_or_failure_cannot_replace_the_newest_working_set(self):
        page = self.page("guide-state.js", "guide-api.js")
        payload = working_set()
        result = page.evaluate("async p=>{const held=[];const api=PeerSlateGuideApi.create({fetch:()=>new Promise(r=>held.push(r))});"
                               "const s=PeerSlateGuideState.create();const first=api.refresh(s);const second=api.refresh(s);"
                               "held[1]({ok:true,json:async()=>p});await second;held[0]({ok:false});await first;"
                               "return [s.loadState(),s.data().working_set_token];}", payload)
        self.assertEqual(result, ["loaded", payload["working_set_token"]])

    def test_non_tab_reference_and_waiting_child_count_are_separate_from_cards(self):
        page=self.page("guide-state.js")
        payload=working_set()
        contact=deepcopy(payload["sections"][1]["items"][0])
        contact.update(item_ref="contact-only",section="contact",record_type="knowledge")
        payload["non_tab_items"]=[contact]
        payload["child_counts"]={"saved":0,"waiting":1,"hidden":0,"skipped":0,"updates_waiting":0}
        parent=deepcopy(contact);child=deepcopy(contact)
        parent.update(item_ref="role-one",origin="saved",state="saved",section="experience",record_type="role",children=[child])
        child.update(item_ref="bullet-one",section="experience",record_type="accomplishment",parent_ref="role-one")
        payload["sections"][2].update(items=[parent],tab_visible=True,counts={**payload["counts"],"saved":1,"waiting":0})
        payload["child_count"]=1;payload["counts"]["saved"]=1
        result=page.evaluate("p=>{const s=PeerSlateGuideState.create();s.accept(p);return "
            "[s.select('contact-only'),s.selected()?.section,s.data().counts.waiting,s.data().child_counts.waiting];}",payload)
        self.assertEqual(result,[True,"contact",1,1])

    def test_approved_geometry_table_phone_fold_and_live_column_edge(self):
        page=self.page("guide-shell.js")
        for width,expected in ((960,[620,284,76]),(1024,[620,284,76]),(1280,[704,288,76]),(1536,[704,416,76])):
            with self.subTest(width=width):
                self.assertEqual(page.evaluate("w=>{const g=PeerSlateGuideShell.geometry({width:w,height:1024});"
                    "return [g.width,g.left,g.top];}",width),expected)
        self.assertEqual(page.evaluate("()=>{const g=PeerSlateGuideShell.geometry({width:959,height:650});"
            "return [g.width,g.left,g.top,g.maxHeight,g.draggable];}"),[959,0,0,650,False])
        self.assertEqual(page.evaluate("()=>{const g=PeerSlateGuideShell.geometry({width:1536,height:1024,leftColumnEdge:393});"
            "return [g.width,g.left];}"),[744,396])

    def test_window_reads_live_page_rail_on_relayout_and_falls_back_without_recentering(self):
        page = self.page("guide-shell.js")
        page.set_viewport_size({"width": 1536, "height": 1024})
        page.add_style_tag(path=str(ROOT / "static/css/resume-intake.css"))
        page.evaluate("""()=>{
            window.edge=393;window.reads=0;window.writes=0;
            window.fetch=()=>{writes++;throw Error('Unexpected network')};
            window.PeerSlateResumePage={leftColumnEdge:()=>{reads++;return edge}};
            const panel=document.createElement('section');panel.className='ps-guide-shell';panel.style.height='400px';
            const grip=document.createElement('button');grip.textContent='Move the Guide';panel.append(grip);document.body.append(panel);
            window.panel=panel;window.binding=PeerSlateGuideShell.bind(panel,grip);
        }""")
        def layout():
            box = page.locator(".ps-guide-shell").bounding_box()
            return [box["width"], box["x"]]
        self.assertEqual(layout(), [744, 396])
        page.evaluate("()=>{edge=460;binding.relayout()}")
        self.assertEqual(layout(), [620, 396])
        for bad_edge in (0, -1, None, "393", 2000):
            with self.subTest(edge=bad_edge):
                page.evaluate("value=>{edge=value;binding.relayout()}", bad_edge)
                self.assertEqual(layout(), [704, 396])
        page.evaluate("()=>{PeerSlateResumePage.leftColumnEdge=()=>{throw Error('Page unavailable')};binding.relayout()}")
        self.assertEqual(layout(), [704, 396])
        page.evaluate("()=>{delete window.PeerSlateResumePage;binding.relayout()}")
        self.assertEqual(layout(), [704, 396])
        self.assertGreaterEqual(page.evaluate("reads"), 2)
        self.assertEqual(page.evaluate("writes"), 0)
        page.evaluate("()=>binding.dispose({clearPosition:true})")

    def test_corrected_count_fields_are_required_without_inventing_defaults(self):
        page = self.page("guide-state.js")
        for field in ("child_counts", "updates_waiting"):
            payload = working_set()
            if field == "child_counts":
                del payload[field]
            else:
                del payload["sections"][1]["counts"][field]
            self.assertFalse(page.evaluate("p=>PeerSlateGuideState.create().accept(p)", payload))

    def test_detached_tabs_keep_server_order_card_counts_safe_text_and_no_writes(self):
        page = self.page("guide-state.js", "guide-view.js")
        payload = working_set()
        section = payload["sections"][2]
        section.update(label="Experience <img src=x onerror=alert(1)>", tab_visible=True)
        section["counts"].update(saved=1, waiting=0)
        section["child_counts"].update(saved=2, waiting=3)
        page.evaluate("p=>{window.calls=[];window.fetch=()=>{throw Error('Unexpected network')};"
                      "window.state=PeerSlateGuideState.create();state.accept(p);"
                      "window.root=document.querySelector('main');"
                      "window.view=PeerSlateGuideView.create(root,{onSection:key=>calls.push(key)});"
                      "view.render(state);}", payload)
        buttons = page.get_by_role("button")
        self.assertEqual(buttons.all_text_contents(), ["skills (1)", "Experience <img src=x onerror=alert(1)> (1)"])
        self.assertEqual(page.locator("main img").count(), 0)
        buttons.nth(1).focus()
        page.keyboard.press("Enter")
        self.assertEqual(page.evaluate("calls"), ["experience"])
        self.assertEqual(page.locator("button[aria-current='page']").inner_text(), buttons.nth(1).inner_text())
        page.evaluate("()=>{state.fail();view.render(state)}")
        self.assertEqual(page.get_by_role("button").count(), 0)
        self.assertEqual(page.get_by_role("status").inner_text(), "The Guide is unavailable right now.")

    def test_drag_clamp_and_bottom_growth_preserve_visible_bounds(self):
        page=self.page("guide-shell.js")
        result=page.evaluate("()=>{const f=PeerSlateGuideShell.clampPosition;"
            "const a=f({left:-100,top:2000},{width:704,height:400},{width:1536,height:1024});"
            "const b=f(a,{width:704,height:600},{width:1536,height:1024});"
            "return [a.left,a.top,a.bottom,b.left,b.top,b.bottom];}")
        self.assertEqual(result,[30,616,True,30,416,True])

    def test_detached_window_moves_by_keyboard_clamps_growth_and_folds_without_reset(self):
        page = self.page("guide-shell.js")
        page.set_viewport_size({"width": 1536, "height": 1024})
        page.add_style_tag(path=str(ROOT / "static/css/resume-intake.css"))
        page.evaluate("""()=>{
            document.querySelector('main').innerHTML='<section id="panel" class="ps-guide-shell" style="height:400px;border:2px solid"><header id="head"><button id="grip" type="button" aria-label="Move the Guide">Move</button><button id="finish" type="button">Finish for now</button></header></section>';
            window.panel=document.querySelector('#panel');window.grip=document.querySelector('#grip');
            window.binding=PeerSlateGuideShell.bind(panel,grip,{dragHandle:document.querySelector('#head')});
        }""")
        def rectangle():
            return page.locator("#panel").bounding_box()
        self.assertEqual({key: rectangle()[key] for key in ("x", "y", "width")}, {"x": 416, "y": 76, "width": 704})
        page.get_by_role("button", name="Move the Guide").focus()
        page.keyboard.press("ArrowRight")
        self.assertEqual(rectangle()["x"], 440)
        finish = page.locator("#finish").bounding_box()
        page.mouse.move(finish["x"] + 5, finish["y"] + 5)
        page.mouse.down()
        page.mouse.move(700, 500)
        page.mouse.up()
        self.assertEqual(rectangle()["x"], 440)
        box = page.locator("#grip").bounding_box()
        page.mouse.move(box["x"] + 5, box["y"] + 5)
        page.mouse.down()
        page.mouse.move(700, 1000)
        page.mouse.up()
        self.assertEqual(rectangle()["y"], 616)
        page.evaluate("()=>{panel.style.height='600px'}")
        page.wait_for_function("()=>document.querySelector('#panel').getBoundingClientRect().top===416")
        moved_left = rectangle()["x"]
        page.set_viewport_size({"width": 959, "height": 650})
        page.wait_for_function("()=>document.querySelector('#panel').getBoundingClientRect().width===959")
        self.assertEqual({key: rectangle()[key] for key in ("x", "y", "height")}, {"x": 0, "y": 0, "height": 650})
        page.set_viewport_size({"width": 1536, "height": 1024})
        page.wait_for_function("()=>document.querySelector('#panel').getBoundingClientRect().width===704")
        self.assertEqual(rectangle()["x"], moved_left)
        self.assertEqual(page.evaluate("()=>{binding.dispose({clearPosition:true});return sessionStorage.getItem('peerslate.guide.position');}"), None)

    def test_detached_frame_actions_and_escape_never_close_or_save_without_a_receipt(self):
        page = self.page("guide-view.js", "guide-shell.js")
        page.add_style_tag(path=str(ROOT / "static/css/resume-intake.css"))
        page.evaluate("""()=>{
            window.actions=[];window.writes=0;window.fetch=()=>{writes++;throw Error('Unexpected write')};
            window.dialog=document.createElement('dialog');document.body.append(dialog);
            window.frame=PeerSlateGuideView.frame(dialog,{publicationState:'unpublished',
                onAction:action=>{actions.push(action);return Promise.resolve(false)}});
            const words=document.createElement('textarea');words.value='Newer unsent fictional words';frame.composer.append(words);
            dialog.showModal();window.binding=PeerSlateGuideShell.bind(dialog,frame.grip,{dragHandle:frame.header});
        }""")
        self.assertTrue(page.get_by_role("dialog", name="PeerSlate Guide").is_visible())
        self.assertEqual(page.get_by_role("heading", name="PeerSlate Guide").count(), 1)
        for label in ("Finish for now", "Minimize the Guide", "Close the Guide", "Edit myself"):
            page.get_by_role("button", name=label, exact=True).click()
            self.assertTrue(page.evaluate("dialog.open"))
        page.keyboard.press("Escape")
        self.assertEqual(page.evaluate("actions"), ["finish", "minimize", "close", "manual", "close"])
        self.assertTrue(page.evaluate("dialog.open"))
        self.assertEqual(page.evaluate("writes"), 0)
        self.assertEqual(page.locator(".ps-guide-avatar svg path").count(), 3)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_function("()=>dialog.getBoundingClientRect().width===390")
        page.evaluate("()=>frame.publication('unknown')")
        self.assertEqual(page.get_by_role("status", name="Changes stay private. Publish status unavailable.").inner_text(), "Changes stay private")
        self.assertEqual(page.get_by_role("textbox").input_value(), "Newer unsent fictional words")
        for label in ("Finish for now", "Minimize the Guide", "Close the Guide", "Edit myself"):
            box = page.get_by_role("button", name=label, exact=True).bounding_box()
            self.assertGreaterEqual(box["x"], 0)
            self.assertLessEqual(box["x"] + box["width"], 390)

    def test_publication_header_full_and_narrow_follow_the_manager_ruling_without_a_guessed_count(self):
        page = self.page("guide-view.js")
        table = {
            "unpublished": ("Private draft. Nothing is published.", "Private draft", "lock"),
            "published": ("Published. Changes stay private.", "Published. Changes stay private.", "check"),
            "changes_waiting": ("Published · changes not published yet", "Published · changes waiting", "check"),
            "unknown": ("Changes stay private. Publish status unavailable.", "Changes stay private", "lock"),
        }
        for state, (full, narrow, icon) in table.items():
            for small in (False, True):
                with self.subTest(state=state, narrow=small):
                    actual = page.evaluate("([s,n])=>PeerSlateGuideView.publicationHeader(s,n)", [state, small])
                    self.assertEqual(actual, {"fullText": full, "visibleText": narrow if small else full, "icon": icon})
                    if state != "unpublished":
                        self.assertNotIn("Nothing is published", actual["fullText"])
                    if state == "changes_waiting":
                        self.assertNotRegex(actual["visibleText"], r"\d")

    def test_welcome_starts_are_explicit_safe_text_and_truthful_about_record_then_transcribe(self):
        page = self.page("guide-view.js", "guide-shell.js")
        page.add_style_tag(path=str(ROOT / "static/css/resume-intake.css"))
        page.evaluate("""()=>{
            window.actions=[];window.writes=0;window.fetch=()=>{writes++;throw Error('Unexpected provider work')};
            window.dialog=document.createElement('dialog');document.body.append(dialog);
            window.frame=PeerSlateGuideView.frame(dialog,{publicationState:'unpublished',onAction:a=>actions.push(a)});
            const words=document.createElement('textarea');words.value='Newer words outside the body view';frame.composer.append(words);
            PeerSlateGuideView.welcome(frame.body,{mode:'first_arrival',firstName:'Morgan',onAction:a=>actions.push(a)});
            dialog.showModal();window.binding=PeerSlateGuideShell.bind(dialog,frame.grip,{dragHandle:frame.header});
        }""")
        self.assertEqual(page.get_by_role("heading", name="Welcome to PeerSlate, Morgan.").count(), 1)
        self.assertEqual(page.get_by_text("Ask Morgan AI", exact=True).count(), 1)
        self.assertEqual(page.evaluate("actions"), [])
        self.assertEqual(page.get_by_text("I’ll write it out when you stop.", exact=True).count(), 1)
        self.assertEqual(page.get_by_text("Words appear as you speak.", exact=True).count(), 0)
        for label in ("Upload a file", "Talk it through", "Type or paste"):
            page.get_by_role("button", name=label, exact=True).click()
        self.assertEqual(page.evaluate("actions"), ["upload", "talk", "type"])
        page.get_by_role("button", name="Don’t have a resume yet?", exact=True).click()
        self.assertEqual(page.evaluate("actions"), ["upload", "talk", "type", "no_resume"])
        self.assertEqual(page.evaluate("writes"), 0)
        page.evaluate("""()=>PeerSlateGuideView.welcome(frame.body,{mode:'first_arrival',
            firstName:'<img src=x onerror=alert(1)>',onAction:()=>{}})""")
        self.assertEqual(page.locator(".ps-guide-body img").count(), 0)
        self.assertIn("<img src=x", page.locator(".ps-guide-screen-heading").inner_text())
        self.assertFalse(page.evaluate("""()=>{try{PeerSlateGuideView.welcome(frame.body,{mode:'unavailable',onAction:()=>{}});return true;}catch(e){return false;}}"""))
        page.evaluate("()=>PeerSlateGuideView.welcome(frame.body,{mode:'manual',onAction:()=>{}})")
        self.assertEqual(page.get_by_role("heading", name="Let’s build your resume together.").count(), 1)
        self.assertEqual(page.locator(".ps-guide-ask-intro").count(), 0)
        self.assertEqual(page.get_by_role("textbox").input_value(), "Newer words outside the body view")

    def test_organizing_shows_only_matching_source_milestones_and_real_elapsed_time(self):
        page = self.page("guide-state.js", "guide-view.js")
        page.add_style_tag(path=str(ROOT / "static/css/resume-intake.css"))
        payload = working_set()
        payload["active_sources"] = [{"source_key": "document-one", "source_version": 3, "kind": "document",
            "state": "active", "complete": True, "page_count": 2, "text_page_count": 1, "unit_count": 4,
            "organization": {"state": "unavailable"}}]
        page.evaluate("""p=>{window.writes=0;window.fetch=()=>{writes++;throw Error('Unexpected provider work')};
            window.dialog=document.createElement('dialog');document.body.append(dialog);
            window.frame=PeerSlateGuideView.frame(dialog,{publicationState:'unknown',onAction:()=>{}});
            const words=document.createElement('textarea');words.value='Newer unsent words';frame.composer.append(words);
            window.state=PeerSlateGuideState.create();state.accept(p);
            window.progress=PeerSlateGuideView.organizing(frame.body,{state:state,inFlight:true,elapsedSeconds:74,
                sourceRef:{sourceKey:'document-one',version:3}});dialog.showModal();}""", payload)
        text = page.locator(".ps-guide-body").inner_text()
        self.assertIn("Your file is saved privately", text)
        self.assertIn("Read 2 pages", text)
        self.assertIn("Sorting it into sections · 1:14", " ".join(text.split()))
        for unsupported in ("minute", "%", "Checking dates", "Found", "skills (", "roles"):
            self.assertNotIn(unsupported, text)
        self.assertEqual(page.locator(".ps-guide-tabs").count(), 0)
        page.evaluate("()=>progress.elapsed(75)")
        self.assertIn("1:15", page.locator(".ps-guide-body").inner_text())
        partial = deepcopy(payload)
        partial["active_sources"][0]["complete"] = False
        page.evaluate("""p=>{state.accept(p);PeerSlateGuideView.organizing(frame.body,
            {state:state,inFlight:true,sourceRef:{sourceKey:'document-one',version:3}})}""", partial)
        self.assertIn("saved privately", page.locator(".ps-guide-body").inner_text())
        self.assertNotIn("Read 2 pages", page.locator(".ps-guide-body").inner_text())
        page.evaluate("""()=>PeerSlateGuideView.organizing(frame.body,{state:state,inFlight:true,
            sourceRef:{sourceKey:'document-one',version:4}})""")
        text = page.locator(".ps-guide-body").inner_text()
        self.assertNotIn("saved privately", text)
        self.assertNotIn("Read 2 pages", text)
        self.assertIn("Sorting it into sections", text)
        self.assertNotIn("0:00", text)
        self.assertFalse(page.evaluate("()=>progress.elapsed(76)"))
        page.evaluate("()=>{state.fail();PeerSlateGuideView.organizing(frame.body,{state:state,inFlight:true})}")
        self.assertNotIn("saved privately", page.locator(".ps-guide-body").inner_text())
        self.assertFalse(page.evaluate("""()=>{try{PeerSlateGuideView.organizing(frame.body,
            {state:state,inFlight:false});return true;}catch(e){return false;}}"""))
        self.assertEqual(page.get_by_role("textbox").input_value(), "Newer unsent words")
        self.assertEqual(page.evaluate("writes"), 0)

    def test_detached_composer_keeps_newer_words_across_stale_restore_and_acknowledgment(self):
        page = self.page("guide-view.js", "guide-conversation.js")
        page.evaluate("""()=>{window.sent=[];window.actions=[];window.writes=0;
            window.fetch=()=>{writes++;throw Error('Unexpected network')};
            window.composer=PeerSlateGuideConversation.createComposer(document.querySelector('main'),{
                onSend:s=>{sent.push(s);return Promise.resolve(false)},onAction:a=>actions.push(a)});
            window.start=composer.snapshot();}""")
        send = page.get_by_role("button", name="Send", exact=True)
        self.assertTrue(send.is_disabled())
        words = page.get_by_role("textbox", name="Message to the Guide")
        words.fill("  Original\nfictional words  ")
        send.click()
        self.assertEqual(page.evaluate("sent[0].text"), "  Original\nfictional words  ")
        self.assertEqual(words.input_value(), "  Original\nfictional words  ")
        page.evaluate("()=>composer.setBusy(true)")
        self.assertEqual(page.evaluate("()=>[composer.clear(composer.snapshot().revision),composer.restore('Unsettled old draft',composer.snapshot().revision)]"), [False, False])
        words.fill("Newer unsent words")
        self.assertEqual(page.evaluate("()=>[composer.clear(sent[0].revision),composer.restore('Old saved words',start.revision)]"), [False, False])
        self.assertEqual(words.input_value(), "Newer unsent words")
        self.assertTrue(send.is_disabled())
        self.assertFalse(words.is_disabled())
        page.evaluate("()=>composer.setBusy(false)")
        self.assertTrue(page.evaluate("()=>composer.clear(composer.snapshot().revision)"))
        self.assertTrue(send.is_disabled())
        self.assertTrue(page.evaluate("()=>composer.restore('Saved private draft',composer.snapshot().revision)"))
        self.assertEqual(words.input_value(), "Saved private draft")
        self.assertEqual(page.evaluate("[sent.length,writes]"), [1, 0])
        page.get_by_role("button", name="Attach a file", exact=True).click()
        page.get_by_role("button", name="Record a message", exact=True).click()
        self.assertEqual(page.evaluate("actions"), ["attach", "record"])

    def test_attached_file_can_send_without_words_and_late_ack_keeps_newer_files(self):
        page = self.page("guide-view.js", "guide-shell.js", "guide-conversation.js")
        page.add_style_tag(path=str(ROOT / "static/css/resume-intake.css"))
        page.evaluate("""()=>{window.sent=[];window.actions=[];window.writes=0;
            window.fetch=()=>{writes++;throw Error('Unexpected upload')};
            window.dialog=document.createElement('dialog');document.body.append(dialog);
            window.frame=PeerSlateGuideView.frame(dialog,{publicationState:'unknown',onAction:()=>{}});
            window.composer=PeerSlateGuideConversation.createComposer(frame.composer,{
                onSend:s=>sent.push(s),onAction:(action,detail)=>actions.push([action,detail])});
            window.files=[{clientKey:'file-one',filename:'Notes <img src=x>.txt',phase:'attached'}];
            composer.setAttachments(files);files[0].filename='Mutated outside the component';
            dialog.showModal();window.binding=PeerSlateGuideShell.bind(dialog,frame.grip,{dragHandle:frame.header});
        }""")
        self.assertEqual(page.locator("img").count(), 0)
        self.assertEqual(page.get_by_text("Notes <img src=x>.txt", exact=True).count(), 1)
        self.assertEqual(page.get_by_text("not sent yet", exact=True).count(), 1)
        self.assertNotIn("pages", page.locator("dialog").inner_text())
        send = page.get_by_role("button", name="Send", exact=True)
        self.assertTrue(send.is_enabled())
        send.click()
        self.assertEqual(page.evaluate("[sent[0].text,sent[0].attachmentKeys,Object.isFrozen(sent[0].attachmentKeys),writes]"),
                         ["", ["file-one"], True, 0])
        page.get_by_role("button", name="Remove Notes <img src=x>.txt", exact=True).click()
        self.assertEqual(page.evaluate("[actions[0][0],actions[0][1].clientKey]"), ["remove_attachment", "file-one"])
        self.assertEqual(page.get_by_text("Notes <img src=x>.txt", exact=True).count(), 1)
        page.evaluate("""()=>{composer.setBusy(true);composer.setAttachments([
            {clientKey:'file-one',filename:'Notes <img src=x>.txt',phase:'unknown'},
            {clientKey:'file-two',filename:'Newer fictional file.txt',phase:'attached'}]);}""")
        self.assertTrue(send.is_disabled())
        page.get_by_role("textbox").fill("Newer unsent words")
        page.evaluate("()=>composer.setBusy(false)")
        self.assertTrue(send.is_disabled())
        self.assertEqual(page.get_by_text("send status unavailable", exact=True).count(), 1)
        self.assertFalse(page.evaluate("()=>composer.clear(composer.snapshot().revision)"))
        page.evaluate("""()=>composer.setAttachments([
            {clientKey:'file-one',filename:'Notes <img src=x>.txt',phase:'sent'},
            {clientKey:'file-two',filename:'Newer fictional file.txt',phase:'attached'}])""")
        self.assertFalse(page.evaluate("()=>composer.clear(sent[0].revision)"))
        self.assertEqual(page.evaluate("composer.snapshot().attachmentKeys"), ["file-two"])
        self.assertEqual(page.get_by_role("textbox").input_value(), "Newer unsent words")
        self.assertFalse(page.evaluate("""()=>{try{composer.setAttachments([
            {clientKey:'file-one',filename:'First.txt',phase:'attached'},
            {clientKey:'file-one',filename:'Duplicate.txt',phase:'attached'}]);return true;}catch(e){return false;}}"""))
        self.assertEqual(page.evaluate("composer.snapshot().attachmentKeys"), ["file-two"])
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_function("()=>dialog.getBoundingClientRect().width===390")
        for chip in page.locator(".ps-guide-file-chip").all():
            box = chip.bounding_box()
            self.assertGreaterEqual(box["x"], 0)
            self.assertLessEqual(box["x"] + box["width"], 390)
        self.assertTrue(page.evaluate("()=>composer.clear(composer.snapshot().revision)"))
        self.assertEqual(page.locator(".ps-guide-file-chip").count(), 0)
        self.assertTrue(send.is_disabled())
        self.assertEqual(page.evaluate("writes"), 0)

    def test_saved_composer_words_grow_and_scroll_when_opened_and_resized_without_sending(self):
        page = self.page("guide-view.js", "guide-shell.js", "guide-conversation.js")
        page.add_style_tag(path=str(ROOT / "static/css/resume-intake.css"))
        saved = "\n".join("Saved fictional line " + str(i) for i in range(20))
        page.evaluate("""text=>{window.sends=0;window.dialog=document.createElement('dialog');document.body.append(dialog);
            const frame=PeerSlateGuideView.frame(dialog,{publicationState:'unknown',onAction:()=>{}});
            window.composer=PeerSlateGuideConversation.createComposer(frame.composer,{onSend:()=>sends++,onAction:()=>{}});
            composer.restore(text,composer.snapshot().revision);dialog.showModal();
            window.binding=PeerSlateGuideShell.bind(dialog,frame.grip,{dragHandle:frame.header});}""", saved)
        page.wait_for_function("()=>{const t=document.querySelector('.ps-guide-compose-words');return t.style.overflowY==='auto'&&t.getBoundingClientRect().height===132}")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_function("()=>dialog.getBoundingClientRect().width===390")
        self.assertEqual(page.get_by_role("textbox", name="Message to the Guide").input_value(), saved)
        self.assertEqual(page.evaluate("[sends,composer.snapshot().revision]"), [0, 1])


if __name__ == "__main__":
    unittest.main()

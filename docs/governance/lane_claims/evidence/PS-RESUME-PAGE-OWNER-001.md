# Owner resume page (Lane D package 5): acceptance and execution record

**Goal:** the owner's resume page at `/app/resume`, built to Pete's approved layout idea 1 "One story, told once" and the approved RP6 top, rendered read-only from the signed-in member's own private draft.

**Authority:** Pete, 2026-10-13: "You can do the resume work." Owner ref `role:owner/pete-chat-2026-10-13/claude-manager-local_4fefa9f6/resume-page-claude-writer`. Writer `agent:claude/2026-10-13/resume-page-owner` (Claude PC, Opus 5.5). Protected path; Codex PC is the independent exact-SHA reviewer; Pete's screenshot OK is part of done. Production, schema, configuration, enablement and paid AI calls are withheld.

**Design authority:** `concept-1.html` + `c1-*` pictures (layout idea 1); `rp6-B.html` + RP6 notes (approved top, rail); `PETE_DECISIONS_2026-10-11_evening.md` (beige frame, 12.5 px, Projects only once added, rail Ask grows smoothly when the main Ask card scrolls away and is instant under reduced motion, three-stone thinking, phone Jump to / rail Ask hidden / Credentials at a glance below Ask, Looking Ahead placeholder, 6a backdrop with hairline stones); build plan v2 §4; design rationale §2e/§2f/§6; the C1 width ruling (`.wrap = min(100% − 32px, 1240px)`, 268 px rail, 960 px fold).

## Rounds

- **D1 (merged, `996ea385`):** page shell, layout per concept 1, theme tokens, rail (section list, Credentials at a glance, compact Ask that grows on scroll), read-only sections from the owner's draft through one view-model adapter that follows the shared section order, phone layout, accessibility, the live left-column edge for the Guide. Behind a default-off page flag `PEERSLATE_RESUME_PAGE_ENABLED` (app config, read with `is True`) so today's editor, and every Guide/media/publication test that drives it, stays byte-for-byte the same when the flag is off. With the flag on, today's editor is unchanged and reachable with **Edit myself**.
- **D1d (Pete's second screenshot review):** Ask tabs at every width, the rail Ask always expanded, up to three skill lines with employer and dates, the Looking Ahead picture.
- **D2 (after B2):** Continue with the Guide beside Edit myself, the member's own Looking Ahead line, Projects, highlight tiles by reference with the "waiting for your OK" state (see the D2 round below).

## Integration decisions (D1)

- `/app/resume` is served by `resume_draft_routes.py` (PS-GUIDE-SERVER-001), which renders `templates/resume_editor.html`. No route, `app.py`, `base.html` or Guide file changes. The page reads only `GET /api/resume-drafts/me`; the identity is derived on the server.
- The page makes **no AI call**. Both Ask panels give the truthful unavailable state through a pluggable transport; the owner private preview is package 6.
- The workspace does not yet expose an accomplishment's parent role. Bullets with a parent attach to their role; others show in an owner-only "Highlights not linked to a role yet" list, so nothing saved disappears.
- Data the draft model doesn't hold yet (photo, contact details, highlight tiles, awards, Looking Ahead line, philosophy, "Let's talk") is absent, not invented; the adapter already accepts it so B2 / packages 6–7 swap in one place.

## D1 acceptance record (merged, squash `996ea385`, PR 1367)

D1's plan was `a5d19a70`; its 11 criteria (flag_off_unchanged, owner_identity, layout_concept1, rail, rail_ask_grow, truthful_ask, sections_render, phone, accessibility_motion, left_edge_token, review_and_delivery) all passed at the independently reviewed candidate `997ac8cd40046552d02122dbfabc8528f1d81a91` (`package_acceptance.py check`: PASS 11/11; merge preflight PASS; Azure CI 4582 green). That exact record is preserved on main at `996ea385` and in the branch history (`d33eaf4e`). Round D1d below supersedes only `rail_ask_grow` (Pete now wants the rail Ask always expanded); every other D1 behaviour must stay as it is.

## D1d round (Pete's second D1 screenshot review, 2026-10-13 late evening)

Spec: `PETE_DECISIONS_2026-10-11_evening.md`, "Resume D1 screenshot review, round 2", plus the manager's update that a skill with fewer than three lines has no filler and its lines are centred vertically in the panel. Changes: the main Ask card's three tabs at every width; the rail Ask always expanded (960 too); up to three skill lines with employer and dates, scrolling when they overflow; the member's Looking Ahead picture. Experience, the constellation and the cards stay as they are.

## D1d acceptance record (merged, squash `be2e9126`, PR 1373)

D1d's plan was `393a9de3`; its 6 criteria (ask_tabs, rail_ask_expanded, skill_lines, looking_ahead_picture, rest_unchanged, review_and_delivery) all passed at the independently reviewed candidate `147cd1fada2c594e59792f21f4e08d148680a257` (`package_acceptance.py check`: PASS 6/6; merge preflight PASS; PR CI 4602). That exact record is preserved in the branch history (`984ef6be`) and on main. Round D2 below must keep every D1 and D1d behaviour.

## D2 round (after B2): Edit myself / Guide hook, Looking Ahead, Projects, highlight tiles

Spec: the claim's D2 line; the manager's D2 brief (2026-10-14); approved-v2 and the build-D1 approved pictures; RP4 plan; design rationale 2e and 6 (items 11, 13); `PETE_DECISIONS_2026-10-11_evening.md`; B2 on main (`resume_section_for`, `highlight_refs`, the project normalizer, ruling `8eff4fc`). Six details the approved pictures don't draw are asked in coordination `Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_resume-D2-design-questions.md` with recommended defaults; this plan builds those defaults.

## D2 acceptance record (merged, squash `9360f192`)

D2's plan was `8049f220`; its 6 criteria (guide_entry, looking_ahead, projects, highlight_tiles, rest_unchanged, review_and_delivery) all passed at the independently reviewed candidate `e21456f3c6d80bd9531079ce3ce2ffa55e96ecf5` (`package_acceptance.py check`: PASS 6/6; guide-build exact re-check PASS, coordination `64205e6`; Pete's screenshot OK). That exact record is preserved in the branch history (`dc82b877`) and on main at `9360f192`. Round D2o below must keep every D1, D1d and D2 behaviour.

## D2o round: one section order, Experience before Skills

**Owner decision:** Pete's G6 ruling, one section order everywhere with Experience before Skills (2026-10-15, manager-confirmed), ref `role:owner/pete-chat-2026-10-15/claude-manager-16023c0e/section-order-experience-first`. It outranks the older claim outcome text that lists "Impact Statement, Skills, Experience"; the claim is not edited.

**Change:** the page's one view-model order `SECTION_ORDER` (`static/js/resume-page-model.js`) becomes Impact Statement, Experience, Skills, Projects, Education, Certifications, Awards, exactly the `RESUME_BASE_SECTION_ORDER` that Lane D package 6 round D6c sets (`work/2026-10-14-resume-page-public-001` at `755f8d5c`). The page's sections, rail list and phone Jump to all follow it.

**Lockstep with D6c:** main's shared constant still says Skills first until D6c merges (merge order B3m, then D6c: coordination `42f1c46`, `0f9aeb9`). The pinned order test therefore pins the page to the ruled order and accepts the shared constant in either state: equal to the page (after D6c) or the old Skills-first order (before D6c). It also pins the Guide's own tab order (`GUIDE_TAB_ORDER`, B3m) when present. Main stays green whichever merges first; after D6c merges, the old-order branch can be narrowed away.

## Acceptance plan (D2o, committed before code)

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-RESUME-PAGE-OWNER-001",
  "plan_sha": "f057f26039928bd244d2dd4e5079d9f1f6be9201",
  "baseline": [
    {
      "command": "python -B -m unittest tests.test_resume_page_owner tests.test_resume_page_owner_browser",
      "exit_code": 0,
      "observation": "Pre-change at a6910db9 (branch dc82b877 reconciled with main 6c14d8e2; owned paths equal main's D2 squash 9360f192), PEERSLATE_CHROME = Playwright Chromium 1234, ANTHROPIC_BASE_URL=http://127.0.0.1:9: 76 page tests PASS, 0 skipped. The page's SECTION_ORDER is Impact Statement, Skills, Experience, ...; the rendered sections run story, skills, experience, Looking Ahead, credentials and the nav reads Overview, Skills, Experience; the unit test pins the JS order equal to the Skills-first shared constant, so D6c's Experience-first base order fails it (D6c request 0f9aeb9, cross-claim pin)."
    }
  ],
  "criteria": [
    {
      "id": "section_order",
      "expected": "The owner page's one view-model order is Impact Statement, Experience, Skills, Projects, Education, Certifications, Awards (Pete's G6 ruling), equal to D6c's RESUME_BASE_SECTION_ORDER at 755f8d5c. The rendered sections and the rail/Jump to list put Experience before Skills; nothing else about any section changes.",
      "verification": "Unit test pins the JS literal to the ruled order and accepts the shared base constant only as equal to it or as the old Skills-first order, plus the Guide tab order when present; browser test pins section ids and nav labels Experience before Skills; both fail at the base code. The unit test also passes on a D6c tree (755f8d5c with this round's owned files overlaid)."
    },
    {
      "id": "rest_unchanged",
      "expected": "Every D1, D1d and D2 behaviour still passes; the flag-off /app/resume is unchanged (no template, route or server change); the page still makes no AI call and its only requests are the workspace read and the private draft commands.",
      "verification": "Full page suites (unit + browser with PEERSLATE_CHROME, skipped count reported), the browser module twice concurrently, no-Playwright skip proof, diff limited to the JS order, its comment and the two tests."
    },
    {
      "id": "review_and_delivery",
      "expected": "Each changed test fails at the base code; an independent reviewer the manager assigns passes the exact candidate (Protected); the merge is sequenced by the manager with B3m and D6c.",
      "verification": "Writer verification log (build-D2o), independent review receipt, merge preflight and current-target Azure CI."
    }
  ],
  "candidate_sha": "903c9136eaf53fd5b078dc70a409170456a6334a",
  "checks": [
    {
      "criterion_id": "section_order",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "903c9136eaf53fd5b078dc70a409170456a6334a",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_sections_render_in_the_approved_order_from_the_members_own_workspace",
      "observed": "The model's SECTION_ORDER is Impact Statement, Experience, Skills, Projects, Education, Certifications, Awards, equal to D6c's RESUME_BASE_SECTION_ORDER at 755f8d5c. The rendered sections run story, experience, skills, (projects,) looking-ahead, credentials, and the rail and Jump to read Overview, Experience, Skills, ...; Projects directly follows Skills, after Experience. The unit pin accepts the shared base constant only as the ruled order or the old Skills-first order and requires B3m's GUIDE_TAB_ORDER to equal the page's order; it passes on main, on D6c 755f8d5c and on B3m 00cd41b3 with this round's files overlaid. The reviewer's 7-case lockstep probe and two mutants (model order, builder order) behaved as expected; its own render at 1440 and 390 shows Experience before Skills.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-16T16:52:00Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_sections_render_in_the_approved_order_from_the_members_own_workspace"
      }
    },
    {
      "criterion_id": "rest_unchanged",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "903c9136eaf53fd5b078dc70a409170456a6334a",
      "source_ref": "tests/test_resume_page_owner.py:test_flag_off_renders_todays_editor_only",
      "observed": "The diff from main is only the two page scripts' order (and one comment each), the two owner test files and the evidence file; no template, CSS, route, server, schema or Guide file, so the flag-off page is unchanged. Page suites plus the Guide panel contract and the projection order test: 111 run, OK, 0 skipped; browser module twice concurrently 50/50 each, 0 skipped; without Playwright 77 run, 50 skipped, 0 errors. The reviewer's 5 affected modules ran 158 OK, 0 skipped, and its whole no-Playwright discover gave identical failure sets for candidate and main (8009 vs 8008 run, 16E/19F each, +1 the new builder test)."
    },
    {
      "criterion_id": "review_and_delivery",
      "result": "pass",
      "kind": "manual",
      "candidate_sha": "903c9136eaf53fd5b078dc70a409170456a6334a",
      "source_ref": "X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-16_claude-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-OWNER-001_D2o.md:Verdict",
      "observed": "Each changed test failed with the base page scripts (77 run, exactly the 4 changed tests failed). The independent Claude PC reviewer session:16023c0e-7189-420e-8a4d-11f8012a9713 passed the exact candidate with no Critical, Major or Minor findings (coordination ca3a1eb). The manager sequenced the merge: B3m merged first (17eaaaa4) and the test tolerates both base orders until D6c merges.",
      "provenance": {
        "observer_ref": "session:16023c0e-7189-420e-8a4d-11f8012a9713",
        "captured_at": "2026-10-16T17:57:18Z",
        "source_ref": "X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-16_claude-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-OWNER-001_D2o.md:Verdict"
      }
    }
  ]
}
```

## D2o writer verification (before independent review)

Plan `f057f260` (single parent, main `6c14d8e2`, evidence file only), adopted by merge. Logs in `X:/PeerSlate/Claude/plans/resume-page/build-D2o/`; Playwright Chromium 1234 via `PEERSLATE_CHROME`, `ANTHROPIC_BASE_URL=http://127.0.0.1:9`.
- RED: the four changed tests (unit order pin, unit builder order, browser section/nav order, browser Projects position) fail with the base page scripts (`red.txt`, `red2.txt`: 77 run, 4 failures).
- GREEN: page suites plus the Guide panel contract and the projection order test, 111 run, OK, 0 skipped (`green2.txt`); the browser module twice concurrently, 50/50 each, 0 skipped (`load-1.txt`, `load-2.txt`); without Playwright 77 run, 50 skipped, 0 errors (`no-playwright.txt`).
- Lockstep: the order unit module passes on D6c `755f8d5c` and on B3m `00cd41b3`, each with this round's four files overlaid (`unit-on-d6c.txt`, `unit-on-b3m.txt`); an overlay run caught the owner's name in the model comment (shared-logic rule), fixed in `02414083`.
- Screenshots at 1440 and 390 show Experience before Skills in the page and the rail/Jump to list (`screens/`).

## D2o independent review and delivery

The independent Claude PC reviewer (`session:16023c0e-7189-420e-8a4d-11f8012a9713`, read-only exports) **passed exact `903c9136eaf53fd5b078dc70a409170456a6334a`** with no findings (coordination `ca3a1eb`): scope and history checked, its own render at 1440 and 390, a 7-case lockstep probe, two mutants, the affected modules (158 OK, 0 skipped), the browser pair, the no-Playwright proof and a whole discover with identical failure sets. The receipt is bound to `903c9136`; this tail adds only the receipt and this evidence file. Merge order (manager): B3m first (`17eaaaa4`), then this round; D6c later narrows the old-order arm of the test. Merge is repository truth only: the page stays behind the default-off flag. No deployment, 8444 enablement, schema or paid call. The claim stays open for Lane D.

## D2 design answers and a known temporary gap (manager, after the candidate)

The manager answered "Defaults OK" for all six D2 questions (`24f844a`), as built in `824d7587`: Continue with the Guide left of Edit myself (gold; Edit myself outlined; feature-detected on `window.PeerSlateGuidePanel.open`; Edit myself first on phones); Looking Ahead shown once, in its section; the name fixed until a server label field exists; the Looking Ahead editor in place with no counter and no blank save; Projects with D91's fields, links never fetched, Add a project in Edit myself; tiles only from `highlight_refs`, resolved live, a row only for 2 to 4, the suggested state only when the Guide supplies a proposal.

**Known, temporary gap: Pete's page shows three hero tiles, the approved design shows four** (30+, $19.2M, 35%, 69%). B2 holds one `metric_value` per bullet, and Pete's "Team lead" bullet carries both 30+ and $19.2M, so only one of them can be a tile. The manager is asking PS-GUIDE-SERVER-001 for an optional per-tile metric selector on `highlight_refs`; D2 (or a D2b) uses it once it lands. No fourth tile is faked meanwhile. The build-D2 screenshots label the gap.

## D2 addition from the manager (after the plan): moved items

The manager added one item to D2 after the plan was committed, for the Guide server's B3b review: the owner page shows a privately moved item ("Move to", B3b) in its new place and type. The adapter follows a draft row's `conversion` descriptor only when it has exactly the seven keys (`state`, `base_record_type`, `destination_record_type`, `destination_parent_ref`, `base_content_token`, `base_access_revision`, `conversion_op_ref`), `state` is `confirmed_private`, and it agrees with `conversion_destination` {record_type, parent_key, values}; it then reads the item as that destination type, parent and values. Any other `conversion` hides the row rather than showing it in a place it no longer belongs; rows without one are unchanged. Edits of a moved item save as its destination type (B3b `_save_moved_item`). B3b isn't on main yet; the shape is taken from its candidate `48ca8780` (`ResumeDraftService._present_item`, `conversion_descriptor`) and proven against that exported tree (build-D2 `b3b-probe.txt`). The public copy is unchanged until Publish (D6a refuses meanwhile). Tests: `test_a_confirmed_move_shows_the_item_in_its_new_place_and_type`, `test_editing_a_moved_project_saves_as_its_destination_type`, `test_d2_flag_off_html_is_unchanged_by_a_confirmed_move` (all three fail at `4ca2fdc5`). It has no separate plan criterion (the plan text stays as committed); it is reviewed with this round.

## D2 correction round (guide-build review of `824d7587`: FAIL, F1 Medium)

**F1:** the draft version changed only inside `render()`, and a reload skipped `render()` while a page form had unsaved words, so after any other draft save an open form kept a stale `expected_draft_version`: every save got 409, the retry resent the same body, and the form that had just saved left its section blank. **Fix:**
- The draft version and each item's fingerprint (tokens plus values, proposed values and any move destination) are state, kept from every complete read and every command reply, even while a form stays open.
- A reload now always redraws the page but keeps, as they are, the sections that hold an open owner form (their words untouched); the section whose form just saved is redrawn, so it shows its new line, placeholder or Edit button.
- An uncertain attempt (no reply or 503) is resent exactly (same request id). On 409 the page re-reads the draft and, if this item is unchanged since its form opened, retries once with a fresh request id and the new version; if the item itself changed elsewhere, or the retry still conflicts, the words stay and the page says so. A fresh save never overwrites an item that changed after its form opened.
- **O1:** the "Saved privately" notice is cleared on any failed read.
- **O2 / manager's addition:** Looking Ahead is identified first by its placement (`presentation_section` `looking_ahead` or the "Looking Ahead" label alias, as `resume_section_for` does), then by the title "Looking Ahead" on a work entry as the fallback; a placement entry wins and only one line is shown. A renamed entry keeps its own title when edited.

RED at `824d7587`'s code (`build-D2/f1-red.log`): 5 of 6 new tests fail (two forms, today's editor meanwhile, an unheard save, the saved-notice carry-over, placement); the same-item honest-conflict test is a guard that passes at both. GREEN: page suites 76/76. The reviewer's probe now saves on the first click and the Looking Ahead section keeps its line and Edit button (`build-D2/reviewer-probe-after-fix.txt`; its 2nd scripted click times out only because the form had already closed after saving).

## D2 independent review and delivery

guide-build (`agent:claude/2026-10-14/guide-build`) failed `824d7587` with F1 Medium (coordination `4e41321`) and **passed the narrow re-check at exact `e21456f3c6d80bd9531079ce3ce2ffa55e96ecf5`** (coordination `64205e6`; note N1 accepted, N2 carried to the next round). **Owner's manual check:** Pete reviewed the D2 screenshots at https://claude.ai/artifact/CFU9JNoGWsVQujFt2G8dia and said "Resume looks good." (2026-10-15). The receipt is bound to `e21456f3`; this tail adds only the receipt and this evidence file. Merge is repository truth only: the page stays behind the default-off flag. No deployment, 8444 enablement, schema or paid call. The claim stays open for the next round (N2, and the fourth tile once the Guide server's per-tile metric selector lands).

## D1b revision (Pete's D1 screenshot review, 2026-10-13)

Pete approved the D1 look, the top-of-page phone Jump to bar and the three listed differences, and asked for two changes, made in the same claim and branch:

1. **"The career constellation stays the same on the desktop resume."** At 960 px and wider the constellation is now the live `/petec/resume` design (dark navy scene, curved path with junction and branch, glowing stops, legend, evolution card, stop details, skill chips, evidence card, outcomes strip, quote and trait row), re-implemented in this package's own files as a full-width band after the framed resume. From 960 to 1024 px it uses the live page's own stacked form; below 960 px the simplified phone constellation stays. Stops are placed on the live curves from the member's own dates (everything up to the first role before the junction, later roles on the main path, later education and certifications on the branch, future plans last); optional story pieces render only when the member has them. Nothing is member-specific; Pete's corrected facts exist only in the local screenshot harness.
2. **"Make the experience cards a little more vertical."** Portrait cards, three across on wide desktops, 332 px tall at 1440 (D1: 218 px), with the badge, company, dates, title, location, a 4-line description and "View full chapter".

The acceptance criteria above are unchanged; `layout_concept1`, `phone`, `sections_render` and `review_and_delivery` cover these changes, and the browser suite adds four D1b tests (band placement and text-only rendering, stacked/phone forms, portrait cards).

## D1c corrections (Codex D1b exact-SHA review of `5bf78e97`: FAIL, three findings + one note)

- **F1 (unreadable read shown as empty):** the page renders only a complete read (`items` array and `canonical_read: "ok"`). A malformed body, a non-OK status, a network failure or an incomplete read never becomes "empty": on first load it shows "Your resume can't be shown right now"; after a good read it keeps what was shown and says it is the last loaded version.
- **F2 (invented Present):** only `current_role === true` means Present, in the cards, the phone constellation and the band; a missing end date and no flag show the start alone. The hero headline uses only a role flagged current.
- **F3 (late Ask result overwrote newer typing):** completion is fenced on the box's edit revision and value; the sent question stays in the conversation and the box is never touched once the member types.
- **N1:** the page's footer restyling is removed; the footer stays with the trust-pages package.
- **Sweep (same class):** "Certified" only for a completed certification, and Credentials at a glance lists only completed ones; degree labels only from the saved status (paused shown as paused, never "Completed"; an in-progress degree is "Since" its start); saved highlights alone are not an empty resume; "Highlights not linked to a role yet" (unsupported while the API hides the link) became "More highlights from your experience".

## Dependencies routed (not in this claim)

- Enabling the page on 8444 needs `PEERSLATE_RESUME_PAGE_ENABLED: True` in Lane A's private-site config (`tools/local_reviewer/manager.py`, PS-ONBOARDING-PRIVATE-SITES-001).
- Centered top navigation, the Cairn logo, the green-square favicon and footer A live in `base.html` / the shared header (PS-PUBLIC-TRUST-PAGES-001, then package 11).
- The accomplishment parent link in the draft workspace (`services/resume_draft_service.py`, PS-GUIDE-SERVER-001) or the Guide working set for the page.
- The Guide panel can replace its fallback L with `PeerSlateResumePage.leftColumnEdge()` / `--resume-page-left-edge` (PS-GUIDE-PANEL-001).

## Independent review and delivery (D1)

Codex PC (`session:01a132fe-1f81-77f3-8821-d53d157ca025`) failed D1b `5bf78e97` with three findings (unreadable read shown as empty, invented Present, late Ask result overwriting newer typing) and one footer note, then **passed exact D1c `997ac8cd40046552d02122dbfabc8528f1d81a91`** at 2026-10-13T18:28:08Z with no remaining required finding (`X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-13_codex-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-OWNER-001_D1c.md`). Its native exact-candidate verification ran all 39 page tests (PASS) and an independent probe over the real owner route. The receipt is bound to that SHA. This tail adds only the receipt and this evidence file.

Merge is repository truth only: the page stays behind the default-off `PEERSLATE_RESUME_PAGE_ENABLED` flag, so nothing changes for any user. No deployment, 8444 enablement, schema or paid call. The claim stays open for round D2.

## D1d independent review and delivery

Codex PC (`session:01a132fe-1f81-77f3-8821-d53d157ca025`) failed `8258d321` with one P2 finding: the Looking Ahead image guard accepted an encoded traversal (`/static/%2e%2e/healthz`). It then **passed the narrow re-check at exact `147cd1fada2c594e59792f21f4e08d148680a257`** (2026-10-14T02:45:42Z, no remaining finding; `X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-13_codex-pc_to-claude-pc_RECHECK_PS-RESUME-PAGE-OWNER-001_D1d-F1.md`). Candidate history this round: `272d13c4` (D1d), superseded by `8258d321` (the manager's parity correction: "Employer · Role · dates" plus "See it in the role →"), superseded by `147cd1fa` (one same-origin `/static/` guard for every image source). The receipt is bound to `147cd1fa`; this tail adds only the receipt and this evidence file.

Merge is repository truth only: the page stays behind the default-off `PEERSLATE_RESUME_PAGE_ENABLED` flag. No deployment, 8444 enablement, schema or paid call. The claim stays open for D2.

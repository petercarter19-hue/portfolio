# Owner resume page (Lane D package 5): acceptance and execution record

**Goal:** the owner's resume page at `/app/resume`, built to Pete's approved layout idea 1 "One story, told once" and the approved RP6 top, rendered read-only from the signed-in member's own private draft.

**Authority:** Pete, 2026-10-13: "You can do the resume work." Owner ref `role:owner/pete-chat-2026-10-13/claude-manager-local_4fefa9f6/resume-page-claude-writer`. Writer `agent:claude/2026-10-13/resume-page-owner` (Claude PC, Opus 5.5). Protected path; Codex PC is the independent exact-SHA reviewer; Pete's screenshot OK is part of done. Production, schema, configuration, enablement and paid AI calls are withheld.

**Design authority:** `concept-1.html` + `c1-*` pictures (layout idea 1); `rp6-B.html` + RP6 notes (approved top, rail); `PETE_DECISIONS_2026-10-11_evening.md` (beige frame, 12.5 px, Projects only once added, rail Ask grows smoothly when the main Ask card scrolls away and is instant under reduced motion, three-stone thinking, phone Jump to / rail Ask hidden / Credentials at a glance below Ask, Looking Ahead placeholder, 6a backdrop with hairline stones); build plan v2 §4; design rationale §2e/§2f/§6; the C1 width ruling (`.wrap = min(100% − 32px, 1240px)`, 268 px rail, 960 px fold).

## Rounds

- **D1 (this candidate):** page shell, layout per concept 1, theme tokens, rail (section list, Credentials at a glance, compact Ask that grows on scroll), read-only sections from the owner's draft through one view-model adapter that follows the shared section order, phone layout, accessibility, the live left-column edge for the Guide. Behind a default-off page flag `PEERSLATE_RESUME_PAGE_ENABLED` (app config, read with `is True`) so today's editor, and every Guide/media/publication test that drives it, stays byte-for-byte the same when the flag is off. With the flag on, today's editor is unchanged and reachable with **Edit myself**.
- **D2 (after B2):** Edit myself / Guide Me hooks in the new page, Looking Ahead editing, Projects, highlight tiles "waiting for your OK", Hidden (n) markers.

## Integration decisions (D1)

- `/app/resume` is served by `resume_draft_routes.py` (PS-GUIDE-SERVER-001), which renders `templates/resume_editor.html`. No route, `app.py`, `base.html` or Guide file changes. The page reads only `GET /api/resume-drafts/me`; the identity is derived on the server.
- The page makes **no AI call**. Both Ask panels give the truthful unavailable state through a pluggable transport; the owner private preview is package 6.
- The workspace does not yet expose an accomplishment's parent role. Bullets with a parent attach to their role; others show in an owner-only "Highlights not linked to a role yet" list, so nothing saved disappears.
- Data the draft model doesn't hold yet (photo, contact details, highlight tiles, awards, Looking Ahead line, philosophy, "Let's talk") is absent, not invented; the adapter already accepts it so B2 / packages 6–7 swap in one place.

## Acceptance plan (committed before code)

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-RESUME-PAGE-OWNER-001",
  "plan_sha": "a5d19a703a464803f9621e8d2149c2bef0a61df3",
  "baseline": [
    {
      "command": "python -B -m unittest tests.test_resume_editor_http tests.test_resume_draft_routes tests.test_resume_intake_routes tests.test_resume_publication_routes -q",
      "exit_code": 0,
      "observation": "Pre-change at fb1468fb: 92 editor/draft/intake/publication route tests PASS in 11.1s (in-memory stores, fake providers, process-local placeholder key, no paid calls). No owner resume page exists yet; /app/resume renders only today's editor."
    }
  ],
  "criteria": [
    {
      "id": "flag_off_unchanged",
      "expected": "With PEERSLATE_RESUME_PAGE_ENABLED absent, false or any non-True value, /app/resume renders today's editor with no new markup, styles or scripts, and every existing editor/Guide/media/publication suite passes unchanged.",
      "verification": "Unit render tests; normalized flag-off HTML at base vs candidate; affected suites and the whole no-Playwright discover at base vs candidate."
    },
    {
      "id": "owner_identity",
      "expected": "The page derives identity on the server, sends no owner id, renders only the signed-in member's own workspace, redirects signed-out visitors to sign in, and escapes the member name.",
      "verification": "Unit tests (other member never rendered, ?owner= ignored, sign-in redirect, hostile display name) and the browser cross-member check."
    },
    {
      "id": "layout_concept1",
      "expected": "Desktop (>=960px): centred min(100%-32px,1240px) wrapper, 268px left rail, beige frame on the #3f6a51 backdrop with fixed hairline-outline stones; overview (hero + main Ask), then My Story, Skills in Practice, Experience (half-height cards, View full chapter in place), Projects only when present, Looking Ahead (placeholder until written), Credentials, Career constellation; 12.5px body text; no sideways scroll.",
      "verification": "Browser order/geometry/type checks and side-by-side screenshots at 1440x900, 1280, 960 and 390 against concept-1 / RP6 top."
    },
    {
      "id": "rail",
      "expected": "Rail order is section list, Credentials at a glance, Ask; the list shows only sections with content in page order and marks the current section; Credentials at a glance shows up to four real rows (completed degree, upcoming degree, certification, award).",
      "verification": "Browser rail tests and the unit template order test."
    },
    {
      "id": "rail_ask_grow",
      "expected": "The rail Ask starts compact and grows smoothly (CSS transition) when the main Ask card scrolls away and the rail has room, shrinks back when the card returns, is instant under reduced motion, and keeps its hidden part inert while compact.",
      "verification": "Browser scroll tests with normal and reduced motion and a short window."
    },
    {
      "id": "truthful_ask",
      "expected": "No AI request is made; a question gets 'Ask AI isn't available right now.' with the question kept; the three-stone thinking state shows only while a transport request is pending; answers render in place as text.",
      "verification": "Static fetch/sink checks; browser unavailable and fake-transport tests."
    },
    {
      "id": "sections_render",
      "expected": "Sections render read-only from the draft (proposed over saved values) through one adapter whose order equals the shared Guide order; empty sections are absent; member text is never interpreted as markup; saved changes re-render the page.",
      "verification": "Browser render, hostile-text and refresh tests; unit order test against GUIDE_SECTION_ORDER when present."
    },
    {
      "id": "phone",
      "expected": "Below 960px: one column at most 760px wide, a Jump to control listing the member's sections, rail Ask hidden, Credentials at a glance just below the Ask card, no sideways scroll at 390 and 320; 960px keeps the desktop layout.",
      "verification": "Browser tests at 320, 390, 959 and 960."
    },
    {
      "id": "accessibility_motion",
      "expected": "WCAG 2.2 AA: named landmarks/regions, one page h1, keyboard section navigation moves focus, controls at least 24x24px, AA text contrast for every token pair, motion removed under reduced motion, light theme only.",
      "verification": "Unit contrast/motion/theme tests; browser keyboard and target-size tests."
    },
    {
      "id": "left_edge_token",
      "expected": "The page publishes the live left-column edge L for the Guide: 284 at 960, 288 at 1280, 416 at 1536, 0 below 960, matching the C1 ruling.",
      "verification": "Browser test of PeerSlateResumePage.leftColumnEdge()."
    },
    {
      "id": "review_and_delivery",
      "expected": "Affected suites pass normally and under load, the whole no-Playwright discover shows no new failure, Codex PC independently passes the exact candidate, and Pete's screenshot OK is recorded before merge.",
      "verification": "Verification receipt, independent review receipt, screenshot packet, merge preflight and current-target Azure CI."
    }
  ],
  "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
  "checks": [
    {
      "criterion_id": "flag_off_unchanged",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "tests/test_resume_page_owner.py:test_flag_off_renders_todays_editor_only",
      "observed": "Flag absent, False, 'true' and 1 render no page markup, CSS or scripts and every legacy editor id once; whitespace-normalized /app/resume HTML equals the base template rendered through the same app (editor-only and intake+media+publication+synthesis); affected editor/draft/intake/publication/media suites 271/271 PASS and the whole no-Playwright discover has identical failure sets at base fb1468fb and the candidate (16 errors / 19 failures each). Independently: reviewer saw identical footer styles flag on/off."
    },
    {
      "criterion_id": "owner_identity",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "tests/test_resume_page_owner.py:test_identity_is_server_derived_and_other_members_never_render",
      "observed": "The page writes no owner key, ?owner= is ignored, the other member's role never renders (unit and browser), signed-out requests redirect to sign-in, and a hostile display name is escaped in every server-rendered slot."
    },
    {
      "criterion_id": "layout_concept1",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_sections_render_in_the_approved_order_from_the_members_own_workspace",
      "observed": "Real browser at 1440: sections in the approved order, 12.5px body text, no sideways scroll; desktop constellation is the live band (Pete's D1 review) and experience cards are portrait (332px at 1440); side-by-side screenshots at 1440/1280/960/390 and the constellation close-up against live are in the screenshot packet. Pete approved the D1 look on 2026-10-13 and asked for the two changes D1b implements; the revised screenshots are for his glance after merge (flag stays default-off).",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-13T18:05:00Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_sections_render_in_the_approved_order_from_the_members_own_workspace"
      }
    },
    {
      "criterion_id": "rail",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_sections_render_in_the_approved_order_from_the_members_own_workspace",
      "observed": "Rail order is section list, Credentials at a glance, Ask; the list holds only rendered sections in page order and marks the current one; the glance shows completed degree, upcoming degree, completed certification (status-truthful after D1c).",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-13T18:05:00Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_sections_render_in_the_approved_order_from_the_members_own_workspace"
      }
    },
    {
      "criterion_id": "rail_ask_grow",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_rail_ask_grows_smoothly_when_the_main_card_scrolls_away",
      "observed": "Compact with an inert hidden part at the top; grows with a non-zero transition after the main card scrolls away and shrinks back; instant under reduced motion; stays compact in a 560px-tall window.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-13T18:05:00Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_rail_ask_grows_smoothly_when_the_main_card_scrolls_away"
      }
    },
    {
      "criterion_id": "truthful_ask",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_late_unavailable_keeps_newer_typing",
      "observed": "No AI request exists (one fetch, no /api/ literal); a question gets the unavailable reply with the question kept; three stones show only while a fake request is pending; answers render as text; delayed answer and delayed unavailable never touch newer typing (D1b F3, independently reproduced fixed).",
      "provenance": {
        "observer_ref": "session:01a132fe-1f81-77f3-8821-d53d157ca025",
        "captured_at": "2026-10-13T18:28:08Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_late_unavailable_keeps_newer_typing"
      }
    },
    {
      "criterion_id": "sections_render",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_canonical_outage_after_a_good_read_keeps_what_was_shown",
      "observed": "Sections render read-only from proposed-over-saved values through one adapter in the shared Guide order; hostile text stays text; saved changes re-render; only a complete read renders, an outage or malformed body is never shown as empty and a later failure keeps the last good content; Present only from current_role true (D1b F1/F2, independently reproduced fixed).",
      "provenance": {
        "observer_ref": "session:01a132fe-1f81-77f3-8821-d53d157ca025",
        "captured_at": "2026-10-13T18:28:08Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_canonical_outage_after_a_good_read_keeps_what_was_shown"
      }
    },
    {
      "criterion_id": "phone",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_phone_layout_folds_below_960",
      "observed": "Below 960px: one column, Jump to lists the member's sections and moves focus, rail Ask hidden, glance below the Ask card, no sideways scroll at 390 and 320; 960 keeps the desktop layout; the phone constellation card replaces the band.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-13T18:05:00Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_phone_layout_folds_below_960"
      }
    },
    {
      "criterion_id": "accessibility_motion",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "tests/test_resume_page_owner.py:test_text_colour_pairs_meet_wcag_aa",
      "observed": "Every page text token pair meets AA (4.5:1; large numbers and non-text 3:1); reduced motion removes transitions and the stone animation; no dark-theme rules; browser checks prove focus moves with in-page links and no control under 24x24px."
    },
    {
      "criterion_id": "left_edge_token",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_live_left_column_edge_matches_the_shared_guide_rule",
      "observed": "leftColumnEdge() is 284 at 960, 288 at 1280, 416 at 1536 and 0 below 960, matching the C1 ruling.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-13T18:05:00Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_live_left_column_edge_matches_the_shared_guide_rule"
      }
    },
    {
      "criterion_id": "review_and_delivery",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "997ac8cd40046552d02122dbfabc8528f1d81a91",
      "source_ref": "X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-13_codex-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-OWNER-001_D1c.md",
      "observed": "Codex PC independently PASSED exact 997ac8cd (no remaining finding) after a D1b FAIL whose F1-F3/N1 are fixed with tests that fail at 5bf78e97; writer evidence: 39/39 page tests, 25/25 twice concurrently, 39 + 271 affected concurrently, no-Playwright 39 run/25 skipped, identical whole-discover failure sets vs base. Pete reviewed the D1 screenshots and approved the look with two changes, now built; normal current-target Azure CI follows in the PR. Details: X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_REQUEST_PS-RESUME-PAGE-OWNER-001_D1c.md"
    }
  ]
}
```

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

## Independent review and delivery

Codex PC (`session:01a132fe-1f81-77f3-8821-d53d157ca025`) failed D1b `5bf78e97` with three findings (unreadable read shown as empty, invented Present, late Ask result overwriting newer typing) and one footer note, then **passed exact D1c `997ac8cd40046552d02122dbfabc8528f1d81a91`** at 2026-10-13T18:28:08Z with no remaining required finding (`X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-13_codex-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-OWNER-001_D1c.md`). Its native exact-candidate verification ran all 39 page tests (PASS) and an independent probe over the real owner route. The receipt is bound to that SHA. This tail adds only the receipt and this evidence file.

Merge is repository truth only: the page stays behind the default-off `PEERSLATE_RESUME_PAGE_ENABLED` flag, so nothing changes for any user. No deployment, 8444 enablement, schema or paid call. The claim stays open for round D2.

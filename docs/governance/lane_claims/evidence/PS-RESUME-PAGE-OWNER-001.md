# Owner resume page (Lane D package 5): acceptance and execution record

**Goal:** the owner's resume page at `/app/resume`, built to Pete's approved layout idea 1 "One story, told once" and the approved RP6 top, rendered read-only from the signed-in member's own private draft.

**Authority:** Pete, 2026-10-13: "You can do the resume work." Owner ref `role:owner/pete-chat-2026-10-13/claude-manager-local_4fefa9f6/resume-page-claude-writer`. Writer `agent:claude/2026-10-13/resume-page-owner` (Claude PC, Opus 5.5). Protected path; Codex PC is the independent exact-SHA reviewer; Pete's screenshot OK is part of done. Production, schema, configuration, enablement and paid AI calls are withheld.

**Design authority:** `concept-1.html` + `c1-*` pictures (layout idea 1); `rp6-B.html` + RP6 notes (approved top, rail); `PETE_DECISIONS_2026-10-11_evening.md` (beige frame, 12.5 px, Projects only once added, rail Ask grows smoothly when the main Ask card scrolls away and is instant under reduced motion, three-stone thinking, phone Jump to / rail Ask hidden / Credentials at a glance below Ask, Looking Ahead placeholder, 6a backdrop with hairline stones); build plan v2 §4; design rationale §2e/§2f/§6; the C1 width ruling (`.wrap = min(100% − 32px, 1240px)`, 268 px rail, 960 px fold).

## Rounds

- **D1 (merged, `996ea385`):** page shell, layout per concept 1, theme tokens, rail (section list, Credentials at a glance, compact Ask that grows on scroll), read-only sections from the owner's draft through one view-model adapter that follows the shared section order, phone layout, accessibility, the live left-column edge for the Guide. Behind a default-off page flag `PEERSLATE_RESUME_PAGE_ENABLED` (app config, read with `is True`) so today's editor, and every Guide/media/publication test that drives it, stays byte-for-byte the same when the flag is off. With the flag on, today's editor is unchanged and reachable with **Edit myself**.
- **D1d (Pete's second screenshot review):** Ask tabs at every width, the rail Ask always expanded, up to three skill lines with employer and dates, the Looking Ahead picture.
- **D2 (after B2):** Edit myself / Guide Me hooks in the new page, Looking Ahead editing, Projects, highlight tiles "waiting for your OK", Hidden (n) markers.

## Integration decisions (D1)

- `/app/resume` is served by `resume_draft_routes.py` (PS-GUIDE-SERVER-001), which renders `templates/resume_editor.html`. No route, `app.py`, `base.html` or Guide file changes. The page reads only `GET /api/resume-drafts/me`; the identity is derived on the server.
- The page makes **no AI call**. Both Ask panels give the truthful unavailable state through a pluggable transport; the owner private preview is package 6.
- The workspace does not yet expose an accomplishment's parent role. Bullets with a parent attach to their role; others show in an owner-only "Highlights not linked to a role yet" list, so nothing saved disappears.
- Data the draft model doesn't hold yet (photo, contact details, highlight tiles, awards, Looking Ahead line, philosophy, "Let's talk") is absent, not invented; the adapter already accepts it so B2 / packages 6–7 swap in one place.

## D1 acceptance record (merged, squash `996ea385`, PR 1367)

D1's plan was `a5d19a70`; its 11 criteria (flag_off_unchanged, owner_identity, layout_concept1, rail, rail_ask_grow, truthful_ask, sections_render, phone, accessibility_motion, left_edge_token, review_and_delivery) all passed at the independently reviewed candidate `997ac8cd40046552d02122dbfabc8528f1d81a91` (`package_acceptance.py check`: PASS 11/11; merge preflight PASS; Azure CI 4582 green). That exact record is preserved on main at `996ea385` and in the branch history (`d33eaf4e`). Round D1d below supersedes only `rail_ask_grow` (Pete now wants the rail Ask always expanded); every other D1 behaviour must stay as it is.

## D1d round (Pete's second D1 screenshot review, 2026-10-13 late evening)

Spec: `PETE_DECISIONS_2026-10-11_evening.md`, "Resume D1 screenshot review, round 2", plus the manager's update that a skill with fewer than three lines has no filler and its lines are centred vertically in the panel. Changes: the main Ask card's three tabs at every width; the rail Ask always expanded (960 too); up to three skill lines with employer and dates, scrolling when they overflow; the member's Looking Ahead picture. Experience, the constellation and the cards stay as they are.

## Acceptance plan (D1d, committed before code)

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-RESUME-PAGE-OWNER-001",
  "plan_sha": "393a9de3fc4d39e5b9be2633a2edfa39b4f13154",
  "baseline": [
    {
      "command": "python -B -m unittest tests.test_resume_page_owner tests.test_resume_page_owner_browser -q",
      "exit_code": 0,
      "observation": "Pre-change at 53b4fc9b (tree equals accepted main 7dff6365, which carries D1 996ea385): 39 page tests PASS in 18.4s (fictional members, recorded workspace at the draft-service boundary, process-local placeholder key, no AI call). The main Ask card has no tabs; the rail Ask starts compact and grows when the main card scrolls away; the Skills in Practice panel shows only the skill's own summary line with no employer or dates; Looking Ahead always shows a generic stock picture."
    }
  ],
  "criteria": [
    {
      "id": "ask_tabs",
      "expected": "At 1440, 960 and 390 the main Ask card's mountain header holds a pill tab bar 'Ask a question' (selected by default) / 'Career highlights' / 'Compare a job' with a 'Soon' badge, matching rp6-d-first-owner. They are real tabs: tablist/tab/tabpanel, aria-selected and aria-controls, roving tabindex, Left/Right/Home/End move and select, visible focus, targets at least 24px. Ask a question shows today's chips; Compare a job shows only the v3 Coming soon line with no working control; Career highlights shows a Placeholder tag and one plain line saying the Guide will draft highlights from the published resume for the member's OK, with no invented story. The question box and lock line stay visible in every tab and a question asked from any tab still gets the truthful unavailable reply.",
      "verification": "Browser tests at 1440, 960 and 390 (roles, keyboard, box reachable per tab, unavailable reply from each tab, target sizes); unit template test; screenshots of all three tabs beside rp6-d-first-owner."
    },
    {
      "id": "rail_ask_expanded",
      "expected": "On desktop (960px and wider) the rail Ask is the full approved panel from the first screen: mountain header art, 'The person behind the experience.', 'Pick a question, or type your own', three question choices, the box and the lock line, with no compact state, no grow-on-scroll, no inert part and no size animation; it stays the same after scrolling and under reduced motion; a rail taller than the window still scrolls with the page; below 960px the rail and its Ask stay hidden.",
      "verification": "Browser tests at 1440x900, 960x900, a short window and reduced motion; unit static test that the compact/grow code is gone; rail screenshots at 1440 and 960."
    },
    {
      "id": "skill_lines",
      "expected": "For the selected skill the panel lists every resume line that shows it, at most three, each role line with its role's employer and dates ('Employer · dates') underneath. Lines are derived read-only in resume-page-model.js from the member's own draft (skill name and summary, role-linked accomplishments and roles) by a generic rule, never member-specific code; nothing is invented and a skill with no line stays a plain label. Lines that fit are centred vertically in the panel box; lines that overflow scroll in one named, keyboard-focusable region with an always-visible scroll bar, never nested. The first skill with lines is open on load. Member text stays text.",
      "verification": "Browser tests: one/two/three-line skills, a fourth match never shown, employer and dates, centring at 1440 and 960, overflow scroll with a visible bar and no nested scroller, hostile text; adapter unit cases; close-ups with one and three lines."
    },
    {
      "id": "looking_ahead_picture",
      "expected": "When the view model carries a Looking Ahead picture with a local /static/ path, it fills the rp-ahead__pic slot beside the section (desktop) with its phone variant below 960px and its alt text; with no picture there is no picture box and the text spans the card; the Looking Ahead layout and placeholder are otherwise unchanged. Pete's Hawaii picture appears only through the screenshot fixture data.",
      "verification": "Browser tests with and without a picture at 1440 and 390 (non-local src ignored); full-page screenshots against c1-desktop-full."
    },
    {
      "id": "rest_unchanged",
      "expected": "Flag-off /app/resume HTML equals the base; every D1 behaviour other than the replaced grow-on-scroll still passes (identity, order, rail, truthful reads and dates, fenced Ask, constellation band, portrait cards, phone fold, left edge 284/288/416/0, keyboard, AA contrast, light only); Experience, the constellation and the cards look the same.",
      "verification": "The full page suites, normalized flag-off HTML base vs candidate, affected suites and the whole no-Playwright discover base vs candidate with identical failure sets; screenshots at 1440, 1280, 960 and 390."
    },
    {
      "id": "review_and_delivery",
      "expected": "Each new test fails at 996ea385; the affected browser suite passes twice concurrently and alongside the affected suites under load; the browser module skips cleanly without Playwright; Codex PC independently passes the exact candidate; Pete's screenshot OK is recorded before merge.",
      "verification": "Writer verification log, independent review receipt, screenshot packet build-D1d, merge preflight and current-target Azure CI."
    }
  ],
  "candidate_sha": "147cd1fada2c594e59792f21f4e08d148680a257",
  "checks": [
    {
      "criterion_id": "ask_tabs",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "147cd1fada2c594e59792f21f4e08d148680a257",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_main_ask_has_three_real_tabs_at_every_width",
      "observed": "Real browser at 1440, 960 and 390: the main Ask header holds tabs 'Ask a question' (selected, tabindex 0) / 'Career highlights' / 'Compare a job Soon', each a role=tab with its labelled tabpanel, at least 24px and fully inside the card; Career highlights shows the Placeholder tag and the one Guide line, Compare a job the Coming soon line, neither with any control; the box and lock line stay visible in every tab. The keyboard test proves Left/Right/Home/End select and focus with roving tabindex and a solid focus outline, and a question from each tab gets the truthful unavailable reply. Screenshots of all three tabs at 1440/960/390 beside rp6-d-first-owner in build-D1d/screens/compare.html.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-14T01:40:00Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_main_ask_has_three_real_tabs_at_every_width"
      }
    },
    {
      "criterion_id": "rail_ask_expanded",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "147cd1fada2c594e59792f21f4e08d148680a257",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_rail_ask_is_always_the_full_panel_at_1440_and_960",
      "observed": "At 1440x900 and 960x900 the rail Ask shows the title, 'Pick a question, or type your own', three choices, the box, the lock line and the header art (opacity 1) from the first screen, with no inert part and no compact state, and is identical after scrolling away and back; under reduced motion it is the same with no transition; in a 560px window the rail scrolls with the page and the box is reachable; at 959 the rail stays hidden. Unit test proves the compact/grow code and CSS are gone.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-14T01:40:00Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_rail_ask_is_always_the_full_panel_at_1440_and_960"
      }
    },
    {
      "criterion_id": "skill_lines",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "147cd1fada2c594e59792f21f4e08d148680a257",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_skill_lines_are_centred_when_they_fit_and_scroll_when_they_overflow",
      "observed": "Up to three lines per skill, derived read-only in resume-page-model.js skillLines() from the draft's skill name/summary and role-linked accomplishments (summary match, lead-in label, whole-phrase mention; no member-specific code); a fourth match is never shown. Each role line shows 'Employer · Role · dates' (the planned 'Employer · dates' plus the role, per approved picture c1 and the manager's parity correction) and a keyboard-reachable 'See it in the role →' link that opens and focuses that role's chapter. Lines that fit are centred vertically at 1440 and 960; overflowing lines start at the top and scroll in one focusable named region with an always-visible bar (the drawn bar pages on track click and scrolls on thumb drag), with no nested scroller. Hostile text stays text; the first skill with lines opens on load.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-14T01:40:00Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_skill_lines_are_centred_when_they_fit_and_scroll_when_they_overflow"
      }
    },
    {
      "criterion_id": "looking_ahead_picture",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "147cd1fada2c594e59792f21f4e08d148680a257",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_looking_ahead_shows_the_members_picture_or_no_box",
      "observed": "Without a picture there is no picture box and the text spans the card; a remote src is ignored; a local /static/ picture fills rp-ahead__pic beside the text at 1440 with its alt as text, and at 390 the phone variant is the current source. After Codex F1 every image source (Looking Ahead src and phoneSrc, hero photo) passes one guard, staticImagePath(): 16 traversal, encoded, backslash, scheme, host, query and fragment forms are rejected with the text or initials fallback and nothing outside /static/ is requested (test_every_image_source_rejects_traversal_and_foreign_paths). Pete's Hawaii picture appears only through the screenshot fixture data.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-14T01:40:00Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_looking_ahead_shows_the_members_picture_or_no_box"
      }
    },
    {
      "criterion_id": "rest_unchanged",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "147cd1fada2c594e59792f21f4e08d148680a257",
      "source_ref": "tests/test_resume_page_owner.py:test_flag_off_renders_todays_editor_only",
      "observed": "Flag-off /app/resume HTML equals the base for both flag sets; every remaining D1 test passes (page suites 52/52 at the candidate); whole no-Playwright discover from git exports, base 7dff6365 (7692 run, 16E/19F) vs D1d candidate 272d13c4 (7703 run, 16E/19F), identical failure sets, and the later 8258d321 and 147cd1fa deltas touch only the page's own files; 10 affected suites 317/317 under load; Experience, the constellation and the cards are visually unchanged in the 1440/1280/960/390 screenshots."
    },
    {
      "criterion_id": "review_and_delivery",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "147cd1fada2c594e59792f21f4e08d148680a257",
      "source_ref": "X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-13_codex-pc_to-claude-pc_RECHECK_PS-RESUME-PAGE-OWNER-001_D1d-F1.md",
      "observed": "Codex PC independently FAILED 8258d321 with one P2 finding (image guard accepted /static/%2e%2e/healthz) and then PASSED the narrow re-check at exact 147cd1fa with no remaining finding (52/52 page tests, 18 negative browser cases, zero outside-static image requests). Writer evidence at the candidate: page suites 52/52; browser suite twice concurrently 32/32 and 32/32; no-Playwright 52 run / 32 skipped / 0 errors; each new test failed at its predecessor (14 at 996ea385, 2 at 8258d321). Pete approved the D1 look in his round-2 screenshot review subject to exactly these changes; the D1d screenshots (build-D1d/screens/compare.html) await his glance, and the flag stays default-off, so nothing changes for anyone at merge. Current-target Azure CI follows in the PR. Review: X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-13_codex-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-OWNER-001_D1d.md"
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

## Independent review and delivery (D1)

Codex PC (`session:01a132fe-1f81-77f3-8821-d53d157ca025`) failed D1b `5bf78e97` with three findings (unreadable read shown as empty, invented Present, late Ask result overwriting newer typing) and one footer note, then **passed exact D1c `997ac8cd40046552d02122dbfabc8528f1d81a91`** at 2026-10-13T18:28:08Z with no remaining required finding (`X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-13_codex-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-OWNER-001_D1c.md`). Its native exact-candidate verification ran all 39 page tests (PASS) and an independent probe over the real owner route. The receipt is bound to that SHA. This tail adds only the receipt and this evidence file.

Merge is repository truth only: the page stays behind the default-off `PEERSLATE_RESUME_PAGE_ENABLED` flag, so nothing changes for any user. No deployment, 8444 enablement, schema or paid call. The claim stays open for round D2.

## D1d independent review and delivery

Codex PC (`session:01a132fe-1f81-77f3-8821-d53d157ca025`) failed `8258d321` with one P2 finding: the Looking Ahead image guard accepted an encoded traversal (`/static/%2e%2e/healthz`). It then **passed the narrow re-check at exact `147cd1fada2c594e59792f21f4e08d148680a257`** (2026-10-14T02:45:42Z, no remaining finding; `X:/PeerSlate/coordination/claude-pc/Shared/handoffs/2026-10-13_codex-pc_to-claude-pc_RECHECK_PS-RESUME-PAGE-OWNER-001_D1d-F1.md`). Candidate history this round: `272d13c4` (D1d), superseded by `8258d321` (the manager's parity correction: "Employer · Role · dates" plus "See it in the role →"), superseded by `147cd1fa` (one same-origin `/static/` guard for every image source). The receipt is bound to `147cd1fa`; this tail adds only the receipt and this evidence file.

Merge is repository truth only: the page stays behind the default-off `PEERSLATE_RESUME_PAGE_ENABLED` flag. No deployment, 8444 enablement, schema or paid call. The claim stays open for D2.

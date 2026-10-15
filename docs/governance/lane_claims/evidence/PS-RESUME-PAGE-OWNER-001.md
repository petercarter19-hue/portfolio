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

## Acceptance plan (D2, committed before code)

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-RESUME-PAGE-OWNER-001",
  "plan_sha": "8049f22075f743158ead4d0a77ecc63e9c75e728",
  "baseline": [
    {
      "command": "python -B -m unittest tests.test_resume_page_owner tests.test_resume_page_owner_browser -q",
      "exit_code": 0,
      "observation": "Pre-change at 925b995b (tree equals accepted main bd07b1ee, which carries D1 996ea385 and D1d be2e9126): 52 page tests PASS in 22.8s (fictional members, recorded workspace or the real draft service over in-memory stores, process-local placeholder key, no AI call). Edit myself opens today's editor; there is no Guide entry on the page; the page never writes; Looking Ahead always shows the placeholder because the adapter ignores the member's Looking Ahead entry; Projects read retired field names (name/description), so a B2 project (project_name/summary) shows no name and no section; highlight tiles exist only when a harness injects them, because the adapter ignores highlight_refs."
    }
  ],
  "criteria": [
    {
      "id": "guide_entry",
      "expected": "Edit myself (top right of the frame) still opens today's manual editor for the owner, unchanged. A 'Continue with the Guide' button sits just left of it and opens the Guide panel only through its public open hook (window.PeerSlateGuidePanel.open); when that hook is absent the button is absent (hidden), never a dead control, and the page never drives the Guide's own controls or files. Below 960px Edit myself comes first and the Guide button follows in outline style. Both live only on the owner's private page.",
      "verification": "Browser test with and without a stand-in hook at 1440 and 390 (hidden without it, one open call with it, never the editor, hidden again if the hook goes away, order and style on a phone, 24px targets); unit template/static tests (rendered hidden, before Edit myself, flag-off absent, no Guide-internal API); toolbar screenshots."
    },
    {
      "id": "looking_ahead",
      "expected": "The Looking Ahead section after Experience shows the member's own line from their private draft (B2's work knowledge entry titled 'Looking Ahead'), once on the page and never an AI line; a personal or My Story entry with that title is not used. With no line the owner sees the existing placeholder. The owner writes or edits the line in place (one field, the browser's 120-character limit, Save privately / Cancel) through the existing private draft commands (create_private_item, then save_item); an empty line is never saved or sent; a refused or failed save keeps the words; a retry of an uncertain save replays the same command and never saves twice; unsaved words are never wiped by a reload. Nothing is shared or published. Renaming waits on a stored-label field from the Guide server (dependency, not built).",
      "verification": "Browser tests with a recorded workspace and the real draft service over in-memory stores: shown once, not in the hero, placeholder without a line, write/edit/cancel, 120 limit, empty refused with no request, 503 keeps words, lost reply retried once with the same request id and one entry saved, saved entry not displayed to visitors; unit static tests; screenshots."
    },
    {
      "id": "projects",
      "expected": "The Projects section appears only once the member has a project, after Experience, and in the section list. Each project shows B2's fields: name, optional category label, the one-line description, organization and dates, and up to three links shown by site name ('GitHub' for github.com) that open in a new tab with rel='noopener noreferrer'; only https:// links with a host are shown, and no link is ever fetched by the page. The owner adds a project from Edit myself ('Add a project') and edits each one in place, with the Guide's D91 fields and labels, through the existing private draft commands; missing name/description, a non-https link or mixed date detail are explained without sending; server refusals keep the words.",
      "verification": "Browser tests: absent without projects, fields/links/order, javascript:/http: links dropped, at most three, no request to any link host, add with validation then save, edit in place via save_item, refusal keeps input, real draft values checked; unit static test that links are never fetched; screenshots at 1440 and 390."
    },
    {
      "id": "highlight_tiles",
      "expected": "The hero shows two to four highlight tiles, each resolved at render from B2's highlight_refs (at most four saved accomplishment keys) to that saved bullet's own metric_value and metric_label (its own wording when it has no label) and its role, so a tile is a reference, never copied text: a changed number shows, a cleared number drops the tile, and duplicate, missing, number-less or role-less references give no tile; fewer than two resolved tiles means no row. A tile the Guide suggests is drawn dashed with 'Suggested by the Guide · waiting for your OK', is not a link and is never a saved or public tile; the page itself never invents a suggestion (the Guide's pending tile proposal is a later dependency).",
      "verification": "Browser tests with references (order, cap, drops, role link, live follow on reload, one-tile no-row, column count) and a waiting tile rendered through the view model; adapter check that no suggestion is invented; tile screenshots beside approved-v2."
    },
    {
      "id": "rest_unchanged",
      "expected": "Flag-off /app/resume HTML equals the base; every D1 and D1d behaviour still passes (identity, order, rail and always-expanded rail Ask, Ask tabs, skill lines, truthful reads and dates, fenced Ask, constellation band, portrait cards, phone fold, left edge, image guard, keyboard, AA contrast, light only); the page still makes no AI call and its only requests are the workspace read and the private draft commands.",
      "verification": "Full page suites; normalized flag-off HTML base vs candidate; affected suites; strict 152 browser runner normal and twice concurrently; no-Playwright skip proof; whole no-Playwright discover base vs candidate with identical failure sets; screenshots at 1440, 1280, 960 and 390 in build-D2."
    },
    {
      "id": "review_and_delivery",
      "expected": "Each new D2 test fails at the base code; the page browser suite passes twice concurrently; the browser module skips cleanly without Playwright; the Guide builder session independently passes the exact candidate; Pete's screenshot OK is recorded before merge; the six D2 design defaults are confirmed or corrected by the manager.",
      "verification": "Writer verification log (build-D2/PROGRESS.md), independent review receipt, screenshot packet build-D2/screens/compare.html, merge preflight and current-target Azure CI."
    }
  ],
  "candidate_sha": "e21456f3c6d80bd9531079ce3ce2ffa55e96ecf5",
  "checks": [
    {
      "criterion_id": "guide_entry",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "e21456f3c6d80bd9531079ce3ce2ffa55e96ecf5",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_continue_with_the_guide_appears_only_with_the_public_hook_and_opens_it",
      "observed": "Without window.PeerSlateGuidePanel.open the 'Continue with the Guide' button is hidden; with a stand-in hook it shows just left of Edit myself at the top right of the frame (at least 24px), one click makes exactly one open call and never opens the editor, and it hides again if the hook goes away. At 390 Edit myself comes first and the Guide button is outline style. Edit myself still opens today's editor (test_edit_myself_opens_todays_editor_and_saves_refresh_the_page). Unit tests: rendered hidden before Edit myself, absent with the flag off, no Guide-internal API used.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-15T12:36:17Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_continue_with_the_guide_appears_only_with_the_public_hook_and_opens_it"
      }
    },
    {
      "criterion_id": "looking_ahead",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "e21456f3c6d80bd9531079ce3ce2ffa55e96ecf5",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_owner_writes_and_edits_looking_ahead_through_the_private_draft",
      "observed": "The member's own line shows once (not in the hero), the placeholder only without one; it is written and edited in place through create_private_item then save_item with maxlength 120, an empty line is never sent, and the saved entry stays private (no display or visitor-AI permission). A refused (503) save keeps the words; a lost reply is retried with the same request id and saves once. After F1 a form saves after another page form, today's editor or an unheard save (one fresh retry on 409, distinct request ids); an item changed elsewhere stays an honest conflict; Looking Ahead is found by placement first, then title, one line only, a renamed title kept. Tests: test_looking_ahead_is_the_members_own_line_shown_once, test_a_refused_save_keeps_the_members_words, test_a_retry_after_an_uncertain_save_is_never_saved_twice, test_a_second_page_form_saves_after_another_page_form_saved, test_a_page_form_saves_after_todays_editor_saved_meanwhile, test_a_page_form_saves_after_a_save_it_never_heard_about, test_an_edit_of_the_same_item_elsewhere_stays_an_honest_conflict, test_looking_ahead_is_found_by_its_placement_first_then_by_its_title. Renaming is not built (dependency).",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-15T12:36:17Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_owner_writes_and_edits_looking_ahead_through_the_private_draft"
      }
    },
    {
      "criterion_id": "projects",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "e21456f3c6d80bd9531079ce3ce2ffa55e96ecf5",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_owner_adds_and_edits_a_project_through_the_private_draft",
      "observed": "No Projects section or nav entry without a project; with projects it follows Experience and shows name, category label, one line, organization and dates, and up to three https links by site name (GitHub for github.com) with target _blank and rel noopener noreferrer; javascript: and http: links are dropped and no request goes to any link host (test_projects_show_only_once_added_with_their_fields_and_safe_links). Add a project from Edit myself and edit in place use the D91 fields and labels through the private draft commands; missing essentials, a non-https link and mixed date detail are explained without sending; untouched dates are never rewritten (test_editing_a_project_never_rewrites_its_untouched_dates); a moved item saves as its destination type.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-15T12:36:17Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_owner_adds_and_edits_a_project_through_the_private_draft"
      }
    },
    {
      "criterion_id": "highlight_tiles",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "e21456f3c6d80bd9531079ce3ce2ffa55e96ecf5",
      "source_ref": "tests/test_resume_page_owner_browser.py:test_highlight_tiles_are_saved_bullets_resolved_by_reference",
      "observed": "Tiles resolve from highlight_refs to each saved bullet's own metric_value and metric_label (its wording without a label) and its role: duplicate, missing, number-less and role-less references give no tile, at most four show in order, a tile opens its role's chapter, a changed number follows on reload, a cleared number drops the tile, the column count follows the tile count, and fewer than two means no row. A Guide-suggested tile renders dashed and non-interactive with 'Suggested by the Guide · waiting for your OK', and the adapter never invents one (test_suggested_tiles_wait_for_the_members_ok). Known temporary gap: Pete's page shows 3 of the approved 4 tiles because B2 holds one number per bullet; the fourth waits for a per-tile metric selector.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-13/resume-page-owner",
        "captured_at": "2026-10-15T12:36:17Z",
        "source_ref": "tests/test_resume_page_owner_browser.py:test_highlight_tiles_are_saved_bullets_resolved_by_reference"
      }
    },
    {
      "criterion_id": "rest_unchanged",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "e21456f3c6d80bd9531079ce3ce2ffa55e96ecf5",
      "source_ref": "tests/test_resume_page_owner.py:test_flag_off_renders_todays_editor_only",
      "observed": "Flag-off /app/resume HTML equals base bd07b1ee for both flag sets (build-D2 flag-off.txt); every D1/D1d test still passes (page suites 76/76); the page's only requests are the workspace read and the private draft commands (unit contract: two fetches to server-rendered URLs, no /api/ literal, no markup sinks). At e21456f3: 14 affected modules 504/504 (1 skipped); strict 152 runner 152/152 normal and twice concurrently; whole no-Playwright discover from git exports, base 7881 run vs candidate 7905, both 16E/19F with identical failure sets; screenshots at 1440, 1280, 960 and 390 in build-D2/screens."
    },
    {
      "criterion_id": "review_and_delivery",
      "result": "pass",
      "kind": "manual",
      "candidate_sha": "e21456f3c6d80bd9531079ce3ce2ffa55e96ecf5",
      "source_ref": "https://claude.ai/artifact/CFU9JNoGWsVQujFt2G8dia",
      "observed": "Pete, the owner, checked the D2 screenshots and said \"Resume looks good.\" (2026-10-15, relayed by the manager). Independent review: guide-build FAILED 824d7587 with F1 Medium (coordination 4e41321) and PASSED the narrow re-check at exact e21456f3 (coordination 64205e6). The manager confirmed all six design defaults. Writer evidence: each new test failed at its base code (15 at bd07b1ee's code, 3 moved-item tests at 4ca2fdc5, 5 F1 tests at 824d7587); the page browser module passed twice concurrently (50/50 each); it skips cleanly without Playwright (76 run, 50 skipped, 0 errors).",
      "provenance": {
        "observer_ref": "role:owner/pete-chat-2026-10-15/claude-manager-16023c0e/resume-d2-screenshot-ok",
        "captured_at": "2026-10-15T12:36:17Z",
        "source_ref": "https://claude.ai/artifact/CFU9JNoGWsVQujFt2G8dia"
      }
    }
  ]
}
```

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

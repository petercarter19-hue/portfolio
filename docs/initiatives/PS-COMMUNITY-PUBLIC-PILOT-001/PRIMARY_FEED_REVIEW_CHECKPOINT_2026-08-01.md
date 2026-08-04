# PeerSlate primary Feed review checkpoint

## Core record

- **Task/package and delivery path:** `PS-COMMUNITY-PUBLIC-PILOT-001`,
  Protected package with a bounded local primary-page slice.
- **Outcome and member/site effect:** **Approved primary-page visual
  checkpoint — local `/the-slate` Feed slice only.** On 2026-08-01 Pete
  explicitly approved the revised primary page after the Respond and compact
  comment-entry corrections (`looks good`). Pete had rejected the earlier
  oversized Respond panel. The approved primary card uses a compact,
  Facebook-scale emoji rail anchored above Respond. It opens on hover or
  focus and is also usable by click/touch. Choosing an emoji saves the existing
  private viewer response immediately; choosing the active emoji removes it.
  No `Done` or `Remove` footer remains on the primary page. Pete's next
  correction also reduces the overflow-dot glyph and adds a one-line,
  auto-growing `Write a comment…` field below Comment/Respond, with compact
  Voice and Send controls at the right edge. Text submit reuses the existing
  top-level contribution command. The Voice control is truthfully unavailable
  until the protected Voice pass. This is not feature completion, release
  readiness, deployment, or live multi-user behavior.
- **Preview URL:** `http://127.0.0.1:5055/the-slate`.
- **Branch, base SHA, final SHA, and changed paths:**
  - Branch: `codex/2026-08-01-community-primary-feed-sol-ultra`.
  - Authoritative `origin/main` and merge base:
    `2494aa73ed95bfbe97d8cf42f712b9929759e0b2`.
  - Handoff/working-tree HEAD:
    `3210e4030fae30bd45fb05f4ce8351b26c4ee3f1`.
  - Final SHA: none; this review checkpoint remains an unstaged local working
    tree as requested.
  - `static/js/community-v1.js` — primary Feed hierarchy plus the compact
    actual-emoji response rail, hover/focus/click lifecycle, immediate private
    selection, selected-emoji trigger, same-choice removal, smaller overflow
    mark, local/private comment drafts, auto-grow, idempotent top-level text
    comment submit, and the non-recording Voice affordance.
  - `static/css/community-v1.css` — primary composition and 196-by-46 response
    rail with five 36-by-36 controls and 22px emoji, an 11.52px overflow mark,
    and the compact 48px comment field with 36px Voice/Send controls.
  - `templates/community_feed.html` — primary-stage and truthful local-fixture
    markers from the primary-page implementation.
  - `tests/test_community_public_pilot.py` — focused primary-card, emoji-rail,
    comment-field, focus-close, and preview-isolation contracts.
  - `scripts/preview_community_primary_feed.py` — non-production Feed fixture
    plus in-memory `PUT`/`DELETE` response and text-only top-level comment
    support; no SQL, service, or persistence access.
  - `PRIMARY_FEED_ARCHITECTURE_AMENDMENT_2026-08-01.md` — minimum component map,
    corrected reusable response-picker rule, and deferred Community-to-Voice
    seams.
  - `evidence/2026-08-01-primary-feed-respond-rail-desktop-1536x1024.png` —
    exact desktop evidence for the corrected open response rail. It predates
    the later compact comment-row addition and is not by itself evidence of
    the final combined source.
  - `evidence/2026-08-01-primary-feed-comment-entry-mobile-320x1101.png` —
    current narrow browser evidence showing the complete compact comment row.
  - `evidence/2026-08-01-primary-feed-approved-current-browser.png` — final
    current-source browser capture made after Pete's approval and before the
    handoff preview was stopped.
  - `evidence/2026-08-01-primary-feed-final-desktop-1536x1024.png` — PC
    continuation top-of-page capture from the final combined source at a
    1536-by-1024 CSS viewport.
  - `evidence/2026-08-01-primary-feed-final-desktop-lower-1536x1024.png` — PC
    continuation lower-page capture at the same viewport, proving the compact
    comment row in the desktop composition.
  - `evidence/2026-08-01-primary-feed-final-respond-and-comment-desktop-1536x1024.png`
    — PC continuation capture at the same viewport with the compact Respond
    rail and comment row visible together.
  - This checkpoint record.
- **Verification performed and result:**
  - Community runtime, verifier, XLSX, and frontend suite: **PASS, 108 tests**.
  - Adjacent Community-tab, navigation, and Community/Journal milestone suite:
    **PASS, 59 tests**.
  - Community browser focus-lifecycle harness: **PASS, 10 behavioral checks**.
  - JavaScript syntax, preview-harness Python compile, dependency integrity,
    and diff whitespace: **PASS**.
  - Real browser, light theme, 1536-by-1024 CSS viewport: **PASS for the revised
    response state**. The card was 720px wide; the Respond trigger was 44px;
    the open picker was 196-by-46px; every emoji control was 36-by-36px with a
    22px actual emoji; no dialog or primary Save action was open/present; and
    the browser log was empty.
  - Real selection round trip against the isolated local fixture: **PASS**.
    Selecting Celebrate used the local private `PUT`, changed the trigger to
    `🎉` with the accessible name `Respond: Celebrate`, and closed the rail.
    Selecting Celebrate again used `DELETE`, restored the closed Respond
    symbol, and closed the rail.
  - Narrow check at 390-by-844: **PASS**. The 374px card and 196px rail remained
    inside the 390px document with no horizontal overflow.
  - Primary comment entry at the desktop CSS viewport: **PASS**. The card was
    720px wide; the empty field was 686-by-48px; the textarea began at 24px;
    and the overflow glyph computed to 11.52px. A long comment grew the field
    to 65px while both Voice and Send stayed 36-by-36px. Send enabled only with
    text, the local `POST` succeeded, the field cleared back to 48px, and the
    accessible count advanced from 12 to 13. Browser logs were empty.
  - Current narrow evidence at 320-by-1101: **PASS** with no horizontal
    overflow, a 48px empty field, and the reset truthful fixture count of 12.
  - Corrected-response desktop screenshot: exact 1536-by-1024 PNG, SHA-256
    `d17dad38ec854ebf8c96b6c03cc4a2426b6eacd029815b598a13cbc10d0349c7`.
    It was captured before the final compact comment row. The browser panel
    was narrow at final handoff, so no exact 1536-by-1024 capture of the final
    combined source is claimed.
  - Narrow comment-entry screenshot: exact 320-by-1101 PNG, SHA-256
    `16dfac3493b8d48eb53ca0f843a29d1bd2fae90a6f97874a43e87101c556f672`.
  - Final approved current-source capture: exact 320-by-1101 PNG, SHA-256
    `5c358d2dcf3219c7ff2af9aebad8e36f6f926bba1d32b950318d5c72e34391bc`.
  - PC continuation Windows portability: **PASS**. The focused 108-test
    command passed under the ordinary Windows interpreter without setting
    `PYTHONUTF8`; frontend contract fixtures explicitly read UTF-8 source.
  - PC continuation real-browser interaction: **PASS**. Celebrate add/remove
    and a text-comment submit/reset both passed against the isolated local
    fixture. No SQL, Blob, Speech, or production service was used.
  - PC continuation desktop captures have SHA-256 values
    `d3954053a4662ffda5e262485963805fd9c4df2dfdd355573b832e35b6a8ff1f`,
    `0cebf4956d0882488f818a6300c95fcae1e1e1b4dc432c1557991898fe40bfac`,
    and `20791dc5d06ef70efccfb7203fe33dc78a9692c0ee908687b42be340eb4b31c9`.
  - Final PC ruler pass: **PASS**. After rejected 640px and 660px
    intermediates, the rendered desktop card measured 500px wide, with a
    16px inset, 466.5px media/comment width, 44px main actions, and a 48px
    comment field. The compact microphone remained the only Voice affordance,
    expanded Voice panels were zero, narrow layout stayed fluid, and browser
    logs and horizontal overflow were empty.
- **Visible differences from the previous lock/rejected checkpoint:**
  - Pete's correction replaces the oversized inline five-card dialog with a
    small floating pill of actual emoji: `🎉`, `❤️`, `🤝`, `🤔`, and `🙋`.
  - The picker has no heading, explanatory block, close button, card grid,
    `Remove`, or `Done`. Selection is immediate and private.
  - The post-action hit target remains 44px for accessibility, but its visible
    three-dot mark is reduced to 11.52px.
  - Main Feed posts for the currently authorized viewer now include the compact
    text/Voice/Send row. The Voice icon establishes placement only and does not
    request permission or capture/transcribe audio in this checkpoint.
  - Pete's PC review rejected a later expanded Voice activator below this row.
    The corrected card renders no second Voice panel; the compact microphone
    beside Send is the sole idle Voice affordance.
  - Pete rejected the intermediate 640px and 660px desktop widths as still
    oversized. The final ruler-based center Feed stage is 500px; mobile remains
    fluid and uses the available viewport.
  - The captured rail is click-open in the real browser and therefore shows
    the primary trigger's cobalt focus indicator. Pointer hover uses the same
    rail geometry without changing the selection contract.
  - The shared production header remains unchanged and still differs from the
    illustrative visual-authority shell. Shared navigation is outside this
    reserved slice.
  - The local Pete-only fixture truth banner remains on the page. The screenshot
    is centered on the card/response review state; it does not claim persisted
    content or other-member activity.
  - The PC continuation removes `aria-haspopup=true` from the primary Respond
    trigger because the controlled picker is a labelled group of buttons, not
    an ARIA menu. `aria-controls` and `aria-expanded` preserve the truthful
    disclosure relationship.
- **Release state:** **local only**. The existing Community feature flag remains
  default-off. No staging, commit, push, PR, merge, migration, Candidate,
  pipeline, deployment, configuration change, or flag activation occurred.
- **Secondary-state and release work not begun:** full-post modal or full
  conversation page; nested reply interaction branches; full-conversation
  reply composer behavior; composer/Voice states A-H; microphone permission,
  recording, transcription, or failure states; separate public confirmation;
  SQL migration; Azure Blob/Speech; retention; Break; Candidate; PR, merge,
  deployment; and any live/public claim.
- **Next action:** Historical PC checkpoint complete. Pete subsequently froze
  that lane and transferred sole active-writer ownership back to the Mac. See
  `PC_TO_MAC_COLLISION_MATRIX_2026-08-01.md` and the separate Mac continuation
  checkpoint for the reconciled Feed state. No release action is inferred.

## Protected additions

- **Data, identity, privacy, authorization, deletion, publication, or AI:** No
  production contract changed. Existing server-derived identity,
  authorization, explicit Public selection, private local drafts, media
  reauthorization, and default-off flag are preserved. The review harness is
  Pete-only sample content and stores only the selected response and comment
  count in process memory so the real UI interactions can be verified. Comment
  text is discarded after the response and cannot reach SQL, Blob, Speech, or
  production persistence through a served request.
- **Material visual work:** The locked Feed hierarchy remains the authority.
  Pete's explicit correction controls the response picker and is recorded in
  the package-scoped architecture amendment for reuse in later approved
  response surfaces. Pete's later correction also removes the expanded
  below-row Voice activator: the compact microphone beside Send is the only
  idle primary-card Voice affordance, and it remains unavailable.
- **Shared infrastructure or broad release:** Not triggered.
- **Actual handoff:** Triggered by Pete on 2026-08-01 for transfer to his PC.
  Receiving owner: Pete Carter. No pushed SHA exists because Pete requested a
  file package and the checkpoint intentionally remains unstaged, uncommitted,
  and unpushed. The transferable state is the working tree on
  `3210e4030fae30bd45fb05f4ce8351b26c4ee3f1`; its ZIP manifest and checksums
  are authoritative for the overlay. Original transfer limitation: the exact
  desktop response screenshot predates the final comment row and the original
  final current-source capture is narrow. The PC continuation adds final
  desktop top, lower-page, and Respond-plus-comment captures from the restored
  source. Pete later froze the PC writer and transferred sole active editing
  back to the Mac; this record remains historical PC evidence.

# Community primary Feed Mac continuation checkpoint

## Core record

- **Task/package and delivery path:** `PS-COMMUNITY-PUBLIC-PILOT-001`,
  Protected package with a bounded local primary-Feed continuation.
- **Outcome:** The checksum-verified PC work is reconciled into the sole Mac
  writer lane. The primary `/the-slate` Feed now combines Pete's latest
  owner-corrected 748px post/card composition with Threadline Signal:
  supporting desktop rails, exactly one post-local horizontal
  `Replies & updates` Motion shelf, a clipped next card, compact attachment
  ribbons, persistent `View all`, compact Respond emoji rail, and one compact
  type/Voice/Send comment row directly above Motion, plus a top composer bar
  that replaces the floating `New post` control. The page, primary post,
  Motion cards, preview notice, and supporting rails use restrained layered
  tones and shadows rather than flat white.
  This is a local fixture-backed visual checkpoint, not feature completion,
  release readiness, deployment, or live multi-user behavior.
- **Mac worktree:**
  `/Users/petercarter/.codex/worktrees/6be8/portfolio`
- **Branch:** `codex/2026-08-01-community-primary-feed-sol-ultra`
- **HEAD:** `3210e4030fae30bd45fb05f4ce8351b26c4ee3f1`
- **Authoritative `origin/main` and merge base:**
  `2494aa73ed95bfbe97d8cf42f712b9929759e0b2`
- **Final SHA:** none. The continuation remains unstaged, uncommitted, and
  unpushed as instructed.
- **Preview URL:** `http://127.0.0.1:5055/the-slate`

## Continuation package and collision result

- ZIP:
  `/Users/petercarter/Library/Mobile Documents/com~apple~CloudDocs/ChatGPT/PeerSlate-Community-PC-to-Mac-Continuation-2026-08-01.zip`
- Expected and verified SHA-256:
  `be06e6efade43a3e0c73176930fb63f2e3a4f7ba714bb9cc9819348ac219666e`
- ZIP test: **PASS**.
- Payload manifest: **PASS**, all 59 entries. The Windows-authored CRLF
  manifest required a temporary LF-normalized verification copy on macOS; no
  package file was altered.
- Source overlay: 17 files — 6 `MATCH`, 8 `PC-NEWER`, 3 `PC-ONLY`, 0
  `MAC-NEWER`, and 0 unresolved `COLLISION`.
- Complete per-file hashes and actions:
  `PC_TO_MAC_COLLISION_MATRIX_2026-08-01.md`.
- PC-only files adopted: the three final PC desktop evidence PNGs.
- Exact Mac files retained: the four matching historical evidence images,
  matching preview harness starting point, and matching template starting
  point.
- Manually reconciled: visual manifest, package README, primary architecture
  amendment, PC handoff, historical PC checkpoint, route-local CSS, card
  renderer, and frontend tests.
- Mac-only file preserved but not adopted as active authority:
  `COMMUNITY_VOICE_VERTICAL_SLICE_ARCHITECTURE_AMENDMENT_2026-08-01.md`.
  No Voice runtime was implemented.

## Implementation result

- The center Feed stage and primary post are exactly 748 CSS pixels on the
  1536px desktop review viewport and remain fluid at narrow widths.
- Each desktop rail is 234px, exactly thirty percent wider than the previous
  180px rail. Both rails align with the top edge of the 63px composer bar.
- The top prompt and compact photo/file control open the existing private-draft
  composer. A compact microphone matching the primary comment row occupies the
  other action position. The floating `New post` button is absent; no top-bar
  action publishes directly.
- At medium widths, `Community activity` is a 46px single-line control with a
  0.84rem non-wrapping label and compact one-line supporting text. It opens the
  same existing activity panel.
- The existing left rail is restored with `Since you were here`, `Continue the
  conversation`, `A Spark for you`, and caught-up state. The existing right
  rail is restored with `Community pulse` and `Active questions`.
- At compact widths the rails disappear and the existing Catch-up tool remains;
  no new navigation or audience was introduced.
- The compact comment-entry row is immediately below Comment/Respond. The
  existing `renderConversationShelf` follows that row inside the primary card.
- The local preview supplies 12 Pete-only author-update fixtures so horizontal
  behavior is truthful for the first-pilot preview and does not imply member
  authoring. It includes image and macro-free-XLSX metadata cues but changes no
  physical XLSX file, media service, database, or persistence.
- Desktop Motion cards are 145 by 136px with 12px gaps; four complete cards
  and a clipped fifth remain visible. At 390px the cards are 96 by 132px with
  12px gaps; three complete cards and a clipped fourth remain visible. All 12
  remain in the one non-wrapping
  horizontal track.
- Motion cards retain relative time but no longer repeat `Author update`.
  Author and body text use 0.82rem type; body copy is bounded to two lines with
  ellipsis, and attachment/time rows remain inside the equal-height card.
- Motion cards use a layered cool blue-gray gradient, border `#D8E1EE`, and a
  slightly bluer hover/focus gradient. The left rail uses a layered pale warm
  neutral; the right rail and caught-up state use layered pale cool blue; the
  primary post uses a near-white tonal gradient and multi-level shadow. Dark
  equivalents use subtly lifted layered navy surfaces.
- The compact Respond rail remains 196 by 46px with five 36 by 36px actual
  emoji controls. Selection/removal is immediate and private through the
  existing response commands; no `Done`, `Remove`, Save, or repetitive
  Open-post action appears.
- The idle Comment and Respond controls have 36-by-34px borderless visible
  targets with 20px icons; no surrounding circle or pill appears at rest.
- The 40px compact comment row precedes Motion. It has one auto-growing text
  field, 30px Voice and Send controls, the sole unavailable Voice affordance,
  and a separate Send action. No second/expanded Voice activator exists.
- Server-derived identity, fail-closed owner authorization, private local
  drafts, explicit Public selection, canonical publication commands, and the
  existing attachment/Voice service boundaries were not changed.

## Verification

- Community runtime, verifier, XLSX, and frontend modules: **PASS, 110 tests**.
  The count is two above the transferred 108 because the Mac continuation adds
  Motion-card density/color and top-composer contracts.
- Adjacent Community tabs, navigation, and Community/Journal milestone
  modules: **PASS, 59 tests**.
- Community focus-lifecycle harness: **PASS, 10 behavioral checks**.
- JavaScript syntax: **PASS**.
- Preview Python compilation: **PASS**.
- Temporary review environment dependency integrity: **PASS**.
- Git diff whitespace: **PASS**.
- Real browser at 1536 by 1024:
  - 748px primary post; 1,248px three-column grid; 234px rails.
  - document `scrollWidth` equals `clientWidth` at 1536px.
  - 748px-by-63px top composer bar and both rails begin at the same vertical
    coordinate; no `New post` button is rendered.
  - one shelf, 12 Motion cards, one comment row, one compact Voice control,
    zero expanded Voice panels, zero visible Save actions, and zero visible
    Open-post actions.
  - 716px media/comment/shelf width; 145-by-136px Motion cards with 12px gaps;
    four complete cards and a clipped fifth are visible.
  - zero Motion `Author update` labels; the retained timestamp is one line.
  - Comment and Respond occupy 36-by-34px borderless idle targets with 20px
    icons; the comment field is 40px high.
  - Respond rail 196 by 46px; all five emoji controls 36 by 36px. Celebrate
    add changed the trigger to `Respond: Celebrate`; selecting it again removed
    the response and restored `Respond`. The latest owner-correction browser
    pass reopened and closed the same compact rail without altering its size.
  - local text-comment submit enabled Send, returned success, cleared the
    field to its 40px idle height, and advanced the fixture count from 12 to
    13. Restarting the fixture restored the review baseline. The latest pass
    grew the field from 40px to 66px as text wrapped, returned it to 40px after
    clearing, and rendered zero expanded Voice panels.
- Real browser at 390 by 844:
  - 374px fluid post and 346px comment/shelf viewport.
  - 374px top composer bar preserves the compact Voice action; the media
    shortcut hides to preserve the one-line mobile composition.
  - document `scrollWidth` equals `clientWidth` at 390px.
  - desktop rails are hidden; existing Catch-up control is visible.
  - Motion cards are 96 by 132px with 12px gaps; three complete cards and a
    clipped fourth are visible.
  - one shelf, one comment row, and zero expanded Voice panels.
- Browser warning/error log: **empty**.

## Evidence

| Capture | Size | SHA-256 |
| --- | ---: | --- |
| `evidence/2026-08-01-primary-feed-mac-continuation-desktop-1536x1024.png` | 1536 × 1024 | `7a352d9c5f836c5c4da3e140414d507f673d0145530241f14c55a580c83aea60` |
| `evidence/2026-08-01-primary-feed-mac-continuation-respond-desktop-1536x1024.png` | 1536 × 1024 | `860a485e71576ebd8f8fd43e6ed880e2c2c2acdad1b705da35aefa50d87de506` |
| `evidence/2026-08-01-primary-feed-mac-continuation-mobile-390x844.png` | 390 × 844 | `cf3d5285059c6919aa8976501a5197dac2d21636ad95e070acb5ee58ebe1d8f8` |
| `evidence/2026-08-01-primary-feed-mac-continuation-mobile-full-390.png` | 390 × 1238 | `39c7670cf58aa3f174bae5678888273ae079fa20ded8343b47570a2aed4cf756` |
| `evidence/2026-08-01-primary-feed-owner-correction-desktop-1536x1024.png` | 1536 × 1024 | `5ee2929904c63f4c52ec56e498df3f8009a542fbf51dfbdf294a83326e3dee80` |
| `evidence/2026-08-01-primary-feed-owner-correction-narrow-390x844.png` | 390 × 844 | `3ebc808a8367e2c48aeac2ecf9281ae6e8500bdbbf7eee39872bd98c9c0f2ae8` |
| `evidence/2026-08-02-primary-feed-top-composer-desktop-css-1536x1024.png` | CSS viewport 1536 × 1024; DPR raster 1920 × 1279 | `464d3c7e6367a4235334927e00c4adfb39a8b30cf4226c12974da1bcd65a089f` |
| `evidence/2026-08-02-primary-feed-top-composer-narrow-css-390x844.png` | CSS viewport 390 × 844; DPR raster 488 × 1054 | `656c33de7bb90ec60ed2748f26f41d668be4b440eb6c6f987dfd1f1486c522fe` |
| `evidence/2026-08-02-primary-feed-activity-voice-medium-css-1262x1100.png` | CSS viewport 1262 × 1100; raster 1263 × 1100 | `8c5168adf0fd126cf6e0d642ee2706e744cf94961220c542215758242abf0541` |

## Visible differences and honest limits

- Pete's latest correction supersedes the earlier 500px and 650px intermediate
  renders: 748px Feed, 234px rails, a Facebook-familiar top composer bar,
  compact borderless Facebook-scale actions, a 40px comment row
  before Motion, wider-spaced Motion cards, and layered tonal depth across the
  page.
- At medium width the activity tool is now one line, and the top bar retains a
  compact Voice affordance. Voice remains truthfully unavailable; no runtime
  or permission state was opened.
- The shared production navigation remains the real site shell and therefore
  differs from the illustrative board shell. Shared navigation was not changed.
- The local preview banner remains intentionally visible. Pete is fixture
  content, all Motion contributions are Pete-only author updates, and no live
  or broader member activity is claimed.
- The focused-conversation and full-conversation code already in the inherited
  package was not revised or promoted by this continuation. Message remains a
  future seam and no new messaging state was added.

## Work that has not begun

- Full-post or focused-conversation visual revision.
- Nested reply interaction branches or full-conversation composer tranche.
- Community Voice runtime or states A-H; microphone permission, recording,
  upload, transcription, reviewed transcript insertion, retry, or failure.
- New messaging behavior, broader member authorship, audiences, navigation,
  media capabilities, Journal behavior, or Break distribution.
- SQL/schema/migration work, live Azure Blob/Speech, retention execution,
  Candidate, feature-flag activation, PR, commit, push, merge, deployment, or
  any live/public claim.

## Exact next gate

**Closed 2026-08-02:** Pete reviewed the real local page, said it looked good,
and explicitly instructed this task to keep moving forward. The Mac task
remains the sole active Community writer. The next local tranche is the locked
full-conversation/reply surface followed by the protected Community Voice
vertical slice. This approval does not by itself begin Candidate, migration,
feature-flag activation, PR, merge, deployment, or a live/public claim.

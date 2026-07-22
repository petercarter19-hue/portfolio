# PS-JOURNAL-001 J1 Visual Finish — Completion Report

## A. Status

- Package: PS-JOURNAL-001, J1 owner Journal visual finish continuation
- Code branch / commit: `work/2026-07-21-journal-frontend-j1-impl` @ `6a1b74c`
- Azure push: completed to the assigned branch; no merge, PR, deployment, or
  production mutation was performed.
- Production state: unchanged. `PEERSLATE_JOURNAL_ENABLED` remains the
  existing gate and no SQL, migration, procedure, infrastructure, public
  route, or homepage surface changed.
- Visual authority: the four accepted Journal PNGs in
  `visual-authority/accepted/`, docs 10, 11, 13, and the binding doc 15.
- Self-certification: **Conditional**. Structural and automated checks pass;
  fresh visual evidence and the required side-by-side visual sign-off cannot
  be completed in this session because no controllable browser was available.
- Pete / session-manager visual acceptance: not requested; not implied by this
  technical report.

## B. What changed technically

- Rebuilt the Journal’s book/rail/detail/composer finish in
  `static/css/journal.css` and the three Journal templates. The detail view now
  uses the same two-column book and contents rail as timeline, empty, and
  Manage.
- Replaced the unsafe title-keyed `JOURNAL_FIXTURE_ENRICHMENT` map with a
  test-only, server-owned fixture provider in `owner_routes.py`. It is active
  only when both `TESTING is True` and
  `PEERSLATE_JOURNAL_EVIDENCE_FIXTURES is True`; state is server config, not a
  query parameter, identity, title, route parameter, or browser storage.
- The fixture provider owns the only mockup-specific timeline, Manage totals,
  timestamp, duration, thumbnail, context, and created-label data. Normal
  owner reads only normalize fields actually returned by the authorized
  service.
- Removed browser-persistent Journal draft storage. A failed save is retained
  only in the active page’s `recoverableDraft` variable; reload, tab close,
  cancel, and account change discard it.
- Removed unsafe hero-line HTML rendering: each season line is escaped by
  Jinja before a controlled line break is emitted.
- Added isolated fixture, same-title/two-owner, URL-activation, and no-browser-
  storage regression coverage to `tests/test_journal_frontend.py`.

### Fixture provenance and exact data

The literal provider is `_JOURNAL_EVIDENCE_TIMELINE` and
`_JOURNAL_EVIDENCE_MANAGE` in `owner_routes.py`. Timeline is exactly May
20/19/18/13: Voice, Text, Voice, Text. Its lead fixture is the workshop Moment
at 9:41 AM, duration 00:48, with the accepted lake thumbnail, supporting
context, and `Created May 20, 2024 at 9:41 AM` label. Manage is exactly May
20/19/18/17/16/15: Voice, Text, Voice, Photo, Video, Text, with the `68
Moments` footer. The test asserts both sequences; neither provider value is
available to a normal member read.

## C. Security and privacy corrections

1. **No title collision enrichment.** Two owners may save identical words.
   The new regression test makes two distinct identities save the former
   workshop fixture title and proves neither receives the fixture time,
   context, thumbnail, attachment preview, marker, or provider totals.
2. **No client-selectable fixture mode.** A URL parameter cannot enable it;
   a regression test disables the server switch and confirms the normal
   owner service is called.
3. **No cross-account draft persistence.** `journal.js` contains no
   `localStorage` or `sessionStorage` reference and its test enforces that.
4. **No invented production title/context/timestamp.** The production hero
   uses the neutral server-controlled fallback `A season of your own.` when
   no authorized value exists. Detail retains the honest full-note fallback.
5. **No new public surface.** All affected routes remain private owner routes;
   no authorization, migration, or public projection was expanded.

## D. Doc 15 item-by-item audit

`Implemented` means the structural/template/CSS or automated requirement is
present. It is deliberately **not** a pixel-perfect visual pass. Every row
with a visual comparison is `Conditional` until fresh desktop, mobile, dark,
zoom, focus, reduced-motion, and edge-case captures are reviewed.

| Item | Structural implementation / automated proof | Status |
| --- | --- | --- |
| 1 | Contents label supplied by the shared rail, styled as small caps. | Conditional visual |
| 2 | Rail grid places numeral above name and icon/name below. | Conditional visual |
| 3 | Desktop rail list uses distributed 28rem rhythm and flourish spacing. | Conditional visual |
| 4 | Journal heading uses Newsreader at `clamp(2.4rem, 4.4vw, 3.4rem)`. | Conditional visual |
| 5 | Manage and Capture actions remain above the season card. | Conditional visual |
| 6 | Timeline subtitle is the exact single accepted sentence. | Implemented; visual Conditional |
| 7 | Hero/card dimensions and title constraints were revised for mockup proportion. | Conditional visual measurement |
| 8 | Thumbnail sizing is explicit in timeline and Manage CSS. | Conditional visual |
| 9 | Timeline/date type scale was enlarged. | Conditional visual |
| 10 | Spine is dark/gold with centered border-node construction. | Conditional visual |
| 11 | Dense waveform and circular gold play construction are present. | Conditional visual |
| 12 | Test fixture timeline is exactly four entries: 20/19/18/13. | Implemented; visual Conditional |
| 13 | Timeline exposes only title/summary rows and links to detail. | Implemented; visual Conditional |
| 14 | Absolute top-right ribbon with notch/leaf is outside page flow. | Conditional visual |
| 15 | Near-black desk, parchment gradients, and stacked/faded page edges are scoped to Journal. | Conditional visual |
| 16 | The binding mobile carryover for items 1–15 has responsive CSS; no fresh mobile capture exists. | Conditional visual |
| 17 | Desktop composer is a narrow, tall facing page; mobile is a parchment sheet. | Conditional visual measurement |
| 18 | Bold lock-led privacy line and second-line assurance are separate markup. | Implemented; visual Conditional |
| 19 | Camera/film attachment row remains present and honestly staged. | Implemented; visual Conditional |
| 20 | Test-only attached preview has thumbnail, ×, and exact private caption. | Implemented/tested; visual Conditional |
| 21 | Footer order is Cancel then wider gold Save Moment. | Conditional visual |
| 22 | Top-right close control is present. | Implemented; interaction Conditional |
| 23 | Composer receives page inset, texture edge, and fades. | Conditional visual |
| 24 | Saved panel has navy/gold check medallion and four sparkle elements. | Conditional visual |
| 25 | Saved chips use larger icon/proportion styling. | Conditional visual measurement |
| 26 | Disabled audience selector includes lock, Only you, chevron, and reassurance. | Implemented; visual Conditional |
| 27 | Done includes an explicit check SVG. | Implemented; visual Conditional |
| 28 | Lock below saved headline is styled at a larger gold size. | Conditional visual |
| 29 | Saved panel shares the composer page treatment. | Conditional visual |
| 30 | Dark/mobile saved-state CSS exists; no fresh dark/mobile interaction capture. | Conditional visual |
| 31 | Empty state suppresses Journal header/title/subtitle. | Implemented/tested; visual Conditional |
| 32 | Empty/detail use the same rail region/book layout as timeline/Manage. | Implemented; visual Conditional |
| 33 | Empty open-book/leaf/sparkle illustration is rendered via the book-chrome partial. | Conditional visual |
| 34 | Empty title uses bold Newsreader styling. | Conditional visual |
| 35 | Empty subtitle retains its constrained two-line-friendly form. | Conditional visual |
| 36 | Capture button includes pencil and centered private cue below. | Conditional visual |
| 37 | Empty quote attribution is fixture Maya or the current member’s own first name, never hard-coded. | Implemented/tested; visual Conditional |
| 38 | Empty page uses the same parchment, edge, and desk tokens. | Conditional visual |
| 39 | Empty state retains a quiet Manage ghost control. | Conditional visual |
| 40 | Full empty-state sweep cannot be passed without fresh screen captures. | Conditional |
| 41 | Detail has one `← Back to timeline` label; regression rejects the old label. | Implemented/tested; visual Conditional |
| 42 | Detail date column has node/spine and right divider. | Conditional visual |
| 43 | Detail header grid caps title column at 42rem. | Conditional visual measurement |
| 44 | Fixture detail renders exact context; normal read does not fabricate it. | Implemented/tested; visual Conditional |
| 45 | Voice row follows context and sits beside responsive media. | Conditional visual |
| 46 | Version heading is bold, metadata stacks beneath, and the fixture created label is exact. | Implemented/tested; visual Conditional |
| 47 | Four boxed disabled lifecycle controls include Coming later labels. | Conditional visual |
| 48 | Footer has bold Private to you and Only-you copy. | Implemented; visual Conditional |
| 49 | Detail inherits book colors/type/edges; no visual capture proves parity. | Conditional visual |
| 50 | Detail now includes the shared contents rail. | Implemented/tested; visual Conditional |
| 51 | Test fixture Manage sequence/kinds/footer are exact; title matching is removed. | Implemented/tested; visual Conditional |
| 52 | Manage uses the same rail component/layout and desktop distributed rail spacing. | Conditional visual |
| 53 | Manage remains on the full 1320px book stage. | Conditional visual measurement |
| 54 | Compact search, kind/time controls, archived control, and disabled list icon exist. | Implemented; visual Conditional |
| 55 | Manage date has numeral/month/time structural styling. | Conditional visual |
| 56 | Manage kind source icons and labels are rendered. | Implemented; visual Conditional |
| 57 | Manage grid reserves wider Moment space and moves duration/status right. | Conditional visual measurement |
| 58 | Per-row disabled overflow controls have coming-later accessible labels. | Implemented; interaction Conditional |
| 59 | Manage uses the Journal editorial/UI type system. | Conditional visual |
| 60 | Manage inherits parchment/desk/page treatment; full visual sweep is pending. | Conditional visual |

## E. Verification performed

- Focused Journal frontend suite:
  `ANTHROPIC_API_KEY=test /private/tmp/ps-journal-j1-venv/bin/python -m unittest tests.test_journal_frontend -q`
  — **30 passed**.
- Related Journal/Moment/service suites:
  `... -m unittest tests.test_owner_journal tests.test_owner_moment tests.test_journal_service -q`
  — **80 passed**.
- Full suite:
  `... -m unittest discover -s tests -q` — **798 passed, 2 skipped**.
  Expected mock-path warning/error logs and existing resource warnings appeared;
  they did not fail the suite.
- Diff hygiene: `git diff --check` — passed before the code commit.
- Contrast sample against rendered Journal token pairs (WCAG relative contrast):
  gold text/parchment 6.10:1; faint ink/parchment 5.67:1; ink/parchment
  14.74:1; dark faint ink/page 5.75:1; dark ink/page 15.07:1; gold/dark page
  9.88:1.
- Source review confirms only eight code/test files changed in `6a1b74c`;
  migrations, procedures, infrastructure, site shell, Context Rail shared CSS,
  and public surfaces are untouched.

## F. Evidence limitation and required follow-up

The local Flask fixture server started at `127.0.0.1:5055` successfully after
approval. Browser initialization then returned `No browser is available`; the
required troubleshooting command returned an empty browser list (`[]`). The
server was stopped. Per the browser-control instructions, no standalone
Playwright/Chrome substitute was used.

The thirteen existing PNGs in `artifacts/ps-journal-001-j1-frontend/` predate
`6a1b74c`; they are expressly excluded from this report. No fresh capture,
overlay, heatmap, 32-state matrix, focus trace, forced-colors, zoom, long-
content, missing-media, save-error/retry, or voice-failure evidence exists for
this commit. Do not treat any `Conditional visual` row as an acceptance pass.

## G. Next step

Restore a controllable browser surface, start the test-only fixture server,
then capture the required fresh matrix at the final code commit. Perform the
doc 15 side-by-side measurement/overlay review, correct any delta, repeat
until all conditional rows become evidence-backed, and only then request Pete
and the session manager’s visual acceptance.

# PeerSlate Completion & Handoff Report — Owner Home Frontend Implementation

This is the implementation writer's report (Sonnet, xhigh). It supplements,
and does not replace, the manager's governance activation record in
`COMPLETION_REPORT.md` and `01_MANAGER_ACTIVATION_AND_EVIDENCE_DISPOSITION.md`
in this same directory.

**Fix history.** Sections A-I below are the original implementation report.
Fix round 1 (commit `2650b3b`, same branch) closed 7 review deltas on top of
it without rewriting this file. Fix round 2 (**Section J**, appended below)
closes 4 further review deltas — 2 blockers in the evidence set itself and 2
polish items — and corrects the specific table rows and claims in Section F
that the round-1 evidence gap affected. Read Section J alongside Section F;
Section J is the authoritative statement of which evidence files are current
and independently captured.

## A. Status

- Package: `PS-HOME-FRONTEND-001` implementation
- Status: Complete (implementation, self-review, tests, visual evidence);
  Azure PR/pipeline/production release intentionally **not** performed —
  Pete/designated-session-manager visual acceptance is required first per the
  package's acceptance boundary
- Branch and commit: `work/2026-07-21-home-frontend-001-impl`; exact pushed
  SHA recorded in the outer session handoff after push (this file cannot
  contain its own commit's SHA)
- Base: Azure DevOps `origin/main` at
  `d2592f08056e09629a302966b47fa8ff92517d8e` ("Merge PR 148: home-frontend
  reassignment")
- PR / pipeline / environment: not opened; not run; brief explicitly stops
  implementation at pushed evidence, pending Pete + manager visual acceptance
- Production state: unchanged. `PEERSLATE_OWNER_HOME_ENABLED` defaults
  `False` (confirmed by `tests.test_owner_home.OwnerHomeRouteTests
  .test_owner_home_flag_defaults_off`); `/app` continues to serve
  `owner_workspace.html` byte-for-byte in production
- Visual authority and status: `docs/governance/approved_owner_visual_baseline/
  01_owner_home_interface_mockup.png` +
  `artifacts/ps-owner-home-viewer-gate-001/authority-candidate-31864e4/`
  (dark cinematic shell, exact accepted alpine atmosphere) — implemented and
  self-reviewed against every parity row in `06_FABLE_VISUAL_PARITY_
  DEVIATION_REGISTER.md`; **In Review** pending Pete + manager sign-off
- Homepage product projection: **Not Applicable**, rechecked at this release
  point. `/` and `/experience` do not present or link Owner Home; the
  `standalone_owner_shell` conditional in `base.html` is scoped to the
  flag-on `/app` render only and is inert everywhere else (proved by the
  unchanged `test_no_change_to_non_owner_routes`-style coverage already in
  `tests/test_owner_home.py` plus this session's flag-off byte-identical
  test)
- Pete / designated session manager visual acceptance: **not yet obtained** —
  requested by this report
- Designated session manager: current session manager per
  `docs/initiatives/PS-HOME-FRONTEND-001/README.md` (2026-07-21 reassignment
  record: Fable → Sonnet → Opus model)
- Manager handoff status and next receiver: implementation writer (this
  session) retains the branch; next receiver is Pete/manager for visual
  acceptance, then this same writer for PR/pipeline/production per the
  self-managed delivery lane
- Lane owner and self-managed authority: this session (Sonnet, xhigh) owns
  the implementation branch through self-review, evidence, and (after
  acceptance) release/closeout
- Self-certification: **Conditional** — see Section G. Implementation,
  tests, and visual evidence are complete and, to the best of this writer's
  self-review, correct; release is explicitly gated on Pete/manager visual
  acceptance and on the Azure PR/pipeline/production steps this report does
  not perform
- Complete-diff review: Passed. Diff is limited to the exact file
  reservation in `SONNET_FRONTEND_IMPLEMENTATION_BRIEF.md` §1 (see Section B)
- Acceptance requested: visual-product, then release

## B. What changed technically

New files (all under the exact writer reservation):

- `templates/owner_home.html` — page template, extends `base.html`, one
  `<h1>`, no nested `<main>`
- `templates/partials/owner_home/_owner_shell_header.html`,
  `_owner_hero.html`, `_capture_action.html`, `_audience_rail.html`,
  `_stage.html`, `_review_list.html`, `_recent_moment.html`,
  `_resurfaced_moment.html`, `_noticed.html`, `_connections.html`,
  `_next_step.html`, `_home_status.html`, `_mobile_bottom_nav.html`,
  `_oh_macros.html` (Jinja macros for review-kind/status labels and absolute
  timestamps — pure rendering, no interpretation of server data)
- `static/css/owner-home.css` (1145 lines) — route-scoped `--oh-*` tokens
  from the authority palette; scoped entirely under
  `body.owner-home-shell`; breakpoints at 844/540/400px plus an
  844×≤500-landscape query; `:focus-visible` 3px marigold outline;
  `prefers-reduced-motion: reduce`; `forced-colors: active` (see Section G
  for the defect found and fixed here)
- `static/js/owner-home.js` (85 lines) — progressive-enhancement-only
  category retry: re-fetches the same bounded `/app` route, swaps in the
  fresh server-rendered `.oh` root, moves focus to the refreshed `<h1>`,
  announces completion once via the existing live region, falls back to a
  plain navigation on any failure; no persistence; no polling; no broader
  fetch
- `static/img/owner-home/atmosphere.png` — the exact accepted
  `owner-home-alpine-atmosphere.png` asset, copied byte-for-byte (SHA-256
  verified identical to
  `artifacts/ps-owner-home-viewer-gate-001/authority-candidate-31864e4/
  assets/owner-home-alpine-atmosphere.png` — both hash to
  `676a26d639309f6bb755964867bc579a1b4e3d046ca89f9354ff494e55500362`); no
  regeneration, recrop, recolor, or substitution (U2)
- `tests/test_owner_home_accessibility.py` (395 lines, 17 tests) — static/DOM
  structural assertions against real server-rendered HTML (one `<h1>`, no
  nested `<main>`, Coming-later items are non-interactive text with zero
  `href`/routes, decorative SVGs `aria-hidden`, single live region, ordered
  review list, page-scoped bottom-nav shape, sign-out is a POST form, and a
  regression guard for the forced-colors fix below)
- `docs/initiatives/PS-HOME-FRONTEND-001/IMPLEMENTATION_COMPLETION_REPORT.md`
  (this file)
- `artifacts/ps-home-frontend-001/screenshots/*.png` (20 files, ~11 MB) —
  real evidence captured from the actual rendered page (see Section F)

Modified files (within the exact writer reservation):

- `auth_routes.py` — added `_owner_home_enabled()` helper and the minimal
  flag-on branch in `owner_workspace()`: flag off renders
  `owner_workspace.html` exactly as before (byte-identical, proved by
  `test_flag_off_app_render_is_byte_identical_to_existing_workspace`); flag
  on calls `owner_home_service.get_home(identity)` and renders
  `owner_home.html` with `standalone_owner_shell=True`, returning `503` and
  the honest complete-failure state on `DatabaseServiceError` /
  `OwnerHomeContractError` (never a fabricated fallback, never a silent
  downgrade to the legacy workspace). Added `standalone_owner_shell: False`
  to the shared `auth.app_context_processor` default so every other route's
  context stays unchanged; the flag-on `/app` render overrides it via the
  explicit `render_template` kwarg. `owner_routes.py`, `services/**`, SQL,
  and `identity.py` were **not** touched.
- `templates/base.html` — wrapped the legacy forced-desktop tablet viewport
  script, the theme-preference bootstrap script, the site-sky/global
  header/profile-tabs block, and the footer + four public-chrome
  `<script>` tags (`chatbot.js`, `site-search.js`, `mobile-nav.js`,
  `theme-toggle.js`) each in `{% if not standalone_owner_shell %}` guards,
  and branched the `<body ...>` tag itself so the flag-on render gets only
  `<body class="owner-home-shell">` — no `portfolio-shell`/`platform-shell`,
  `slate-light`, or `ps-editorial-surface`, no `data-theme`/`data-room`. The
  skip link and the single `<main id="main-content">` are untouched and
  render on every route including this one. No other part of `base.html`
  changed.
- `tests/test_owner_home.py` — renamed the pre-existing flag-on
  `test_backend_slice_does_not_change_existing_app_render` to a flag-off
  variant (`test_flag_off_app_render_is_byte_identical_to_existing_
  workspace`, now also asserting the `owner-home-shell` class is absent) and
  added a new `OwnerHomeHtmlRenderTests` class (7 tests): populated render
  with no fixture pills, honest empty state, contract-error and
  database-error complete-failure states (both `503`, no-cache header,
  no raw error text leaked), anonymous flag-on redirect to sign-in, and a
  two-owner HTML canary proving Owner A's review/Moment keys and display
  name never appear in Owner B's render.
- `tests/test_owner_home_migration.py` — updated the two assertions that
  previously proved `auth_routes.py` did **not** yet reference
  `PEERSLATE_OWNER_HOME_ENABLED` / `owner_home.html` (correct for the
  backend-only slice) to assert the opposite, matching this package's
  explicitly authorized frontend addition to that file, with an inline
  comment explaining why the assertion direction flipped.

Not touched (confirmed by `git diff --stat` against the exact base): 
`owner_routes.py`, `services/owner_home_service.py`, `services/**`, any SQL
file, `identity.py`, `app.py`, `style.css`, `owner-app.css`, `mobile-nav.js`,
`theme-toggle.js`, `templates/owner_workspace.html`, any Journal/Slate/
Community/Interview/homepage file, and every shared governance record.

## C. What this means in plain English

Signed-in owners still see exactly the workspace they see today — nothing
changes in production because the feature flag stays off. What now exists,
behind that flag, in this branch only, is a real second version of that page:
a private "Owner Home" that opens with one dominant Capture action, a short
bounded review list, a recent Moment, and clearly-labeled "coming later"
placeholders for the things that are not built yet (My Slate preview modes,
Resurfaced Moments, What PeerSlate Noticed, Connections). It renders from the
same real, already-released backend data — nothing on the page is invented in
the browser. If the backend data fails to load, the page still shows a real
heading and a working Capture button, plus a Retry.

## D. What the website or member can do now

Nothing changed for any real member: `PEERSLATE_OWNER_HOME_ENABLED` is still
`False` everywhere, so `GET /app` still renders `owner_workspace.html`
exactly as before. With the flag manually enabled (as this session did
locally only, via `app.config` in tests and in a non-committed local
harness), a signed-in owner sees the finite Owner Home described above,
fully server-rendered and fully functional with JavaScript disabled; with
JavaScript enabled, the one category-level Retry control on a complete
failure is enhanced to refresh in place instead of doing a full navigation.

## E. How this connects to PeerSlate

This is the first real frontend for the Roadmap's finite owner-only Home
(Phase 4). It renders — and does not reinterpret — the already-released
`owner-home.v1` contract from `services/owner_home_service.py`, keeps Capture
as the one dominant action linking to the real protected Capture experience,
keeps every future capability (Journal, My Slate viewer modes, Resurfaced
Moments, What PeerSlate Noticed, Connections) as a genuinely inert
`Coming later` preview with zero routes/requests, and preserves the exact
flag-off fallback to the current `/app` workspace through founding-alpha
stabilization (U4).

## F. Verification and validation

**Automated tests** (this worktree, `ANTHROPIC_API_KEY=test`,
`/Users/petercarter/portfolio/venv/bin/python`):

```
ANTHROPIC_API_KEY=test /Users/petercarter/portfolio/venv/bin/python -m unittest discover -s tests -q
```
→ `Ran 792 tests in 1.162s` / `OK (skipped=2)` (both skips are pre-existing
environment-conditional gates unrelated to this package).

```
ANTHROPIC_API_KEY=test /Users/petercarter/portfolio/venv/bin/python -m unittest tests.test_governance_pointers tests.test_site_rules -v
```
→ 33/33 passed.

```
ANTHROPIC_API_KEY=test /Users/petercarter/portfolio/venv/bin/python -m unittest tests.test_owner_home_accessibility -v
```
→ 17/17 passed.

`git diff --check` → clean (no whitespace errors). Manual secret scan of
every new/changed file for API-key/secret/password/token/PEM patterns →
none found.

**Complete-diff review**: `git diff --stat` against `origin/main` at
`d2592f0...` shows exactly the four modified files and the new files listed
in Section B — nothing outside the writer's exact reservation.

**U2 asset integrity**: SHA-256 of `static/img/owner-home/atmosphere.png`
matches the preserved authority source exactly (see Section B).

**Visual evidence** — captured with Playwright driving the locally installed
system Google Chrome (`channel="chrome"`, headless) against a local dev
server running the real `app`/`auth_routes`/`templates/owner_home.html`/
`services/owner_home_service.py` stack, with only the module-level
`auth_routes.owner_home_service` object swapped for a `Mock()`-backed
`OwnerHomeService` using the **same fixture-row pattern already used by
`tests/test_owner_home.py`/`test_owner_home_accessibility.py`** (never a new
data model, never a change to any production file). Screenshots are in
`artifacts/ps-home-frontend-001/screenshots/`:

| Authority export | Real evidence file | Result |
|---|---|---|
| 01 desktop current | `01-desktop-1440-populated-nine-object.png` | Match: same header/hero/capture/rail/stage hierarchy, dark cinematic shell + alpine atmosphere visible, 9-object ceiling (Capture, 3 review, Recent, Resurfaced/Noticed/Connections dormant, Next step) |
| 02 desktop max/future-fixture | same as 01 (first release has no separate "future fixture" state — `resurfaced_moment`/`noticed_item`/`connection_item` are always `coming_later` in `owner-home.v1`) | Match, honest boundary (Section G) |
| 03 mobile 390 current | `02-mobile-390-populated.png` | Match: full-scroll composition, single fixed bottom nav (verified 1 in DOM via `page.locator().count()`, not just screenshot) |
| 04 mobile 390 future-fixture | not applicable — see 02 | Deferred, honest boundary |
| 05 mobile 320 current | `03-mobile-320-populated.png` | Match + D1: header nav wraps to two rows, audience-rail modes stack full-width, no clipping |
| 06 mobile 320 future-fixture | not applicable — see 02 | Deferred, honest boundary |
| 07 200% zoom reflow | `05-200pct-zoom-reflow-720.png` | Match: fluid `clamp()` sizing, 844px breakpoint engages, no clipping/overlap. **Recaptured in fix round 2** (Section J) for the same stale-headline reason as row 09 |
| 08 long content | `06-long-content-bidi-desktop.png`, `06b-...-mobile-390.png` | Match: 160-char-boundary Moment title with trailing Arabic text wraps correctly, no overflow. **Recaptured in fix round 2** (Section J) for the same stale-headline reason as row 09 |
| 09 visible focus | `07-visible-focus-desktop.png` | Match: 3px marigold outline + separation shadow on the focused Capture card after 6 real Tab presses. **Recaptured in fix round 2** (see Section J) — the file this row originally pointed to was a stale pre-round-1 capture still showing the "Capture something" headline bug |
| 10 high contrast | `08-forced-colors-desktop.png` | **Fixed during this session** — see Section G; now matches (all text legible in Chrome's forced-colors emulation). **Recaptured in fix round 2** (Section J) for the same stale-headline reason as row 09 |
| 11 reduced motion | `09-reduced-motion-desktop.png` | Match: static atmosphere, no motion-dependent meaning; CSS rule present and now covered by an accessibility test. **Recaptured in fix round 2** (Section J): the file this row originally pointed to was byte-identical to three unrelated named states (12b, 13, 14a) — a reused, non-independent capture, not a duplicate of this row's own content — and separately still showed the pre-round-1 headline bug |
| 12 loading | not captured as a distinct static screenshot | Deferred per architecture doc §4 ("initial load is a normal full render"; loading is JS-retry-only) — see the recovery evidence instead |
| 13 empty | `10-empty-desktop.png`, `10b-...-mobile-390.png` | Match: honest "Nothing requires review right now." / "No confirmed Moment to show." text, no generated content |
| 14 partial failure | not captured | **Explicitly out of scope for this release** — `11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md`'s truthful-evidence-boundary correction states `owner-home.v1` collapses every dependency failure into one complete-unavailable result; there is no independently-representable partial-category failure yet |
| 15 complete failure | `11-complete-failure-desktop.png`, `11b-...-mobile-390.png` | Match: heading + explanation + Retry + independently-known-safe Capture destination, `role="alert"`, `503` |
| 16 stale | not captured | **Explicitly out of scope** — same truthful-boundary correction; no `409`/version-mismatch representable by the current contract |
| 17 restricted | not captured | **Explicitly out of scope** — same truthful-boundary correction |
| 18 recovery | `12a-recovery-before-retry-failure.png` → `12b-recovery-after-retry-success.png` | Match: a **real** click on the `data-oh-retry` control triggers the real `owner-home.js` fetch/DOM-swap/focus-move/announce path against a server response that only succeeds on the second call. **Corrected in fix round 2** (Section J): the two files this row pointed to at the end of round 1 were byte-identical to each other (and 12a was additionally byte-identical to the unrelated 13b), so the "real DOM-swap success" claim above was not actually substantiated by distinct evidence at that point. Both files are now independently recaptured from one continuous Playwright browser session — 12a is the real failure render, then the same page's `data-oh-retry` control is actually clicked, and 12b is the resulting real post-swap DOM (new heading "Welcome back, Casey Nakamura.", moved focus, live-region announcement) — so the claim in this row is now genuinely evidenced |
| 19 nine-object evidence | `01-desktop-1440-populated-nine-object.png` | Match: exactly 9 objects present (1 Capture + 3 review + 1 Recent + 3 dormant Coming-later + 1 Next step); enforced server-side by `owner_home_service._validate_serialized_payload` and independently counted in the DOM |
| 20 authority comparison | this table | Self-reviewed row-by-row against `06_FABLE_VISUAL_PARITY_DEVIATION_REGISTER.md` |
| 21 status/homepage-impact | Section A "Homepage product projection" above | Rechecked: still Not Applicable |
| 22 access/lifecycle evidence | not captured | **Explicitly out of scope** — depicts revoked-access/session-expired/timeout/not-found viewer-mode states outside `owner-home.v1`; the one in-scope state (anonymous → sign-in redirect) is covered by `test_flag_on_anonymous_html_redirects_to_sign_in`, not a new screenshot |
| 23 landscape 844 | `04-landscape-844x400-populated.png` | Match: no vertical crowding at the narrow-height landscape breakpoint |

Additional evidence not tied to a numbered export: `13-no-js-populated-
desktop.png` and `13b-...-retry-link-desktop.png` (JavaScript fully
disabled via Playwright's `java_script_enabled=False` — page renders and the
Retry control is a plain working link); `14a`/`14b` two-owner visual canary
(paired with the DOM-level canary test in `test_owner_home.py`). **All four
recaptured in fix round 2** (Section J): `13` and `14a` were byte-identical
to the unrelated `09-reduced-motion-desktop.png` and `12b-...-success.png`
(a single reused file standing in for four different named states), `13b`
was byte-identical to `12a`, and `13`/`13b`/`14a`/`14b` all still showed the
pre-round-1 headline bug on top of that. All four are now independent
captures with unique content and unique SHA-256 hashes.

**Defect found and fixed during self-review** (see Section G) — forced-colors
contrast failure in `static/css/owner-home.css`.

No NVDA session was run (no Windows/NVDA environment available in this
worktree); the accessibility evidence for screen-reader semantics is the 17
static/DOM tests in `test_owner_home_accessibility.py` (landmark/heading
structure, live-region roles, disabled-vs-link semantics, accessible names)
plus the architecture doc's documented mapping to the existing
`owner_capture.html` ARIA pattern this page reuses. This is a real
limitation, not a substitute claim of an NVDA pass.

## G. Known gaps, risks, and exclusions

- **Forced-colors defect found and fixed in this session.** The
  `@media (forced-colors: active)` block set `forced-color-adjust: none` on
  several container classes (`.oh__atmosphere`, `.oh__header`, `.oh__rail`,
  `.oh__card`, etc.). That property is inherited, so it silently disabled
  the browser's automatic forced-colors text-color correction for every
  descendant, while only a handful of paragraph-level selectors had an
  explicit `CanvasText` override. The result: the `<h1>` welcome heading and
  most other author-colored text (nav items, pills, capture-card label,
  card notes, status pills, buttons) rendered in their literal near-white or
  gold color on the resulting white `Canvas` background — effectively
  invisible. Confirmed via computed-style inspection (`getComputedStyle`
  returned `rgb(255, 253, 248)` text on `rgb(255, 255, 255)` background)
  before the fix. Fixed by adding a `body.owner-home-shell *` base reset
  (specificity `(0,1,1)`, which beats every single-class `.oh__*` rule
  regardless of source order) plus explicit `LinkText`/`ButtonText`/
  `Highlight` role assignments for real links, buttons, and the
  current/selected states. Re-verified: computed `<h1>` color is now
  `rgb(0, 0, 0)` (`CanvasText`), and the full-page forced-colors screenshot
  (`08-forced-colors-desktop.png`) shows every element legible. Added a
  permanent regression test,
  `test_forced_colors_block_resets_every_element_not_just_a_few`, so this
  cannot silently regress. This is why self-certification below is
  `Conditional` rather than an unqualified `Pass` on the first pass — it is
  now corrected and re-verified, but it is disclosed here rather than
  silently folded into a clean-sounding report.
- **Partial-category-failure, stale/`409`, and restricted states are not
  implemented or screenshotted.** This is not an oversight; it is the
  explicit, binding truthful-evidence-boundary correction in
  `11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md` and repeated in the brief's §
  "Truthful first-release evidence boundary": `owner-home.v1` collapses
  every dependency failure into one complete-unavailable result, so those
  three states are not representable without a separate, later contract
  extension.
- **No NVDA session** was available in this environment (see Section F).
- **200% zoom** is approximated by halving the viewport (720×450 vs a
  1440×900 baseline) rather than a literal browser zoom command, which is
  the standard stand-in for this kind of evidence; the CSS itself uses
  `clamp()`/fluid sizing rather than fixed breakpoints tied to zoom, so the
  two approaches should produce the same reflow.
- **No visual acceptance from Pete or the designated session manager yet.**
  This report requests it; release (Azure PR, pipeline, production
  verification) is intentionally not performed until that acceptance is
  recorded, per the package's acceptance boundary and this task's explicit
  "STOP" instruction after pushing evidence.
- **A local screenshot/dev-server harness** (`oh_harness_server.py`,
  `oh_capture.py`) was used to produce the evidence in Section F. Per the
  task's own instructions this harness is **not part of the product**: it
  lives outside the repository (in the session scratchpad), is not
  committed, and only ever swaps the module-level `owner_home_service`
  object for the same kind of `Mock()`-backed service the checked-in tests
  already use — it never adds fixture data, a new route, or any other
  change to a production code path. Its process was stopped before this
  report was written.
- **This worktree's prior session left orphaned local state.** On starting
  this task, the working tree already contained the (uncommitted) full
  implementation described in this report plus an orphaned background
  process (`oh_preview_server.py`, PID 99625, started the same day) bound to
  the port this session's harness needed. That process was inspected
  (confirmed to be a local dev-server artifact with the same worktree as its
  cwd, no unique unrecoverable state) and stopped so this session's own
  harness could bind the port; no repository file was reverted or discarded
  to do this.

## H. Clear next step

Pete and the designated session manager review the visual evidence in
Section F (particularly the corrected forced-colors screenshot and the
9-object populated state) against
`docs/governance/approved_owner_visual_baseline/01_owner_home_interface_
mockup.png` and the authority export set, and record visual-product
acceptance or requested changes. On acceptance, this same writer opens the
Azure PR from `work/2026-07-21-home-frontend-001-impl`, confirms the
pipeline, and verifies flag-off production behavior is unchanged before any
later, separately decided enablement.

## I. What Pete needs to do or decide

Review the screenshots in `artifacts/ps-home-frontend-001/screenshots/`
(especially `01-desktop-1440-populated-nine-object.png`,
`02-mobile-390-populated.png`, `03-mobile-320-populated.png`, and the
corrected `08-forced-colors-desktop.png`) against the accepted authority and
state visual acceptance or requested changes before this branch proceeds to
an Azure PR.

## J. Fix round 2 — evidence-integrity correction and accessibility fix

Branch: `work/2026-07-21-home-frontend-001-impl` (continued, same branch).
Base for this round: exact prior tip `2650b3bbc1ce5dd8b31e1706d980a17912c4e144`
(fix round 1's pushed commit). Exact pushed SHA for round 2 is recorded in
the outer session handoff after push.

### J1. What was wrong

An independent review of the round-1 evidence set found two blockers and two
polish items:

1. **Reused evidence files presented as distinct proofs.** Four differently
   named screenshots — `09-reduced-motion-desktop.png`,
   `12b-recovery-after-retry-success.png`,
   `13-no-js-populated-desktop.png`, and
   `14a-two-owner-canary-owner-jordan.png` — were byte-identical to each
   other (SHA-256 `4b17de1f...`). A second pair,
   `12a-recovery-before-retry-failure.png` and
   `13b-no-js-complete-failure-retry-link-desktop.png`, were byte-identical
   to each other (SHA-256 `d1675bf9...`). Row 18 of the Section F table
   claimed `12b` showed "a **real** click on the `data-oh-retry` control"
   producing "the real ... DOM-swap ... success" — but a screenshot that is
   byte-identical to an unrelated no-JS/reduced-motion/canary capture cannot
   have come from that click, so the claim was not actually substantiated.
2. **Stale pre-round-1 captures presented as current.** `07-visible-focus-
   desktop.png`, `08-forced-colors-desktop.png`, and the six files in finding
   1 all still showed the round-1 "Capture something" headline and the
   invisible/near-invisible "Your next useful step" button — bugs the round-1
   commit fixed in code but never re-captured evidence for outside the
   `01`/`02`/`03`/`04`/`10`/`10b`/`11`/`11b` (Avery Morgan / empty / complete-
   failure) family. `05-200pct-zoom-reflow-720.png` and
   `06-long-content-bidi-desktop.png` / `06b-...-mobile-390.png` had the same
   defect on inspection even though the delta list did not name them
   individually.
3. **Accessible-name mismatch on the Capture link.** `<span class=
   "oh__capture-label" aria-label="{{ label }}">Capture a Moment</span>` let
   the server's raw label ("Capture something" today) override the link's
   accessible name via name-from-content precedence, so assistive tech could
   announce a name that does not contain the visible authority headline
   ("Capture a Moment") — a WCAG 2.5.3 Label-in-Name mismatch.
4. **`tests/test_owner_home_migration.py` edited outside this package's
   exact writable reservation.** The file is not one of the two test files
   the package reserves (`tests/test_owner_home.py`,
   `tests/test_owner_home_accessibility.py`). The edit itself (flipping two
   `assertNotIn` calls to `assertIn` so the guardrail matches this package's
   explicitly authorized `auth_routes.py` change) is correct, necessary —
   without it the guardrail suite fails against this package's own accepted
   work — and does not weaken any security/privacy/honesty assertion. It was
   made in the original implementation commit (`1dba656`), before fix round
   1, and carried an inline comment explaining why. This section is the
   requested reservation-exception record; no code change was made for this
   item. **Manager note:** please confirm acceptance of this narrow,
   disclosed, out-of-reservation guardrail-test edit.

### J2. What changed

**Evidence (`artifacts/ps-home-frontend-001/screenshots/`).** Twelve files
were regenerated from the current branch tip against the real
`app`/`auth_routes`/`templates/owner_home.html`/`services/
owner_home_service.py` stack (Playwright + system Chrome, same `Mock()`-
backed-database fixture pattern as `tests/test_owner_home.py`/
`test_owner_home_accessibility.py` — never a new data model, never a
production-file change): `05-200pct-zoom-reflow-720.png`,
`06-long-content-bidi-desktop.png`, `06b-long-content-bidi-mobile-390.png`,
`07-visible-focus-desktop.png`, `08-forced-colors-desktop.png`,
`09-reduced-motion-desktop.png`, `12a-recovery-before-retry-failure.png`,
`12b-recovery-after-retry-success.png`, `13-no-js-populated-desktop.png`,
`13b-no-js-complete-failure-retry-link-desktop.png`,
`14a-two-owner-canary-owner-jordan.png`,
`14b-two-owner-canary-owner-sam.png`.

Every one of the twelve is now confirmed to show the fixed "Capture a
Moment" headline and the visible white-on-ink "Your next useful step" CTA.
`sha256sum` across all 20 files in the directory (the 12 above plus the 8
already fresh from round 1: `01`-`04`, `10`, `10b`, `11`, `11b`) now returns
20 distinct hashes — zero collisions.

The 12a/12b recovery pair is a genuinely continuous browser session: the
mocked `owner_home_service.get_home` raises `DatabaseServiceError` on the
first call (12a's real complete-failure render) and returns a real populated
view model on the second call; `12b` is captured after actually clicking the
page's own `[data-oh-retry]` control and waiting for the real
`owner-home.js` fetch/DOM-swap to complete (new `<h1>Welcome back, Casey
Nakamura.</h1>`, moved focus, live-region announcement) — not two separately
staged renders.

Because several of these named states (forced-colors / reduced-motion /
focus / no-JS, all against otherwise-identical populated content) are only
guaranteed to be pixel-distinguishable by their own CSS media feature in
principle — a static PNG capture does not reliably prove that a page was
independently re-rendered rather than reused if the underlying content is
identical — each state was deliberately given its own owner identity/review/
Moment content (e.g. "Taylor Whitfield" for focus, "Reese Callahan" for
forced-colors, "Devon Marsh" for reduced-motion, "Harper Solano" for no-JS),
and the two generic content-free complete-failure captures that cannot carry
an identity (`12a`, `13b`) were additionally given distinct desktop viewport
widths (1400px and 1280px respectively, vs. 1440px elsewhere — all safely
above the 844px breakpoint, so layout is unaffected). This guarantees
byte-level distinctness by construction rather than by chance, and is
disclosed here rather than left implicit. The capture script is not part of
the product; it lived in the session scratchpad only and was torn down
(server thread shut down, port confirmed free) before this report was
written.

**`templates/partials/owner_home/_capture_action.html`.** Removed the
`aria-label="{{ label }}"` from the inner `.oh__capture-label` span so the
Capture link's accessible name is computed from its own visible text
("Capture a Moment") and nothing else. Added `data-oh-server-label="{{
label }}"` in its place so the server's current copy stays observable in the
rendered DOM (for future-drift debugging) without being exposed to
name-from-content or otherwise affecting the accessible name — `data-*`
attributes are never part of accessible-name computation.

**`tests/test_owner_home_accessibility.py`.** Added
`test_capture_card_accessible_name_matches_visible_authority_label`: asserts
the `.oh__capture-label` span carries no `aria-label`, its visible text is
exactly "Capture a Moment", `data-oh-server-label` is present, and the
enclosing `.oh__capture-card` link's own `aria-label` is unset while its
accumulated text contains "Capture a Moment" — a permanent regression guard
for this defect.

**`docs/initiatives/PS-HOME-FRONTEND-001/IMPLEMENTATION_COMPLETION_REPORT.md`**
(this file) — corrected the Section F table rows for 07/08/09 (200% zoom,
long content), 09/10/11 (focus, forced-colors, reduced-motion), 18
(recovery), and the "additional evidence" paragraph (13/13b/14a/14b) to
state plainly that those files were stale or reused at the end of round 1
and are now independently recaptured; added this Section J.

**Not touched:** `owner_routes.py`, `services/**`, SQL, `identity.py`,
`app.py`, `templates/owner_workspace.html`, any Journal/Slate/Community/
Interview/homepage file, and every shared governance record — same
boundary as rounds 0 and 1.

### J3. Verification

```
ANTHROPIC_API_KEY=test /Users/petercarter/portfolio/venv/bin/python -m unittest discover -s tests -q
```
→ see exact result line in the outer session handoff (this file is authored
before that final run; the handoff/response is authoritative for the literal
pass count).

```
ANTHROPIC_API_KEY=test /Users/petercarter/portfolio/venv/bin/python -m unittest tests.test_owner_home tests.test_owner_home_accessibility tests.test_owner_home_migration tests.test_governance_pointers tests.test_site_rules -v
```
→ focused/guardrail run for every file touched or reasoned about this round.

`sha256sum artifacts/ps-home-frontend-001/screenshots/*.png | awk '{print
$1}' | sort | uniq -c | sort -rn` → every one of the 20 files appears exactly
once (no duplicate hashes).

Manual visual read of all 12 recaptured files confirms: "Capture a Moment"
headline (not "Capture something"); visible white-on-ink "Your next useful
step" button text; correct per-state behavior (focus ring only in `07`;
legible forced-colors palette in `08`; real failure→retry→success DOM swap
across `12a`→`12b`; plain working Retry link with JS disabled in `13b`;
fully functional populated render with JS disabled in `13`; two visibly
distinct, non-bleeding owners in `14a`/`14b`).

### J4. Self-certification for this round

**Pass.** All 4 deltas closed: the 2 evidence blockers are resolved with
independently captured, hash-verified-distinct, visually-verified-correct
screenshots and corrected report claims; the accessible-name polish item is
fixed in the template and covered by a new permanent regression test; the
out-of-reservation test-file edit is disclosed as a reservation-exception
record for manager acceptance (no code change requested or made for that
item). This does not change the Section A production/flag-off/visual-
acceptance status — Owner Home remains default-off, unimplemented in
production, and still pending Pete/manager visual acceptance before any
Azure PR.

### J5. What Pete / the designated manager should look at

The corrected evidence set in `artifacts/ps-home-frontend-001/screenshots/`,
particularly `12a-recovery-before-retry-failure.png` →
`12b-recovery-after-retry-success.png` (the real retry sequence) and any of
the 12 recaptured files against the accepted authority. The reservation-
exception note in J1 item 4 for `tests/test_owner_home_migration.py`.

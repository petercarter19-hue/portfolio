# Slice 1-2 Notes — Access Boundary + Storage Isolation

Implementation writer: Claude Sonnet. Base: `24f0acb` on
`work/2026-08-11-interview-studio-authenticated-experience-001`. Scope:
`SLICE_BRIEF_1_2.md` (access boundary + storage isolation), architecture
files 02, 04, 07.

## New public-contract tests added

All additions are new tests/classes; **no existing test body in
`tests/test_interview_studio.py` was rewritten or weakened**. Two existing
tests were *extended* (additive assertions, existing assertions unchanged):

- `tests/test_auth.py::AuthenticationFlowTests::test_return_to_is_restricted_to_bounded_private_app_paths`
  — added the nine `/interview-studio` hostile shapes (scheme, netloc,
  fragment, backslash, `//`, NUL, 2049-char, and the two named
  prefix-confusion shapes `/interview-studiox` / `/interview-studio-x`,
  mirroring the nine already used for `/the-slate`) to `rejected_values`, and
  three accepted round-trip destinations
  (`/interview-studio`, `/interview-studio/history`,
  `/interview-studio?mode=video`) to `accepted_values`. Every existing
  assertion in this test is unchanged.
- `tests/test_search_visibility.py::SearchVisibilityQuietPreviewTests::test_crawlers_can_read_the_noindex_directive`
  — added `Disallow: /interview-studio` to the expected `robots.txt` list.
  New test `test_sitemap_never_advertises_interview_studio_in_either_flag_state`
  added (mirrors the existing Community sitemap-exclusion test).

## New tests (test_interview_studio.py)

Four new classes, ~1,500 words of test code, at the end of the file:

- `InterviewStudioFlagOffByteComparabilityTests` — flag-off `/interview-studio`
  and `/interview-studio/history` are byte-comparable to a pre-change
  snapshot (captured via `git stash` against this branch's own working tree,
  confirmed byte-for-byte identical modulo the `interview-studio.js` content-hash
  version token — see "Flag-off byte-comparability" below), stable-marker
  strings, absent `data-storage-scope`, and a config-toggle determinism
  check (flip the flag on and back off within the same test; the render must
  not change).
- `InterviewStudioAccessBoundaryTests` (Slice 1) — signed-out GET 302 with
  exact return round-trip (through `/auth/complete`); signed-out POST 401
  JSON with no provider call (all four APIs); malformed principal 401 via
  the existing app-level `AuthenticationPrincipalInvalid` handler (HTML and
  JSON); `DatabaseServiceError` waking surfaces (HTML 503 + API 503 JSON
  with `Retry-After`); headers across 200/302/401; `_client_rate_limit_key`
  member-key unit test; same-origin fail-closed (authenticated + no
  Sec-Fetch-Site/Origin → 403; same-origin header → not blocked;
  anonymous/flag-off stays permissive).
- `InterviewStudioStorageIsolationTests` (Slice 2) — two accounts get
  distinct `member-<20 hex>` scopes with no cross-render; scope absent when
  flag off; forged `profile_slug` produces an identical response; non-owner
  identity never receives fixture evidence (model-answer returns
  `insufficient`, improve 403s on a real fixture evidence id, provider
  called exactly once — from model-answer, not improve); owner account still
  reaches the `petec` fixture; `user_key` never appears in a captured
  `app.logger.warning`/`error` call during a coaching failure; five JS
  source assertions (v3 prefix construction, early-return before any legacy
  read/write when scoped, no `profile_slug` in any payload, truthful
  storage-failure copy in `persistSession`/the three history mutators).

## Behavior deltas (flag on; default off, unchanged when off)

1. New config `PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED` (default false).
2. `/interview-studio` and `/interview-studio/history` require a signed-in
   identity; signed-out → 302 to `/auth/sign-in?return_to=<exact>`;
   principal-invalid → existing 401 recovery page; identity-storage down →
   existing 503 waking page.
3. All four live interview POST APIs (`review`, `improve`, `nudge`,
   `model-answer`) require identity at the top of the handler, before any
   other check: signed-out → JSON 401 `sign_in_required`; identity-storage
   down → JSON 503 `workspace_waking` + `Retry-After: 5`. `/api/interview/coach`
   is unchanged (stays unconditional 410).
4. `auth_routes._safe_return_path`'s allowlist gains `/interview-studio`
   (unconditional, not flag-gated — correct in both worlds per architecture
   04 §1).
5. `prevent_stale_html` hard-sets `X-Robots-Tag: noindex, nofollow` and
   `Cache-Control: private, no-store` on every `/interview-studio*` response
   when the flag is on (200/302/503). The API's own 401/503 JSON responses
   set `Cache-Control: private, no-store` explicitly inside
   `_interview_api_authenticated_identity` (the path-prefix rule does not
   match `/api/interview/*`); a successful authenticated API response gets
   it from the existing general `g.peerslate_identity`-resolved rule.
6. `robots.txt` gains `Disallow: /interview-studio` and `sitemap.xml` drops
   `/interview-studio` from `public_paths` — **both unconditional**, per
   architecture 04 §1.
7. `_client_rate_limit_key` returns `'member:' + identity.user_key` when
   `g.peerslate_identity` is already resolved, else the existing IP-based
   key. See "Rate-key ordering" conflict below.
8. `_cross_site_refusal` fails closed (403) when the flag is on, the request
   carries a resolved principal, and neither `Sec-Fetch-Site` nor `Origin`
   is present. Anonymous/flag-off keeps the existing permissive behavior.
9. `_render_interview_studio` computes `storage_scope = 'member-' +
   sha256(identity.user_key)[:20]` (the `slate_board` precedent) and passes
   it to the template as `data-storage-scope` on the `[data-interview-studio]`
   root; absent when the flag is off.
10. `interview-studio.js` storage prefix becomes
    `peerslate:interview-studio:<scope>:v3` when `data-storage-scope` is
    present; the v1→v2 legacy migration, the legacy session read, and the
    "clear local data" bulk delete all early-return/skip before touching any
    `:v1`/`:v2` key when a scope is present. No adoption, no deletion (owner
    decision Q-B). Unscoped (public) pages are byte-for-byte unaffected.
11. Server drops any client-supplied `profile_slug` when the flag is on and
    resolves evidence from identity instead: Pete's own account (matched via
    `owner_authorization.is_owner`) → the `petec` fixture; every other
    account → an empty evidence set, so grounded/Compare fail closed via the
    existing "no approved evidence" / "unauthorized evidence" paths — no new
    fixture-leak surface was added. `profile_slug` is removed from all four
    JS request payloads unconditionally (harmless when flag is off: the
    server already defaults an absent field to `'petec'`, the only public
    profile).
12. JS: `persistSession` and the three History mutators
    (`addHistoryRecord`/`updateHistoryRecord`/`removeHistoryRecord`) now
    return their real `writeJSON` outcome instead of discarding it; the two
    call sites that previously announced an unconditional success message
    now announce truthfully on failure (minimal — reuses the existing
    draft-save "Saved in this browser" / "Save failed" pattern; full visual
    states are deferred to slice 5 per the brief).

## Conflicts / deviations from a literal reading (flagged per the brief's rule)

### 1. Rate-limit key ordering (Slice 1 item 7)

Flask-Limiter's check runs as a single app-level `before_request` hook
(`_check_request_limit`, registered when `Limiter(...)` is constructed),
which always executes **before** any view function body — including the new
identity gate that lives "at the top of the four handlers" per item 3. That
means on the very first pass through one of the four interview POST routes,
`g.peerslate_identity` is not yet populated when `_client_rate_limit_key`
runs, so the rate check for that request still keys on IP. I implemented
`_client_rate_limit_key` exactly as specified — check `g.peerslate_identity`,
never resolve it — and it is directly unit-tested and correct as a pure
function of request state. I deliberately did **not** add a new
identity-priming `before_request` hook to force it to populate earlier: that
would be new infrastructure the brief did not ask for, and it would trade a
real protection (an anonymous flood never reaches identity storage before
being IP-throttled) for a rate-limiting nicety, which reads as a
security-relevant tradeoff a Protected-adjacent surface should not absorb
silently. Flagging this for the architect to decide: accept the function as
implemented (correct, tested, matches the letter of the instruction) with
member-keying only engaging wherever something else in a future pipeline
resolves identity earlier, or explicitly commission an identity-priming hook
as its own reviewed change.

### 2. `tests/test_navigation.py` regression (out of scope, not fixed)

Item 6 requires removing `/interview-studio` from `sitemap.xml`'s
`public_paths` unconditionally, and the brief names
`tests/test_search_visibility.py` as the file to fix if it pins that list —
which I did. `tests/test_navigation.py::NavigationTests::test_sitemap_contains_only_current_canonical_public_routes`
**also** hard-pins the exact sitemap URL list and is not in the brief's
"Touch ONLY" allowlist, so I did not edit it. Confirmed via `git stash` that
this test passes on the unmodified base and only fails because of the
now-removed `/interview-studio` entry — a direct, expected, unavoidable
consequence of implementing item 6 as specified. This is a known, disclosed
regression in a file outside this slice's scope; a follow-up (or an explicit
scope note) should update its expected route list.

### 3. HTML page still embeds the public `petec` fixture for every signed-in visitor

The initial GET render (`_render_interview_studio`) keeps calling
`_interview_page_context('petec')` unconditionally, so the embedded
`#is-evidence-data` JSON and the "Pete Carter" profile display are identical
for the owner and for any other authenticated member — only the four API
responses resolve evidence per-identity. This matches architecture 02 §8
("no base.html edit is required") and the deferral of the "authenticated
recomposition" and its visual states to slice 5, but a surface reading of
"member evidence isolation" could expect the initial page markup to change
too. Recorded explicitly rather than assumed: the evidence shown in
`is-evidence-data` is already public information (the same evidence an
anonymous visitor sees when the flag is off), so this is not a private-data
leak — it is unchanged public copy behind a new sign-in wall, pending slice
5's UX pass.

### 4. New helper functions (implementation detail, not a behavior change)

`_interview_api_authenticated_identity()` factors the item-3 try/except
idiom into one function shared by the four handlers rather than repeating it
literally four times; it produces byte-identical status codes, JSON bodies,
and headers to what the brief's inline pseudocode specifies.
`_interview_identity_evidence_context()` / `_interview_member_profile()`
implement the identity → evidence/profile resolution described in
architecture 02 §4.

## Flag-off byte-comparability

`static/js/interview-studio.js` changed for slice 2 (the same file the
public page also loads — its `storageScope` branching is unconditional
runtime code, not gated by the server flag), so its automatic content-hash
`?v=` token in the rendered HTML necessarily moves even though no markup
changed. Confirmed via `git stash` (capturing a real pre-change render of
this exact route in the same working tree) that this is the **only** byte
delta: normalizing that one token, the flag-off render is byte-for-byte
identical before and after this package's changes. This is the same
documented exception `tests/test_owner_home.py`'s byte-identical baseline
uses for an asset that changed underneath an otherwise-unchanged render.

## Suite results

`ANTHROPIC_API_KEY=test-placeholder-key`, via
`C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe -m unittest <module>`:

- `tests.test_interview_studio` — 226 tests, 1 skipped (Node dictation test,
  self-skips: Node is not installed), 0 failures.
- `tests.test_auth` — 26 tests, 0 failures.
- `tests.test_search_visibility` — 6 tests, 0 failures.
- `tests.test_governance_pointers` — 20 tests, 0 failures.
- `tests.test_delivery_preflight` — 38 tests, 0 failures.
- All five together: 316 tests, 1 skipped, 0 failures.
- Wider check: `python -m unittest discover -s tests -p "test_*.py"` — 3315
  tests, 12 skipped, 4 failures + 2 errors. Investigated every one:
  - `test_community_maintenance_off_request_path` (deadline/media sweep
    `KeyError`, bounded-sweep exit code) and
    `test_community_disposable_sql_proof::test_private_environment_file_has_owner_only_permissions`
    (POSIX file-mode check on Windows) — confirmed pre-existing on the
    unmodified base via `git stash`; unrelated to this package.
  - `test_journal_frontend::test_mobile_achievement_annotation_stays_in_content_flow_with_visible_star`
    — a Playwright layout test; passes cleanly in isolation, fails only
    inside the full 3,315-test run (resource contention), not caused by
    this diff.
  - `test_navigation::test_sitemap_contains_only_current_canonical_public_routes`
    — the one real, expected, out-of-scope regression from item 6; see
    "Conflicts / deviations" #2 above.

## Honest limitations

- No true DOM/browser execution test exists for the JS storage module (Node
  is not installed in this environment); coverage is source-string
  assertions, matching this file's established pattern for every other JS
  contract test except the one Node-based dictation test that self-skips.
- Rate-limit member-keying is implemented and unit-tested correctly but, per
  conflict #1 above, will rarely observably engage end-to-end for these four
  routes under the current Flask before_request ordering.
- `tests/test_navigation.py` needs a follow-up edit outside this slice's
  scope (conflict #2).

---

# Slice 0 (review close-out) + Slice 3-4 Notes — Rate-Limit Fallback,
# Nav Fix, Authenticated Shell, Consequence Stack

Implementation writer: Claude Sonnet. Base: `d0fc755` (itself stacked on the
slice 1-2 base). Scope: two close-out items from the slice 1-2 review, then
`SLICE_BRIEF_3_4.md` (authenticated shell + Interview Me consequence stack),
architecture files 03 and 06, and all 19 hash-locked visuals in
`02_VISUAL_AUTHORITY/FINAL/`.

## Step 0 — slice 1-2 review close-out

1. **Rate-limit member keying now actually engages.** `_client_rate_limit_key`
   keeps its existing `g.peerslate_identity` read unchanged, then — only when
   `PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED` is true and the path starts with
   `/api/interview/` and the g-based read found nothing — attempts
   `identity.get_optional_principal()` (header-only Easy Auth parse, the same
   validation `get_current_identity()` uses minus the database upsert) inside
   `try/except Exception: principal = None`, and keys on
   `principal.auth_subject` (the stable subject identifier the identity
   mapping consumes into `user_key`). Falls through to the existing IP key
   otherwise. Directly unit-tested (`test_client_rate_limit_key_falls_back_to_a_header_only_principal_for_interview_apis`)
   for: engagement with a valid header, no-engagement when the flag is off,
   no-engagement outside `/api/interview/`, and safe IP fallback on a
   malformed header — asserting `identity.database_service.first_row` is
   never called in any branch. This resolves conflict #1 from the slice 1-2
   notes: member-keying now engages on the very first pass through the four
   routes, without ever touching identity storage from the limiter.
2. **`tests/test_navigation.py` fixed narrowly**, per its
   `CURRENT_LANES.json` surface note: removed `/interview-studio` from
   `test_sitemap_contains_only_current_canonical_public_routes`'s expected
   route list (the one assertion the unconditional item-6 de-listing breaks).
   No other assertion in the file changed.

## Slice 3-4 — server-side foundation (base commit `d0fc755`)

1. **Identity-scoped GET render** (review addendum, not in the original
   brief text but specified by the orchestrator before slice 3 began):
   `_render_interview_studio` now calls `_interview_identity_evidence_context(identity)`
   once identity is resolved, instead of the unconditional
   `_interview_page_context('petec')` slice 1-2 left in place. A non-owner
   member's page now carries their own name and an empty `#is-evidence-data`
   island; the owner's own account still gets the `petec` fixture (Q-C). The
   flag-off public path is untouched (identity is `None` there, so it keeps
   calling `_interview_page_context('petec')` exactly as before) — confirmed
   byte-comparable. `data-profile-slug` now renders `''` instead of the
   literal string `"None"` for a non-owner's unset `slug` (`interview_profile.slug or ''`).
2. **Bracket-confirmation marker contract** (architecture 03 section 2):
   `_IMPROVEMENT_MARKER_PATTERN = re.compile(r'\[[A-Z][a-zA-Z]*\s[^\[\]]*\.\]')`
   — a bracketed span opening with a capitalized word + space and closing
   with `.]`. `validate_interview_improvement` extracts every match from the
   draft into an order-preserving, de-duplicated `confirmations` list. The
   improve system prompt is strengthened to request exactly that shape
   ("imperative sentence starting with a capitalized verb and ending in a
   period... never a bare word or fragment"). `interview_review()` rejects
   (400, before any provider call) an authenticated submission whose answer
   still matches the pattern — defense in depth against a client bypass of
   the disabled "Review Revised Answer" button. The pattern is narrow by
   construction: `[sic]` and `M[1-9]` never match (no capitalized-word+space
   opening, or no closing period), proven by
   `test_answer_with_incidental_brackets_is_accepted`.

## Slice 3 — authenticated shell (flag-selected)

**Template** (`templates/interview_studio.html`): the entire file gained a
`interview_authenticated` boolean fork. Every fork uses one of two verified
Jinja whitespace-trim patterns so the flag-off branch remains byte-for-byte
identical to its pre-existing markup (see "Byte-comparability mechanics"
below) — this was the single hardest correctness problem in this slice.

- Root `<div class="is" data-interview-studio>` gains `data-authenticated="true"`
  only when the flag is on (omitted, not `"false"`, for flag-off).
- `{% if not interview_authenticated %}` keeps the entire public
  `<header class="is__bar">` (brand, card-style mode tabs, "Public demo
  profile" chip) verbatim; `{% else %}` renders the new
  `<aside data-is-auth-rail>`: INTERVIEW STUDIO eyebrow; a compact mode-nav
  (same `data-is-mode`/tablist attributes, new pill styling); a standalone
  History link (`data-is-history-link`, needed unconditionally so it can sit
  in the rail instead of the header); a mobile-only "Session" trigger;
  CURRENT SESSION (five discrete icon rows instead of the public page's one
  slash-joined summary string — same five fields `updateSetupSummary()`
  already computed, just rendered as five spans instead of one) +
  "Change setup"; SESSION TOOLS (New session, Finish session); the exact
  locked truth line. Responsive via CSS only (`@media max-width: 72rem`
  reflows the same elements into a horizontal compact row) — no duplicate
  `data-is-*` elements, so every existing JS binding works unchanged in both
  layouts.
- The old `<aside data-is-session-rail>` (Interview Me's local session rail)
  and Interview Me's `<aside class="is__side-column">` (session-settings
  selects, Question trail/Need a nudge/Need an example doorway, privacy
  card) are retired (`{% if not interview_authenticated %}`) for
  authenticated. Their surviving functional content relocates:
  - Different question / Create question / Need a nudge / Need an example
    move into a new `.is-auth__composer-groups` row directly under the
    "Review My Answer" button (matching visual 01's QUESTION/COACHING
    layout exactly), reusing the identical `data-is-*` attributes so no JS
    changes were needed for their handlers — the public page's copies of
    these controls are hidden for authenticated via CSS
    (`#is-panel-me .is__question-controls-row .is__question-actions { display: none; }`)
    rather than removed, so `syncQuestionChangeControls()`'s existing
    `all()` iteration still finds and correctly disables both sets.
  - The standalone experience-level/question-family/interview-stage selects
    are **not** relocated — dropped for authenticated. None of the 19
    locked visuals show them in the rail (only "Change setup"), and
    `levelSelect`/`familySelect`/`stageSelect` are already null-guarded
    everywhere in the JS, so omitting them is a safe, visual-authority-driven
    simplification, not an oversight. `labelExperienceLevel()` (new) supplies
    the rail's own "Experienced"/"Leadership"/etc. label since the fallback
    label source (`levelSelect.options[...]`) no longer exists for
    authenticated.
  - The `<dialog data-is-queue>` (question-trail dialog) is not part of any
    locked visual's rail either, but `one('[data-is-queue]')` is dereferenced
    unconditionally in several places (`setMode`, `finishCurrentSession`,
    etc.), so removing it outright would throw. It stays exactly where it
    was (inside the flag-off-only retired aside) for the public branch
    (byte-comparability), and a second, separate copy renders inside a new
    `{% if interview_authenticated %}` block for the authenticated branch —
    two template-source copies, never two DOM copies in the same render.
    The shared mobile "Question trail" composer button
    (`.is__queue-mobile`, inside the unconditional answer form) still opens
    it in both branches.
- Demo cards (`data-is-demo-card`, "You are not signed in as...") are
  retired on every panel (AI, Video, History) via
  `{% if not interview_authenticated %}`.
- The four-item public truth strip and the "Public Interview Studio ·
  browser-local practice" footer line are retired for authenticated.
- The New Session setup section (`data-is-session-setup`) now starts
  `hidden` for authenticated (`{% if interview_initial_view == 'history' or
  interview_authenticated %}hidden{% endif %}` — an `or` added to an
  existing boolean expression, not a new conditional, so flag-off output is
  byte-identical) — it is a focused attached surface per architecture 03
  section 6, not a permanently-visible bar. `setMode()`'s existing
  `setHidden(controls, false)` (which unconditionally re-showed it on every
  mode switch) is now `if (!authenticated) setHidden(controls, false);` —
  this was the one real bug caught during manual verification: without this
  guard, `setMode`'s own initialization pass immediately un-hid the section
  again, defeating the template default.
- **Truth copy** (exact strings, brief item 5): "Your answer is sent only
  when you click Review My Answer." (composer, authenticated branch, new
  `.is-auth__transmit-line`) and "Your revised answer is sent only when you
  click Review Revised Answer." (JS-built ImprovementSection). "Clearing
  browser data may remove these practice records." (History's storage-ok
  band, authenticated branch). "This recording exists only on this page.
  PeerSlate does not upload, save, or analyze it." (Video's privacy note,
  authenticated branch — the public copy is preserved unchanged in the
  `{% else %}` branch). "Coaching is guidance. Your answer remains yours."
  (JS-built CoachingSection, both first-attempt and revised).
- **Material**: a new scoped token layer,
  `.is[data-authenticated="true"] { --is-canvas: #f7f2e6; ... }`, replacing
  only the canvas/line/surface-2 tokens (the public page's existing
  ink/gold/forest-green/error tokens already matched the locked warm
  palette closely — the real material delta was the deep-textured Smoked
  Eucalyptus canvas versus the locked flat warm ivory). `.is__backdrop`'s
  heavy grain/vignette gradient stack is replaced with a flat canvas + a
  light top bloom for authenticated only. No `body[data-theme="dark"]` rule
  added or edited (dark theme stays paused).
- **One document scroll**: `.is[data-authenticated="true"] { min-height: 0; }`
  overrides the public page's `min-height: 100svh`. `.main-content`'s
  existing `overflow: clip` is left untouched (verified it does not clip
  appended content — `.main-content` is not height-constrained).
- **No permanent right rail**: `.is__content-grid` collapses to
  `grid-template-columns: minmax(0, 1fr) !important` for authenticated,
  everywhere. The Interview AI panel required an extra, non-obvious fix:
  it defines a bespoke `grid-template-areas: "form side" "main side"`, and
  CSS grid derives an *implicit* minimum column-track count from
  `grid-template-areas` independent of `grid-template-columns` — the first
  override alone left it visually two-column. Fixed by also overriding
  `grid-template-areas: "form" "main" "side" !important` (the same
  single-column stack this stylesheet already defines at its own narrow
  breakpoint). Caught and fixed via real-browser inspection (see
  "Verification" below), not by static reading — recorded because it is
  exactly the kind of bug static CSS review does not catch.
- **No fixed bottom composer dock** (brief item 3): the public page's
  `@media (max-width: 48rem) { .is__composer-actions { position: fixed; ...} }`
  gets an authenticated override (`position: static`, no backdrop-filter/
  shadow, in-flow) merged into that *same* existing media-query block
  (not a new one appended after it — appending a new block broke
  `test_desktop_ipad_and_mobile_layouts_keep_the_task_stage_primary`'s
  "last `@media (max-width: 48rem)` block" assumption; merging into the
  existing block is also simply better CSS practice).
- Mobile compact control row: **deviation from the literal visual.**
  Visuals 13/14a show a collapsed "Interview Me ▾" dropdown next to
  Session/History. I implemented the *same* three always-visible mode-nav
  pills (Interview Me / Interview AI / Video Practice) reflowed horizontally
  instead of a collapsed single-selection dropdown, plus History and a
  dedicated mobile "Session" trigger. Reasoning: this is the same rail
  markup responsively restyled (zero duplicate controls, zero new JS
  binding surface, native semantics preserved) rather than a second,
  independent control needing its own state management; it does not change
  hierarchy, causal order, information available, or material visual
  direction — only the interaction pattern for switching modes on a phone,
  which the brief's own accessibility-adaptation allowance ("you may adapt
  ... responsive stacking without changing hierarchy") covers. Flagged
  explicitly rather than silently substituted.
- **AI/Video/History/Session Complete panels**: per this package's own
  README slice table, the full visual-lock recomposition of these panels'
  *internal* content (Interview AI's exact source-card copy, Video's status
  chip states, History's four truth states, Session Complete's own layout)
  is slice 5's scope, not slice 3's. What slice 3 delivers for these four
  panels is bounded to the brief's explicit shell-level items: demo-card
  retirement, single-column collapse (no permanent right rail), and the two
  truth-copy swaps item 5 names by panel (Video's media truth, History's
  clearing consequence). Their remaining internal composition (card styling,
  labels, order) is currently whatever the shared, unconditional CSS/markup
  already produced for the public page, now just laid out in one column.
  This is a scope decision, not an oversight — recorded explicitly so slice
  5 does not read the current state as "already matching."

### Byte-comparability mechanics (why this took real iteration)

Every `{% if %}` fork wrapping *previously-unconditional* content had to
reconstruct the exact original bytes for the branch that keeps that content.
Jinja's default whitespace handling (`trim_blocks`/`lstrip_blocks` both off,
unchanged) means a bare `{% if %}`/`{% endif %}` pair on their own lines
leaves stray blank-ish lines in the output for the branch that *is* taken —
this broke `InterviewStudioFlagOffByteComparabilityTests` twice before the
fix held. Two verified, reusable patterns (proved by diffing the flag-off
render against a `git stash`-captured pre-change baseline with both assets'
`?v=` tokens normalized, until the diff was empty):

1. **Wrapping previously-existing content, single branch or if/else**: right-trim
   the opening tag (`{% if X -%}`) and left-trim the tag that ends the
   preserved branch (`{%- endif %}`, or `{%- else %}` when an else branch
   follows) — leave the *other* side of each tag untouched. This works
   because the tag's own leading indentation substitutes for the wrapped
   content's original first-line indentation (right-trim discards the
   duplicate), and the trailing whitespace after the closing tag naturally
   supplies the one separator that existed between the wrapped block and
   whatever followed it (left-trim discards the would-be duplicate).
2. **Pure new-content insertion (nothing existed there before, no else)**:
   left-trim the opening tag only (`{%- if X %}...{% endif %}`, endif fully
   untouched) — this leaves exactly one of the two whitespace runs
   surrounding the insertion point intact, which is what the surrounding
   original document actually had.

Both patterns are used throughout the diff; getting either backwards (or
trimming both sides of one tag) reliably produces either a stray blank
line or an accidentally-merged line — both caught immediately by the byte
test, which is precisely why it exists.
`static/css/interview-studio.css` and `static/js/interview-studio.js` both
legitimately changed (same file the public page also loads), so both their
content-hash `?v=` tokens move in the flag-off render even though the
markup does not. `_INTERVIEW_JS_VERSION_TOKEN`'s regex was widened to also
normalize the CSS asset's token (same established exception pattern from
slice 2); `FLAG_OFF_INTERVIEW_STUDIO_BYTE_LENGTH`/`_SHA256` and the history
route's equivalents were re-captured with both tokens normalized, confirmed
against a `git stash` pre-change baseline.

## Slice 4 — the Interview Me consequence stack (authenticated branch)

All in `static/js/interview-studio.js`. Purely additive: every existing
flag-off function (`renderReview`, `requestImprovement`, and all their
fixed-slot DOM targets) is unchanged; the flag-off page still uses them
exactly as before. New code reads the same validated server payloads and
appends separate DOM nodes instead.

1. **Append-only stack, no new wrapper element.** `stackAnchor()` returns
   `answeringBlock.parentNode` — the existing parent that already holds the
   live composer/submitted/reviewing/error group — rather than a new
   template-added `<div>` (which would have added bytes to the shared,
   byte-comparable answering-form markup). `appendStackNode(node)` calls
   `stackAnchor().insertBefore(node, answeringBlock)`, so new permanent
   blocks accumulate directly above the one still-live composer group, in
   causal order. Every appended node carries `data-is-stack-node` so
   `resetConsequenceStack()` (called from `clearReviewState()`, itself
   already called by `renderQuestion()`/`startNewSession()` on every new
   question or session) can remove exactly the appended set.
2. **Structural immutability.** On a validated review, `appendAuthenticatedAttempt`
   freezes the just-submitted text into a brand-new, permanent
   `.is-stack__answer-snapshot` node (`appendAnswerSnapshot`) and hides the
   reusable live `submittedBlock` (`setHidden(submittedBlock, true)`) — the
   snapshot is a genuinely separate DOM node per attempt, not the same
   element relabeled, and the success path never re-shows `answeringBlock`
   (asserted directly by `test_structural_immutability_freezes_the_editor_not_a_readonly_flag`,
   which inspects the exact `.then()` body). Failure is the sole exception,
   unchanged from the existing code: `answeringBlock` re-shows with the
   preserved value, badge text swaps to "Review unavailable" (`is-auth__badge--warning`).
3. **Coaching composition** (`buildCoachingSection`): COACHING REVIEW /
   REVISED COACHING eyebrow + verdict heading; three-column summary
   (WHAT'S WORKING/STRENGTHEN IT/TRY THIS NEXT for a first attempt, WHAT
   CHANGED/WHAT STILL NEEDS WORK/NEXT FOCUS for a revision — the revised
   columns are a compact re-reading of the *same* review payload shape,
   there is no separate revised-review server contract); STRONGER APPROACH
   + five-dimension DETAILED COACHING table (first attempt only); RELEVANT
   EVIDENCE line with the exact "No authorized evidence suggestion is
   available for this answer." fallback; FINAL ACTIONS; the exact member
   authority line. All fields map directly from the existing validated
   review object (verdict/encouragement/whatCameThroughClearly/strengths/
   improvements/strongerApproach/focusedFollowUp/dimensions) — the server
   review contract is unchanged.
4. **Completed-action states** (QA-ledger rule): "Improve My Answer"
   (`makeActionButton`) replaces itself in place
   (`improveButton.replaceWith(makeCompletedChip(...))`) with an inert
   "Improvement draft created" chip the instant it is clicked, before the
   network call even resolves — it never remains an active control after
   its consequence (the improvement request) exists. The revised
   coaching's "Revision reviewed" is rendered as an always-inert chip
   alongside its three live buttons (Next question / Revise again / Finish
   session). `setFinishSessionCompleted(true)` (called from
   `renderSessionComplete()`) disables every `[data-is-finish-session]`
   button, swaps its label span to "Session finished", and reveals the
   rail's `data-is-finish-session-truth` line ("This session is stored only
   in this browser for this account.") — `setFinishSessionCompleted(false)`
   in `startNewSession()` restores the active control for a fresh session.
5. **Bracket-confirmation marker contract** (architecture 03 section 2,
   brief item 4). Client `IMPROVEMENT_MARKER_PATTERN` is byte-identical in
   shape to the server's `_IMPROVEMENT_MARKER_PATTERN`
   (`test_marker_gate_pattern_matches_the_server_exactly` asserts both
   verbatim), so the client's live marker count and the server's
   re-validation can never disagree about what counts as unresolved.
   `appendAuthenticatedImprovement` renders the editable draft
   (`.is-stack__improve-draft`), an input-driven `syncMarkers()` that shows
   "Needs your confirmation (N remaining)" and disables "Review Revised
   Answer" while any marker survives, and the exact helper copy "Replace
   or remove every bracketed prompt before review." Clicking "Review
   Revised Answer" (only reachable once the count is 0) copies the
   resolved draft into `answer.value`, increments `session.attemptNumber`,
   and calls the *existing* `submitReview()` — the brief's own resolution
   of the marker-contract ambiguity ("an ordinary review call with
   attempt>1... add attempt awareness ONLY client-side") is implemented
   literally: no new endpoint, no new request shape, only the client-side
   attempt increment plus the server-side bracket-pattern re-validation
   already landed in Step 0/foundation.
6. **Request binding widened** (item 6): `currentRequestBinding()` captures
   `{sessionId, contextId, questionId, attemptNumber}` from `session` at
   request time; `bindingStillCurrent(binding)` re-reads the same four
   fields at resolution time. Both the review request's `.then()`/`.catch()`
   and `startAuthenticatedImprove`'s `.then()`/`.catch()` now check
   `requestId !== <epoch> || !bindingStillCurrent(binding)` (extends, does
   not replace, the existing bare-epoch guard) — a late response is
   dropped if the epoch *or* any of the four identity fields changed.
   `nudge`/`model-answer` were not widened (out of this slice's scope —
   the brief's item 6 and architecture 03 section 1-2 both scope this to
   Interview Me specifically).
7. **`startAuthenticatedImprove`** is a new, independent function — not a
   branch inside the existing `requestImprovement()` — because the
   authenticated composition has no evidence-suggestion/"Add more answer
   context" sub-flow (not shown in any of the 19 locked visuals; the
   mobile visual 14b's "+ Add context or evidence" affordance is the one
   named element from the visuals this slice does **not** implement — see
   deviations below). It posts the identical minimal payload the public
   page's plain "Improve My Answer" click already sends
   (`evidence_ids: []`, `additional_context: ''`), through the same
   `explicitContextForAi()` bounded/untrusted context helper every other
   AI request already uses.
8. **Session-tearing-down "new question"**: `resetConsequenceStack()` runs
   inside the existing `clearReviewState()`, which `renderQuestion()`
   already calls unconditionally on every question change (Different
   question / Create question / Next question / a new session) — verified
   this is the correct, already-existing hook rather than something new to
   invent; no change needed to `renderQuestion()`/`advanceQuestion()`
   themselves.

## Deviations / conflicts flagged (per the brief's rule)

1. **Mobile mode selector** — three reflowed pills, not a collapsed
   "Interview Me ▾" dropdown. See "Slice 3" above for the full reasoning.
   Not a STOP: composition, hierarchy, and available actions are unchanged;
   only the interaction pattern for a responsive control differs.
2. **"Add context or evidence" / "Use relevant public history" sub-flow**
   (visible in mobile visual 14b as a `+ Add context or evidence` button)
   is not implemented for the authenticated Improve flow. The brief's own
   text for this area is explicitly unresolved/rambling ("Decision:
   implement server check as...") and never names this sub-flow as a
   required item; the marker-gate contract (the actual named requirement)
   does not depend on it. `startAuthenticatedImprove` always requests with
   empty evidence/no extra context, matching the plain "Improve My Answer"
   path the public page already has.
3. **Session-settings selects** (experience level / question family /
   interview stage) are dropped from the authenticated rail rather than
   relocated — none of the 19 locked visuals show them; only "Change
   setup" appears. Mid-session recalibration without starting a new
   session is a public-only convenience now; every JS reference to these
   selects was already null-guarded, so no other behavior changed.
4. **AI/Video/History/Session Complete panels' internal composition**
   is not recomposed to their own locked visual states in this slice —
   per this package's own README slice table, that is slice 5's scope.
   Slice 3 delivers only the brief's explicit shell-level items for these
   panels (demo-card retirement, single-column collapse, the two
   panel-specific truth-copy swaps item 5 names). Recorded explicitly so
   slice 5 does not read "no permanent right rail" as "already visually
   locked."
5. **`<dialog data-is-queue>` has no rail trigger** in the authenticated
   composition (no locked visual shows a "Question trail" affordance
   outside the shared mobile composer button). The dialog element itself
   is kept reachable (a second template copy, for the reason in "Slice 3"
   above) rather than removed, since several JS call sites dereference it
   unconditionally.

## New tests (tests/test_interview_studio.py)

- `InterviewStudioAccessBoundaryTests` gained
  `test_client_rate_limit_key_falls_back_to_a_header_only_principal_for_interview_apis`,
  `test_revised_answer_with_surviving_marker_is_rejected`,
  `test_answer_with_incidental_brackets_is_accepted` (Step 0 + marker
  contract server-side).
- `ReviewSchemaTests` gained
  `test_improvement_extracts_bracketed_confirmation_markers_only`,
  `test_improvement_confirmations_empty_when_no_markers`,
  `test_improvement_confirmations_deduplicated_preserving_order`.
- `InterviewStudioStorageIsolationTests` gained
  `test_page_render_uses_identity_scoped_evidence_for_a_non_owner`,
  `test_page_render_still_uses_the_petec_fixture_for_the_owner` (review
  addendum).
- Two new classes: `InterviewStudioAuthenticatedShellTests` (HTML-level:
  public chrome retired, rail structure + exact truth copy present, setup
  disclosure starts hidden, demo cards retired everywhere) and
  `InterviewStudioConsequenceStackContractTests` (JS source-string
  contract: stack functions exist and are append-only, structural
  immutability, completed-action states, marker-gate pattern parity with
  the server, widened request binding, exact truth/failure copy, rail
  wiring) — ~10 new tests, matching this file's established source-string
  pattern for JS behavior no Node/browser harness runs in CI.

## Rewritten public-contract tests

- `InterviewStudioEmptyReviewListTests.test_empty_review_lists_state_the_absence`:
  `EMPTY_STRENGTHS_MESSAGE` occurrence count 3 → 5. The two new occurrences
  are the authenticated `buildCoachingSection`'s first-attempt and revised
  branches, which legitimately reference the same single-edit-point
  constant (`test_the_empty_strengths_wording_lives_in_exactly_one_place`,
  right below it, still passes unchanged — the literal string still
  appears exactly once).
- `InterviewStudioAssetTests.test_new_session_is_local_and_ai_context_is_explicit_bounded_and_untrusted`:
  `opportunity_context: explicitContextForAi()` occurrence count 4 → 5. The
  new occurrence is `startAuthenticatedImprove`'s request body, using the
  identical bounded/untrusted context helper every other AI request call
  site already uses.
- `InterviewStudioAssetTests.test_desktop_ipad_and_mobile_layouts_keep_the_task_stage_primary`:
  no assertion text changed, but the fixed-dock-retirement CSS had to be
  merged into the *existing* last `@media (max-width: 48rem)` block rather
  than appended as a new one, because the test locates content via
  `css.rsplit('@media (max-width: 48rem) {', 1)[1]` (the last such block)
  — recorded because it shaped where the CSS was placed, even though no
  test assertion itself was edited.

## Verification

- `tests.test_interview_studio` — 246 tests, 1 skipped (Node dictation test),
  0 failures.
- `tests.test_auth`, `tests.test_search_visibility`, `tests.test_navigation`,
  `tests.test_governance_pointers`, `tests.test_delivery_preflight` — 104
  tests combined, 0 failures. All six suites together: 350 tests, 1 skipped,
  0 failures.
- `git diff --check` — clean.
- Wider check: `python -m unittest discover -s tests -p "test_*.py"` — 3336
  tests, 12 skipped, 2 failures + 2 errors, all four confirmed pre-existing
  and unrelated (same exact test names slice 1-2 already investigated and
  disclosed: `test_community_maintenance_off_request_path`'s
  `ScheduledRunnerTests` deadline/media/exit-code trio, and
  `test_community_disposable_sql_proof::test_private_environment_file_has_owner_only_permissions`'s
  POSIX file-mode check on Windows).
- **Manual real-browser verification** (not part of the committed/CI test
  suite — recorded here as evidence, not as a substitute for it): ran the
  Flask dev server locally with `PEERSLATE_ALLOW_DEV_IDENTITY=true` and a
  disposable Playwright script (not committed) that mocked
  `/api/interview/review` and `/api/interview/improve` responses via
  Playwright's request routing and drove the actual page. Confirmed
  end-to-end: the authenticated shell renders correctly (rail, mode nav,
  truth copy, single-scroll); a full first attempt produces a real appended
  AnswerCard + CoachingSection matching visual 04a/04b's layout; clicking
  "Improve My Answer" correctly converts to the "Improvement draft created"
  chip and appends an editable draft with bracketed markers and a genuinely
  disabled "Review Revised Answer" button; editing the draft to remove all
  markers correctly re-enables it; submitting it appends the "Original
  answer and first coaching remain above." context line, a
  "Reviewed revision · Attempt 2" snapshot, and a RevisedCoachingSection
  matching visual 06 almost exactly (WHAT CHANGED/WHAT STILL NEEDS
  WORK/NEXT FOCUS + Next question/Revise again/Finish session/"Revision
  reviewed"); the failure path (a real provider error, since the local
  ANTHROPIC_API_KEY is a placeholder) correctly re-shows the editable
  composer with the preserved answer, the "Review unavailable" badge, and
  the exact locked failure copy; no JavaScript console errors were
  observed at any step. One real bug (`setMode`'s unconditional
  `setHidden(controls, false)` defeating the new hidden-by-default setup
  section) and one real CSS bug (Interview AI's `grid-template-areas`
  defeating the single-column override) were caught this way and fixed —
  both are the kind of defect static source review alone would not catch,
  which is the reason this verification pass happened before closeout
  despite not being part of the committed suite.

## Honest limitations (slices 3-4)

- The manual Playwright verification above is real but not committed,
  reproducible-on-demand evidence, not a CI-enforced regression guard — a
  future change could silently break the end-to-end flow without a
  committed test catching it. The committed coverage for slice 4's runtime
  behavior is source-string assertions (established pattern; no Node/
  browser harness runs in this repository's CI).
- AI/Video/History/Session Complete panels' own visual-lock recomposition
  (deviation #4) is real, scoped, disclosed work remaining for slice 5 —
  their current authenticated rendering is single-column and demo-card-free
  but not yet copy/state-matched to visuals 07-12/15-17.
- The "Add context or evidence" sub-flow (deviation #2) and the
  standalone session-settings selects (deviation #3) are real, scoped
  feature narrowings versus a maximal reading of the visuals/prior code,
  not silent omissions — both are named above with their reasoning.
- No accessibility audit (keyboard traversal, live-region announcements
  for the append-only stack, reduced-motion, 200% reflow) was performed
  beyond what the existing shared dialog/focus/announce machinery already
  provides — that is slice 6's named scope.

---

# Slice 5-6 Notes — Preserved Destinations, Architect Rulings R1-R4,
# and a Mid-Session Scope Handoff

Implementation writer: Claude Sonnet. Base: `b0f1a1b` on
`work/2026-08-11-interview-studio-authenticated-experience-001`. Scope:
`SLICE_BRIEF_5_6.md`, architecture 03 §3-5/06/07, the review-cycle
rulings R1-R5, and the 19 locked visuals. **Mid-session scope change**
(below) narrowed the second half of this work to functional wiring only;
read that section before judging what "done" means for the visual items.

## R1 — mobile mode picker (visual 13)

`templates/interview_studio.html`: `<div class="is-auth__mode-picker">`
wraps the existing `<nav class="is-auth__modes" role="tablist">` (same
three `<a data-is-mode="…">` elements, zero duplicates) with a new
`<button data-is-mode-toggle>` sibling. CSS shows only the toggle above
the rail breakpoint (unchanged desktop rail) and only the popover-styled
tablist below it, toggled by a new `data-is-open` attribute on the
picker. JS (`static/js/interview-studio.js`): `syncModeToggle(mode)`
mirrors the active tab's icon/label onto the toggle and is called from
`setMode()`; `closeModePicker`/`modePickerIsOpen` handle open/close via
click, outside-click, and Escape; each mode tab's existing click handler
also closes the picker. `modeNavigation` (`role="tablist"` bookkeeping,
arrow-key roving tabindex) now falls back to `.is-auth__modes` when
`.is__modes` (public-only) doesn't exist — a real, disclosed bug fix:
slice 3 left this `null` for authenticated, silently dropping both the
role cleanup in `showHistoryView()`/`showOrientationView()` and arrow-key
navigation between mode tabs.

## R2 — "Add context or evidence" sub-flow (visuals 05/14b)

New `buildImproveContextForm(review, onSubmit)` builds the same
1,200-char confirmed-context textarea and evidence-suggestion checkboxes
the public "Make it more yours" flow already has, as stack-appended
nodes (not the public flow's fixed-slot elements — a second, independent
implementation of the same visual/data contract, appropriate for the
append-only stack). Evidence checkboxes reuse `evidenceById` (populated
from `#is-evidence-data`, already empty for non-owners per slice 2), so
"owner account only, else the exact fallback line" falls out of the
existing identity-scoping with no new gate. `appendAuthenticatedImprovement`
now also takes `review` (needed for the resubmission's `improvements`
field and `evidenceSuggestions`) and `startAuthenticatedImprove` gained
optional `selectedIds`/`additionalContext`/`onSuccess`/`onError` params:
the plain "Improve My Answer" click still calls it with no extra args
(unchanged behavior, appends a new section); the context form's submit
calls it with the supplied ids/context and an `onSuccess` that updates
the *same* appended section's draft/basis/markers in place, matching how
the public page's own `requestImprovement()` re-use pattern works.
Feeds the unchanged existing improve API contract (`additional_context`
+ `evidence_ids`) — no new endpoint, no schema change.

## R3 — experience level folded into the setup form

Added an `<label class="is__select">…<select data-is-level>…` to the
shared New Session form, gated `{% if interview_authenticated %}` (pure
insertion, left-trim-only on the `if`, `endif` untouched — flag-off gets
zero bytes). Reuses the *exact* `data-is-level` hook the public page's
retired `is__session-card` already used, so `levelSelect`'s entire
existing change handler (mid-session recalibration, rail-summary-level
update, `announce()` copy) works unchanged — this is a markup relocation,
not new JS. Question family/mix needed no change: `data-is-session-mix`
was already unconditional in the New Session form for both branches.

## R4 — Question trail rail item

A quiet `is-auth__rail-action--quiet` button in the rail's Session
tools group, reusing `data-is-queue-open` (the same hook the public
page's Interview Me/Video Practice side columns and the shared mobile
composer button already open the trail dialog with) — no new JS. Not
part of the locked rail composition; recorded per the ruling as a
non-material capability-preservation adaptation.

## R5 — Interview AI, Video Practice, Session Complete, History

### Interview AI (visuals 07/08)

Exact heading/subhead swap; a new inline SOURCE control (three radio
cards, `data-is-ai-source-radio`, synced to the pre-existing
`data-is-ai-mode` select via an extracted `applyAiModeChange(value)`
function — the select stays the single source of truth so
`selectedAiMode()` needed no change); the exact info line; a highlighted
result card (border/background keyed off the existing
`data-is-ai-state="ready"` root attribute, zero new markup) with an
eyebrow-style label (`GENERIC BEST-PRACTICE EXAMPLE` / `{name}'S
APPROVED PUBLIC EXAMPLE`) and a 3-up "why this works" grid; a distinct
insufficiency composition (icon, "Not enough approved public evidence"
eyebrow, the two exact locked lines); the exact generic-example
disclaimer; an authenticated action row (Practice This Answer / New
question, reusing `data-is-different-question`'s existing pick-another-
question handler / a permanently disabled "Follow-up isn't available
yet" placeholder). Follow-up is forced disabled for authenticated
regardless of token availability (`followUpAvailable = !authenticated &&
…`), per architecture 03 §3 item 2 — the token plumbing itself is
untouched.

**Deviations (disclosed):** the visual's crop shows no "Get example"
button; I kept it (repositioned under the SOURCE info line) rather than
inventing an implicit auto-fetch-on-source-change, to preserve the
existing explicit-request trust model (question text is sent only on a
deliberate click, matching "Question text is sent only when you request
… an example"). The insufficiency lock's "Use best practice" one-click
shortcut was not implemented; "Practice This Answer" auto-disables when
insufficient (existing behavior) and the member can reach the same
outcome by selecting the "Best practice" SOURCE radio directly (one
extra click versus the locked shortcut).

### Video Practice (visuals 09/10/15)

Eyebrow/subtitle copy swap; question chips/Different-Create-question row
hidden inline (CSS, same rationale as the AI panel — reachable via
Interview Me/the rail); a new "Turn camera off" action
(`releaseMedia(true); resetVideoUi();`, no re-enable); authenticated-only
runtime label overrides ("Start recording", "Discard recording" — set
via JS after capturing/reinserting the button's icon node, never
touching the shared flag-off bytes); a recovery-lock composition for the
`denied`/`unavailable` `data-is-video-state` values with the exact
locked copy and its own action set (Use transcript instead / Try camera
again / Camera help), driven by a new `syncVideoRecoveryState(state)`
called from `setVideoState()`.

**Fix (architecture 03 §4 item 2):** `releaseMedia()` now revokes
`media.playbackUrl` itself whenever `discardRecording` is true, instead
of relying on `resetVideoUi()` (called separately by every existing
call site) to do it. Audited every current call site: all already
paired `releaseMedia(true)` with `resetVideoUi()` immediately after
except the `pagehide` handler (which revokes inline) — so this closes a
*structural* gap (a future call site that forgets the pairing) rather
than a currently-observable leak; still a direct implementation of the
brief's named FIX item.

**Deviation (disclosed, not implemented):** the locked visuals overlay
the Camera ready/Microphone ready and Local recording ready · MM:SS
status chips directly on the camera frame; the device-status side card
(`data-is-camera-status`/`data-is-mic-status`) was kept in its existing
location rather than relocated onto the frame, given the risk of
touching the live camera/recording state-machine markup under time
pressure on a trust-sensitive surface. The truthful status text itself
is correct and reachable; only its on-page position differs from the
locks.

### Session Complete (visual 11)

New centered `.is-complete` composition (check icon, "You finished this
practice session.", a summary sentence naming practiced and reviewed
counts explicitly and distinctly per architecture 03 §5, three cards —
FROM THIS SESSION / NEXT FOCUS FROM THIS SESSION / QUESTIONS REVIEWED —
the exact browser-truth line, and renamed actions). Reuses the existing
`renderSessionComplete()` computation (`records`,
`session.questionTrail.length`, `latest.improvements[0]`) with new
element targets only; the public branch's own targets and behavior are
byte/behavior-unchanged.

### History (visuals 12/16/17)

New `renderAuthenticatedHistory()` implements the four distinct truth
states (storage unavailable / genuinely empty / filtered-empty /
populated) via four early-return branches, reusing
`storageAvailable`/`readHistoryRecords`/`filteredHistory`/
`v2ReviewedRecords`/`comparableDimensionGroups`/`statusRank` — no
duplicated comparison-gate logic. Mode/Question-family/Most-recent
filters replace the public page's Mode/Competency/Time-window trio for
this branch only (`filteredHistory()` extended with a null-guarded
family filter and a sort step; both null for the public branch). The
exact `Not enough comparable practice yet.` gate string, the
`Clearing browser data may remove these practice records.` /
`Nothing was cleared or deleted.` consequence lines, and the four-state
copy are all present. "Clear local History" reuses the existing
`clearLocalData()` confirm-and-clear handler via the shared
`data-is-history-clear-local` hook (same tested behavior as the public
page's own button).

**Deviation (disclosed):** the locked visual's per-row overflow (⋮) menu
opens a menu with further actions; I implemented it as a single delete
button (with the existing confirm dialog copy) rather than building a
new menu/popover component, given time constraints. "View review"
correctly opens the existing shared history-detail dialog.

## A critical bug found and fixed during real-browser verification

Removing `data-is-follow-up-open` (Interview AI's disabled placeholder,
by design) and `data-is-practice-recommendation` (dropped from the
authenticated History composition) left two **pre-existing, unconditional**
`one(selector).addEventListener(...)` call sites — written years before
this package, when both elements always existed in every render — with
nothing to bind to. Both threw `TypeError: Cannot read properties of
null (reading 'addEventListener')` at script-init time, on **every**
authenticated page load, in **every** mode. Because `interview-studio.js`
is one large synchronous IIFE that wires up all four panels' controls at
load time, an uncaught exception partway through silently aborted every
line of setup code that appeared later in the file — Video Practice,
History, Settings, and the mode-picker wiring never registered at all
on any authenticated page. No committed test caught this (the suite is
entirely source-string assertions; no Node/browser execution runs in
CI). Found via headless Playwright, `page.on('pageerror', …)`, across
all four modes. Fixed by (1) keeping `data-is-follow-up-open` on the
authenticated placeholder button (now forced permanently disabled at
both dynamic-assignment sites instead of removed from the DOM) and (2)
null-guarding the History recommendation handler. Re-verified clean
(zero pageerrors) across `mode=me`/`ai`/`video` and `/history` after the
fix; audited every other `one(selector).method(...)` call site in the
file against every element either branch removes or makes conditional —
no further instances found. Regression tests added
(`test_interview_ai_follow_up_stays_forced_disabled_for_authenticated`,
`test_history_recommendation_button_handler_is_null_guarded`,
`test_history_filter_change_listener_is_null_safe_across_both_branches`).

**Correction (independent review finding P1-1, recorded honestly below in
"Independent Review Close-out"):** the audit claim above is narrower than
it reads. It covered `one(selector).method(...)` call sites only — i.e.
places the code invokes a method (`addEventListener`, `.close()`, etc.)
directly on a `one()` result. It did **not** cover plain property
*assignments* on a `one()`-derived variable stored earlier (e.g.
`levelSelect.value = …`), which is a different call-site shape the same
audit should have swept and did not. `clearLocalData()`'s
`levelSelect.value = session.level; familySelect.value = session.family;`
was exactly such a site and crashed on every authenticated "Clear local
data" click for the same structural reason (`familySelect` is `null` for
authenticated — `[data-is-family]` does not exist in that branch). See
"Independent Review Close-out" for the fix and its regression test.

This is the same class of defect prior slices' real-browser verification
caught (the `setMode()`/`grid-template-areas` bugs in slices 3-4) — the
kind static source review does not reliably catch, and exactly why the
brief calls for real-browser evidence before closeout.

## Mid-session scope change (owner-directed, recorded in
## `docs/governance/CURRENT_LANES.json` by Pete/Fable — not edited here)

Two coordinator-relayed directives arrived mid-session, in order:

1. **Early screenshot request.** Before the rest of slice 5-6 was
   built, capture and commit an early comparison batch covering
   01/04a/04b/05/07/09/12/13. I set up a local dev server
   (`PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED=true`,
   `PEERSLATE_ALLOW_DEV_IDENTITY=true`, a dev user key also listed in
   `PEERSLATE_OWNER_USER_KEYS`) and a headless-Playwright capture script
   that mocks `/api/interview/review`, `/api/interview/improve`, and
   `/api/interview/model-answer` (JSON bodies matching the server's own
   validated response envelope — `{"review": …}` / `{"improvement": …}`
   / `{"modelAnswer": …, "profile": …, "contextToken": …}`) and drives
   the real UI. **01, 04a, 04b, and 05 were captured and committed**
   (`artifacts/2026-08-11-interview-studio-authenticated/visual-comparison/`).
   07 failed mid-run — that failure was the first symptom that led to
   finding the crash bug above (Interview AI's setup runs after the
   crash point in file order, so 07/09/12/13 all depend on code that
   never executed). By the time the crash was fixed, the next directive
   (below) had arrived, so 07/09/12/13 were not captured.
2. **Visual ownership reassignment.** Pete reviewed the early captures,
   failed the visual composition broadly, and reassigned all remaining
   visual/composition/CSS work to Claude Fable at extra-high effort
   (recorded verbatim in `CURRENT_LANES.json`'s `model_routing`, commit
   `3af8436`, made concurrently by a separate session on this same
   branch — I did not write that commit and did not touch
   `docs/governance/*`). My remaining scope was narrowed to *functional*
   wiring only: element/data-hook structure and state-toggling logic for
   Interview AI/Video Practice/Session Complete/History, the R2/R3
   wiring, and their tests — explicitly **not** further visual
   iteration, **not** any more screenshot capture, **not** any styling
   changes. CSS is left exactly as it stood at that point (everything
   described under R5 above), for Fable to rebuild against the 19 locks.

**Consequence for this record:** slice 6's "side-by-side comparison
against all 19 locked visuals, self-judged match/adapted/STOPPED per
state" was **not completed** — only 4 of 19 states have a captured
render, and none were formally self-judged against their lock (that
judgment belongs to the visual rebuild pass, not this functional-only
close-out). The R5 compositions above are real, tested, and functionally
correct implementations of their target states' *structure and
behavior*; their *pixel/visual* fidelity to the 19 locks is explicitly
unverified and is Fable's stated scope going forward, not mine.

## Suite results (this session)

`ANTHROPIC_API_KEY=test-placeholder-key`, via
`C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe -m unittest <module>`:

- `tests.test_interview_studio` — 262 tests, 1 skipped, 0 failures
  (247 pre-existing + 15 new in `InterviewStudioSlice56RecompositionTests`,
  1 test extended for the negative-regression guard).
- `tests.test_auth`, `tests.test_search_visibility`,
  `tests.test_navigation`, `tests.test_governance_pointers`,
  `tests.test_delivery_preflight` — 104 tests, 0 failures.
- All six together: 366 tests, 1 skipped, 0 failures.
- `git diff --check` — clean on every commit.
- Flag-off byte-comparability — confirmed via `git stash` diff against
  the pre-session baseline after every template edit in this slice
  (caught and fixed two real whitespace-trim mistakes before they ever
  reached a commit — see the AI panel's insufficiency-block insertion
  history in this branch's working notes); the committed byte-length/
  SHA256 constants needed no update (the CSS/JS `?v=` token churn is
  already normalized by the existing regex/placeholder substitution).
- Wider check: `python -m unittest discover -s tests -p "test_*.py"` —
  3351 tests, 12 skipped, 3 failures + 2 errors. All five confirmed
  pre-existing and unrelated to this package (same four items slices
  1-4 already investigated and disclosed —
  `test_community_maintenance_off_request_path`'s `ScheduledRunnerTests`
  deadline/media/exit-code trio,
  `test_community_disposable_sql_proof::test_private_environment_file_has_owner_only_permissions`'s
  POSIX file-mode check on Windows — plus one Playwright layout test,
  `test_journal_frontend::test_hero_headline_is_italic_and_remains_a_two_line_identity`,
  confirmed passing cleanly in isolation and failing only under full-suite
  resource contention, the same class of flake slice 1-2's notes already
  documented for a different journal test).

## Honest limitations

- The 19-state visual comparison (slice 6 item 3) is incomplete: 4 of 19
  states captured, none self-judged. This is a direct, disclosed
  consequence of the mid-session scope reassignment above, not an
  oversight.
- Accessibility evidence (keyboard-only walk, focus-trap on the new
  mode-picker popover, live-region announcements for the new History/AI/
  Video states, 200% reflow, reduced-motion for the new elements) was
  not gathered beyond what the existing shared dialog/focus/announce
  machinery and the global reduced-motion rule already provide.
  Long-content stress (300-char question, 5,000-char answer, 100-record
  History, filtered-empty) was not separately exercised against the new
  compositions.
- Video Practice's frame-overlay status-chip placement (visuals 09/10)
  was not implemented — the device-status side card was kept instead
  (see deviation above).
- History's overflow menu was simplified to a single delete button (see
  deviation above).
- The AI panel keeps an explicit "Get example" button not shown in the
  visual crop, and does not implement the insufficiency lock's one-click
  "Use best practice" shortcut (see deviations above).
- The critical crash bug was caught by targeted headless-browser
  verification of page-load errors across the four modes, not by a
  systematic accessibility/interaction pass — a narrower check than
  slice 6 originally called for, sufficient to catch this specific
  defect but not a substitute for the fuller pass.

---

# Fable Review Pass 1-9 Close-out Polish Notes

Implementation writer: Claude Sonnet. Scope: four small polish items under
the Fable architect's review of the visual rebuild (passes 1-9), plus one
architect-relayed mid-session addendum (Task 5, the global header's color).
Worked exclusively in worktree
`portfolio-interview-studio-auth-20260811` on this same branch; no push, no
`docs/governance/*` edit.

## Task 1 — History row layout (lock 12)

`static/js/interview-studio.js`'s `renderAuthenticatedHistory()` row
builder previously appended the mode·family meta line into the same
`.is-history__row-body` div as the title (stacked under it), then a
separate `date`/`chip`/`view`/`deleteButton` directly onto the row as flex
children. Lock 12's composition is title left, then a distinct
mode·family-over-date meta column, then the Reviewed
chip/View-review/overflow cluster.

- JS: `body` now gets only the title (`body.append(question)`); a new
  `.is-history__row-meta` div holds `metaLine` + `date` together
  (`meta.append(metaLine, date)`); `chip`/`view`/`deleteButton` are
  grouped into a new `.is-history__row-actions` flex wrapper
  (`actions.append(chip, view, deleteButton)`) instead of each being a
  top-level row child — so the row template only needs four grid cells
  (icon/title/meta/actions) rather than six, and the three trailing
  controls wrap as one unit instead of each needing its own responsive
  placement. `view`'s className gained `is-history__row-view` (was
  `is__button is__button--quiet` alone) so CSS can target it without a
  fragile child-combinator selector.
- CSS: `.is-history__row` is `display: grid;
  grid-template-columns: 2.2rem minmax(0, 1fr) 12rem auto;` (was
  `display: flex`) so every row's chip/button/overflow cluster lines up
  down the list regardless of that row's own title/meta text length.
  `.is-history__row-actions` is the new flex cluster (chip + view +
  delete). A `@media (max-width: 36rem)` addition collapses to a
  2-column grid (icon spans 3 implicit rows via `grid-row: span 3`, so
  title/meta/actions auto-flow into column 2 across three rows in DOM
  order) — deliberately not using named `grid-template-areas` for the
  narrow layout, since giving two sibling items the same named area would
  overlap them; auto-placement with a spanning icon avoids that risk
  without needing a live browser to prove no overlap.
- New test: `test_history_row_layout_matches_lock_12_title_meta_column_actions`
  (source-string, matches this file's established JS-contract-without-a-
  browser-harness pattern) — confirms the title node no longer receives
  the old two-argument `append(question, meta)`, the meta div groups
  `metaLine`/`date`, the actions div groups `chip`/`view`/`deleteButton`,
  and the row CSS is a grid with explicit `grid-template-columns`.

## Task 2 — Content-coaching card trim (locks 09/10)

`templates/interview_studio.html`'s video-transcript form intro paragraph
was one long sentence (4 clauses) shared by both branches. Public branch
is untouched (byte-comparable, verified); authenticated now reads: heading
(already styled uppercase/letter-spaced) → one short lead line → composer
→ the two required truth sentences, relocated below the composer as a
smaller muted line, never deleted.

- Template: `{% if interview_authenticated -%}` / `{%- else -%}` /
  `{%- endif %}` around the lead `<p>` (mirrors the exact established
  if/else byte-comparability pattern used a few dozen lines up for the
  Video Practice eyebrow/heading fork — right-trim the opening tag,
  trim both sides of `else`, left-trim `endif`). A second, pure-insertion
  `{%- if interview_authenticated %}...{% endif %}` block (endif fully
  untouched — the established insertion pattern, e.g. the R3 experience-
  level select a few hundred lines up) adds
  `<p class="is__video-content-review-truth">Automatic transcription is
  not enabled. Submitting the transcript removes the local recording.</p>`
  right before `</form>`, after the existing dictation-status/interim/
  error paragraphs.
- Dropped from the authenticated composition (not required truth copy,
  covered by the new lead line instead): "Type, paste, or dictate what
  you said to use the same content review as Interview Me, grounded in
  the approved history. You can use this before or after recording."
- CSS: the existing `.is[data-authenticated="true"]
  .is__video-content-review > p` rule (enlarged 0.9rem lead-line
  treatment) is now scoped `> p:first-of-type` so it only ever touches the
  lead paragraph, not the new trailing truth line (which now correctly
  falls back to the base 0.76rem fine-print `.is__video-content-review p`
  size the public branch's own paragraph already used — no new font-size
  rule needed for it) nor the dictation-live/interim/error paragraphs
  (a latent, unrelated, pre-existing quirk this incidentally fixes: those
  three already-classed paragraphs were being swept into the same
  0.9rem-muted override by the old blanket `> p` selector, out-
  specificity-ing their own dedicated color/size rules).
- New tests: `test_content_coaching_card_trims_the_intro_and_keeps_the_truth_line`
  (authenticated composition, source + rendered HTML) plus the existing
  `InterviewStudioFlagOffByteComparabilityTests` (unchanged, still passes)
  for the public branch's byte-for-byte preservation — no new public-
  branch test needed given that suite's stronger byte-for-byte guarantee.

## Task 3 — Device Settings button binding (investigated, one real finding)

Traced `one('[data-is-device-settings]')` (both the
`syncVideoRecoveryState` show/hide call and the
`.addEventListener('click', ...)` binding, `static/js/interview-studio.js`)
against the authenticated DOM. Two elements match the selector for
authenticated: the camera-controls copy inside `.is__camera-controls`
(shown only in the `preview` state, matching lock 09) and the retained
`.is__video-device-card` side card's own quiet copy (never gated by
`interview_authenticated`, so it renders in every state). `one()` /
`querySelector` binds to whichever is first in DOM order, which is the
camera-controls copy (main column precedes the aside in the template) —
**confirmed the binding genuinely fires** and its body is exactly
guard (`prepareVideoContextChange`) → `releaseMedia(true)` →
`resetVideoUi()` → `enableCamera()`, already covered by the pre-existing
`test_completed_video_playback_requires_confirmation_before_context_reset`.

The one real finding: the side card's copy was never hidden by that same
`one()`-driven show/hide logic (it only ever touches the first match), so
it sat on screen as a second, unbound, visually-identical "Device
settings" control whenever the camera-controls copy was hidden (every
state except `preview`) — a dead duplicate, not a lost binding. Fixed with
a scoped CSS rule (`static/css/interview-studio.css`):
`.is[data-authenticated="true"] #is-panel-video .is__video-device-card
[data-is-device-settings] { display: none; }` — the JS binding itself
needed no change since it was already correctly wired to the working,
lock-matching element. New regression test
`test_device_settings_binding_targets_the_lock_09_control_not_the_dead_duplicate`
asserts: exactly two matching elements exist in the authenticated render,
the camera-controls copy stays first in DOM order (so `one()` keeps
binding to it), the new CSS hiding rule exists, and the click handler's
guard→release→reset→enableCamera ordering is intact.

## Task 4 — Full checks

`ANTHROPIC_API_KEY=test-placeholder-key`, via
`C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe`:

- `tests.test_interview_studio` — 269 tests, 1 skipped, 0 failures (6 new
  test methods added for tasks 1/2/3/5 combined; a seventh draft test for
  Task 2's public-branch preservation was written, found to be redundant
  with `InterviewStudioFlagOffByteComparabilityTests`'s stronger
  byte-for-byte guarantee and incorrectly scoped against a test class
  that forces the flag on, and removed before commit).
- All six named suites together (`test_interview_studio`, `test_auth`,
  `test_search_visibility`, `test_navigation`, `test_governance_pointers`,
  `test_delivery_preflight`) — 372 tests, 1 skipped, 0 failures.
- `git diff --check` — clean.
- Flag-off byte-comparability
  (`InterviewStudioFlagOffByteComparabilityTests`) — still passes; the
  Task 2 template fork preserves the public branch's original paragraph
  byte-for-byte.
- Wider check: `python -m unittest discover -s tests -p "test_*.py"` —
  3358 tests, 12 skipped, 3 failures + 2 errors. All five confirmed
  pre-existing and unrelated, matching the items slices 1-6 already
  investigated and disclosed: `test_community_maintenance_off_request_path`'s
  `ScheduledRunnerTests` deadline/media/exit-code trio (2 errors + 1
  failure), `test_community_disposable_sql_proof`'s
  `test_private_environment_file_has_owner_only_permissions` (POSIX
  file-mode check on Windows, 1 failure), and
  `test_journal_frontend::test_hero_headline_is_italic_and_remains_a_two_line_identity`
  (1 failure) — reconfirmed passing cleanly in isolation this session,
  failing only under full-suite resource contention, the same documented
  flake class as the other journal tests slices 1-2/5-6 already recorded.

## Task 5 — Authenticated header color (architect addendum, mid-session)

Owner-reported/architect-measured: the shared `.global-header` (and
`.platform-nav__links`/`.nav-search__input`/`.platform-brand__logo`/
`.sign-in-btn`/`.nav-sign-out__btn`) render with the site's default cool
band (`static/css/style.css`'s unscoped `.global-header { background:
#f6f8fc; border-bottom: 1px solid rgb(125 157 198 / 34%); }` and
`.platform-brand__logo`'s cool silver-blue gradient) on every page,
including the authenticated Studio, while all 19 locked visuals show a
warm ivory header. Fixed page-scoped, in `static/css/interview-studio.css`
only — no shared stylesheet or `base.html` edit — following the existing
`body.interview-studio-page` precedent already in this file (line 9, and
the pre-existing `body[data-theme="dark"].interview-studio-page` header
overrides). Scope:
`body.interview-studio-page:has(.is[data-authenticated="true"]):not([data-theme="dark"])`.

- The `:not([data-theme="dark"])` guard is a deliberate addition beyond
  the architect's literal instruction: this exact page already carries
  its own dedicated `body[data-theme="dark"].interview-studio-page`
  overrides for several of these same elements (nav links, sign-in-btn),
  and the new selectors here are specific enough to out-rank them if not
  excluded — which would have silently broken dark mode on this one page.
  Dark theme is paused (author no new dark rules; do not touch the
  existing ones per owner direction 2026-08-03), so this guard is
  required to honor that, not optional polish.
- Colors reuse this file's own already-locked authenticated tokens
  (`--is-canvas`/`--is-surface` `#fdf9f6`, `--is-line` `#eae2d8`,
  `--is-line-strong` `#d9cfc2`, `--is-active` `#114a2b`, all defined
  around line 3830) hardcoded into the new rules, since the header lives
  outside the `.is[data-authenticated="true"]` subtree those custom
  properties are scoped to.
- `.sign-in-btn`'s ("My Slate") fill/text color is untouched per the
  architect's explicit note (navy ink already reads correctly on warm);
  only its border and `.nav-sign-out__btn`'s border move to the warm
  hairline family. Added a `.nav-search__input:focus` border/background
  override beyond the architect's literal five items (kept the same warm
  family instead of leaving the default cool `var(--accent)` focus ring)
  — a one-line, low-risk extension in the same spirit as the request, not
  scope creep on any of the four writer tasks.
- New test class `InterviewStudioAuthenticatedHeaderColorTests`: asserts
  each scoped rule/declaration exists, that neither shared stylesheet
  (`style.css`, `public-navigation.css`) nor `base.html` picked up the new
  hex values, and that the pre-existing dark-mode header override
  (`body[data-theme="dark"].interview-studio-page .sign-in-btn`) is still
  present and reachable (not shadowed).

## Honest limitations (this pass)

- No live-browser visual verification was possible for any of the five
  tasks. `preview_start` in this environment binds to a fixed project
  directory (`C:\Users\peter\Documents\portfolio`, the main checkout —
  confirmed via `preview_list`'s reported `cwd`), not this worktree
  (`portfolio-interview-studio-auth-20260811`); the request's own scope
  ("work ONLY in the git worktree") rules out redirecting that server at
  the main checkout. Verification here is therefore comprehensive
  source-string/rendered-HTML/CSS-content assertions (this file's
  established pattern for JS/CSS behavior with no Node/browser harness in
  CI) plus careful manual specificity/grid/Jinja-whitespace analysis
  cross-checked against this package's own already-proven patterns
  (mirrored, not invented, wherever a working precedent existed in this
  same file) — not a substitute for a real-browser pixel check. The
  architect's own re-measurement after this pass is the actual visual
  verification step for Task 5; Tasks 1-3 should get the same scrutiny at
  the next visual review checkpoint.
- Task 1's mobile (`max-width: 36rem`) row layout is unverified in a real
  browser; the auto-placement/spanning-icon approach is reasoned to avoid
  overlap (see Task 1 above) but not visually confirmed.
- Task 3 fixed a dead-duplicate-control finding beyond the literal
  "confirm the binding still exists and fires" ask, since the working
  binding turned out not to need restoring — the duplicate it left
  visible did.

---

# Independent Review (Opus) Close-out — REJECT findings resolved

Implementation writer: Claude Sonnet (maximum care), this session, worktree
`portfolio-interview-studio-auth-20260811`, branch
`work/2026-08-11-interview-studio-authenticated-experience-001`, base for
context SHA `81d8f21`. Scope: close every finding in the first independent
review's REJECT verdict. No push, no PR, no `docs/governance/*` edit. Ten
small commits, one per finding group, each with
`Co-Authored-By: Claude Sonnet <noreply@anthropic.com>`.

**Mid-session governance note (transparency, not acted on by this writer):**
partway through this closure run, a concurrent Fable architect session
committed `docs/governance/CURRENT_LANES.json` and
`CODEX_COMPLETION_HANDOFF_2026-08-12.md` to this same branch, recording that
Pete directed Codex to finish the remainder of this package (push, PR,
merge, deploy dark, live verification) due to Claude usage limits. This
writer's assignment was always narrowly scoped to closing the Opus
findings only (no push/PR/governance edits, per its own instructions), so
that scope is unaffected either way. This section is written so Codex's
documented "FIRST ACTION — reconcile the interrupted writer" step (handoff
§2) finds a complete, clean, fully-tested, honestly-disclosed state: every
commit after `81d8f21` up to this point is finished work, not a fragment to
discard.

## P1-1 — `clearLocalData()` crash + false completed-state UI

**Disposition: fixed.** `static/js/interview-studio.js:4685-4686` —
`levelSelect.value = session.level;` / `familySelect.value = session.family;`
were unguarded. `[data-is-family]` does not exist in the authenticated DOM
(retired for authenticated; only `[data-is-level]` was relocated into the
rail per R3), so `familySelect` is `null` there and every authenticated
"Clear local data"/"Clear local History" click threw before the storage
wipe, history reset, or the truthful "Interview Studio browser data
cleared." announcement ran. Guarded both assignments to match the file's
own established pattern (both are already null-guarded at every other call
site, e.g. ~1376-1377 and ~4598-4599). New test:
`InterviewStudioSlice56RecompositionTests.test_clear_local_data_null_guards_level_and_family_selects`
(`tests/test_interview_studio.py`), a source-string guard pinning the null
checks in `clearLocalData()`'s body.

**Correction recorded honestly:** the "critical bug found and fixed"
section above claims an audit of "every other `one(selector).method(...)`
call site" found no further instances. That claim is accurate as far as it
goes but narrower than it reads — it covered method-call sites
(`.addEventListener`, `.close()`, etc.) on a `one()` result, not plain
*property assignments* on a `one()`-derived variable stored earlier. This
P1-1 crash lived in exactly that second, unaudited shape. Corrected inline
at the claim's original location (search "Correction (independent review
finding P1-1..." above) rather than silently rewritten.

**Live verification:** seeded a fake `history` localStorage record for the
current session on `/interview-studio/history`, clicked "Clear local
History" — zero page errors (`window.addEventListener('error', ...)`
observed none), the rows container went `hidden` and the empty state
showed (rows disappeared), the localStorage `history` key was actually
removed (real wipe, not a cosmetic hide), and the aria-live region carried
"Interview Studio browser data cleared." (truthful announcement).

## P1-2a — Systemic `.is__card` gradient bleed

**Disposition: fixed.** `static/css/interview-studio.css` — section 20's
Smoked Eucalyptus `.is__card` gradient (cool/green stops, the public
page's own light calibration) was never scoped away from the authenticated
composition. Added
`.is[data-authenticated="true"] .is__card { background: #fdf9f6; border-color: var(--is-line); box-shadow: 0 1px 2px rgb(6 30 71 / 5%), 0 10px 26px rgb(6 30 71 / 6%); }`
(placed just after `.is__backdrop`'s own authenticated rule) — deliberately
blanket, not scoped only to Session Complete/History cards, since the
finding names this "SYSTEMIC" and the fix instruction is general. Elements
that need their own distinct treatment (`.is__ai-answer`, stripped to
transparent for authenticated) already have a later, higher-or-equal-
specificity override, unaffected. New test:
`test_authenticated_cards_override_the_public_pages_cool_gradient`.
**Live verification:** a probe `.is__card` element appended under the
authenticated root computed `background-color: rgb(253, 249, 246)`
(`#fdf9f6`), `background-image: none`, `border-color: rgb(234, 226, 216)`
(`#eae2d8`, `--is-line`) — confirmed on both a Session Complete card and a
History info card directly.

## P1-2b — Lock 08 (Interview AI insufficient-evidence state)

**Disposition: fixed**, three sub-items; two sub-items were **already
correct, verified not changed**.

- *Card container* (fixed): `.is-ai-insufficient` and its action row
  rendered bare on canvas — no card border/background/shadow. Added
  `.is[data-authenticated="true"][data-is-ai-state="insufficient"] #is-panel-ai [data-is-ai-answer-content] { background: #fdf9f6; border: 1px solid var(--is-line); border-radius: 0.9rem; box-shadow: ...; }`,
  keyed off the same `data-is-ai-state` root attribute the "ready" state's
  own nested card already uses — no markup change, the insufficiency
  message and the (already-DOM-adjacent) actions row both fall inside this
  wrapper automatically.
- *Question scale* (already correct, confirmed unchanged):
  `.is[data-authenticated="true"] .is__ai-question-frame .is__title--stage { font-size: clamp(1.5rem, 2vw, 1.85rem); }`
  already exists and already wins the cascade over the generic
  display-serif `.is__title--stage` override (higher specificity via the
  `.is__ai-question-frame` ancestor). Verified live: computed
  `font-size: 25.6px` at 1280px viewport, inside the clamp range, and
  `font-family: Newsreader, Georgia, serif` — this is styling correctness
  (scale), not a typeface swap; no code change made.
- *SOURCE label placement* (fixed): the label sat in a fourth `auto`
  grid column beside the three cards, vertically centered — not above them
  on its own row like the lock. Changed `.is-ai-source` to
  `grid-template-columns: repeat(3, minmax(0, 1fr))` and the label to
  `grid-column: 1 / -1; align-self: start;`. Verified live: label
  `top < card top`, both `left`-aligned at the same x.
- *"Use best practice" dominant action* (fixed): no such control existed;
  the row always showed a static "Practice This Answer" whose only
  state-dependent behavior was `disabled = insufficient`. The same
  `[data-is-practice-answer]` element is now relabeled ("Use best
  practice"/"Practice This Answer") and always enabled for authenticated;
  its click handler branches on `root.getAttribute('data-is-ai-state') === 'insufficient'`
  to select the `best_practice` source radio and re-request generation,
  reusing `applyAiModeChange`/`requestModelAnswer` exactly as a manual
  radio-click + Get-example click would. **Disclosed reasoning for reusing
  one element instead of adding a fourth button:** the lock image shows
  exactly three buttons (`Use best practice` / `Change question` /
  disabled follow-up) with no fourth "Practice This Answer" visible
  anywhere in that state; the finding's closing sentence — "'Practice This
  Answer' stays visible but disabled per lock" — is read as describing the
  *existing, already-correct* disabled-toggle behavior being preserved
  (still true: the same control is never hidden, and is disabled
  whenever there is truly nothing practiceable), not a mandate for a
  fourth, lock-contradicting button. Flagged explicitly per the package's
  own disclosure convention rather than assumed silently.
  New tests: `test_source_label_renders_above_the_three_cards_not_beside_them`,
  `test_insufficient_state_renders_in_a_locked_card_container`,
  `test_use_best_practice_replaces_practice_this_answer_when_insufficient`.
  **Live verification (full round trip, mocked `/api/interview/model-answer`):**
  clicked "Get example" → insufficient response → card container present
  (`background-color: rgb(253, 249, 246)`, bordered), SOURCE label above
  the cards, button read "Use best practice" and was enabled → clicked it →
  request body carried `mode: "best_practice"`, the radio + select both
  flipped to `best_practice`, state transitioned to `ready`, button label
  reverted to "Practice This Answer".

## P1-2c — Lock 09 (Video Practice frame/chips/order)

**Disposition: fixed**, all three sub-items.

- *Order* (fixed): `.is__camera-controls` previously rendered inside
  `.is__camera` (before the truth line, which rendered after `.is__camera`
  closed). Restructured `templates/interview_studio.html`'s authenticated
  branch (`{% if not interview_authenticated %}...{%- else %}...{%- endif %}`)
  so the truth line now sits directly under the frame and one live copy of
  the controls renders as a sibling after it — public branch is
  byte-for-byte unchanged (covered by
  `InterviewStudioFlagOffByteComparabilityTests`, still green). New test:
  `test_video_frame_order_is_frame_then_truth_line_then_controls` (asserts
  DOM-order position AND exactly one live copy of every control hook
  except the documented `data-is-device-settings` dead-duplicate — see
  below).
- *"Local camera preview" caption* (fixed): did not exist. Added
  `<p class="is__camera-caption" data-is-camera-caption>Local camera preview</p>`
  inside `.is__camera`, `z-index: 2` (above the empty/recovery placeholders
  and the live `<video>`, below the chips row's `z-index: 3`) so it stays
  legible once a real camera stream is active.
- *Chip leading icon/status dot* (fixed): chips were plain text, no icons.
  `setDeviceStatus()` already creates a dot marker (`<i>`) via
  `replaceChildren()` on whatever `[data-is-camera-status]`/`[data-is-mic-status]`
  resolves to — moved those hooks to a new inner `.is-video-chip__label`
  span (a sibling of a new leading `<svg>` icon), so the icon survives
  `replaceChildren()` untouched; zero JS changes needed. Added
  `.is-video-chip__label > i` dot styling (hardcoded colors for this
  permanently-dark frame, matching the file's existing convention for this
  exact component rather than the light-surface `--is-success`/`--is-error`
  tokens). New test: `test_video_chips_have_leading_icons_and_status_dot_markup`.

**Found and fixed while implementing the above (not one of the ten
numbered findings, same class of defect Task 3 already found once in this
file):** `[data-is-camera-status]`/`[data-is-mic-status]` each exist twice
for authenticated — the new frame chips, and the retained device-status
side card's own spans. `one()` binds `setDeviceStatus()` to the frame copy
(first in DOM order), so the side-card spans were never updated. Confirmed
live: after a real `enableCamera()` failure the frame chip correctly read
"Camera unavailable" while the side-card span stayed "Camera not
requested" forever — contradicts this file's own prior claim (Task 3 notes)
that "the truthful status text itself is correct and reachable; only its
on-page position differs." Fixed by hiding the whole now-redundant row
(`.is[data-authenticated="true"] #is-panel-video .is__video-device-card .is__device-status { display: none; }`)
— the card's own `data-is-video-state-copy` paragraph already states the
same information truthfully in one sentence. New test:
`test_device_status_side_row_hidden_for_authenticated`.

**Live verification:** DOM order confirmed (`.is__camera` no longer
contains `.is__camera-controls`; truth line precedes it); caption text and
position confirmed; a real `enableCamera()` failure produced `is-error`
class + red dot (`#f03d54`) on the frame chip and correctly hid the
side-card row.

## P1-2d — Lock 11 (Session Complete)

**Disposition: fixed**, three sub-items; two sub-items (circular icon
badges, warm-ivory cards) were **already correct** (badges: `border-radius:
50%` on `.is-complete__card-icon`, pre-existing; cards: fixed by P1-2a).

- *Gold rule under headline* (fixed): added
  `<hr class="is-complete__rule">` between the summary `<p>` and the cards
  row; CSS `border-top: 1px solid var(--is-gold);` spans the same width as
  the three-card row. Live-verified computed `border-top-color: rgb(197, 162, 100)`
  (`#c5a264`).
- *Action-button arrow icons* (fixed): all three buttons
  (`data-is-complete-practice-next`/`-new-session`/`-history`) gained the
  same trailing-arrow svg the public "Get example" button already uses.
  "Lock scale" was checked and found already correct (base `.is__button`
  sizing, no shrinking override existed) — no separate fix needed.
- *"Completed questions" rail group* (fixed): did not exist. Added
  `<div class="is-auth__rail-completed" data-is-rail-completed hidden>` (a
  new eyebrow + `<ol data-is-rail-completed-list>`) between "Change setup"
  and "Session tools" in the rail. `renderSessionComplete()` populates it
  from the same reviewed-answer `records` the main "Questions reviewed"
  card already uses (checkmark svg + CSS-truncated title, this file's
  established truncation pattern — full text stays in the DOM with a
  `title` attribute, not JS-truncated). `resetConsequenceStack()` (already
  called by `clearReviewState()`, itself already called on every path that
  leaves the completion view — a new question or a new session) hides and
  clears it. New tests:
  `test_session_complete_gold_rule_and_action_arrows`,
  `test_completed_questions_rail_group_wiring`.

**Live verification (full round trip):** seeded a valid v2 history record
(5 dimensions, correct `DIMENSION_STATUSES`) for the current
`session.sessionId`, clicked "Finish session" — rail group unhidden with
one `<li>` (checkmark svg present, full question text in a
CSS-`overflow:hidden`/`text-overflow:ellipsis` span), gold rule's computed
`border-top-color` read `#c5a264`. Clicked "Practice the next focus" — rail
group hid and its list emptied again (`renderQuestion()` →
`clearReviewState()` → `resetConsequenceStack()` fired as expected).

## P1-2e — Lock 12 (History filter selects)

**Disposition: fixed.** `.is-history__filters select` (the authenticated-
only filter class — the public history page's own filters use the
separate `is__history-filters` class, so no `[data-authenticated="true"]`
scope was needed) rendered as the browser's native select. Added
`appearance: none` + a drawn chevron (`background: ... url("data:image/svg+xml,...")`)
+ `border-radius: 999px` + `border: 1px solid var(--is-line-strong)`. Green
info-card tint (also named in this finding) was already fixed by P1-2a
(`.is-history__card` carries `.is__card`); verified live, not re-fixed.
New test: `test_history_filter_selects_are_styled_pill_dropdowns`.
**Live verification:** computed `appearance: none`, `border-radius: 999px`,
`border-color: rgb(217, 207, 194)` (`#d9cfc2`), chevron background-image
present.

## P2-1 / P2-2 — Marker gate scope and client/server divergence

**Disposition: fixed**, both directions.

- *Server* (`app.py`, `interview_review`): `_IMPROVEMENT_MARKER_PATTERN`
  previously rejected bracket markers on every authenticated submission,
  including a first attempt — exactly the Opus repro ("I built the
  pipeline. [I can share the architecture diagram if useful.]") would 400
  before ever reaching the provider. Added a client-reported `attempt`
  field, validated strictly (`isinstance(attempt, int)`, excludes `bool`,
  bounded `1..1000`, defaults to 1 for anything else — the strictly more
  permissive direction), and scoped the rejection to `attempt >= 2`.
  `attempt` is advisory UX truth; the improve contract that actually
  produces a bracket marker remains the real security boundary, unchanged.
- *Client* (`interview-studio.js`): `appendAuthenticatedImprovement` now
  stores the improve response's `confirmations[]` (re-assigned on every
  new payload, including the R2 "Add context or evidence" resubmission);
  `syncMarkers()` counts unresolved markers by literal string containment
  against the draft when `confirmations` is present, falling back to the
  existing regex only when it is absent — closes the gap where a marker
  shaped differently from the client's own regex (e.g. a bare `[TBD]`
  placeholder, which would never match the imperative-sentence shape)
  could otherwise never be caught. `submitReview()` sends
  `attempt: session.attemptNumber` (already incremented before the call)
  in the authenticated payload only.
- New/updated tests:
  `test_revised_answer_with_surviving_marker_is_rejected` (updated to send
  `attempt: 2`, otherwise the new default would let it through — this is
  the correct behavior change, not a weakened test: a *revision* with a
  surviving marker must still 400);
  `test_first_attempt_with_member_authored_brackets_is_accepted` (exact
  Opus repro, both `attempt: 1` and `attempt` omitted);
  `test_attempt_field_is_a_bounded_int_not_a_security_boundary` (string,
  negative, zero, huge, `None`, float, list — all default to 1, never
  crash, never wrongly tighten the gate);
  `test_marker_gate_prefers_server_confirmations_over_the_client_regex`;
  `test_review_revised_answer_sends_the_attempt_number`.

**Live verification against the real running server** (not mocked): an
unmocked first-attempt request with the exact Opus repro answer returned
500 "The coach is unavailable right now" (placeholder API key) — i.e. it
passed the marker gate and reached the real provider call, instead of the
previous 400 "Replace or remove every bracketed prompt before review."
The same answer with `attempt: 2` was still correctly rejected with the
400.

## P2-3 — Lock 09 no-inference line + "public" copy

**Disposition: fixed**, both sub-items.

- The line "Video Practice does not analyze eye contact, appearance,
  confidence, emotion, personality, pace, or delivery." did not exist
  anywhere in the template (the existing Task 2 truth line is a different
  sentence, about transcription/recording removal, placed below the
  composer). Added it persistently under CONTENT COACHING, above the
  transcript composer, per the lock.
- The result block's `<strong>Delivery analysis is not part of this
  public practice session.</strong>` was unconditional (shared by both
  branches). Forked inline:
  `this{% if not interview_authenticated %} public{% endif %} practice session.`
  — public keeps the exact original bytes, authenticated drops " public".

**Byte-comparability regression caught and fixed during this change:** an
inline Jinja comment with no trim markers left a stray blank line in the
flag-off render (111447 vs. the golden 111406 bytes — caught immediately
by `InterviewStudioFlagOffByteComparabilityTests`). Root cause: the
comment sat between `<div class="is__analysis-unavailable">` and its
preceding `<p>`, and unlike an `{% if %}` tag a `{# #}` comment's own
surrounding whitespace is not implicitly consumed. Fixed by left-trimming
only the comment's opening delimiter (`{#- ... #}`, right side untouched)
— collapses the comment into the preceding line without disturbing the
newline/indent that separates it from the next element. This is the same
"trim exactly one side" mechanics the slice 3 byte-comparability section
above documents for `{% if %}` tags, applied to a `{# #}` comment for the
first time in this file.

New tests: `test_no_inference_line_is_persistent_under_content_coaching`,
`test_delivery_analysis_sentence_drops_public_for_authenticated_only`.

**Live verification:** on the authenticated running server, the
no-inference line's `textContent` matched the locked copy exactly and sat
before `.is__transcript-composer` in DOM order; the delivery-analysis
`<strong>` read "Delivery analysis is not part of this practice session."
Toggling `app.config['PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED']` to
`False` in the same process (the test suite's own technique, since
`PEERSLATE_ALLOW_DEV_IDENTITY` authenticates every request against a
locally flag-on server, so the public branch isn't otherwise reachable on
a single running instance) confirmed the flag-off render still reads
"...this public practice session." verbatim.

## P3 — Legacy redirect paths' cache/robots headers

**Disposition: fixed.** `prevent_stale_html`'s namespace check
(`request.path.startswith('/interview-studio')`) missed the three legacy
redirect paths that 302 into the now identity-gated destination. Extended
the condition with the existing `LEGACY_INTERVIEW_PATHS` set (already used
by the redirect handler itself, so no new list to keep in sync) so their
302 responses carry the same `X-Robots-Tag: noindex, nofollow` /
`Cache-Control: private, no-store` treatment, both signed out and signed
in. New test:
`test_legacy_redirect_paths_carry_the_same_noindex_no_store_headers`.
**Verified:** flag-off behavior is unchanged (no headers added, ordinary
`no-cache, must-revalidate` `Cache-Control`).

## Suite results (this closure pass)

`ANTHROPIC_API_KEY=test-placeholder-key`, via
`C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe -m unittest <module>`:

- `tests.test_interview_studio` — 287 tests, 1 skipped, 0 failures (21 new
  test methods added across the ten finding groups above).
- All six named suites together (`test_interview_studio`, `test_auth`,
  `test_search_visibility`, `test_navigation`, `test_governance_pointers`,
  `test_delivery_preflight`) — 391 tests, 1 skipped, 0 failures.
- `InterviewStudioFlagOffByteComparabilityTests` — green (after the
  comment-trim fix documented under P2-3).
- `git diff --check` (against `81d8f21`) — clean.
- Wider check: `python -m unittest discover -s tests -p "test_*.py"` —
  3377 tests, 12 skipped, 2 failures + 2 errors, all four confirmed
  pre-existing and matching the exact items every prior slice in this file
  already disclosed: `test_community_maintenance_off_request_path`'s
  `ScheduledRunnerTests` deadline/media/exit-code trio (2 errors + 1
  failure) and `test_community_disposable_sql_proof`'s
  `test_private_environment_file_has_owner_only_permissions` (POSIX
  file-mode check on Windows, 1 failure). The previously-documented
  journal-frontend contention flake did not reproduce this run (a known
  flake class, not a regression — its absence is expected variance, not a
  new pass condition to rely on).

## Honest limitations

- Live verification throughout this pass used direct `fetch`/DOM
  injection via the Browser pane's `javascript_tool` against a real local
  flag-on server (`PORT=5019`, `PEERSLATE_ALLOW_DEV_IDENTITY=true`) rather
  than a scripted Playwright walk — screenshots were unavailable in this
  environment (`computer{action:"screenshot"}` consistently reported "the
  Browser pane is not displayed"), so every visual claim above is backed
  by `getComputedStyle`/DOM-position assertions, not a pixel capture. This
  is real, reproducible evidence (documented per finding above with exact
  computed values), not a substitute for an eyes-on screenshot pass.
- P1-2b's disposition on "Practice This Answer' stays visible but disabled
  per lock" is a judgment call, disclosed above and at the fix site: the
  same control is reused/relabeled rather than a fourth button added,
  because the lock image itself shows only three buttons. If the
  reviewing architect intended a literal fourth always-present disabled
  button, that reading was not taken; flagged for confirmation rather than
  guessed silently in either direction.
- This pass did not recapture the 19-state visual comparison sheet or run
  `tooling/capture_states.py`/`capture_measure.py` — per the Codex
  handoff's remaining-sequence step 2, that recapture (plus the final
  independent review and the merge/deploy/live-verification steps) is
  explicitly out of this writer's assigned scope (findings-closure only;
  no push, no PR, no governance edits) and is carried forward to whoever
  continues the lane from here.
- No accessibility-specific pass (keyboard traversal, live-region timing
  for the new rail group/chips/caption, reduced-motion, 200% reflow) was
  performed beyond what the existing shared dialog/focus/announce
  machinery already provides — unchanged from every prior slice's own
  disclosed scope boundary.

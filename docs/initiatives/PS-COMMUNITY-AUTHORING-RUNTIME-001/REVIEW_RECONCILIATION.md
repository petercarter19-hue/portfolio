# Independent review reconciliation

## Scope

This record reconciles the findings returned against implementation-content
SHA `6e3936f89c28edb2e34ecf35fd1ceb33c1b74e91`. It does not grant merge,
deployment, configuration, enablement, launch, or live-behavior authority.

## Accepted findings

### 1. Hidden native selects remained in keyboard order

**Accepted.** The native `audience` and `response_posture` selects remain named,
required, enabled form controls so `FormData` and ordinary submission retain
their values. Both now use `tabindex="-1"`; the visible audience trigger remains
the only audience control in sequential keyboard order.

Evidence:

- `templates/community_feed.html` retains both `name` attributes, required
  values, and enabled options while adding `tabindex="-1"`.
- The focused regression suite asserts both controls are excluded from tab
  order and are not disabled.
- Browser inspection returned `tabIndex: -1`, `disabled: false`, and the
  expected values (`public`, `open_feedback`) for both controls. The effective
  composer tab-order inventory contains the close control, visible audience
  trigger, editor, attachment/Voice/AI controls, and Post button, but neither
  hidden select.

### 2. Community confirmation inherited full-height phone treatment

**Accepted.** A confirmation-specific responsive override now preserves a
compact, centered white dialog at phone widths and at short 200%-reflow
viewports. Its specificity deliberately outranks the older general
`.cv1-dialog:not(...)` short-viewport rule.

Evidence:

- `static/css/community-v1.css` fixes the confirmation at a maximum 360px
  width, fit-content height, centered auto margins, bounded viewport height,
  and an independently scrollable frame when needed.
- Browser geometry: 320×800 -> 288×436 at `(16, 182)`; 390×844 -> 358×371 at
  `(16, 237)`; 768×480 reflow equivalent -> 360×302 at `(204, 89)`. All three
  were horizontally and vertically centered without horizontal overflow.
- The first 768×480 pass exposed a selector-specificity failure; the stronger
  confirmation selector was applied and the corrected geometry above was
  reverified.

### 3. Active Questions and My Mix contained fabricated assertions

**Accepted.** The two invented questions and the invented personalized
checklist recommendation were removed. The rail now states that no questions
or recommendations are available to show and explains that member-backed
results will appear when available.

Evidence:

- `templates/community_feed.html` contains the truthful empty states and no
  longer contains any of the three rejected assertions.
- Focused regressions assert the new empty-state copy and the absence of every
  rejected assertion.
- Browser inspection at 1180px returned both empty states from the rendered
  Beyond rail.

### 4. Editor height was calculated while the composer was hidden

**Accepted.** Create/draft restoration and edit flows now schedule editor
measurement after `showModal()` using two animation frames. The existing
92–240px bound and internal overflow behavior are unchanged.

Evidence:

- `static/js/community-v1.js` calls
  `recalculateEditorAfterComposerOpen()` immediately after
  `presentComposer()` in both `openComposer()` and `openEdit()`.
- Focused regressions assert post-open ordering in both paths.
- Browser restoration: a 2,044-character draft reopened at 240px with
  `scrollHeight: 1264`, `overflow-y: auto`, and active internal scrolling.
- Browser edit: an in-memory fixture edit was saved, reloaded, and reopened at
  2,258 characters, 240px height, `scrollHeight: 1362`, `overflow-y: auto`, and
  active internal scrolling. The fixture mutation is process-local and never
  reads or writes Community persistence.

## Rejected finding

### Claimed rail disappearance from 901–1288px

**Rejected as invalid, per Pete's direction.** The earlier
`@media (max-width: 1288px) { .cv1-rail { display: none; } }` declaration is
superseded in the same stylesheet by the later equal-specificity
`.cv1-rail { display: block; }` declaration. No rail breakpoint change was
implemented.

Evidence:

- A regression contract pins the later override after the earlier media rule.
- Browser results showed both rails as `display: block` with no horizontal
  overflow at 901px (170/180px rails), 1024px (210/220px rails), and 1180px
  (210/220px rails).

## Responsive and visual verification

- Required widths: 320, 390, 901, 1024, and 1180px all had
  `document.documentElement.scrollWidth <= innerWidth`.
- 320 and 390 retained the Ours-first mobile tabs and bottom-sheet composer.
- 901, 1024, and 1180 retained Mine / Ours / Beyond simultaneously.
- 768×480 was used as the 200%-zoom reflow equivalent of a 1536×960 viewport;
  it had no horizontal clipping, retained the reachable composer, and used the
  corrected compact confirmation.
- Current desktop and mobile browser captures were compared with locked
  visuals `01_desktop_mine_ours_beyond_structure.png`,
  `03_desktop_composer_empty_geometry.png`, and
  `09_mobile_ordinary_composer.jpg`. The dominant center Feed, flanking rails,
  compact centered white desktop composer, icon strip, and mobile bottom sheet
  remain materially aligned. Rail copy differs only where this reconciliation
  intentionally removes unsupported claims.
- Browser console: no warning or error entries.

## Fresh review of implementation SHA `04c3dff5`

The fresh read-only review confirmed all four corrections above and rejected
the prior rail claim. It also found one release-blocking draft-preservation
defect: after a member saved an edit to an existing post, the shared composer
unconditionally removed the separate create-post draft and its pending
idempotency key. Browser reproduction saved an edit successfully and then
reopened Create post with an empty body and disabled Post control.

Although the unconditional cleanup predated this package's product diff, the
exact candidate still contradicted the package's safe-draft recovery and
user-authored-content preservation requirements. The review verdict was
therefore REJECT.

## First draft-preservation correction and second rejection

Pete transferred the existing package lane to this correction writer at exact
pushed handoff SHA `dd372fea3e7e63b31aacef2523a4d6aa717f20e5` after directing:
"Fix and complete it." The correction is deliberately narrow:

- `clearCreateDraftAfterSuccessfulMutation(editing)` now returns immediately
  for edit mutations. A successful new post still removes its consumed draft
  and pending command key.
- The dependency-free behavioral harness executed the shipped helper against
  a stub store and appeared to prove both the edit-preservation and
  create-cleanup cases.
- A focused Python contract pins the edit guard and the successful-mutation
  call site.
- Browser verification seeded a 511-character create draft, closed the
  composer, saved an existing post edit through a process-local `PATCH 200`,
  and reopened Create post. The body matched byte-for-byte, Post remained
  enabled, and the console contained no warnings or errors.
- Corrected verification at that stage: 198 focused tests passed; 3,834
  repository tests passed with 24 expected skips; the draft harness passed 16
  behavioral checks; JavaScript syntax and `git diff --check` passed.

The different reviewer rejected implementation-content SHA
`4dc1cba43bb3dedc602a3affd0061f359610299d`: successful create cleanup ran,
then `closeComposer()` saved the still-populated published body back into the
device draft. The test covered the cleanup helper alone and missed the
following close lifecycle.

## Complete mutation-close correction

The new correction covers the complete asynchronous dialog-close sequence:

- Successful create and edit mutations close the composer with draft saving
  explicitly suppressed. Create still clears its consumed draft and pending
  command key; edit leaves the unrelated create draft and key untouched.
- The dialog `close` event consumes and resets the one-shot suppression flag
  instead of saving after mutation success. Ordinary user closes retain the
  existing private-draft save behavior.
- The dependency-free harness now executes cleanup, composer close, and the
  delayed close-event finalizer. It proves edit preservation byte-for-byte,
  final create absence for both storage entries, and ordinary-close saving.
- The fixture-only preview now accepts a process-local create response so the
  full browser publication path can be exercised without Community
  persistence.
- Browser verification published the restored 511-character fixture draft,
  reopened Create post at `0 / 4,000` with Post disabled, then saved a fixture
  edit and reopened the separate 443-character create draft intact. The
  browser console contained no warnings or errors.
- Final writer verification: 198 focused tests passed; 3,834 repository tests
  passed with 24 expected skips; the integrated draft harness passed 17
  behavioral checks; JavaScript syntax and `git diff --check` passed.

The corrected implementation-content SHA is
`887bd087e722562fd4c78f4d75a3b128d1cd74d9`. This reconciliation is writer
evidence, not independent acceptance or release authority; a fresh different
reviewer must inspect that exact SHA before any grant or merge.

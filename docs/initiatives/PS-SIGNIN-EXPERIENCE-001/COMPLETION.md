# PS-SIGNIN-EXPERIENCE-001 — completion record

**Self-certification: Pass.**
Both approved items are implemented, verified in a real browser, and covered by
tests. Nothing is deployed; this package stops at a reviewed branch.

## Outcome in plain English

**Item 2 — a paused database no longer looks like a broken product.** Azure SQL
serverless pauses when it is idle, so the first signed-in request after a quiet
period fails while it resumes. Two things were wrong with that. On `/app` the
flag-on Owner Home collapsed a resuming database and a genuinely invalid
`owner-home.v1` payload into the same "HOME DATA FAILED / Owner Home data could
not load" card — a product failure shown at the exact moment of first sign-in.
And on both waking surfaces recovery was manual: the member had to keep pressing
a link through the whole 30–60 second resume.

Now `DatabaseServiceError` renders a separate, truthful "your private workspace
is starting" state that checks again on its own — a bounded ~90 second window of
backed-off re-checks (4, 6, 9, 13, 18, 25 s), a visible line saying what it is
doing, and a real control to stop it. `OwnerHomeContractError` still gets the
existing failure card, untouched. Both waking surfaces keep 503 +
`Retry-After: 5` + `Cache-Control: private, no-store`. Sign-in also fires one
best-effort background connection immediately before the Easy Auth redirect, so
the database starts resuming while the member is on the Microsoft page.

**Item 5 — the signed-in mobile header no longer overlaps.** The wordmark was
the one header element with no width ceiling, so on the crowded signed-in row
(which carries "My Slate" and "Sign out" on top of everything the signed-out row
has) it kept its intrinsic width and the theme toggle and Menu button rendered
on top of it. It now cannot exceed the column it was given, and below 34rem the
row reclaims the width those two extra controls need. Every viewport from 545px
up is pixel-identical to `origin/main`.

## Base and final commits

- Base: `origin/main` at `388f47307a65bec6e70731a1b7794acad2dd1884`
- Branch: `work/2026-08-02-signin-smoothness-001`
- Final: see the branch tip; this record is committed with the implementation.
- Not pushed. The coordinating session reviews the diff, then pushes.

## Changed files and why

### Item 2

| File | Reason |
|---|---|
| `auth_routes.py` | Split `DatabaseServiceError` (transient wake) from `OwnerHomeContractError` (real failure) on the flag-on `/app` path; add `Retry-After: 5` to the waking response; pass the retry URL and the 90 s budget to both waking templates; add the non-blocking sign-in pre-warm. |
| `templates/partials/owner_home/_stage.html` | New `home_waking` branch reusing the failure panel's exact geometry with truthful copy, a polite live region, and a stop control. Failure branch unchanged. |
| `templates/partials/owner_home/_home_status.html` | Truthful footer line for the waking state. |
| `templates/owner_home.html` | Loads the retry script only for the waking render. |
| `templates/identity_storage_unavailable.html` | Same auto-retry treatment; copy now says how long this normally takes and that nothing was published, shared, deleted, or changed. |
| `static/js/workspace-waking.js` (new) | The bounded, stoppable, quiet automatic re-check. Progressive enhancement only. |
| `static/css/owner-home.css` | Waking dot + status line, `[hidden]` guard for `.oh__btn`, reduced-motion and forced-colors entries added to the file's existing blocks. |
| `static/css/owner-app.css` | The same for the identity waking panel. |

### Item 5

| File | Reason |
|---|---|
| `static/css/public-navigation.css` | Wordmark can no longer exceed its grid column (public shell); new `≤34rem` block compacts only the signed-in row. |
| `static/css/style.css` | The same ceiling for the `/app` public-shell header, where `public-navigation.css` is not loaded; `≤34rem` block gives the brand column priority and lets the controls wrap. |

### Tests

| File | Reason |
|---|---|
| `tests/test_auth.py` | Waking-page markup, the bounded auto-retry contract, and four pre-warm tests. |
| `tests/test_owner_home.py` | The two now-distinct `/app` states, response headers, and the recaptured flag-off golden hash. |
| `tests/test_signin_experience.py` (new) | Pins the stylesheet and script declarations the browser-verified result depends on. |

## Verification

Python: `C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe`, run from
the worktree root with `ANTHROPIC_API_KEY` set to a placeholder.

```
python -m pytest tests/test_auth.py tests/test_owner_home.py tests/test_signin_experience.py -q
    -> 58 passed

python -m pytest tests/test_site_rules.py tests/test_governance_pointers.py -q
    -> 15 passed

python -m pytest tests -q
    -> 1293 passed, 4 skipped, 749 subtests passed
```

### Real-browser behaviour (headless Chromium)

40 assertions across both waking surfaces, all passing:

- a fresh visit schedules one automatic re-check and announces it politely;
- "Stop checking automatically" really stops it, and no further request is made;
- past the 90 s budget the page stops on its own and says so;
- with JavaScript disabled there is no automatic reload, the stop control stays
  hidden, and the server-rendered manual route is present;
- the page never navigates while focus is inside the waking panel.

### Layout measurement

- 32 combinations (`/` and `/petec` × 320/360/390/414 × light/dark × signed
  in/out): zero overlapping header controls, zero horizontal scroll. The base
  build overlaps in 8 of the 16 signed-in cases.
- The `/app` identity waking header: overlapping in the base build at all four
  widths, clean here, wordmark at full size.
- 32 pixel comparisons against the base build at 545/640/744/900/1025/1100/
  1280/1440px, both routes, both themes: **0 differing pixels**.
- `/app` header parity at the same wider widths: 0 differing pixels.

### Pre-warm against the real connection

One connection opened and immediately closed, no query, no member data:

```
GET /auth/sign-in -> 302 in 5.0 ms
background thread finished after 0.75 s
second sign-in within the interval started no new attempt
```

### Recaptured golden hash

`FLAG_OFF_APP_RENDER_SHA256` in `tests/test_owner_home.py` moved to
`37fc92609af60488923653e29435580c806482ea7513bee6b0ead44f0fe4298f`. This was not
a convenience recapture: the byte length is unchanged (18214), and normalizing
the two automatic `?v=` content tokens for `style.css` and `owner-app.css` back
to their `origin/main` values reproduces the previous hash
`bbd9139b78011b5f9d273ed2711a97a68608a766c73321247b7d75a174033a12` exactly. The
render is otherwise byte-for-byte identical.
`tests/test_community_journal_home_milestone.py` imports the same constants, so
it needed no edit.

### Accessibility

- Status lines announce through `role="status" aria-live="polite"`, updated only
  when the state changes — never on a per-second tick. The contract failure card
  keeps its `role="alert"`; the transient state deliberately does not.
- WCAG 2.2 SC 2.2.1: the automatic re-check is bounded and can be turned off
  with a visible control.
- Contrast of the new status text: 6.9:1 on the Owner Home panel, 6.0:1 on the
  identity panel (AA needs 4.5:1).
- The pulse dot is decorative (`aria-hidden`), has `animation: none` under
  `prefers-reduced-motion` (verified: computed `animation-name` is `none`), and
  has a forced-colors rule so it does not vanish into Canvas.
- Keyboard focus on the stop control is clearly visible (screenshot).
- Heading order is unchanged: the waking panel uses the same `<h2>` level the
  failure panel used.

## Visual authority

No new visual direction was created. The Owner Home waking panel is the released
`oh__failure` panel — same geometry, radius, padding, type scale, and marigold
eyebrow — saying something true instead of something false. The identity waking
page keeps its released `owner-app__panel`, eyebrow, and pill treatments. Item 5
restores the already-locked header layout at widths where it had broken.

Documented non-material adaptations:

- A small pulsing dot on each waking eyebrow, and one quiet status line under
  the copy, both in the panel's existing ink.
- The identity page's two links moved into the existing `.owner-app__actions`
  container so the new third control sits in a proper row (2rem top margin,
  0.75rem gap) instead of three inline-flex siblings.
- "Try again" became "Check now" on the identity page, matching the automatic
  checking model and the Owner Home waking panel.
- Below 34rem, signed in, the Menu button uses the icon-only treatment this
  stylesheet already ships at 22rem, and the sign-out pill gets the compact
  sizing `.sign-in-btn` beside it already had.
- Below 34rem on `/app` public-shell pages the header controls may wrap to a
  second line rather than squeeze the wordmark out.

Nothing changes composition, hierarchy, dominant action, typography family,
colour language, or the responsive interaction model.

**Homepage parity:** the logged-out homepage makes no claim about database
availability or the header's signed-in state, so no homepage update is due. The
homepage header itself is covered by item 5 and is pixel-identical above 544px.

## Honest limits

1. **Not deployed, not pushed.** No pipeline has run and no production behaviour
   has been verified. Everything above is local.
2. **Chromium only.** All browser evidence is headless Chromium. The signed-in
   compaction is scoped with `:has()`; a browser without `:has()` support falls
   back to a proportionally smaller wordmark, never to an overlap, because the
   width ceiling is unconditional.
3. **The wordmark scales down below 414px when signed in.** 121.6px at 414,
   116.8px at 390, ~86px at 360 and 320 on `/`. It is never clipped, never
   distorted (`object-fit: contain`), and never overlapped. The alternative was
   removing a control, which the package forbids.
4. **`/app` public-shell headers can become two rows below 544px.** That is the
   identity waking page and the flag-off owner workspace, whose header carries a
   long status label plus Ask AI. Before this change those rows overlapped
   instead. Worth folding into the deferred item 3 (chrome unification)
   discussion rather than solving here.
5. **One retry path is not enhanced.** `owner-home.js` swaps `/app` in place when
   the *contract failure* card's Retry is used. If that particular retry happens
   to land on the waking state, the injected panel has no automatic checking
   (its script was not loaded on the failure page) and the member falls back to
   the manual "Check now" link. Reaching this needs a contract error followed by
   the database pausing in between; the degradation is graceful.
6. **The pre-warm has no environment switch.** `PEERSLATE_SIGN_IN_PREWARM_ENABLED`
   is read with a default of on (off under `TESTING`), but `app.py` is outside
   this package's writable files, so it is not wired to an environment variable.
   Add that in a package that owns `app.py` if an operational switch is wanted.
7. **The pre-warm inherits `db.py`'s connect timeouts** (2 attempts, 60 s each).
   Worst case a daemon thread lives about two minutes and then exits. It cannot
   block, delay, or fail the redirect, and at most one runs at a time with a
   30-second floor between attempts — a public unauthenticated endpoint must not
   let a caller create work on demand.
8. **`OwnerHomeContractError` cannot be produced from a running preview**, so its
   screenshot was taken by serving the exact bytes the same Flask app rendered
   for that branch. The unit tests exercise the real route.

## What the reviewer should look at

- `auth_routes.py`: the three-way `try/except` on the flag-on `/app` path, and
  the pre-warm's lock/rate-limit and total exception containment.
- `static/js/workspace-waking.js`: the budget, the stop control, the same-origin
  check on the retry URL, and the focus guard.
- The `≤34rem` blocks in `public-navigation.css` and `style.css`: they are the
  only rules that change anything, and only below 544px.
- The recaptured golden hash and the reasoning above it.

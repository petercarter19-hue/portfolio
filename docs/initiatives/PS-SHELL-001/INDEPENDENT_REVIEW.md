# PS-SHELL-001 — independent review record

Evidence file for the merge grant on lane
`work/2026-08-12-shell-editorial-top-bar-001`.

## What performed these reviews

**Each of the three review rounds below was performed by a fresh delegated
Claude Opus session acting as an independent reviewer.** No round was performed
by a human. No round was performed by Pete. "Independent" here means a separate
session with no memory of the implementation work, reviewing the committed diff
and the running application — it does not mean an independent person.

**This file is not owner acceptance and must not be read as one.** Pete's
visual acceptance of the Editorial Top Bar, and any owner review of this
package, are separate steps and **have not occurred**. Nothing in this document
records a human signing off on anything.

The implementation was written by a delegated Claude Opus session. The reviews
were written by different Claude Opus sessions. Both sides of this record are
machine-produced.

---

## ANNOTATION — the commit names below are pre-rebase and no longer resolve

**Added 2026-08-13 by the implementation writer. Nothing below this note has
been reworded: every reviewer's sentence, verdict and figure is exactly as
written. This is a pointer, not a correction.**

The lane was rebased after these rounds were recorded — from base
`68d14a4` onto `1abb3fb`, which is the current merge-base with
`origin/main`. Rebasing rewrites every commit on the branch, so **eight of the
nine commit names cited below no longer name anything reachable from this
branch**. Verified with `git merge-base --is-ancestor` at head
`70d9c4e`:

| Cited as | Still reachable from this branch? |
|---|---|
| `27fad0f` — Round 1's reviewed commit | no |
| `74950e9` — Round 2's reviewed commit | no |
| `7f5fbc9` — the start of Round 3's reviewed range | no |
| `cb9d000346abe771318393edf8c3225b7ae232c5` — Round 3's reviewed commit | no |
| `89cb1f8`, `859102a`, `b54de5f` — the post-Round-3 commits | no |
| `23465bc` — where "382 tests" was re-measured | no |
| `68d14a44de4007f8643396833a481601d5dbb4a3` — the stated base | **yes** |

Only the base survives, because it is a commit on `main` rather than on this
branch. The eight branch names still exist as loose objects in the worktree
that performed the rebase, so `git show` may resolve them there; they are not
in any branch, they would not survive garbage collection, and a fresh clone
would not have them at all. **Do not read a failure to check one out as
evidence that the review did not happen.**

What this does and does not cost. The reviews were performed, and their
findings and measurements stand — the tree each round examined is preserved
in the current branch's content, not in the names it was examined under. What
is lost is the ability to reproduce a round by checking out its exact commit,
which is a real reduction in the evidence's strength and is recorded here
rather than left for a reader to discover. Any future round should record the
patch-id or the tree hash alongside the commit name, both of which survive a
rebase.

**A fourth round followed all of these.** The owner reviewed rendered
screenshots for the first time on 2026-08-13 and directed a further round of
fixes — the always-revealed logo, findings F1–F4, and the shell colour
consistency pass. That work is recorded in `IMPLEMENTATION.md` §14 and **has
not been independently reviewed**.

---

## Round 1 — reviewed commit `27fad0f`

**Verdict: PASS WITH FINDINGS. 16 findings (F1–F16), 2 of them HIGH.**

The two HIGH findings:

- **F1** — at 320px the phone bottom bar overflowed and clipped the "More"
  slot. Bar `clientWidth` 320 against `scrollWidth` 344, with More running from
  x=280.8 to x=335.5, i.e. 15.5px past the viewport edge. Because
  `.mobile-tabbar` sets `scrollbar-width: none`, nothing signalled that the row
  scrolled, and the implementation had also hidden the header Menu on those
  routes — so Workshop, Opportunity Slate, Settings, My Slate and Sign out were
  reachable only by discovering an invisible horizontal drag.
- **F2** — "Sign out" rendered at 11.52px in a 32px row in both dropdowns below
  544px, beside neighbours at 15px in 44px. A `@media (max-width: 34rem)` rule
  written for a standalone header pill outranked the menu rows the control had
  since moved into.

Both were fixed and re-measured before Round 2.

## Round 2 — reviewed commit `74950e9`

**Verdict: PASS WITH FINDINGS. 12 findings (F-A–F-L).**

The two most significant:

- **F-A (HIGH)** — the More sheet's bottom rows were permanently unreachable on
  short viewports. The sheet is `position: absolute` under a `position: sticky`
  header, so its bottom edge is pinned to the viewport and scrolling the page
  could not bring a row below the fold into view; twelve Tab presses could not
  either. Unreachable rows were measured at 390×400 (Sign out), 568×320 (My
  Slate, Settings, Sign out), 640×360 (Settings, Sign out) and 320×256 (four
  rows). Recorded as a **WCAG 2.2 SC 1.4.10 Reflow failure**.
- **F-C** — the tokenization commit was **not a pure substitution**. Alongside
  the aliases it introduced a new focus rule which, at specificity (0,2,1),
  outranked `.theme-toggle:focus-visible` (0,2,0) and stacked a third ring on a
  control that draws its own. The 150-frame screenshot baseline could not see
  it because the theme toggle is flag-gated off.

Round 2 also correctly rejected one of its own candidate findings' premises on
the facts: assumption A1 stands, because `profile_routes.py` exists on main but
its blueprint is not registered and nothing outside tests imports it, so
pointing the first navigation item at a per-member profile route would 404.

## Round 3 — final merge-readiness review

- **Reviewed commit:** `cb9d000346abe771318393edf8c3225b7ae232c5`
- **Base:** `68d14a44de4007f8643396833a481601d5dbb4a3`
- **Verdict: PASS WITH FINDINGS — safe to merge and deploy.**

All eight claimed fixes were verified TRUE, several by methods stronger than
the original checks:

- `elementFromPoint` occlusion testing on every More-sheet row, which confirmed
  the sheet's `z-index: 1210` sits above the bar's `1150`, so no row hides
  behind the fixed bottom bar;
- painted-pixel measurement of the active underline, finding exactly 8px of
  overhang each side and 3 painted rows — matching the approved board's own
  measured 8px signature.

Tokenization was independently confirmed inert by an **independently
implemented** computed-style proof using the reviewer's own parsed alias map:
**57 states, 5,865 node snapshots, 0 non-custom-property deltas.**

Four findings, none merge-blocking. The highest is the 200%-text sticky header
reaching 441px at 1200–1366px viewport widths when five destinations are
enabled; it is recorded as a known limitation in `IMPLEMENTATION.md` §12.3
rather than fixed, because fixing it properly means collapsing the responsive
ladder on content width rather than viewport width — a design change belonging
to its own round.

### Round 3 verdict — the reviewer's own words, verbatim

Quoted exactly as written by the independent reviewer (a fresh delegated
Claude Opus session), for the reviewed commit
`cb9d000346abe771318393edf8c3225b7ae232c5`:

> Independent review of PS-SHELL-001 at
> `cb9d000346abe771318393edf8c3225b7ae232c5`, based on
> `68d14a44de4007f8643396833a481601d5dbb4a3` (verified as an ancestor;
> merge-base equals base). Reviewer wrote none of this code and used no
> writer-supplied script. Method: full read of the unreviewed delta
> `7f5fbc9..cb9d000` (the post-rebase equivalent of `74950e9`) across CSS,
> template, JS, tests and record; two Flask servers pinned to the review
> worktree with the served `?v=1287fcd16e75` token checked against the on-disk
> SHA-256 of `public-navigation.css` before measurement; independent
> Playwright/Chromium 149 probes for all eight claimed fixes, including
> `elementFromPoint` occlusion testing of every More-sheet row (a check the
> writer's harness did not perform) and a painted-pixel measurement of the
> active underline; an independently implemented tokenization proof whose alias
> map is parsed from the stylesheet's own declarations and whose de-tokenized
> twin is served by request interception rather than by modifying any file; a
> ChoiceLoader re-proof that the anonymous `/interview-studio` delta is
> shell-markup-only; and pixel measurement of the approved board
> `GLOBAL_SHELL_PUBLIC_MEMBER_OWNER.png`. All eight claimed fixes (F-A, F-B,
> F-C, F-D, F-F, F-G, F-H, F-I) verified TRUE. Tokenization independently
> confirmed inert: 57 states, 5,865 node snapshots, 0 non-custom-property
> deltas; the shell focus rule separately confirmed a pure restatement (0 of 6
> visible header controls change when it is removed). 382 tests across the five
> affected suites pass, including the `test_owner_home` D1 byte-locks and the
> recaptured Interview byte-lock; `.gitattributes` pins `eol=lf` and disk bytes
> equal git blob bytes, so the Windows-captured digests are platform-stable for
> Linux CI. Changes to `tests/test_interview_studio.py` are confined to the
> four locked constants plus comments. Assumption A1 confirmed still true at
> base. Conclusion: safe to merge and deploy. Four findings recorded, none
> blocking; the highest concerns an unrecorded 441px sticky header at 200% text
> in the 1200–1366 band with all five destinations enabled, and a completion
> record that still describes the Interview byte-lock as unfixed.

### Editorial note — what changed after the reviewed SHA

**Not part of the reviewer's statement.** Added by the implementation writer so
that what the reviewer said stays distinguishable from what happened next.

**The independent review covers `cb9d000`, not the current head.** Three
commits followed it — `89cb1f8`, `859102a`, `b54de5f` — plus this record.
**Those commits have not been independently reviewed.** They were verified by
the writer's own closing proofs, described below, and that is a weaker warrant
than an independent round.

Two clauses in the paragraph above were accurate at `cb9d000` and have since
been overtaken:

- *"a completion record that still describes the Interview byte-lock as
  unfixed"* — corrected in `89cb1f8`. `IMPLEMENTATION.md` §9 and §12.1 now
  describe the recapture as authorized, complete and passing. **A reader should
  not go looking for this defect; it no longer exists.**
- *"an unrecorded 441px sticky header at 200% text"* — now recorded, as
  `IMPLEMENTATION.md` §12.3, with measurements taken by the writer that match
  the reviewer's independently.

One clause still holds exactly. *"382 tests across the five affected suites
pass"* was re-measured at head `23465bc`: **still 382, still passing** (1
skipped). Larger figures elsewhere in this package's records — 463, and 3,713
for the full discovery run — count different and wider suite sets, not these
five.

The post-`cb9d000` changes were verified by two computed-style proofs, because
they moved colour declarations between sibling rules and edited stylesheet
comments:

| Proof | Scope | Result |
|---|---|---|
| Tokenization still inert | 174 states, 18,118 node snapshots | 0 non-custom-property deltas |
| The post-review revision itself inert | 40 states, 4,055 node snapshots | 0 deltas, custom properties included |

Both were written and run by the implementation writer, not by a reviewer.

---

## Work done after Round 3, and its verification

Round 3 raised three truth corrections. A fourth was found by the
implementation writer in the same file during the same pass. All are in
`89cb1f8`.

1. `IMPLEMENTATION.md` §9 still described the Interview Studio byte lock as a
   known-failing test awaiting another lane's writer, quoting
   `114728 != 111406`. A reader would have concluded a failing test was being
   merged. §9 and §12.1 now describe what happened.
2. A stylesheet comment described the active state as a **2px** underline; the
   F-F fix had made it 3px.
3. A stylesheet comment described the phone bar as taking a **2px indicator**;
   the F-D fix had deleted that indicator in favour of the board's filled-mark
   current slot.
4. **Found by the writer, not the review:** the token block still cited the
   150-frame pixel diff whose comparison the writer had already found defective
   and withdrawn. It now cites the computed-style proof that replaced it.

The same commit narrowed the dark-theme guard. The dormant
`body[data-theme="dark"] .mobile-tabbar__item` colour rule is (0,1,1) and would
outrank an unguarded selector, so the guard is needed — but wrapping the whole
rule meant a revived dark theme would have lost `display: flex`, the 2.75rem
target, the padding, the type and the icon column. Layout is now unguarded and
colour guarded.

`859102a` recaptured the Interview byte-lock digests. Byte lengths were
unchanged at **114833** and **114610**, and for both locked routes the new
stylesheet token was shown to occur exactly once and to reproduce the
previously locked sha when swapped back — establishing that the stylesheet
fingerprint was the only delta.

### Closing proofs (`b54de5f`)

The post-Round-3 pass moved colour declarations between sibling rules, which is
the class of change that is usually inert and occasionally is not. It was
measured rather than assumed. Both proofs are by computed style; the screenshot
frame set was demoted to a visual record after its comparison method was found
defective.

| Proof | Scope | Result |
|---|---|---|
| Tokenization still inert | 174 states, **18,118** node snapshots | **0** non-custom-property deltas |
| The post-Round-3 revision itself inert | 40 states, **4,055** node snapshots | **0** deltas, custom properties **included** |

The split's own rules were checked property by property: `.mobile-tabbar__item`
observed 90 times, `.mobile-tabbar__label` and `.mobile-tabbar__mark` 60 times
each, and all **2,550** watched property comparisons matched.

---

## What none of these rounds verified

This list is the honest boundary of the evidence above. Everything in it
remains unverified across all three rounds.

- **Real tablet and phone hardware.** No physical device was used. Two of the
  fixes depend on declarations that are inert in a headless browser:
  `env(safe-area-inset-bottom)` resolves to 0, and `100dvh` — which the F-A fix
  relies on so a retracting mobile URL bar cannot hide the sheet's last row —
  behaves as `100vh`. The behaviour these were written for has not been
  observed.
- **The touch-tablet code path.** A genuine tablet is forced to a 1280px
  viewport by the shell's own script, which is a different path from a resized
  desktop browser. Only the resized-browser path was exercised.
- **Live production behaviour.** Nothing was deployed or observed on the live
  site.
- **Genuine authenticated states.** There is no local identity provider. Every
  signed-in state was produced by the application's development-identity path,
  which yields a server-rendered authenticated shell but not a real session,
  real account, or real sign-in and sign-out round trip.
- **Screen-reader speech.** Accessible names, roles and focus order were read
  from the accessibility tree and from computed markup. No screen reader was
  run, so what a user would actually hear is unverified.
- **Non-Chromium browsers.** All measurement used headless Chromium. Safari and
  Firefox are unverified, which matters most for `:has()`, `100dvh` and
  `text-wrap` behaviour.
- **Three of the five destinations were never exercised as rooms.** Verified
  directly against the local application: `/the-slate`, `/opportunity-slate`
  and `/app/workshop` all return **404** locally. The 404 template renders the
  shared shell, so shell frames captured on `/opportunity-slate` measured the
  shell **on a 404 page**, not the Opportunity Slate room. The shell has
  therefore never been seen on Community, Opportunity Slate or Workshop.
  **`/the-slate` matters most:** it is the only other route that owns its own
  mobile tab bar, and the whole §5 resolution — one bar, page-owned behaviour
  preserved — turns on that interaction. It was verified on `/petec/*`, which
  also owns a section-tab bar, but never on Community.
- **Three of the four captured routes are real pages.** `/`,
  `/interview-studio` and `/petec/resume` returned 200; `/opportunity-slate`
  did not. Route counts elsewhere in `IMPLEMENTATION.md` should be read with
  that correction, which is now recorded there as §13.

## Package state at the time of this record

- Public/owner shell convergence remains deferred, with the byte-lock proof in
  `IMPLEMENTATION.md` §5.
- The 200%-text five-destination header height is a recorded known limitation,
  not a fix.
- Pete's visual acceptance has not occurred.

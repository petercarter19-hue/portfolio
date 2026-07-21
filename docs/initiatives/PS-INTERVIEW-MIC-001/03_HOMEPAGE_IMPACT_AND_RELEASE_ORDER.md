# 03 — Homepage impact assessment and release order

_Recorded 2026-07-21 by the designated session manager (Claude Code), under
Pete's written delegation of the remaining calls. This closes the two open gates
the implementation record left: the homepage-parity assessment and the release
sequencing._

## 1. Homepage impact assessment — no update required

`docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md` requires every user-facing
package to assess whether the logged-out homepage presents, demonstrates, or
links the product, and to update it in the same wave when the real product
changes materially. It requires the **assessment** in every case; it requires an
**update** only when the public projection has become stale or untruthful.

**Affected section:** `templates/partials/homepage/_interview_demo_scene.html`.

**What it claims about dictation** (line 165):

> "Dictation is optional in the real Studio — speak and it transcribes into the
> answer box. Written practice comes first."

**Assessment against the changed product:**

| Claim | After this package | Still true? |
|---|---|---|
| Dictation is optional | Unchanged; typing is first-class on every failure path | Yes |
| Speak and it transcribes into the answer box | Unchanged; final segments land in the same editable field | Yes |
| Written practice comes first | Unchanged; the written composer is still the primary path | Yes |

**What this package actually changed** — control placement, session continuity,
the ten-second silence rule, and the listening colour — **is not depicted on the
homepage at all.** The walkthrough is fixed fictional content that states
"No microphone, no visitor input" (line 12) and "No microphone, AI request,
draft, attempt, history, or media storage" (line 40). It never renders the
composer action row, a listening state, or any timing behaviour.

**Conclusion: the homepage projection remains truthful, current, and
product-specific. No homepage update is required in this wave, and no downstream
parity package is opened.**

This is a deliberate decision not to manufacture an open gate. Homepage
Interview parity was closed on 2026-07-20 by `PS-HOME-INTERVIEW-PARITY-001`
(PR 105 / pipeline 154, closeout PR 106 / pipeline 156). Opening a parity
package that no stale claim justifies would recreate the drift that
`PS-GOV-TRUTH-RECONCILIATION-001` was created to repair.

**What would reverse this conclusion.** If a later package makes the homepage
walkthrough depict the composer action row, a listening state, or the dictation
timing, or if dictation stops being optional, this assessment must be redone.

## 2. Release order — this package merges second

`work/2026-07-20-interview-validator-truthfulness-001` must merge **before** this
branch.

1. That branch repairs two live production defects: best-practice and compare
   "Get Answer" fail on every request, and Interview Me coaching fails whenever
   the model honestly returns zero strengths.
2. It carries no visual-acceptance gate, so it can ship immediately.
3. Its changed files are a subset of this branch's, so ordering it first
   minimises the merge surface.

## 3. Asset signature — corrected to `studio-5a5c-4`

**This is a required correction, not a preference.**

Both this branch and the validator branch independently bumped the Interview
Studio asset signature from `studio-5a5c-2` to `studio-5a5c-3`. Because the two
sides make the *identical* textual change, Git merges it silently: there is no
conflict and no warning.

`app.py` leaves versioned static assets cacheable by design — only `text/html`
is marked `no-cache`, and the comment there is explicit that "Versioned static
assets (?v=...) are left cacheable". The `?v=` string is therefore the only
cache-busting mechanism the Studio has.

Had both branches shipped as `studio-5a5c-3`, the second release would have
published **different bytes under a URL browsers had already cached from the
first release**. A returning visitor would receive this package's new markup
while still running the previous release's JavaScript, so the dictation controls
would render and do nothing — reproducing the exact "there is no microphone"
failure this package exists to fix.

This branch therefore now publishes **`studio-5a5c-4`** in
`templates/interview_studio.html`, with
`tests/test_interview_studio.py::test_asset_signature_is_bumped_so_the_change_can_reach_production`
updated to match. The validator branch keeps `studio-5a5c-3`.

**Standing rule for any later Interview branch:** before merging, check the
signature actually on `origin/main` and bump beyond it. Do not assume the
number recorded in your own branch is still ahead.

## 4. Manager visual acceptance — granted

Recorded in full in `docs/governance/OPEN_BRANCH_REGISTER.md`. Summary: the
branch was run locally at its exact pushed tip and inspected in both themes.
Deviation D-1 measures 4.92:1 in light and 6.14:1 in dark, both passing WCAG 2.2
AA, using the approved Marigold text-safe and soft tokens rather than a new
colour.

**Not verified and not verifiable here:** real microphone permission and real
vendor transcription. No browser in this environment can grant them
non-interactively. One real dictation should be exercised after release.

# Owner Technical Completion Report — PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001

**Date:** 2026-08-12 · **Delivery path:** Protected · **Release state:** merged and
deployed **DARK** (flag off, verified live). **Not enabled.**

## Outcome

The real Interview Studio is ready to move behind sign-in and has been
recomposed to the 19 hash-locked warm-material visual states from the
owner-accepted 2026-08-11 architecture. Everything ships behind one
default-off flag, so nothing a visitor sees changes until Pete enables it.

When enabled: both Studio routes and all four interview APIs require a
signed-in identity as one unit (signed-out pages bounce to sign-in and return
to the exact page; signed-out API calls get a clean JSON 401); identity is
derived server-side and the browser can no longer assert whose profile it is;
each account gets an opaque browser-storage namespace, with anonymous legacy
records left untouched and never adopted; Interview Me becomes the append-only
answer → coaching → improvement → revised-coaching stack with structurally
immutable submitted snapshots; grounded Interview AI fails closed to the
locked insufficiency state for any account without approved evidence; video
stays page-local; History carries four distinct truth states.

## Evidence

- **Base / final:** base main `24f0acb`; final candidate `e7437af` (PR 391),
  squash-merged as main **`8ac4395`**. The merged tree is byte-identical to
  the reviewed candidate tree (`c978663…`), verified by direct tree compare.
- **Deployment:** automatic run **839** (batchedCI, exact SHA `8ac4395`)
  succeeded at 12:40 UTC. It arrived after a ~7.5-minute watch window had
  closed, so a governed manual fallback (run 840) was queued; the pipeline's
  own duplicate-work guard correctly refused it — "automatic exact-SHA run
  already succeeded (839); verify live identity instead of redeploying". No
  duplicate deployment occurred and the guard behaved exactly as designed.
- **Live verification (post-deploy, release `de17671b7786493aca57f026`):**
  public `/interview-studio` still 200 at 111,659 bytes and byte-identical to
  the pre-deploy capture apart from the two asset content-hash tokens;
  public markers present, zero authenticated markup; anonymous
  `POST /api/interview/review` still returns the ordinary 400 validation
  error (not 401), proving the wall is dark; `/interview-studio/history` still
  200; legacy `/interview-me` still 302s to the canonical route. The
  unconditional discovery changes are live as designed: robots.txt now
  disallows `/interview-studio` and the sitemap no longer lists it.
- **Changed paths:** `app.py`, `auth_routes.py`,
  `templates/interview_studio.html`, `static/css/interview-studio.css`,
  `static/js/interview-studio.js`, `tests/test_interview_studio.py`,
  `tests/test_auth.py`, `tests/test_search_visibility.py`,
  `tests/test_navigation.py` (recorded surface note), this package folder, and
  `artifacts/2026-08-11-interview-studio-authenticated/`. All inside the lane's
  recorded writable surfaces.
- **Tests:** 415 focused tests green across the six named suites (1
  environment skip). Full `unittest discover` clean except four documented
  inherited failures (ScheduledRunnerTests trio; a POSIX file-mode test on
  Windows). No test weakened; every rewritten contract pin is itemized in
  SLICE_NOTES.
- **Flag-off byte-comparability:** the anonymous `/interview-studio` and
  `/interview-studio/history` renders are byte-identical to a pristine base
  render (asset content-hash tokens normalized), verified independently by the
  final reviewer rather than trusted from constants.
- **Visual:** all 19 states captured from the real client flow and compared
  against the locked authorities; captures and the side-by-side sheet are
  committed under `artifacts/2026-08-11-interview-studio-authenticated/`.
- **Reviews:** Opus 5 independent review REJECTed `81d8f21` (2 P1, 3 P2); every
  finding was fixed and live-verified. A fresh independent final review
  APPROVED `11ea73e` with zero P0/P1, ruled the lock-08 dominant-action
  question in the implementation's favor, and raised one P2 label defect now
  fixed at `919b0b6` with a regression test.

## Honest limitations and carried items

1. **Enablement is not done and is not authorized here.** The flag stays off in
   every environment. Pete's browser acceptance of the flag-ON experience
   should happen against a local or candidate run, not by flipping production.
2. **Control-plane gap (needs the control-plane owner).** `merge_allowed_for`
   and `release_allowed_for` are now reserved by a 2026-08-12 control for
   direction-authority, non-production-capable lanes carrying a formal
   `merge_grant` object, so an implementation lane cannot be listed there and
   the machine `--intent merge` gate has no representation for one. This merge
   proceeded under Pete's recorded owner authority through the ordinary Azure
   PR with all required policies passing. `tests/test_delivery_preflight.py` is
   outside this lane's surfaces and two other lanes were actively merging
   through it, so it was deliberately left untouched.
3. **Attempt-counter drift (P3, cosmetic).** A failed revision review leaves
   `attemptNumber` incremented, so a retry can label the snapshot one attempt
   high. Not fixed here because the request-binding uses that counter and a
   naive rollback would re-open a stale-response acceptance path; it deserves
   its own small change with its own test.
4. **Latent follow-up server surface (P3).** The server still accepts a
   follow-up with a signed context token even though the affordance is
   client-disabled while `interview_followup_mode_provenance` is open. Harmless
   today (evidence resolves empty and validation fails closed); the follow-up
   package should close it server-side.
5. **Deferrals unchanged** from the architecture: no member-evidence read
   contract (D2), no anonymous-legacy import (D3), no cloud History, schema,
   provider change, or follow-up expansion (D4).
6. **Session cookie posture (Q-D)** remains as previously recorded; this
   package puts no member data in the Flask session.

## Next action

Pete reviews the shipped-dark state and the comparison sheet, then decides on
enablement. Turning the flag on is a separate, recorded act with its own live
verification and a proven flag-off rollback.

## Post-enablement defect, fix, and final state (2026-08-12)

Pete used the live signed-in Studio and reported that he could submit the
first answer but not the second. Reproduced by driving the real page in a
scripted browser: on desktop the submit control was present for the first
answer and **absent** for the next question.

**Cause.** On a completed review the authenticated action band was hidden, and
the only submit control lived inside that band. Nothing restored it when the
member moved on, so the next question rendered with no way to submit.

**Fix (owner-directed shape).** Dictation, the live "Heard so far" transcript,
and the send control now live INSIDE the answer box at every width, so a typed
or spoken answer always has a visible way to submit and the control shares the
composer's own lifetime. Band visibility is additionally derived from the stage
machine rather than ad-hoc per-call-site toggles, so the question/coaching
groups return with the next question. A full interaction sweep across all modes
at desktop and phone also caught the video status chips overflowing the
viewport at phone width; they now wrap.

**Deployment truth for this fix.** The automatic run (858) delivered the code
and then failed its own post-deploy smoke, as did the manual fallback (861).
Neither failure was the application: the smoke asserted `/interview-studio`
returns 200, an expectation written when the Studio was public. With the wall
enabled the route answers signed-out callers with a redirect, so a healthy
deployment was being marked failed — for every lane, not only this one. The
smoke now accepts exactly two contracts for that route (public 200 with its
markers, or the precise signed-out redirect with the exact return destination)
and still fails on any other redirect target, 404, 500, or transport failure;
all five cases were exercised directly. Run 864 deployed that repair and passed
its smoke, which is the proof it works.

**Verified live at release `ff44992bb27589f1a15f1ae8`:** the served CSS and JS
carry the in-box composer and the stage-derived band fix; `/interview-studio`
redirects signed-out callers; the interview APIs return 401; the homepage,
public resume, and Community are unaffected.

**Honest limit.** The final end-to-end walk while signed in as the owner on
production (type, submit, next question, submit again) is Pete's to perform;
that exact sequence was proven against the same code in a scripted browser,
failing before the fix and passing after.

## Lessons recorded for future work here

1. A green pipeline run does not mean code shipped: check the stages actually
   executed and verify the served assets. A scheduled maintenance run shares
   the same commit and can be mistaken for a deployment.
2. This App Service has twice needed an explicit restart before a change took
   effect; do not trust the automatic restart alone.
3. A route that gains a sign-in wall must have its deployment smoke updated in
   the same change, or every later deployment fails on a false signal.

## Final disposition (2026-08-12)

Pete approved the closeout. The lane was released so the control plane returns
to `controlled_idle` and the next writer can activate.

It is recorded in `CURRENT_LANES.json` as **`paused_preserved`**, not
`merged_closed`. `--intent close` was run and refused for reasons that are
structural rather than procedural: it requires a `direction_authority` lane
with `production_capable` false, a formal `merge_grant`, a branch tip unmoved
since review, and a **single** merge commit that introduced every writable
surface. This is a production-capable implementation lane that merged its
implementation, an owner-reported production fix, a repository-wide
deployment-smoke repair, and its own completion record, so no such commit
exists and none could be manufactured honestly. The pause record carries the
reason and the resume contract, and the 2026-08-12 control-plane handoff now
carries the captured error output plus this second finding. Nothing was
forced: no assertion was weakened and no `merge_grant` was fabricated.

Releasing the lane exposed a related defect worth naming, because it would
have turned main red for every lane the moment the control plane went idle:
four tests in the delivery-preflight suite built their fixtures from
`active_lanes[0]`, so they crashed when no lane was active — even though
`controlled_idle` is a supported state the preflight itself produces. They now
source that fixture from the active, paused, and closed records, and the two
that had been inheriting a lane class or operating state from whatever
happened to be live set it explicitly. The suite was verified both ways: 72
tests pass with a lane active and 72 pass against an empty control plane.

**Preserved for recovery.** Branch
`work/2026-08-11-interview-studio-authenticated-experience-001` plus tags
`archive/2026-08-12-interview-studio-authenticated-pre-squash` and
`archive/2026-08-12-interview-studio-authenticated-lane-tip` hold every commit,
including the pre-squash history.

## Round 2: post-enable mobile correction (2026-08-12)

Pete reopened the package after confirming the delivered experience works,
with a handoff scoping a mobile correction round. Route, core workflow, truth
boundaries, logo and global shell untouched, as instructed.

**Delivered and live at release `874aaa0b77463d3af91ef020` (main `2d83eba`).**

- **Post-review scroll and focus.** The global header is sticky at 0 and 65px
  tall, but the rail pinned itself at 1.1rem -- *behind* that header. That is
  what sliced the mobile Interview Me / Session / History row in half. The
  stylesheet had always intended a static control row below the rail
  breakpoint, but the desktop shell rule outranked the bare selector, so the
  sticky one kept winning; the mobile rule now matches that specificity.
  Scrolled content takes matching clearance from one shared variable. Measured
  zero occlusion at all three widths.
- **Responsive collapse.** Coaching columns, "Why this works", Interview AI
  source cards, the three-action rows and the History stats were each pinned to
  three or four fixed tracks at every width -- about 97px per coaching column on
  a 390px phone. Two carried a second, higher-specificity authenticated rule
  that silently overrode the first fix; only re-measuring caught that.
- **Phone composer.** Compact mic and a 48px circular send inside the answer
  box. The visible word is dropped at phone width, never the accessible name.
- **Live dictation.** A second element carried the same hook as the in-composer
  transcript; since the JS resolves it with `querySelector`, the duplicate could
  never update and would have stolen the binding if the order changed.
- **Model answer.** A post-review "See a strong answer + why it works" action,
  entitlement-gated, on the same reviewed question. It is an anchor to the
  existing Interview AI surface: no new AI call, no new claim, and it never
  replaces or saves the member's answer. A test asserts the absence of fetch,
  storage writes and answer mutation on that path.

**Verified** through the real client flow at 390x844, 768x1024 and 1440x900:
first and second submission, review, improve, revised review, next question,
every AI source mode, History, no horizontal overflow, correct focus, clean
console. Flag-off anonymous HTML byte-identical. 367 focused tests pass; four
Community tests fail identically on a checkout without these changes.

### A repo-wide blocker fixed along the way

Every pull request was failing the secret scan. It was not this lane: a
pipeline run against a branch containing unmodified `main` and nothing else
failed identically. Commit `423e64f0` had entered history carrying Profile test
fixtures whose keyword arguments match `generic-api-key` on the *shape* of a
key assignment; no credential is involved. The merge that carried it used
`[skip ci]`, so no build ever scanned it.

Deleting the files could not clear it -- they are already gone from `main` and
the pipeline scans full history -- so two allowlist entries were added, scoped
by rule, exact path and exact line, never commit-pinned.

Two things are worth remembering from that repair:

1. **The allowlist can become its own finding.** Written out in full, the
   patterns were themselves key-shaped assignments in files that are also
   scanned. Both now use a character class where the identifier would appear
   verbatim, which breaks the run of value characters the rule needs.
2. **A working-tree fix cannot clear a history finding.** Correcting the file
   left the bad lines in the earlier commit, so the scan still failed; the
   branch had to be collapsed to a single clean commit. For the same reason, a
   pull request that has been force-pushed can still fail on its own superseded
   iterations -- a fresh pull request on the clean commit was the fix.

### Honest limits

The signed-in walk on production is Pete's; the flow was proven in a scripted
browser at all three widths against the same code. The lane remains active.


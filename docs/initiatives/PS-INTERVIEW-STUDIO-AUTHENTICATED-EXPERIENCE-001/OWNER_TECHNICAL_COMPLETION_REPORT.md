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

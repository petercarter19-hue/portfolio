# PS-AUTH-JOURNEY-REPAIR-001 - Technical completion report

## Core record

- **Task/package and delivery path:** PS-AUTH-JOURNEY-REPAIR-001 / Protected.
- **Outcome:** The implemented release separates absent, invalid, and unmapped
  trusted identities; uses a principal-only checkpoint/session probe; adds
  non-looping recovery, fixed-target opt-in canonical-host behavior, and safe
  rendered account-control reconciliation.
- **Branch/base/rebase status:** The original implementation branch
  `codex/2026-08-02-auth-journey-repair-001` was rebased onto Azure DevOps
  `origin/main` `97d008919d285b17e510212701db76543215f5d0`. The six-commit auth series was
  replayed patch-equivalently as `fb11c55`, `f045c94`, `161df33`, `548fe07`,
  `15c93bf`, and `9022951`. The first independent review found three blockers
  and one non-blocking finding; all four were remediated, and the prior corrected SHA
  `a2b3470b7c840ec533f1391f8af1e0f13e4c8af9` passed with no findings. Exact
  independent review of the prior rebased application patch
  `ba6cc4a706c84edaf788dd08c0dd72a2eed8edd1` also passed with no findings.
  Candidate 338 passed the prior exact SHA
  `ec6c2d8d63ca3660fdf07bd36e22b5f15e091194`, but promotion stopped when main
  advanced. The scanner-corrected main then advanced the base again; no
  Candidate result was then claimed for that newer rebased branch tip. This
  historical pending state is superseded by Candidate 348, which passed all
  Candidate stages and stopped the Candidate resource for exact source
  `39fad9f53555743c8112cc20056110af3c2a4497` (artifact content-hash prefix
  `4134b55c`). The subsequent package PR 242 squash is `origin/main`
  `9696fa6481dac6f33fd01ab582a8c610b6541327`. After PR 243's accepted
  public-header CSS repair advanced `origin/main` to
  `3485675387b22307b5e43768782fb416c9212a22`, this narrow authority update
  was replayed patch-equivalently on
  `codex/2026-08-02-auth-alias-scope` from that exact current base.
- **Changed paths:** `identity.py`, `app.py`, `auth_routes.py`,
  `templates/base.html`, `templates/auth_recovery.html`,
  `static/js/easy-auth-callback.js`, `static/js/auth-state.js`, focused
  auth/identity/edge/Control Room/JS tests, `tests/test_auth_release_template.py`,
  and this package record. The narrow authorization correction also changes `owner_authorization.py` and
  `tests/test_control_room.py`; the recovery template now preserves the base
  page's single main landmark. The post-PR-243 evidence correction changes
  `tests/test_owner_home.py` only: it proves the inherited shared stylesheet
  token returns the prior golden before the existing callback-token proof.
  No database, pipeline, shared governance, or Owner Home runtime
  template/CSS/service file changed in this lane.
- **PR 246 integration disposition:** After the narrow authority refresh,
  authoritative `origin/main` advanced through Azure PR 246 to
  `58d95723d42103be95ee51b3e85a22c0be5bcb63`. Its Owner Home golden-test
  repair conflicted only in comments and constant naming, so the auth branch
  merged that main commit as `0096f080c1113a19c1c954044c0f0e9b5d185d9c`
  and resolved `tests/test_owner_home.py` to the exact main blob
  `ae26d299e97e9b99d0e365d2e037d0b6e9622ce6`. That inherited test is not an
  auth-lane change relative to main. PR 246 also added a Candidate-manifest
  task skip that is corrected separately under `PS-OPS-001`; it does not
  alter this package's runtime, auth, production, or canonical-cutover truth.
- **Release state:** Package PR 242 subsequently merged to
  `9696fa6481dac6f33fd01ab582a8c610b6541327`. Candidate 348 passed all
  Candidate stages for exact source
  `39fad9f53555743c8112cc20056110af3c2a4497`, recorded artifact content-hash
  prefix `4134b55c`, and stopped the Candidate resource. Production pipeline
  run 349 passed; production `/healthz` returned `ok` with release
  `5857d7f6a264f9e104d42a3a`. These supersede the earlier pending-Candidate
  statements below. They are not owner credential acceptance or a
  canonical-cutover claim. This authority update makes no production
  configuration, Entra callback, DNS, or binding change.
- **Azure pre-cutover record:** observed sign-in evidence is 17 exchanges in
  18 seconds ending `AADSTS50196`; the app registration has three host-scoped
  callbacks, the Easy Auth cookie is 8 hours with 72-hour grace, and no
  Conditional Access policy is present. This is staging evidence only, not
  owner credential acceptance or a release claim. Session duration and
  `offline_access` remain unchanged for the initial cutover.
- **Verified live alias scope (2026-08-02):** the only alternate sign-in
  surfaces are
  `peerslate-pete-d9hhdeerd7frg2gc.centralus-01.azurewebsites.net` and
  `pete.peerslate.com`; `peerslate.com` is the canonical destination.
  `www.peerslate.com` has no DNS record, App Service binding, or Entra callback
  and is not part of the current cutover. Existing code/tests remain
  future-safe for `www`, but a future owner-authorized introduction must first
  provide DNS, App Service binding/TLS, and proven canonical behavior before
  use or callback registration.
- **Deferred external findings:** malformed optional Microsoft-account provider
  behavior and same-email admin/customer behavior need provider or
  administrator changes, so they remain outside this package. No secret or
  full app-settings dump is committed.

## Verification

- `C:\\Users\\peter\\Documents\\portfolio\\venv\\Scripts\\python.exe -m py_compile
  app.py identity.py auth_routes.py owner_authorization.py` - Pass.
- Focused Python tests (`tests/test_auth.py`, `tests/test_identity.py`,
  `tests/test_http_edge_security.py`, `tests/test_control_room.py`) - Pass:
  133 tests, 177 subtests.
- Independent corrected-SHA review - Pass with no findings on
  `a2b3470b7c840ec533f1391f8af1e0f13e4c8af9`: 158 focused tests and
  `git diff --check` passed. Mocked native Azure CLI failure, empty JSON,
  malformed JSON, and valid JSON cases confirm the staged template helpers
  stop before mutation or evidence writing when required.
- Independent prior rebased-SHA review - Pass with no findings on
  `ba6cc4a706c84edaf788dd08c0dd72a2eed8edd1`. Rebased local validation passed
  350 focused tests, 1 skipped, and 310 subtests; both Node behavioral suites
  passed 6 + 4 checks; compile and `git diff --check` passed; and the full
  Python suite passed 1,386 tests, 4 skipped, and 778 subtests.
- Scanner-corrected rebase validation - Pass: 390 focused tests, 1 skipped,
  and 340 subtests across auth, identity, HTTP edge, Control Room, Owner Home,
  Workshop, and governance coverage. Both Node behavioral suites passed 6 + 4
  checks; Python compile plus working-tree and final-range `git diff --check`
  passed.
- Bundled Node runtime
  (`C:\\Users\\peter\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\bin\\node.exe`)
  syntax checks for both auth scripts plus `tests/easy_auth_callback.test.js`
  and `tests/auth_state.test.js` - Pass: 6 + 4 behavioral checks.
- Full Python suite before the scanner-corrected rebase - Pass: 1,386 passed,
  4 skipped, 778 subtests (19 pre-existing/non-blocking warnings reported by
  the suite). Candidate 348 subsequently ran its required Candidate path for
  exact source `39fad9f53555743c8112cc20056110af3c2a4497` and passed all
  Candidate stages; this historical full-suite entry is not a separate current
  Candidate claim.
- PowerShell parser validation - Pass: all four staged Azure-template blocks
  parse without syntax errors; every native Azure CLI and curl invocation is
  routed through a helper with an immediate LASTEXITCODE check.
- Alias-scope/Graph-template regression - Pass: offline checks in
  `tests/test_auth_release_template.py` lock the pinned External ID tenant,
  exact production Easy Auth client/issuer preflight, in-memory-only token
  handling, exactly-one Graph app resolution, exact pre-mutation host/callback
  inventories (including callback casing), a same-snapshot pre-reduction
  full-web drift check, supported-field-only web PATCH/fresh verification, a
  mocked 204 No Content PATCH path with Windows PowerShell basic parsing, and
  literal `www` callback matching. The four
  PowerShell blocks also parse and the matcher accepts `www.peerslate.com`
  while rejecting wildcard lookalikes.
- Manager local in-process performance evidence (not live network): 300
  requests each gave sign-in median/p95 of 0.326/0.577 ms, completion
  0.316/0.513 ms, and session 0.296/0.431 ms; identity mapping made 0 database
  calls across all 900 requests.
- Locked flag-off `/app` regression proof: the prior evidence verified the
  baseline render at exactly 18,214 bytes. The auth callback content token
  changed the direct body hash from `37fc9260...` to `92adb278...`. PR 243's
  accepted shared `style.css` public-header repair then changed only its
  rendered fixed-width asset token from `62c0e8511b80` to `0b1b477c07af`,
  producing current hash
  `f581cee9de570e46a308c5b85021fa4ca7c577df0e887ce0c9010c00757fed5f`.
  Run 350 stopped before deployment solely because two shared `/app` golden
  assertions still expected the pre-PR-243 value. The correction in
  `tests/test_owner_home.py` asserts the current token occurs once, normalizes
  it to reproduce exact `92adb278...`, then performs the existing callback
  normalization to reproduce exact `37fc9260...`. No Owner Home markup,
  layout, destination, or control semantics changed.
- Current local authority/golden validation - Pass: the shared-golden modules
  (`tests/test_owner_home.py` and
  `tests/test_community_journal_home_milestone.py`) passed 34 tests and 23
  subtests; the focused auth/sign-in/navigation/owner set passed 153 tests and
  235 subtests; and `python -m unittest discover -s tests` passed 1,398 tests
  with 4 skipped. The four PowerShell template blocks parse and `git diff
  --check` passes. The independent review that identified documentation-truth
  blockers is pending again against the amended local SHA; this record makes
  no independent-review PASS claim for that amended SHA.
- Base-sync validation: `97d0089` contains the scanner correction, unrelated
  Workshop CSS/templates, governance/tests, and documentation/visual-authority
  records; it has no auth path overlap. The scanner correction narrowly
  allowlists verified historical false positives and is preserved unchanged.
  The six-commit rebase applied cleanly and `git range-diff` reports every
  replayed auth commit patch-equivalent. The earlier W2 Blueprint registration,
  default-off session flag, and rate limits remain alongside the reviewed auth
  imports, canonical-host controls, private principal cache handling, and
  recovery handlers; no incoming unrelated path appears in the final auth diff
  against the new base.
- Candidate run 335 (`20260802.11`) at pre-rebase
  `efd0e264e936edb815260d8c6a08c2cec63d3c21` built successfully; production
  stages were skipped. `CandidateDeploy` and `CandidateStop` failed solely
  with `ResourceNotFound` because the authorized temporary Candidate app and
  plan had been removed; `CandidateSmoke` was skipped. This is diagnostic
  evidence only, not a Candidate gate pass.
- The authorized temporary Linux Basic B1 plan
  `ASP-peerslate-candidate` and Python 3.14 Web App `peerslate-candidate` were
  recreated separately with TLS 1.2, only the default hostname, exactly the
  two approved inert app-setting names, no connection strings, managed
  identity, App Service authentication, or custom domain. Production remained
  Running. Candidate 348 subsequently passed all Candidate stages and left the
  Candidate app `Stopped`, pending canonical cutover and owner credential
  acceptance; then the temporary resources may be cleaned up through the
  authorized release closeout.
- Candidate run 337 (`20260802.13`) targeted a stale pre-rebase SHA. Its Build
  was canceled when main advanced; production deploy/smoke and
  `CandidateDeploy`/`CandidateSmoke` were skipped, while `CandidateStop`
  succeeded. No deployment occurred. Main build 336 for `803b34b` succeeded
  and its live health was good; that main evidence is not an auth Candidate
  gate pass.
- Historical Candidate run 338 passed exact pre-rebase
  `ec6c2d8d63ca3660fdf07bd36e22b5f15e091194`. Promotion stopped when
  `origin/main` advanced to `efb0b5f846a87ac8132e8d5b90dca628b040ac1e`; no
  PR, merge, deployment, or live claim followed. This does not claim a
  Candidate pass for the then-current rebased branch tip. The intervening
  scanner-corrected main squash is
  `97d008919d285b17e510212701db76543215f5d0`. This historical pending state is
  superseded by Candidate 348: exact source
  `39fad9f53555743c8112cc20056110af3c2a4497`, artifact content-hash prefix
  `4134b55c`, all Candidate stages passed, and the Candidate resource stopped.
- `git diff --check` and complete-diff self-review are recorded after final
  documentation and workspace-cleanliness verification.

## Protected additions

- **Identity/privacy contract:** no trusted header is anonymous unless it is
  genuinely absent; malformed and mapping-failed sessions remain distinct and
  render generic private/no-store recovery without claims or error detail.
- **Owner-route non-exposure:** a valid but unmapped principal now follows the
  same neutral 404 path as a mapped non-owner or storage failure on both
  Control Room routes; no route, JSON, or dashboard distinction is exposed.
- **Recovery accessibility:** the recovery panel no longer adds a nested main
  landmark or duplicate main-content id; its render is covered by the focused
  auth test.
- **Release/rollback:** `THREAT_AND_ROLLBACK.md` records the required staged
  Azure forward order, fail-fast sanitized temporary evidence templates, and
  the exact rollback order: restore and verify callback web object first, then
  restore the prior presence/value of both canonical settings before any prior
  artifact. The forward template dynamically inventories the direct Azure
  hostname and fails fast unless it and `pete.peerslate.com` are bound; it also
  records and rejects an unexpected `www` binding or callback.
- **Independent review:** the first review of
  `7868fd820967e1bd09b1c47b2e34f9130ea528ee` found three blockers plus one
  non-blocking finding. The correction commit
  `a2b3470b7c840ec533f1391f8af1e0f13e4c8af9` remediated all four and passed a
  fresh independent review with no findings. The patch-equivalent rebase
  `ba6cc4a706c84edaf788dd08c0dd72a2eed8edd1` also passed independent review
  with no findings. Candidate 338 passed only the prior exact
  `ec6c2d8d63ca3660fdf07bd36e22b5f15e091194` before promotion stopped at the
  main advance; its then-current pending state is superseded by Candidate 348
  for exact source `39fad9f53555743c8112cc20056110af3c2a4497` (artifact
  content-hash prefix `4134b55c`), which passed all Candidate stages and
  stopped the Candidate resource. Protected canonical configuration and owner
  credential acceptance remain separate; PR 242 is already merged.

## Known limits and next action

No canonical-cutover configuration change is authorized or claimed by this
authority update. Next: the manager may stage the two canonical settings only
through the updated fail-fast template, test exactly the two verified aliases,
and retain the exact callback rollback gate. `www.peerslate.com` remains out of
scope unless a separately authorized future slice first binds and canonicalizes
it. This writer does not queue a deployment or alter Azure/Entra/DNS.

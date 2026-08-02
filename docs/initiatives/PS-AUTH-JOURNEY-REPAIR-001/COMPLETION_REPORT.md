# PS-AUTH-JOURNEY-REPAIR-001 - Technical completion report

## Core record

- **Task/package and delivery path:** PS-AUTH-JOURNEY-REPAIR-001 / Protected.
- **Outcome:** Local implementation separates absent, invalid, and unmapped
  trusted identities; uses a principal-only checkpoint/session probe; adds
  non-looping recovery, fixed-target opt-in canonical-host behavior, and safe
  rendered account-control reconciliation.
- **Branch/base/rebase status:** `codex/2026-08-02-auth-journey-repair-001`,
  rebased onto Azure DevOps `origin/main`
  `97d008919d285b17e510212701db76543215f5d0`. The six-commit auth series was
  replayed patch-equivalently as `fb11c55`, `f045c94`, `161df33`, `548fe07`,
  `15c93bf`, and `9022951`. The first independent review found three blockers
  and one non-blocking finding; all four were remediated, and the prior corrected SHA
  `a2b3470b7c840ec533f1391f8af1e0f13e4c8af9` passed with no findings. Exact
  independent review of the prior rebased application patch
  `ba6cc4a706c84edaf788dd08c0dd72a2eed8edd1` also passed with no findings.
  Candidate 338 passed the prior exact SHA
  `ec6c2d8d63ca3660fdf07bd36e22b5f15e091194`, but promotion stopped when main
  advanced. The scanner-corrected main then advanced the base again; no
  Candidate result is claimed for this newer rebased branch tip.
- **Changed paths:** `identity.py`, `app.py`, `auth_routes.py`,
  `templates/base.html`, `templates/auth_recovery.html`,
  `static/js/easy-auth-callback.js`, `static/js/auth-state.js`, focused
  auth/identity/edge/Control Room/JS tests, and this package record. The narrow
  authorization correction also changes `owner_authorization.py` and
  `tests/test_control_room.py`; the recovery template now preserves the base
  page's single main landmark. No database, pipeline, shared governance, or
  Owner Home runtime template/CSS/service file changed.
- **Release state:** Candidate 338 passed only for the prior exact SHA above;
  promotion stopped at the main advance. The current exact Candidate run is
  pending. There is no PR, merge, production configuration, deployment, or
  auth live claim.
- **Azure pre-cutover record:** observed sign-in evidence is 17 exchanges in
  18 seconds ending `AADSTS50196`; the app registration has three host-scoped
  callbacks, the Easy Auth cookie is 8 hours with 72-hour grace, and no
  Conditional Access policy is present. This is staging evidence only, not
  owner credential acceptance or a release claim. Session duration and
  `offline_access` remain unchanged for the initial cutover.
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
  the suite). It is intentionally not rerun for this rebase because multiple
  prior full passes exist and the exact Candidate run will execute the full
  suite; this is not a current-Candidate pass claim.
- PowerShell parser validation - Pass: all four staged Azure-template blocks
  parse without syntax errors; every native Azure CLI and curl invocation is
  routed through a helper with an immediate LASTEXITCODE check.
- Manager local in-process performance evidence (not live network): 300
  requests each gave sign-in median/p95 of 0.326/0.577 ms, completion
  0.316/0.513 ms, and session 0.296/0.431 ms; identity mapping made 0 database
  calls across all 900 requests.
- Locked flag-off `/app` regression proof: the prior evidence verified the
  baseline render at exactly 18,214 bytes. The new callback content token
  changes the direct body hash from `37fc9260...` to `92adb278...`; replacing
  only the single rendered `fd13bc50ca97` token with verified baseline token
  `9a8e38ddf7ba` reproduces the prior body byte-for-byte and its exact
  `37fc9260...` SHA-256. `tests/test_owner_home.py` encodes both the current
  golden and that normalization assertion. No Owner Home markup, layout,
  destination, or control semantics changed.
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
  Running. The Candidate app is now `Stopped` pending the next run; neither
  temporary resource is removed until verified production release.
- Candidate run 337 (`20260802.13`) targeted a stale pre-rebase SHA. Its Build
  was canceled when main advanced; production deploy/smoke and
  `CandidateDeploy`/`CandidateSmoke` were skipped, while `CandidateStop`
  succeeded. No deployment occurred. Main build 336 for `803b34b` succeeded
  and its live health was good; that main evidence is not an auth Candidate
  gate pass.
- Candidate run 338 passed exact pre-rebase
  `ec6c2d8d63ca3660fdf07bd36e22b5f15e091194`. Promotion stopped when
  `origin/main` advanced to `efb0b5f846a87ac8132e8d5b90dca628b040ac1e`; no
  PR, merge, deployment, or live claim followed. This does not claim a
  Candidate pass for the current rebased branch tip. The intervening
  scanner-corrected main squash is
  `97d008919d285b17e510212701db76543215f5d0`; the current exact Candidate run
  remains pending.
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
  artifact.
- **Independent review:** the first review of
  `7868fd820967e1bd09b1c47b2e34f9130ea528ee` found three blockers plus one
  non-blocking finding. The correction commit
  `a2b3470b7c840ec533f1391f8af1e0f13e4c8af9` remediated all four and passed a
  fresh independent review with no findings. The patch-equivalent rebase
  `ba6cc4a706c84edaf788dd08c0dd72a2eed8edd1` also passed independent review
  with no findings. Candidate 338 passed only the prior exact
  `ec6c2d8d63ca3660fdf07bd36e22b5f15e091194` before promotion stopped at the
  main advance; the scanner-corrected rebase has no current Candidate pass
  claim. Protected release/PR acceptance remains separate.

## Known limits and next action

No production change is authorized or claimed. Next: current exact Candidate
run after the manager's explicit release-path decision. This writer does not
queue it.

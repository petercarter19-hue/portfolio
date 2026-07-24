# PS-AUTH-SQL-WAKE-001 — Owner technical completion report

## 1. Executive result

Implementation, Azure release, and production cold-resume verification are
complete for the Azure SQL serverless wake-up failure reproduced after a
successful Microsoft Entra External ID sign-in. PeerSlate retries only SQL
connection establishment and presents an honest temporary workspace state if
secure identity storage remains unavailable. The live retry then returns the
signed-in member to the private owner workspace after storage is online.

## 2. Authority, base, and ownership

- Owner authorization: Pete Carter, 2026-07-23, selected option 1.
- Manager and sole writer: the current Codex session.
- Authoritative repository: Azure DevOps `origin`.
- Base branch and SHA:
  `origin/main` at `e8bbc3bf6df17db9f117be08573d121d9b650969`.
- Task branch: `work/2026-07-23-auth-sql-wake-001`.
- Worktree:
  `C:\Users\peter\Documents\portfolio-auth-sql-wake-001`.
- Implementation source commit:
  `908fd3726e935c3b20d2d7512f80a809638b7338`.
- Release source tip:
  `6fd5c037477e7e2fd1531eada413595584489b22`.
- Azure PR: 166.
- Azure squash-merge commit:
  `7ebab4de77be874f79abf93cb58dbd254c98e61d`.
- No other worktree, branch, file, or artifact was changed.

## 3. Changed files

| File | Reason |
|---|---|
| `db.py` | Add two-attempt, connection-only serverless wake-up recovery with privacy-safe logging. |
| `auth_routes.py` | Distinguish authenticated identity-storage failure from provider misconfiguration and prevent a duplicate lookup during error rendering. |
| `templates/base.html` | Show a truthful workspace-waking account control when a trusted signed-in request cannot resolve identity storage. |
| `templates/identity_storage_unavailable.html` | Provide the private no-store 503 recovery state and explicit retry. |
| `tests/test_db.py` | Prove bounded connect retry, timeout, missing configuration, and exhausted failure behavior. |
| `tests/test_database_service.py` | Prove stored-procedure execution errors are never retried. |
| `tests/test_auth.py` | Prove `/app` and `/auth/session` truth, headers, copy, and single identity lookup. |
| `docs/initiatives/PS-AUTH-SQL-WAKE-001/README.md` | Record authority, scope, runtime contract, visual authority, and acceptance. |

## 4. Trust and resilience review

- Identity remains server-derived from the trusted App Service Easy Auth
  principal.
- No browser identity, user identifier, credential, or connection string is
  logged or persisted.
- The retry boundary ends before `cursor()` or procedure execution; no query or
  mutation can be replayed by this change.
- The private failure response is 503, `private, no-store`, and carries a
  bounded `Retry-After` hint.
- The real authentication-configuration fallback remains separate and
  unchanged.
- Azure SQL auto-pause, capacity, schema, procedures, and data are unchanged.

## 5. Verification evidence

All commands use a process-local non-secret
`ANTHROPIC_API_KEY=test-key-for-ci-only` placeholder where required.

| Check | Result |
|---|---|
| `python -m unittest tests.test_db tests.test_database_service tests.test_auth tests.test_identity -q` | Pass — 33 tests. |
| Repository suite, `test_[a-h]*.py` | Pass — 258 tests, 1 expected skip. |
| Repository suite, `test_[i-k]*.py` | Pass — 226 tests. |
| Repository suite, `test_[l-p]*.py` | Pass — 324 tests, 2 expected skips. |
| Repository suite, `test_[q-z]*.py` | Pass — 98 tests. |
| Complete Python total | Pass — 906 tests, 3 expected skips, no failures. |
| `git diff --check` and complete-diff self-review | Pass. |
| In-app real-browser semantic verification | Pass — live `/app` rendered “Your private workspace is waking up,” identified the request as signed in, exposed one “Try again” link, and did not present the configuration-error copy. |
| Azure DevOps pipeline 227, build `20260724.4` | Pass — Build and Deploy both succeeded for exact merge `7ebab4de77be874f79abf93cb58dbd254c98e61d`. |
| Azure SQL serverless activity evidence | Pass — the database auto-pause operation started and succeeded at `2026-07-24T01:47:08Z`; no auto-pause, capacity, schema, or data setting was changed by this package. |
| Production `/app` recovery | Pass — the live “Try again” action loaded `My PeerSlate`, “Welcome, Pete Carter,” Account `Signed in`, and Default audience `Private`; database status was then `Online`. |

## 6. Visual, accessibility, and homepage parity

Visual authority is the released account-state panel in
`templates/auth_unavailable.html` with `static/css/owner-app.css`. The new state
uses the same semantic `<main>`, labelled `<section>`, heading hierarchy, and
keyboard-operable links. There is no motion. Copy distinguishes successful
sign-in from temporary private-storage availability, and both retry and safe
home navigation remain available.

The shared account control retains its released class and dimensions while
changing only the temporary label. The public homepage layout, content, assets,
and product demonstration are unchanged, so no homepage parity implementation
is required.

## 7. Release status

| Gate | Status |
|---|---|
| Local implementation | Complete |
| Local self-review | Complete |
| Azure DevOps branch push | Complete |
| Azure DevOps pull request and squash merge | Complete — PR 166 |
| Exact-commit pipeline build/deploy | Complete — pipeline 227 / `20260724.4` |
| Production signed-in verification | Complete |
| Natural cold-resume observation | Complete — activity-log pause, truthful 503 recovery state, successful retry |

## 8. Remaining risks and decisions

- A serverless resume can take about one minute. Two 60-second connection
  attempts remain within the platform request boundary, but an unusually slow
  resume can still reach the truthful 503 state and require the explicit retry.
- The first production checks briefly returned the known App Service restart
  404 after deployment. The same routes recovered without code or
  configuration changes before acceptance testing proceeded.
- Azure's activity log independently recorded the natural auto-pause used for
  production acceptance. No manual pause or database reconfiguration was used.
- The in-memory Flask-Limiter warning in local tests is pre-existing and outside
  this bounded package.
- GitHub mirror updates remain on hold under the current baseline.

## 9. Truth labels

- Connection-only wake-up retry: **implemented, locally verified, deployed,
  and exercised by the live cold-resume request**.
- Workspace-waking state: **implemented, deployed, and observed in
  production**.
- Azure SQL serverless configuration: **unchanged**.
- Azure deployment: **live through PR 166 and pipeline 227**.
- Natural production cold-resume acceptance: **passed**.

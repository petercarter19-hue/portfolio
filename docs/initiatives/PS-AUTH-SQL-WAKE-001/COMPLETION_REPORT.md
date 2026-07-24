# PS-AUTH-SQL-WAKE-001 — Owner technical completion report

## 1. Executive result

Implementation and local verification are complete for the
Azure SQL serverless wake-up failure reproduced after a successful Microsoft
Entra External ID sign-in. PeerSlate now retries only SQL connection
establishment and presents an honest temporary workspace state if secure
identity storage remains unavailable.

This report does not describe the change as deployed or live until the Azure
DevOps merge, exact-commit pipeline, and production verification sections are
complete.

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
- Azure squash-merge commit: pending.
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
| Real-browser visual automation | Not run — the Playwright skill's required `npx` launcher is not installed; semantic render assertions and exact copy/header checks passed. |
| Azure DevOps Build and Deploy | Pending. |
| Production `/app` signed-in verification | Pending. |

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
| Azure DevOps branch push | Pending |
| Azure DevOps pull request and squash merge | Pending |
| Exact-commit pipeline build/deploy | Pending |
| Production signed-in verification | Pending |
| Natural cold-resume observation | Pending; cannot be forced without changing live database configuration |

## 8. Remaining risks and decisions

- A serverless resume can take about one minute. Two 60-second connection
  attempts remain within the platform request boundary, but an unusually slow
  resume can still reach the truthful 503 state and require the explicit retry.
- A deterministic test proves the cold-start contract. A natural production
  auto-pause/resume observation remains separate because this package is not
  authorized to pause or reconfigure the live database.
- The in-memory Flask-Limiter warning in local tests is pre-existing and outside
  this bounded package.
- GitHub mirror updates remain on hold under the current baseline.

## 9. Truth labels

- Connection-only wake-up retry: **implemented and locally verified**.
- Workspace-waking state: **implemented and locally verified**.
- Azure SQL serverless configuration: **unchanged**.
- Azure deployment: **pending**.
- Natural production cold-resume acceptance: **pending**.

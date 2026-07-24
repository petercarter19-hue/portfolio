# PS-AUTH-CALLBACK-001 — Owner technical completion report

## 1. Executive result

Implementation and local verification are complete for the Entra External ID
callback transition defect reproduced on 2026-07-23. The change prevents an
opaque Easy Auth `#token=` return from leaving stale pre-sign-in content on a
private PeerSlate route. It removes the fragment without parsing, logging,
storing, or using its value and requests the clean route once so App Service
Easy Auth can supply trusted server-side identity headers.

This report records implementation completion. Azure DevOps merge, deployment,
and a fresh owner sign-in remain release gates and must be recorded externally
before the capability is described as live.

## 2. Authority, base, and ownership

- Owner authorization: Pete Carter, 2026-07-23, “do everything please.”
- Manager and sole writer: the current Codex session.
- Authoritative repository: Azure DevOps `origin`.
- Base branch and SHA:
  `origin/main` at `e2c084c8d701936684cd9267d672dbb439bba62d`.
- Task branch: `work/2026-07-23-auth-callback-hardening-001`.
- Implementation commit:
  `2cbc6f89ab6ac4470cf772a346f1220f60cba9d3`.
- Worktree:
  `C:\Users\peter\Documents\portfolio-auth-callback-hardening`.
- No other active writer’s worktree, branch, file, or artifact was changed.

## 3. Changed files

| File | Reason |
|---|---|
| `static/js/easy-auth-callback.js` | Detect the callback prefix at initial load, `hashchange`, and back/forward-cache `pageshow`; discard the opaque fragment and reload the clean private route. |
| `templates/base.html` | Load the guard before page scripts on `/app`, `/app/*`, and `/auth/*` only. Public pages remain unchanged. |
| `tests/easy_auth_callback.test.js` | Exercise initial, delayed, cache-restored, unrelated-fragment, and History API fallback behavior. |
| `tests/test_auth.py` | Prove early private-route inclusion and public-home exclusion while retaining the existing auth/security contract. |
| `tests/test_owner_home.py` | Recapture the exact authorized private `/app` shell bytes and hash for the one added script element. |
| `docs/initiatives/PS-AUTH-CALLBACK-001/README.md` | Record authority, scope, production evidence, implementation contract, and acceptance gates. |

## 4. Contract and trust review

- The callback value is opaque. The application does not parse, decode, log,
  persist, transmit, or use it as identity.
- The clean reload preserves only `pathname` and `search`; the entire fragment
  is removed from the current history entry.
- Identity remains server-derived from the trusted App Service Easy Auth
  header. No browser-provided identity or user identifier was added.
- Unrelated URL fragments are untouched.
- The code is dependency-free and useful when AI is unavailable.
- No secret, identity-provider setting, database, migration, feature flag,
  public design, or shared governance pointer changed.

## 5. Verification evidence

All commands used a process-local non-secret
`ANTHROPIC_API_KEY=test-key-for-ci-only` placeholder where required.

| Check | Result |
|---|---|
| Bundled Node on `tests/easy_auth_callback.test.js` | Pass — 5 behavioral checks. |
| `python -m unittest tests.test_auth tests.test_identity -q` | Pass — 17 tests. |
| Repository suite, `test_[a-h]*.py` | Pass — 252 tests, 1 expected skip. |
| Repository suite, `test_[i-k]*.py` | Pass — 226 tests. |
| Repository suite, `test_[l-p]*.py` | Pass — 324 tests, 2 expected skips. |
| Repository suite, `test_[q-z]*.py` | Pass — 98 tests. |
| Complete Python total | Pass — 900 tests, 3 expected skips, no failures. |
| `git diff --check` and cached diff check | Pass. |

The first combined `test_[i-p]*.py` invocation printed its successful
550-test summary but the terminal wrapper reached its 60-second limit before
returning the process status. The same set was immediately rerun as
`test_[i-k]*.py` and `test_[l-p]*.py`; both returned exit code 0 and together
ran the same 550 tests.

## 6. Visual, accessibility, and homepage parity

This change adds no visible control, copy, layout, color, focus behavior, or
motion. Its only visible effect is replacing stale pre-sign-in content with
the server’s current authenticated or unavailable state. The script is
restricted to private account/auth routes, and the automated home response
check proves the public homepage does not include it. No new visual acceptance
gate is introduced.

## 7. Release status

| Gate | Status |
|---|---|
| Local implementation | Complete |
| Local self-review | Complete |
| Azure DevOps branch push | Pending |
| Azure DevOps pull request and squash merge | Pending |
| Main pipeline build/deploy | Pending |
| Production static asset and route verification | Pending |
| Fresh owner sign-in and callback verification | Pending owner credential interaction |

## 8. Remaining risks and decisions

- A fresh production sign-in must prove that the real Microsoft callback
  clears the fragment and reaches the private workspace without a manual
  refresh. That is the release acceptance gate, not an assumption from local
  tests.
- Because callback material appeared in user-provided evidence, the existing
  browser session should be signed out after deployment and replaced by the
  fresh acceptance session.
- The existing fallback copy for a true storage outage is outside this bounded
  callback package and was not changed.
- GitHub mirror updates remain governed by the current baseline and are not
  part of this Azure publishing path.

## 9. Truth labels at implementation handoff

- Callback guard: **implemented and locally verified**.
- Entra External ID provider: **production-connected, verified read-only during
  diagnosis**.
- Signed-in owner workspace: **production-connected and observed before this
  code change**.
- Callback guard in production: **not yet deployed**.
- Fresh post-deployment sign-in acceptance: **pending**.

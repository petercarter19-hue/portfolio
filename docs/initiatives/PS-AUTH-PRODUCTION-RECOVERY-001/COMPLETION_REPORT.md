# PS-AUTH-PRODUCTION-RECOVERY-001 - completion record

## Core record

- Task/package and delivery path: `PS-AUTH-PRODUCTION-RECOVERY-001`, Protected
  production investigation and recovery; documentation-only repository
  reconciliation after current runtime/configuration passed.
- Outcome and member/site effect: PeerSlate is reachable at its apex and Azure
  hostname, the owner sign-in/session journey passes, the corrected issuer and
  hosted branding remain exact, redundant historical auth work was cleaned up,
  and current deployment truth replaces stale baseline pointers. No runtime or
  identity setting was changed.
- Branch and base SHA:
  `work/2026-08-03-auth-production-recovery-001` from
  `05f0c228404655d63d5c1ddbbc0a3c2d1d54491e`. The exact final branch and
  Azure squash-merge SHAs are recorded in the PR and final handoff because a
  commit cannot contain its own hash.
- Changed paths:
  `docs/governance/CURRENT_BASELINE.yaml` for current release truth;
  `tests/test_operational_readiness.py` for the lockstep release-pointer
  contract; `tests/test_governance_pointers.py` for the current baseline date;
  and
  this package for authority, evidence, limits, cleanup, and closeout.
- Verification performed and result: **Pass**. Targeted Azure, Entra Graph,
  DNS, TLS, HTTP, App Service metric/deployment, repository, test, and real
  browser checks described in `README.md` all passed within their stated
  limits. Focused Python result: 101 passed and 54 subtests passed. Full local
  repository result: 1,645 tests ran successfully, with four
  environment-specific skips. The existing Flask-Limiter development-storage
  warning remained.
- Release state: the pre-existing exact runtime is pipeline 388 and is live
  verified. This branch changes documentation/tests only and is intended for a
  `[skip ci]` Azure PR; it makes no new deployed artifact claim.
- Known limits, deferred work, or owner decision needed: hosted password-field
  visuals remain unobserved because SSO reused the account; no new live 390 px
  geometry measurement was possible because the in-app viewport override did
  not apply. The exact live CSS bytes and focused regression contract passed.
- Next action: merge this documentation-only reconciliation through Azure,
  delete its remote task branch, and do not manually redeploy the same runtime
  SHA merely to publish bookkeeping.

## Protected additions

- Identity/security contract changed: **No**.
- Threat/risk review: canonical host, callback inventory, issuer split, trusted
  principal boundary, sign-out, and no-credential handling were rechecked.
- Permission/negative-path evidence: signed-out `/app` remained protected;
  alternate hosts remained canonicalized; one apex callback remained; app and
  publishing credential policies remained fail-closed; no secret or member
  payload was retrieved.
- Migration or rollback: not applicable because no schema, data, application,
  DNS, Entra, or Azure setting changed.

## Plain-English translation

The website and sign-in system are working now. The second manual deployment
reinstalled the exact same code and restarted the live app again, which was
unnecessary and is the most credible reason the site was temporarily hard to
reach. Nothing currently broken justified another restart. The safe cleanup
removed only old, already-released auth worktrees and local branch labels; it
left production, evidence, active work, and user files alone.

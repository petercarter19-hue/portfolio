# PS-AUTH-SQL-WAKE-001 — serverless identity-storage recovery

## Authority and ownership

- Owner authorization: Pete Carter, 2026-07-23, selected option 1 after the
  production sign-in diagnosis: preserve Azure SQL serverless auto-pause and
  add bounded application recovery.
- Manager and sole writer: the current Codex session.
- Authoritative base:
  `e8bbc3bf6df17db9f117be08573d121d9b650969` from Azure DevOps
  `origin/main`.
- Working branch: `work/2026-07-23-auth-sql-wake-001`.
- Writable scope:
  - connection establishment in `db.py`;
  - the `/app` and `/auth/session` identity-storage unavailable states;
  - the existing shared account control only where needed to avoid presenting
    a second sign-in action to an already authenticated member;
  - focused tests and this package's evidence.
- Forbidden scope: Azure SQL service-tier, capacity, or auto-pause changes;
  identity-provider settings; schemas or migrations; stored procedures;
  secrets; Owner Home feature-flag behavior; homepage design; shared
  governance pointers; and unrelated active lanes.

## Reproduced production condition

Microsoft Entra External ID and App Service Easy Auth successfully authenticated
the owner and forwarded the trusted server principal to Flask. During the same
request, Azure SQL serverless was waking from an automatic pause. The identity
mapping connection failed, `/app` returned 503, and the generic authentication
fallback incorrectly said that sign-in was not configured. A later request in
the same browser loaded the private signed-in workspace after SQL was online.

The live database remains General Purpose serverless with a 60-minute
auto-pause delay, 0.5 minimum vCore, and 2 maximum vCores. This package does not
change those settings.

## Implementation contract

1. Retry connection establishment at most once after a one-second delay.
2. Cap each connection attempt at 60 seconds.
3. Never retry a cursor operation, stored procedure, transaction, or mutation.
4. Close a partially prepared connection before retrying.
5. Log only attempt counts and the recovery action, never connection strings,
   identity claims, or private payloads.
6. When trusted identity reached Flask but storage remains unavailable, return
   503 with `Retry-After: 5`, `Cache-Control: private, no-store`, and a truthful
   workspace-waking state.
7. Do not make a second identity lookup while rendering that recovery page.
8. Preserve the existing true configuration-error state and copy.

## Named visual authority

The released `templates/auth_unavailable.html` account-state composition and
`static/css/owner-app.css` are the visual authority. This package adds no new
layout system, color, typography, motion, or navigation layer. It uses the same
panel and control classes with truthful recovery copy and an explicit retry
action. The public homepage is outside scope and unchanged.

## Acceptance

- A transient first connection failure is followed by exactly one connection
  retry, then the successful connection is returned.
- Exhausted attempts propagate the final driver error.
- Procedure execution failures are not retried.
- `/app` renders the workspace-waking state with one identity lookup and no
  misleading sign-in configuration copy.
- `/auth/session` distinguishes authenticated-but-unavailable from signed out.
- Anonymous sign-in and genuine provider-configuration failures retain their
  existing behavior.
- Focused and complete repository tests pass.
- Azure DevOps squash merge, exact-commit deployment, and production route/auth
  verification are recorded before the change is called live.

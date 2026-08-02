# PS-AUTH-JOURNEY-REPAIR-001 — Protected auth/session journey repair

## Authority and ownership

- **Owner authorization:** Pete Carter, “Fix it all,” 2026-08-02.
- **Delivery path:** Protected — trusted identity, session interpretation, and
  shared canonical-host configuration change together.
- **Manager/architect:** current root Codex session.
- **Sole implementation writer:** `codex/2026-08-02-auth-journey-repair-001`
  in `C:\Users\peter\Documents\portfolio-auth-journey-repair-001`.
- **Authoritative base:** Azure DevOps `origin/main`,
  `97d008919d285b17e510212701db76543215f5d0` (rebased 2026-08-02 after
  the scanner-corrected main squash; no auth behavior was changed there).

## Accepted outcome

The application distinguishes three server-side facts instead of presenting
all of them as a signed-out browser:

1. no trusted principal arrived (`AuthenticationRequired`);
2. a trusted Easy Auth principal was malformed or did not satisfy issuer/
   provider validation (`AuthenticationPrincipalInvalid`); and
3. a structurally valid principal did not yield a usable PeerSlate account
   mapping (`IdentityMappingError`).

`PeerSlatePrincipal` is a request-cached, database-free representation of the
trusted principal. The existing stored-procedure mapping runs only from
`get_current_identity()` and only once per request. `/auth/session`, global
header controls, `/auth/sign-in`, and `/auth/complete` therefore do not wake
Azure SQL merely to inspect session state.

The return destination is restricted to a bounded `/app` path. Easy Auth
always returns to `/auth/complete`, which validates only the trusted principal
and redirects once. Missing or invalid sessions render a generic manual
recovery surface; no route in this package redirects a broken session back to
the provider automatically.

The callback guard loads from the shared base on every page and never parses
or stores a callback fragment. Its bounded private bfcache refresh covers
`/app` and `/auth` documents. The separate account-state script is public-only:
it reconciles already-rendered controls through the fixed same-origin
principal-only `/auth/session` response and preserves the server-rendered
state for unavailable, malformed, non-JSON, or unknown responses. It is not
loaded on `/app` or `/auth`, so it cannot duplicate the callback's private
bfcache reload.

## Azure release staging record

This is a release plan and evidence record, not a claim that the cutover has
occurred. The current observed sign-in evidence is 17 exchanges in 18 seconds,
ending in `AADSTS50196`. The current app registration has three host-scoped
callbacks, the Easy Auth cookie lifetime is 8 hours with a 72-hour grace
period, and no Conditional Access policy is present. Session duration and the
`offline_access` permission remain unchanged during this initial cutover.

The required forward order is:

1. Merge and deploy this code while `PEERSLATE_ENFORCE_CANONICAL_HOST` remains
   false.
2. Capture sanitized current app-setting and app-registration web evidence in
   a temporary, operator-local evidence directory.
3. Set `PEERSLATE_CANONICAL_HOST=peerslate.com` and
   `PEERSLATE_ENFORCE_CANONICAL_HOST=true`.
4. Verify alias GET/HEAD requests redirect to the fixed apex target and unsafe
   alias methods are rejected without a `Location` header.
5. Reduce the app-registration callbacks to the owner-approved apex callback
   only, using the captured callback-web object for an exact rollback.
6. Obtain owner credential acceptance before treating the journey as released.

The release templates are fail-fast: every native Azure CLI and curl command
checks its exit status, JSON is parsed and validated before evidence is written,
and callback reduction must leave exactly the approved apex URI. Rollback first
restores and re-verifies the callback web object, then restores the prior
presence and value of both canonical settings (deleting settings that had been
absent), before any prior artifact is restored.

The malformed optional Microsoft-account provider behavior and same-email
admin/customer behavior are recorded findings, not this package's solution.
They require provider or administrator changes and are explicitly deferred.
No secret, full app-settings dump, or credential material belongs in this
package, repository history, screenshots, or release evidence.

## Scope and explicit boundaries

- Keeps Easy Auth as the only provider boundary; no password, OTP, passkey,
  native credential form, token parsing, app cookie, schema, SQL, stored
  procedure, account-keying, or email-linking change is authorized.
- Adds opt-in canonical-host enforcement for `www`, the deployment-provided
  `WEBSITE_HOSTNAME`, and private/authentication paths on `pete.peerslate.com`.
  It uses `request.host`; `X-Forwarded-Host` is not trusted and ProxyFix does
  not enable `x_host`.
- Reuses the released `owner-app.css` panel/control language for the recovery
  state. This is a non-material truthful/reflow adaptation, not new visual
  authority.
- Preserves the released PS-HOME-FRONTEND runtime at `88d6f8f`: Owner Home
  flag selection, `owner-home.v1`, U1/U3 standalone shell, its templates,
  CSS, and service are outside this package. The narrow collision reassignment
  permits only shared auth handling around those routes.
- Does not alter pipeline, production/DNS/custom-domain settings, Workshop,
  Interview, Capture, Journal, Community, résumé, or AI behavior.

## Required evidence

- Principal/header parsing is database-free and request cached.
- Mapping runs once, and a missing mapping cannot be downgraded to anonymous.
- A valid principal with no mapping receives the same neutral Control Room 404
  contract as a mapped non-owner, for both the HTML and JSON-named routes.
- `/auth/session` exposes only `signed_out`, `authenticated`,
  `invalid_session`, or `auth_unavailable` and never uses database storage.
- Return-path, completion, malformed-session, protected-route, host, unsafe
  method, forwarded-host, recovery, callback, and browser-reconciliation
  cases are covered by focused regression tests.
- The final package handoff must include independent review before Protected
  release consideration, a compact completion report, PR/pipeline status, and
  truthful deployment status. This writer is not authorized to commit, push,
  merge, or deploy this work yet.

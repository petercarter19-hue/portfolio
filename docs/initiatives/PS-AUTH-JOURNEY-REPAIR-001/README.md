# PS-AUTH-JOURNEY-REPAIR-001 — Protected auth/session journey repair

## Authority and ownership

- **Owner authorization:** Pete Carter, “Fix it all,” 2026-08-02.
- **Delivery path:** Protected — trusted identity, session interpretation, and
  shared canonical-host configuration change together.
- **Manager/architect:** current root Codex session.
- **Sole implementation writer:** The original application delivery is
  `codex/2026-08-02-auth-journey-repair-001`; the narrow alias-scope authority
  refresh is `codex/2026-08-02-auth-alias-scope`, in
  `C:\Users\peter\Documents\portfolio-auth-journey-repair-001`. Both are the
  same single-writer lane; this refresh changes package evidence and release
  templates only. The post-live issuer evidence correction continues that
  lane on `codex/2026-08-02-auth-issuer-followup` from exact merged main
  `d5fe87bb94118e9aa959524210e2ebe912d2d9d9`; it changes documentation and
  offline release-template tests only.
- **Authoritative base for this post-live evidence slice:** Azure DevOps
  `origin/main`, `d5fe87bb94118e9aa959524210e2ebe912d2d9d9` (PR 252's
  Workshop merge on top of PR 245's verified auth application source
  `aee72312b69d8e5ed915c9c2913389da9ab76dc8`). PR 252 does not overlap this
  package or its release-template test. The earlier authority refresh was
  based on `3485675387b22307b5e43768782fb416c9212a22`; that base is now
  historical. This slice corrects release-template evidence only; it does not
  alter merged application behavior.

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

## Live release and acceptance result

- Azure DevOps PR 245 squash-merged the final application/release-safety
  package to main at
  `aee72312b69d8e5ed915c9c2913389da9ab76dc8`. Production pipeline 373
  (`20260803.23`) passed Build, Deploy, and ProductionSmoke; live `/healthz`
  returned exact release `89f4fc476d70ca5cc3b340ce`.
- The later non-overlapping Workshop PR 252 advanced main to
  `d5fe87bb94118e9aa959524210e2ebe912d2d9d9`. Production pipeline 377
  (`20260803.27`) passed Build, Deploy, and ProductionSmoke; live `/healthz`
  returned its exact release `c606060eb591d8e41dd46424`. The canonical-host
  settings and corrected `PEERSLATE_AUTH_ISSUER` remained exact after that
  deployment.
- The canonical settings are live with `peerslate.com` as the single fixed
  destination. Both the App Service default hostname and
  `pete.peerslate.com` return exact `308` redirects for safe requests and
  `400` without `Location` for unsafe alias requests. The app registration
  now has exactly one callback:
  `https://peerslate.com/.auth/login/aad/callback`.
- The first strict alias check safely rolled back because Azure had persisted
  the settings before recycling the worker. A bounded retry then waited for
  the restarted process and passed on activation attempt 8; no callback
  reduction occurred before alias proof.
- Live browser acceptance exposed a separate pre-existing issuer mismatch.
  Easy Auth correctly uses the custom-domain discovery authority
  `https://peerslatemembers.ciamlogin.com/.../v2.0`, while its live OpenID
  metadata returns the principal issuer
  `https://b6cac548-9b4b-43da-b366-e95be960ec2f.ciamlogin.com/.../v2.0`.
  Production `PEERSLATE_AUTH_ISSUER` incorrectly contained the discovery URL,
  so PeerSlate rejected a Microsoft sign-in that Entra recorded as successful.
  The application setting was corrected to the metadata issuer and the App
  Service was explicitly restarted; Easy Auth's discovery authority was not
  changed.
- The corrected owner session reached `/app` and rendered "Welcome, Pete
  Carter." The complete signed-out `Sign In` click through Microsoft to
  `/app` took 2,921 ms. Refresh, public-site navigation and browser return,
  browser history, and a second tab all retained the authenticated private
  workspace. No agent requested or entered a password, or inspected, copied,
  logged, or stored a token, cookie, or raw principal. Microsoft reused an
  existing SSO session, so password-entry and password-reveal appearance still
  require Pete's own signed-out/private-browser inspection rather than an
  agent-entered credential claim.

## Historical Azure pre-cutover staging record

The following is the pre-cutover release plan and evidence record; the live
result above supersedes it. The observed failing sign-in evidence was 17
exchanges in 18 seconds, ending in `AADSTS50196`. At that time, the app
registration had three host-scoped callbacks, the Easy Auth cookie lifetime
was 8 hours with a 72-hour grace period, and no Conditional Access policy was
present. Session duration and the
`offline_access` permission remain unchanged during this initial cutover.

The verified current alternate sign-in aliases are exactly the App Service
default hostname
`peerslate-pete-d9hhdeerd7frg2gc.centralus-01.azurewebsites.net` and
`pete.peerslate.com`; `peerslate.com` is the fixed canonical destination.
`www.peerslate.com` has no DNS record, App Service binding, or Entra callback
and is outside this cutover. The existing code and regression coverage retain
safe behavior if `www` is introduced later, but a future owner-authorized slice
must first provide DNS, an App Service binding/TLS, and verified canonical GET,
HEAD, and unsafe-method behavior before it can be used or added to callbacks.

The required forward order is:

1. Merge and deploy this code while `PEERSLATE_ENFORCE_CANONICAL_HOST` remains
    false.
2. Capture sanitized current app-setting, Easy Auth client/issuer, hostname,
   and app-registration web evidence in a temporary, operator-local evidence
   directory. Before any Graph token or app lookup, require production Easy
   Auth to match the pinned External ID client ID and issuer/tenant; require
   the App Service binding and callback inventories to be the exact approved
   three-member sets, with no additional host or callback.
3. Set `PEERSLATE_CANONICAL_HOST=peerslate.com` and
   `PEERSLATE_ENFORCE_CANONICAL_HOST=true`.
4. Dynamically enumerate and verify both currently bound aliases (the App
   Service default hostname and `pete.peerslate.com`): GET/HEAD requests must
   redirect to the fixed apex target and unsafe alias methods must be rejected
   without a `Location` header. Stop if either alias is missing or if `www` has
   entered the binding or callback inventory without new authority.
5. Reduce the app-registration callbacks to the owner-approved apex callback
   only, using the captured callback-web object for an exact rollback.
6. Obtain owner credential acceptance before treating the journey as released.

The release templates are fail-fast: every native Azure CLI and curl command
checks its exit status, JSON is parsed and validated before evidence is written,
and callback reduction must leave exactly the approved apex URI while retaining
the other writable Graph `web` fields. Rollback first restores and re-verifies
the full callback web object, then restores the prior
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
- Adds opt-in canonical-host enforcement for the currently bound App Service
  default hostname and private/authentication paths on `pete.peerslate.com`.
  `www.peerslate.com` is not created, bound, or added to Entra in this package;
  its existing code/test protection is retained only as a future-safe guard.
  It uses `request.host`; `X-Forwarded-Host` is not trusted and ProxyFix does
  not enable `x_host`.
- Reuses the released `owner-app.css` panel/control language for the recovery
  state. This is a non-material truthful/reflow adaptation, not new visual
  authority.
- Preserves the released PS-HOME-FRONTEND runtime at `88d6f8f`: Owner Home
  flag selection, `owner-home.v1`, U1/U3 standalone shell, its templates,
  CSS, and service are outside this package. The narrow collision reassignment
  permits only shared auth handling around those routes.
- This authority/golden commit made no production mutation. The separately
  approved live cutover changed
  `PEERSLATE_CANONICAL_HOST=peerslate.com`,
  `PEERSLATE_ENFORCE_CANONICAL_HOST=true`, the Entra app-registration
  callbacks, and corrected `PEERSLATE_AUTH_ISSUER` from the discovery
  authority to the distinct issuer returned by that authority's live OpenID
  metadata. Easy Auth's provider/discovery configuration did not change. DNS,
  custom domains/bindings, identity-provider configuration,
  session/cookie duration, `offline_access`, pipelines, Workshop, Interview,
  Capture, Journal, Community, résumé, and AI behavior remain excluded.

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
  truthful deployment status. The manager explicitly authorized the current
  commit, push, and PR sequence; the writer never merges, deploys, or changes
  production configuration without a further manager instruction.

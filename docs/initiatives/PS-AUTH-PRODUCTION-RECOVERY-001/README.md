# PS-AUTH-PRODUCTION-RECOVERY-001 - production availability and sign-in reconciliation

## Authority and scope

- Owner authorization: Pete Carter, 2026-08-03, asked Codex to resolve the
  inaccessible live site, inspect Azure and PeerSlate behind the scenes,
  verify the improved sign-in experience, catch records up, and remove proven
  trash.
- Delivery path: **Protected investigation and recovery** because production
  identity and shared Azure configuration were inspected. No protected
  configuration or runtime mutation was needed.
- Manager and sole writer: the current root Codex session.
- Branch: `work/2026-08-03-auth-production-recovery-001`.
- Authoritative base: Azure DevOps `origin/main` at
  `05f0c228404655d63d5c1ddbbc0a3c2d1d54491e`.
- Writable repository scope: this package, the release pointers in
  `CURRENT_BASELINE.yaml`, and their exact expectations in
  `tests/test_operational_readiness.py`.
- Runtime scope was read-only unless a current defect was proved. No password,
  token, cookie, raw principal, connection string, member record, or secret was
  requested, printed, stored, or changed.

## Outcome

Production is healthy and the owner sign-in journey works end to end. No code,
Azure, Entra, DNS, certificate, SQL, or application-setting repair was required
after the current evidence was reconciled.

The active App Service artifact is manual pipeline 388, build
`20260803.36`, for exact current-main SHA
`05f0c228404655d63d5c1ddbbc0a3c2d1d54491e`. Its expected and live release
identity is `9348c418fb50fcee788fda77`. Build, Deploy, and ProductionSmoke all
passed with zero stage or job errors and warnings.

Automatic pipeline 386 had already deployed the same SHA successfully about
40 minutes earlier. Both runs used ZipDeploy, performed the same remote Oryx
build, and logged `Triggering recycle (preview mode disabled)`. Pipeline 388
was a manual same-SHA redeployment and changed no application code. That second
recycle is the strongest production-side explanation for a temporary inability
to reach the site during the reported period, but there is no client-side
timestamped failure capture proving the exact request coincided with it. Azure
recorded zero App Service HTTP 5xx responses during the inspected six-hour
window, so this package does not invent a persistent outage cause.

## Current production evidence

### Public edge and artifact

- `peerslate.com` resolves to `13.89.172.22`; the apex, `pete.peerslate.com`,
  and direct Azure hostname complete TLS successfully.
- The apex and `pete` certificates are SNI-enabled and valid into January
  2027. The direct Azure hostname uses Microsoft's valid wildcard certificate.
- `/` and `/healthz` return 200. Signed-out `/app` redirects once to
  `/auth/sign-in`, which redirects once to Easy Auth.
- The direct App Service hostname and the private/auth path on
  `pete.peerslate.com` return fixed 308 redirects to the apex. Unsafe alias
  redirect behavior remains covered by the released contract.
- App Service is `Running`, availability is `Normal` in the Web App record,
  `httpsOnly` and HTTP/2 are enabled, TLS minimum is 1.2, `alwaysOn` is true,
  and both SCM and FTP basic publishing credential policies are disabled.
- Six hours of App Service metrics contained 384 requests, 285 HTTP 2xx,
  seven HTTP 4xx, and zero HTTP 5xx. The highest five-minute average response
  time was 1.9281 seconds.

### Identity and hosted sign-in

- Easy Auth remains enabled and anonymous public routes remain allowed.
- Easy Auth discovery authority is the custom-domain
  `peerslatemembers.ciamlogin.com/.../v2.0` URL.
- Live OpenID metadata returns the distinct UUID-hosted principal issuer, and
  `PEERSLATE_AUTH_ISSUER` matches that metadata issuer exactly.
- The Entra app registration has exactly one redirect URI:
  `https://peerslate.com/.auth/login/aad/callback`.
- The app registration homepage is `https://peerslate.com`; no competing
  callback, alternate-host callback, or temporary app registration was found.
- Tenant branding retains Deep Navy `#101B30` and the truthful text
  `Private by default. You choose what you share.` The live background,
  wordmark, square logos, and favicon match the local approved branding files
  byte-for-byte by SHA-256.

### Owner journey

Using the existing Microsoft SSO session, without entering or handling a
credential:

- signed-out Sign In reached `/app` and `Welcome, Pete Carter.` in 2,348 ms;
- `/app` refresh completed in 1,426 ms;
- leaving for the public homepage preserved the signed-in `My Slate` control;
- browser Back returned to `/app` in 437 ms;
- a second tab reached the same private workspace in 364 ms;
- sign-out cleared the PeerSlate session and the public page returned to the
  signed-out `Sign In` control; and
- the three live sign-in/header stylesheets use content tokens matching the
  current-main file hashes, including the released mobile-overlap correction.

The repository's current auth, Owner Home, sign-in experience, release-template,
and operational-readiness tests passed: 101 tests and 54 subtests. The complete
local repository suite then ran 1,645 tests successfully, with four
environment-specific skips.

## Cleanup

Azure contains one production Web App and one one-site B1 App Service plan. No
Candidate/temp Web App, orphan plan, or candidate-named resource exists, so no
Azure resource was deleted.

The following clean local historical auth worktrees and branch refs were
removed only after their trees were proved identical or patch-equivalent to
released Azure merge history and their remote branches were confirmed gone:

- `portfolio-auth-callback-hardening` /
  `work/2026-07-23-auth-callback-hardening-001`;
- `portfolio-auth-sql-wake-001` /
  `work/2026-07-23-auth-sql-wake-closeout-001`;
- `work/2026-07-23-auth-sql-wake-001`; and
- `work/2026-08-02-auth-pill-hidden-css-fix`.

The approved Entra branding assets, sign-in assessment, overnight audit,
unrelated worktrees, active Opportunity Slate pull requests, user artifacts,
backups, and the dirty primary checkout were preserved.

## Honest limits

- Microsoft reused the existing SSO session, so the hosted password-entry
  field and password-reveal control were not observed. No credential will be
  requested to force that state.
- The in-app browser's requested 390 px viewport override did not change its
  actual 1280 px CSS viewport. This package therefore proves that production
  serves the exact previously browser-verified mobile-fix bytes and that the
  focused regression contract passes; it does not claim a new independent
  live 390 px geometry measurement.
- The duplicate manual deployment is the strongest Azure-side explanation for
  transient reachability, not a proven client-request correlation. Avoid
  manually redeploying an already green exact SHA unless current live evidence
  requires it.

## Release boundary

This reconciliation changes documentation and pointer tests only. It must use
an Azure pull request with `[skip ci]` after the exact tests pass so bookkeeping
does not trigger a third same-SHA production recycle. The deployed application
remains pipeline 388 until a later normal runtime release.

Azure PR validation 394 correctly caught two reconciliation defects before
merge: the control-plane reader does not support a folded multiline release
note, and the baseline date assertion still named the prior date. The note was
returned to the repository's supported single-line form, the required
`not a substitute` warning was retained, the date assertion was advanced, and
the full local suite passed. PR validation does not meet the production-stage
branch condition and therefore did not deploy or recycle the Web App.

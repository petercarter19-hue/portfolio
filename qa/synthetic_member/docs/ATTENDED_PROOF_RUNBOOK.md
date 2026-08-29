# Sealed attended two-member proof runbook

This runbook defines one exact, local, complete-lifecycle operation for two
temporary ordinary PeerSlate customer identities. Repository implementation
does not authorize or represent a live run. A live operation is permitted only
after this Protected package is merged, independently reviewed, and separately
authorized for the fixed production target.

## Fixed authority and target

The worker has one compiled-in owner authorization reference:

`session:01a04348-7e3e-7a11-a443-752498be91b5/owner-authorization:2026-08-28/workshop-fg-sealed-private-proof-complete-lifecycle`

It accepts no authorization-reference argument or prompt. It targets only:

- Azure subscription `bd0ecf48-6940-4fd3-9687-3eaf72469d67`;
- resource group `peerslate`;
- App Service `peerslate-pete`;
- site origin `https://peerslate.com`; and
- Microsoft Graph `v1.0` user and deleted-item endpoints.

The worker cannot change roles, Graph grants, App Service authentication,
configuration, schema, licensing, billing, DNS, or application code. Missing
pre-existing authority is a refusal, never permission to broaden the operation.

Pete makes the owner decision that authorizes the attended operation and its
irreversible exact-two identity deletion. The worker then performs the bounded
sequence without asking Pete, Codex, a browser operator, or the package manager
to enter or disclose an identifier, password, issuer, tenant, object ID, token,
MFA or recovery value, mailbox, credential, or authorization reference. The
command includes only safe run metadata and explicit structural confirmations.

## Sealed and retained boundaries

The worker holds generated login identifiers, passwords, Graph tokens, caller
object ID, tenant routing, customer object IDs, private item handles, versions,
and synthetic wording only in its process. It clears its direct references on
exit. Python cannot promise physical zeroization of immutable strings, so the
enforced guarantee is no file, argument, environment, report, log, exception,
manifest, screenshot, trace, browser profile, storage-state export, or retained
evidence path for those values.

Only allowlisted structural result codes and counts may leave the process. The
worker never retains DOM or page content, private network traffic, downloads,
cookies, browser storage, claims, authorization headers, Graph responses,
database rows, identity inventories, item handles, or its finite mutation
ledger. Do not enable Playwright tracing, video, screenshots, downloads, remote
debugging, ODBC tracing, SQL-driver diagnostics, Azure CLI telemetry, or verbose
credential output.

## Separate manual browser-operator boundary

The complete-lifecycle sealed broker above is the normal path for this package
and asks Pete for no identity material. The following boundary remains the
contract for a separately authorized non-broker/manual fallback or another
attended proof that deliberately uses human-controlled credential entry. It
does not grant that fallback, make it part of this package, or allow it to be
substituted for the exact sealed lifecycle.

In that separate path, the browser-capable operator opens each sign-in flow and handles ordinary
controls. The operator performs A-to-B and B-to-A switch journeys. After each operator-clicked sign-out,
the operator performs refresh, second-tab, public-return, sign-out, and
cross-tab checks. The operator deletes or archives every created item, and the
operator signs out and destroys Clients A, B, the signed-out control, and the
switch client. If a safety issue appears, the operator closes the
affected view without copying its contents.

Before Pete enters a login identifier or credential, the operator stops issuing
browser commands and suspends all capture and observation. Pete controls the
visible input and says only `ready` when ordinary browser operation may resume;
Pete does not disclose the entered value. Later ordinary UI may unavoidably render a login
identifier or account label. Incidental visibility is not evidence, and the
operator must not intentionally inspect, transcribe,
export, capture, record, or retain that detail. The operator refers to the pair only
as `member_a` and `member_b`. If any secret, code, or credential is rendered unmasked,
stop without capture.

### Browser observation boundary

Screenshots are optional, never the default retained proof, and are prohibited
for the sealed broker. In a different explicitly screenshot-authorized manual
proof, any image must exclude credentials, identifiers, sentinel or
private item content, unrelated private data, and session material. Destroy any
transient privacy-safe screenshot before final validation unless separate
evidence authority explicitly permits retention. Never photograph, copy, or
export a suspected private exposure. Any transient privacy-safe screenshot is destroyed
when that manual proof closes.

The operator never inspects, exports, records, or persists passwords, MFA codes,
cookies, tokens, claims, authentication headers, browser profiles, or private
session files. The operator never exports, records, or persists browser storage,
private network traces, or DOM/page content.

## Entry gate

Before invoking `run`, the operation owner confirms outside the worker that:

1. this exact independently reviewed broker package is merged;
2. the deployed application source and release are known and Workshop is the
   authorized private proof surface;
3. the operation is authorized for exactly two new, temporary, ordinary
   customer identities and their irreversible deletion;
4. the exact UTC creation cutoff is current and run-scoped;
5. no unrelated identity, private data, broad inventory, production content,
   screenshot, or retained private evidence is in scope; and
6. the active Azure principal already has the required delegated scopes and
   eligible directory role.

Do not substitute Pete's owner account, another person's account, an existing
QA identity, or a mocked outcome. The repository package itself performs no
live Azure, Graph, browser, SQL, or identity operation.

## Production authority binding

Before any Graph token or browser credential entry, the worker reads the fixed
App Service authentication configuration and binds two deliberately different
authorities:

1. It uses `az` only for discovery, then requires the installed
   `<CLI2>/wbin/az.cmd` layout and its sibling `<CLI2>/python.exe`. The
   `.cmd` file is never executed. Before starting a shell-free child, the
   worker resolves and confines that `python.exe` to the same `CLI2` runtime,
   then runs it only as `-I -B -m azure.cli` for the two bounded read-only App
   Service commands (`webapp auth show` and `webapp config appsettings list`)
   and for the bounded Microsoft Graph token read (`account get-access-token`).
   Neither path is taken from an operator argument, and the worker never runs
   bare `az`, `az.cmd`, or a shell. A missing, escaped, or unusable runtime
   refuses before Azure, Graph, or browser work.
2. `az webapp auth show` selects only its current top-level `enabled` and
   `issuer` fields. The worker requires exactly that shape, maps it only inside
   the worker to its closed `platformEnabled` and `openIdIssuer` fields, and
   requires enabled App Service authentication and one
   no-trailing-slash OIDC discovery authority of the form
   `https://<tenant-label>.ciamlogin.com/<tenant-uuid>/v2.0`.
3. The exact discovery document must return HTTP 200 from the requested URL,
   without redirect and within the bounded response size.
4. Its `authorization_endpoint` must use the same discovery host and exact
   tenant UUID. The browser is allowed to reach only that authorization origin.
5. Its metadata `issuer` must be the no-trailing-slash principal issuer
   `https://<tenant-uuid>.ciamlogin.com/<tenant-uuid>/v2.0`.
6. The fixed App Service `PEERSLATE_AUTH_ISSUER` setting must equal that metadata
   principal issuer byte for byte.

The custom tenant-label discovery/authorization host and UUID-hosted principal
issuer are not interchangeable. A host, tenant, slash, metadata, redirect,
setting, or cross-label mismatch is a pre-mutation refusal.

After email submission, each sealed sign-in resolves a document-bound password
input handle without passing a secret, then proves that the top-level page
origin exactly equals the bound authorization origin. Only then does one
synchronous browser-side callback recheck that same document and origin and
write the generated password. A redirect during locator waiting detaches or
changes the handle before any secret crosses the boundary, so the redirected
page receives zero password material. The exact origin is checked again
immediately before password submission; a later redirect stops without
submitting the password.

Every Graph token is requested through that same confined CLI2 Python runtime
for the exact bound tenant UUID. Before use, its claims must prove:

- the bound tenant (`tid`) and Microsoft Graph audience;
- delegated scopes `User.Read`, `User.ReadWrite.All`, and
  `User.DeleteRestore.All`;
- the `User Administrator` directory role only for this lifecycle
  (`fe930be7-5e62-47db-91af-98c3a49a38b1`);
- a usable expiry; and
- one caller object ID (`oid`) that stays identical across all token
  reacquisitions.

The authenticated Graph organization must have the same tenant UUID and one
initial verified `<tenant-label>.onmicrosoft.com` domain. That tenant label must
match the App Service discovery host. Tokens are cleared after each bounded
use. Any scope, role, tenant, organization, label, issuer, or caller-OID mismatch
stops the operation.

## Pinned disposable browser gate

The browser gate completes before the first Graph POST. On either approved
Darwin arm64 / Python 3.14 or Windows AMD64 / Python 3.13 host, the worker
verifies the reviewed lock and provisions one operation-scoped runtime using
hash-required binary packages. The Windows target uses its native
`Scripts/python.exe` and `Lib/site-packages` venv layout; the Darwin target
uses `bin/python` and `lib/python3.14/site-packages`:

- Playwright `1.62.0`;
- greenlet `3.5.5`;
- pyee `13.0.1`;
- typing-extensions `4.16.0`; and
- Chromium revision `1234`, browser version `151.0.7922.34`, installed only
  through the locked shell-free venv command
  `python -I -m playwright install chromium --no-shell`.

It then launches a separate headed probe in a second disposable root, verifies
the exact browser version, opens `about:blank`, closes the page, context, and
browser, and proves the probe root removed. Only after that closed probe does it
launch the actual headed browser, create exactly four fresh non-persistent
contexts (`member_a`, `member_b`, never-authenticated signed-out control, and
switch), and prove the signed-out Workshop private baseline.

The actual browser, imported runtime modules, four contexts, and complete
operation root must be released and removed before SQL retirement. The cleanup
result must be exactly `BrowserCleanup(destroyed_contexts=4,
temporary_root_removed=True)` before the SQL retirement core or an irreversible
Graph purge can begin. Probe
cleanup and actual-session cleanup are independent and aggregated: one cleanup
failure must not suppress attempts to clean the other resources. If Playwright
starts but executable validation fails before the provider returns, that local
driver handle is stopped before imported-module and path release; cleanup
failures are aggregated. Stale roots, an unexpected runtime or executable,
capture/debug environment, fewer or more than four contexts, a failed private
baseline, or incomplete removal stops the operation.

## Exact complete lifecycle

For an accepted structural result, the worker executes this order and may not
skip or reorder a gate:

1. Bind the fixed owner reference, production App Service discovery authority,
   metadata principal issuer, authorization origin, tenant UUID, and tenant
   label.
2. Provision and close the pinned Playwright probe; launch the actual runtime,
   prepare four contexts, and prove the signed-out private baseline.
3. Prove the Graph tenant, initial domain, delegated scopes, User Administrator
   role, usable expiry, and stable caller OID.
4. Derive exactly two run-scoped identifiers, random per-alias creation markers,
   and passwords in worker memory. Each generated `issuerAssignedId` and
   Graph-valid mail nickname is at most 64 characters.
5. Before either POST, perform four exact collision reads: active users and
   deleted users for each generated issuer/identifier pair. Each bounded exact
   filter must return an empty result with no next page. Any match or ambiguous
   result refuses creation.
6. POST `member_a` and then `member_b` exactly once each. Require exact HTTP 201
   and final URL, then directly GET the returned subject and prove the exact
   operation-local creation window, enabled `Member` / `LocalAccount` customer
   shape, random mail marker, single generated email identity, and distinct
   object IDs. No response data may enter output.
7. Complete all 38 canonical journeys and the initial exact Workshop
   history/disclosure proof below.
8. After archive and restore, re-read each restored active item and re-prove
   exactly three retained versions newest first, with byte-exact original v1
   source in all three rows. Only then permanently delete each synthetic
   Workshop item through the application and prove zero active and zero
   archived item residue for each alias. A signed-out or preview page can never
   count as zero residue.
9. Repeat the signed-out clean-start proof, close all four contexts and the
   browser, unload the disposable runtime, remove the operation root, and prove
   the exact `BrowserCleanup(4, true)` result. Any other cleanup result blocks
   both SQL retirement and irreversible Graph purge.
10. Pass only the two in-memory object IDs and the metadata principal issuer to
    the accepted exact-two SQL retirement core. Require exactly two eligible
    private ordinary mappings retired, commit success, and closed structural
    output. This step is forbidden on every path unless step 9 returned that
    exact cleanup proof.
11. Soft-delete exactly those two Graph users, prove both soft states, purge
    exactly those two deleted objects, and prove final active-and-deleted
    absence for both. Irreversible purge remains bound to the same exact cleanup
    proof as well as committed exact-two SQL retirement.
12. Clear the caller binding and all remaining direct sealed references and
    emit only the allowlisted structural report.

## Workshop proof contract

Each alias creates exactly one minimal run-scoped private item. Both member
contexts stay open for bidirectional list/read isolation checks, browser-state
isolation, and distinct mapping. The switch context proves both A-to-B and
B-to-A switching. Refresh, second-tab, public-return, ordinary sign-out, and
cross-tab sign-out are exercised for each alias.

The browser request-context API cannot atomically bind a foreign mutation
endpoint to the actor page's canonical owner document. Supplying synthetic
`Origin` or `Sec-Fetch-Site` headers is not such proof. The worker therefore
sends no foreign update or delete request, passes no peer row version into an
out-of-band form, and truthfully records both journey pairs as unavailable
`Conditional` outcomes. This is fail-closed evidence, not a successful denial
claim and not permission to mutate.

Each item is edited exactly twice. Its history must prove exactly three retained
versions, newest first. The wording sequence is exactly
`<marker>-source  byte & stable`, `<marker>-edit-one`, then
`<marker>-edit-two`. For every version row:

- the approved wording must equal the expected wording for that version;
- `Source wording on record` must remain byte-for-byte equal to the original
  v1 source, including its internal double space and `&`; and
- the exact retained-history note below must be present, with no truncated
  history window.

> Some older AI-assisted versions may show refined wording under “Source
> wording on record” because the original wording was not retained at the time.
> PeerSlate does not infer or backfill wording it cannot prove.

Workshop D must contain exactly one `Downstream use` disclosure whose value is
`Not used elsewhere`; its direct `dt` and direct `dd` must be children of that
same row. Every private or generated Workshop DOM read, write, check, click,
and navigation is bound in the browser task to canonical
`https://peerslate.com`; a port, userinfo, hostile owner document, or redirect
race is indeterminate. A generic history note, missing row, reordered version,
normalized v1 bytes, unavailable/cited deletion state, or different disclosure
is indeterminate. Archive and restore are exercised without creating another
wording version. After restore, the worker must re-read the active item and
repeat the exact three-version, newest-first, byte-stable original-v1 proof
before deletion or an accepted result. This is a revalidation of the same three
rows, not an additional version or retained-source count. Application deletion
must expose the exact uncited permanent delete confirmation before use.

The 38-journey result has exactly ten `Conditional` outcomes:

- `member_a_cannot_update_member_b`, `member_b_cannot_update_member_a`,
  `member_a_cannot_delete_member_b`, and
  `member_b_cannot_delete_member_a` use
  `neutral_denial_not_distinguishable`;
- `member_a_forged_reference_denied`,
  `member_b_forged_reference_denied`,
  `member_a_cannot_export_member_b`, and
  `member_b_cannot_export_member_a` use `feature_surface_unavailable`; and
- `member_a_expired_session_safe` and `member_b_expired_session_safe` use
  `session_expiry_not_controllable`.

The foreign update/delete checks do not issue an API request against a peer
item: Workshop has no atomically provable page-document and endpoint authority
for that mutation. The worker records the closed limitation without mutation.
Every other canonical journey must pass its exact structural outcome. A missing,
extra, substituted, or differently placed Conditional, including a cross-tab
Conditional, is indeterminate and cannot yield the accepted structural result.
After both customers exist, that browser-proof failure still enters bounded
identity containment only when cleanup equals `BrowserCleanup(4, true)`
exactly: independently attempt application-item deletion, retire only the exact
two mappings, and delete only the exact two bound Graph subjects before
returning `indeterminate`. An exception, absent proof, or non-exact returned
cleanup value blocks that containment boundary.

## Exact Graph deletion state machine

Irreversible Graph purge begins only after cleanup equals
`BrowserCleanup(4, true)` exactly and exact-two SQL retirement has committed.
That gate applies regardless of whether the Workshop journey path succeeded or
failed. The full exact-pair path then follows the state machine below. The
worker maintains a finite in-memory ledger and never emits it.

1. Issue one active-user DELETE for each exact object ID. Each must return 204
   with an empty body.
2. For each object ID, read the exact active endpoint and exact deleted-item
   endpoint. The required four soft-state proofs are active `404` and deleted
   `200` containing that same ID for both users.
3. Only when both soft deletes and all four soft-state proofs are exact, issue
   one deleted-item DELETE for each object ID. Each must return 204 with an empty
   body.
4. Read both exact endpoints again for each ID. All four final reads must return
   `404`: no active object and no deleted object for either alias.

There is no blind retry. An unexpected status, redirect, body, ID, token binding,
network result, partial transition, or cleanup result after mutation is
`indeterminate`. Do not repeat a POST, soft DELETE, purge DELETE, retirement, or
the complete run from that result. Obtain separate authority for read-only
reconciliation of the exact attempted pair. The creation failure path permits
only one bounded exact-filter reconciliation and recoverable containment pass;
it never lists unrelated identities or repeats either POST. A definitive
rejected 4xx, including 409, is `known_not_created` and never enters
reconciliation for that alias. A transport/status ambiguity is
`ambiguous_maybe_created` and becomes containment-eligible only when one exact
object matches the generated identity, random creation marker, complete
customer shape, and operation-local attempt window. Before browser cleanup,
that bounded partial-create path may reconcile and soft-delete only active exact
proven subjects if safely needed, including an earlier independently bound
broker subject, then attempt bounded direct state probes. Probe ambiguity stays
indeterminate. An exact subject already found in deleted items remains
unpurged. The path attempts session cleanup independently and never purges a
deleted item. Purge remains forbidden until the exact
`BrowserCleanup(4, true)` proof exists and exact-two SQL retirement has
committed.

## Commands

The plan is inert and emits only structural shape:

```powershell
python scripts/run_synthetic_sealed_credential_broker.py plan
```

Only a separately authorized attended operation may use `run`:

```powershell
python scripts/run_synthetic_sealed_credential_broker.py run `
  --run-id <SAFE-RUN-ID> `
  --created-after-utc <EXACT-UTC-CREATION-CUTOFF> `
  --execute `
  --confirm-exact-two-synthetic-members `
  --confirm-no-production-proof `
  --confirm-permanent-exact-two-deletion
```

There is no credential, issuer, tenant, subject, mailbox, identity, profile,
authorization-reference, recovery, or deletion-target argument. There is no
secret prompt. The permanent-delete confirmation does not expand the exact-two
target or replace the fixed owner authorization.

## Structural output

A complete valid run reports `result: conditional` because of the exact ten
bounded journey limitations, and
`state: retired_and_permanently_deleted`. Its count-only report proves:

- 2 requested and provisioned identities;
- 4 precreation absence proofs;
- 2 arrivals, 2 switches, 38 journeys, and 10 Conditionals;
- 2 created items, 4 edits, 6 retained versions, 6 exact retained-source
  proofs, and 2 downstream disclosures;
- 0 active and 0 archived item residue;
- 4 destroyed contexts;
- 2 retired mappings;
- 2 soft-deleted identities and 4 soft-state proofs; and
- 2 permanently deleted identities and 4 final absence proofs.

Before mutation, a closed mismatch returns `refused`. Once an external mutation
may have occurred, an unresolved state returns `indeterminate`. Neither result
contains material values. A `conditional` report is not proof that this
repository package ran live; only separately authorized operation evidence can
establish that fact.

## Retained proof

Stop immediately if private peer content appears, identities collide, a member
maps to the same application account, signed-out access exposes private state,
a switch carries prior-member state, Workshop history or downstream disclosure
differs, application residue is nonzero, or any cleanup/deletion proof is
ambiguous. Do not capture exposed content.

The retained operation bundle is limited to the final allowlisted structural
JSON plus independently established source/release labels and a package-level
result. Do not retain the cleanup or mutation ledger, sentinel text, generated
wording, DOM/page content, screenshots, browser history, network traces,
database rows, an identity inventory or identifiers, credentials, tokens,
session material, cookies, claims, headers, browser profiles, private session
files, runtime roots, or Graph responses.

This complete-lifecycle broker supersedes the prior SQL-retirement-only handoff.
For this exact sealed path, verified exact-two SQL retirement, soft deletion,
purge, and four final `404` proofs are all mandatory before success. The manual
identity-retirement utility remains a different recovery-controlled tool; it is
not part of this run and cannot be substituted into it.

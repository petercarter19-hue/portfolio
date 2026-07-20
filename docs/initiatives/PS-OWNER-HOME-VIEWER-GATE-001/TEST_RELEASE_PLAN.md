# PS-OWNER-HOME-VIEWER-GATE-001 Test and Release Plan

## Release position

Current result: **Conditional**. This plan describes future package gates; it does not authorize implementation or claim that viewer/publication capability exists.

Owner Home and viewer/preview work release separately behind default-off flags. Owner Home is the first release slice. Viewer/preview flags cannot turn on until the authorization/projection migration, real publication/grant lifecycle, route map, production-intent designs, and all negative-access gates pass.

## Required test layers

Every implementing package supplies focused unit tests, SQL migration verification, service/integration tests, HTTP contract tests, browser/accessibility tests where UI changes, full repository regression, and production verification proportional to its change. Tests must use generic profiles and at least two owners; no shared fixture owner is allowed to mask tenant failures.

## Two-owner isolation matrix

Use Owner A and Owner B with different identity issuer/subject mappings and opaque account/profile keys. Add Viewer C and Anonymous D when the relevant mode exists.

| Test | Setup/action | Required result |
|---|---|---|
| Owner Home isolation | A and B each have Captures, Moment versions, placements, reviews, and different timestamps; request Home as A then B in the same test process | A response contains only A opaque keys/summaries; B only B; no stable cache/session bleed |
| Foreign selector | A supplies B profile/Moment/Placement/grant keys to every owner endpoint parameter/body/header location | Neutral `404` or validation error; no B fields, counts, timing-specific existence hint, or log content |
| Sequential browser identities | Sign in as A, sign out, sign in as B, then use Back/restore/retry | No A private DOM/payload reappears; protected responses are `no-store`; B receives fresh state |
| Selected-person grant | A grants C one entity; B owns a similar entity; C requests both | Only A's explicitly granted projection is returned; B is neutral `404` |
| Connection pair | A-C active, B-C pending/ended, plus normalized pair order variations | C sees only eligible A connection projection; pending/ended B projection is unavailable |
| Authenticated member | C has no relationship to A or B; A publishes member-mode content and B does not | Only A's member-published projection; no relationship inference or private counts |
| Public | A has a current public manifest; B is private/unpublished | A public projection only; B neutral `404`; signing in does not broaden either public response |
| Block precedence | Add a block in either direction after a grant/connection exists | Projection fails closed on next request and after retry; no stale content |
| Delete/withdraw | A deletes a referenced record or withdraws projection while C has it open | Authorization/publication version changes; next read removes content; no newest-version substitution |

At the SQL layer, tests must show the stored procedure cannot return another owner even when passed a valid foreign internal ID. At the API layer, inspect serialized bytes, headers, redirects, and logs. At the browser layer, inspect DOM, accessibility tree, storage, history title, and back/forward cache behavior.

## Payload-level privacy tests

For every mode, build a canary dataset with unique strings in:

- raw Capture body and revisions;
- transcript and audio URL;
- discarded proposal and unconfirmed Moment version;
- owner email/name/private profile fields;
- other owner's Moment;
- selected-person-only, connection-only, member-only, and public fields;
- deleted body/tombstone metadata;
- internal numeric IDs and grant/relationship keys.

Assert both presence of authorized canaries and absence of every prohibited canary in:

- SQL result sets;
- Python service/view model;
- serialized JSON bytes;
- rendered HTML/DOM and hydration/bootstrap data;
- response headers, redirects, cookies, and URLs;
- application/access/telemetry logs;
- browser cache, storage, and history;
- error, retry, restricted, stale, and revoked responses.

Snapshot tests are allowed only as readable supporting evidence. Explicit field allowlists and canary absence assertions are required so a snapshot update cannot silently approve a leak.

## Route and API contract tests

### Owner Home

- Anonymous JSON -> `401 authentication_required`; anonymous HTML `/app` -> validated local sign-in redirect.
- Signed-in owner -> `owner-home.v1`, at most 64 KiB, at most 3 review and 9 total objects.
- Missing categories -> `null`/empty and honest availability, not fixtures.
- Approved future categories -> item remains `null`, `availability.state` is `coming_later`, and the rendered capability preview contains only approved feature/purpose/status copy.
- Duplicate eligible record -> appears in only the highest-priority category.
- Stable ties -> deterministic order across repeated requests.
- Foreign/deleted/inactive inputs -> absent or approved tombstone only.
- Core/optional dependency failures -> defined partial/complete failure behavior.
- Headers -> `private, no-store`; content type and security headers correct.
- Legacy `/api/dashboard` response changes do not alter Home contract and Home never calls it.
- Capability previews are genuinely disabled, excluded from forms, issue no route/API request, cannot be activated by DOM/query/client flag changes, and retain the nine-object budget.

### Viewer modes

- Mode allowlist rejects unknown/case-confused/duplicated values.
- Requested mode never elevates the resolved mode.
- Selected-person grant checks grantee, entity, owner, access level, expiry, revocation, active state, block, and publication.
- Connection checks normalized active pair and block; pending/ended is insufficient.
- Authenticated-member requires identity but no connection; public requires no identity and never sees member-only data.
- Unknown/private/unpublished/withdrawn/inaccessible subjects share neutral negative behavior.
- Optional `410 access_changed` occurs only for a safe previously possessed opaque grant context and never leaks a new subject.
- Concurrent revocation/version change produces no superseded content.
- Public signed-in request is byte-equivalent in content to public anonymous request, aside from non-content request identifiers if any.

### My Slate preview

- Only owner can request preview of their subject.
- For identical subject/mode/version, preview projection content is byte-equivalent to the live serializer output; preview adds only its outer context envelope.
- Public preview cannot see a draft/unpublished public projection.
- Selected/connection preview without a real eligible viewer returns truthful eligibility guidance and no simulated projection.
- Block, expiry, withdrawal, and deletion affect preview exactly as live view.
- Preview controls cannot alter/save/publish/grant by GET or by client-side state.

### Error and recovery

- `400`, `401`, neutral `404`, safe `410`, `409`, and `503` use the stable codes in AUTHORIZATION_PROJECTION_MATRIX.md.
- Error bodies contain no subject/private fields, database messages, stack traces, SQL names, or echoed unsafe selectors.
- Retry is idempotent, bounded, and does not change authorization or create duplicate lifecycle rows.

## Migration verification

Any database package must pass an isolated SQL gate before application release:

1. Start from the exact supported production-schema baseline.
2. Apply migration using the repository runner.
3. Run structural and behavioral verification, including legacy audience audit and indexes.
4. Seed two-owner/multi-viewer cases with no production data.
5. Run authorization-before-retrieval, block, expiry, concurrency, and canary privacy tests.
6. Roll back and verify previous schema/data behavior is restored without canonical loss.
7. Reapply and rerun verification.
8. Record commands, output, database target class (never credentials), timings, and cleanup.

Passing repository unit tests does not replace apply/rollback/reapply proof. Ambiguous legacy `shared`/`recruiter` rows are a release blocker, not an invitation to infer a mapping.

## Performance and resilience

Use a documented founding-alpha profile with at least:

- 100 review-eligible records per owner even though only 3 may return;
- 1,000 confirmed Moment versions and representative placements per owner;
- 100 grants and 100 connections across subjects, including expired/revoked/blocked rows;
- 100 projection-manifest references where the product contract's tighter section limit is also exercised;
- concurrent Home/viewer reads plus grant revocation/withdrawal.

Required evidence:

- Owner Home p50/p95/p99 server and database duration; p95 database <= 250 ms and endpoint <= 600 ms.
- Viewer p50/p95/p99; p95 database <= 250 ms and endpoint <= 500 ms.
- Query count: Home one core plus at most two optional adapters; viewer maximum two within one consistent boundary; no N+1.
- Payload <= 64 KiB and object count limits enforced before serialization completes.
- Timeout returns safe `503`; no fixture or stale fallback.
- Revocation race test proves zero superseded payloads after the authorization version commits.
- Repeated Retry/backoff does not overload dependencies or duplicate work.

Performance datasets must contain synthetic generic content. Production private text never enters benchmark logs or artifacts.

## Accessibility and responsive validation

For every user-facing state, perform:

- automated semantic/contrast scan with zero unresolved serious/critical findings;
- keyboard-only flow and focus-order/visible-focus inspection;
- NVDA plus supported Chromium manual validation on Windows;
- 200% zoom, 320 CSS-pixel reflow, text-spacing overrides, forced colors/high contrast, and reduced motion;
- desktop and mobile screenshots at the design package's named sizes;
- touch target, orientation, long/missing/translated/bidirectional content tests;
- loading, empty, partial/complete failure, retry, private/unpublished, restricted/not-found, stale, deleted, revoked/access-changed tests;
- visible **Coming later** preview labels, native disabled/`aria-disabled` semantics, form exclusion, no-request behavior, readable contrast, and no fabricated people/results/counts/content;
- owner/viewer/preview context comprehension and absence of hidden owner controls from viewer DOM.

Named screenshots must be compared against the owner-approved production-intent visual authority. Deviations are recorded and require ChatGPT Work plus Pete approval unless Pete delegates that gate in writing.

## Regression suite

At each future merge candidate, run the repository's then-current documented suite plus focused tests. At minimum protect:

- identity/Easy Auth, sign-in/out/session, return-path safety, and test/dev identity isolation;
- Owner Settings;
- Capture text lifecycle, export, delete, and two-owner isolation;
- Voice behavior without modifying its active correction lane;
- canonical Moment source-version/tombstone/concurrency behavior;
- body-free Placement ownership and exact-version validation;
- public canonical Pete routes and redirects until their own convergence package changes them;
- Living Resume feature-flag behavior;
- CSP/security headers, rate limits, stored-procedure allowlist, and SQL migration ledger;
- governance pointer/site rules.

No future package may "fix" a failing unrelated lane by editing its reserved files without manager reassignment. Record the blocker and coordinate.

## Rollout sequence

### Release 1: finite Owner Home

1. Merge backend Home read contract and complete approved frontend through their bounded packages; keep `PEERSLATE_OWNER_HOME_ENABLED` default off.
2. Deploy migration/code with flag off; verify legacy `/app` and all regressions.
3. Enable for designated founding-alpha accounts only using server-side configuration that does not log identity content.
4. Complete Pete and Danielle validation and visual acceptance.
5. Expand only after privacy, reliability, performance, and support observations pass.

The first enabled Home should preserve the approved insight and connection silhouettes as disabled **Coming later** capability previews, following the accepted Voice pattern. Their real item fields remain `null`; they contain no filler, people, counts, observations, or working controls.

### Release 2: projection service, viewer modes, and preview

1. Deploy reversible authorization/projection schema and services with all viewer flags off.
2. Verify SQL production migration, procedure permissions, application health, and no change to existing public fixtures.
3. Create real controlled founding-alpha publication/grant cases through the separately approved lifecycle; do not seed them by hand in application code.
4. Enable owner preview for approved modes, then selected-person/connection/member modes in the manager-approved order.
5. Enable public generic projection last, after canonical route/SEO/cache decisions and withdrawal proof.
6. Keep fixture-route convergence as a separate package.

The accepted Home flag is `PEERSLATE_OWNER_HOME_ENABLED`. Suggested future
viewer flags are `PS_SLATE_PROJECTION_ENABLED`, `PS_SELECTED_VIEW_ENABLED`,
`PS_CONNECTION_VIEW_ENABLED`, `PS_MEMBER_VIEW_ENABLED`,
`PS_PUBLIC_VIEW_ENABLED`, and `PS_SLATE_PREVIEW_ENABLED`; their exact names are
owned by their future packages and all default off.

## Rollback

- Immediate application rollback: disable the affected flag(s); return the previous real route or an honest unavailable response. Do not route to fixture content as if equivalent.
- Code rollback: redeploy the last known-good Azure artifact through the pipeline, not GitHub Actions or a direct main push.
- Migration rollback: execute only the verified rollback for the exact migration after confirming no later dependency. Preserve canonical records and audit evidence.
- Privacy incident: disable all non-owner projection flags first, invalidate authorization/publication versions and any approved public cache, preserve protected audit evidence, then follow the incident process.
- Owner Home failure must not require disabling Capture/Moment canonical workflows; route separation and feature flags must preserve those paths.
- Rollback completion requires pipeline/deploy success plus exact live-route/API/header/body checks. A successful Build alone is insufficient.

## Azure pipeline and production verification

For each release, record:

- Azure PR number, squash-merge SHA on `origin/main`, pipeline ID/run/build number, and deploy completion;
- production migration ledger and verification output when schema changed;
- application build/version evidence matching the exact SHA;
- anonymous checks for `/`, `/app`, `/auth/session`, canonical Pete public routes, and all new public/negative routes;
- signed-in owner checks for Home, Settings, Capture, Moment, preview, sign-out, and two-owner isolation;
- signed-in selected/connection/member positive and negative cases using real authorized alpha records;
- response headers, payload canaries, cache/storage, retry/revocation, mobile/desktop screenshots, accessibility evidence, and telemetry without private content;
- restart/stale-worker handling if a just-deployed route disagrees with deploy evidence, followed by recheck before code changes.

Credentials remain off-limits. Pete/Danielle use already configured secure sign-in; the writer records outcomes without requesting, exposing, or storing secrets.

## Founding-alpha acceptance: Pete and Danielle

Both founders validate with distinct real accounts and account-owned records. Neither account may stand in for the other.

### Owner Home tasks

- Confirm each sees only their own finite Home and recognizes Capture as the obvious action.
- Complete/visit a real review item, recent/resurfaced Moment, and next step where eligible.
- Confirm future insight, connection, and viewer features remain visibly present as polished **Coming later** capability previews, while no control works and no fabricated data appears.
- Exercise mobile, keyboard, zoom, loading/failure/retry, stale, and sign-out/back behavior.

### Viewer/preview tasks when released

- As owner, preview each actually eligible mode and compare with the live view for the same real viewer/context.
- Grant and revoke selected-person access through the approved lifecycle; validate immediate access change.
- Establish/end a real connection case and validate block precedence.
- Compare authenticated-member and public projections; confirm private/draft/source content is absent.
- Withdraw/delete a published reference and verify no stale view/cache.
- State in their own words whose Slate they are viewing, why they have access, whether it is public/private/permissioned, and what each control will do.

Acceptance evidence records result, build/SHA, mode, viewport/assistive technology, issues, and explicit visual/trust decision. It does not record private content or credentials.

## Release gates

| Gate | Owner Home | Viewer/preview |
|---|---|---|
| Architecture approved | Required | Required |
| Production-intent visual authority accepted | Required | Required |
| Reversible SQL proof | If read procedure/schema changes | Required |
| Two-owner and payload privacy | Required | Required |
| Performance/accessibility/regression | Required | Required |
| Real lifecycle for capability | Existing owner lifecycle sufficient for eligible categories | Publication/grant/connection lifecycle required |
| Pete + Danielle founding-alpha | Required before expansion | Required before expansion |
| ChatGPT Work merge/release readiness | Required | Required |
| Pete visual acceptance | Required | Required |

Any unresolved privacy leak, cross-owner result, simulated capability, visual downgrade, missing rollback proof, or production behavior mismatch is **Fail** for release.

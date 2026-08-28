# C0 account export architecture

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-ARCHITECTURE-001`
**Slice:** C0 — Protected, documentation only
**Authority checkpoint:** `origin/main` `4873cd1528da8bf0706771c5e4727eb82ab09933`
**Status:** Proposed architecture; no export is available, implemented, approved for production, or proven by this record.

## Decision

A future account export is a member-requested, server-authorized, expiring
derived ZIP artifact over existing canonical records. It is never a second
canonical store, client-selected account query, direct Blob link, or partial
archive. C0 defines later C1–C4 boundaries only; it creates no endpoint, job,
worker, container, identity, schedule, migration, grant, UI, or data promise.

## Trust and identity boundary

- The request is a signed-in same-origin `POST` protected by normal CSRF and
  origin controls. `GET`, a cross-origin form, public route, or AI action
  cannot start an export. AI neither selects content nor generates, approves,
  delivers, or makes export data canonical.
- The browser cannot choose an owner, user, profile, record set, Blob object,
  SAS token, or export contents. Owner IDs from a route, form, query, header,
  body, cookie, or idempotency value are ignored or rejected; they never affect
  the resolved owner.
- The server derives the authenticated principal, maps `user_key` to
  `dbo.app_users.id`, then resolves the active `dbo.member_profiles.profile_id`.
  Every job, source read, status response, and download uses that server-derived
  identity. Existing identity and owner-scoped-procedure sources demonstrate
  this shape; C0 did not run a live schema query or assert future reader fit.
- Status and download derive identity and job ownership again at access time.
  Unknown, foreign, inactive, deleted, or no-longer-authorized jobs receive the
  same neutral `404`; no state, object name, member activity, or existence
  information is disclosed. A reauthorized owner may receive a truthful
  `expired` status for that owner's retained job record. Download for an expired
  job is blocked without a ZIP body, provider/object name, or other artifact
  disclosure.
- Delivery is an authenticated application proxy after reauthorization with
  `Content-Type: application/zip`, `Cache-Control: private, no-store`,
  `Pragma: no-cache`, and `X-Content-Type-Options: nosniff`. There is never a
  public container URL, direct Blob URL, provider URL, or SAS URL.
- `ready` means a complete ZIP passed declared-content, SHA-256, and size
  verification, with final hash and size committed to the job ledger. There is
  no partial-ready state or client assembly. A domain that cannot satisfy its
  contract is `unavailable` or `excluded` before readiness.

## Job lifecycle

```text
signed-in same-origin POST
  -> derive active user/profile server-side
  -> atomically create or return one queued job
  -> worker leases and assembles exactly one job
  -> queued -> running -> ready | failed
  -> ready -> expired (before physical deletion)
  -> reauthorized owner may observe retained expired status; download only while ready and unexpired
```

| State | Meaning | Contract |
| --- | --- | --- |
| `queued` | Valid durable request, no worker lease. | An atomic worker claim changes it to `running`; a duplicate request returns the member's existing active job. |
| `running` | One bounded worker attempt has a lease. | It can complete `ready`, fail `failed`, or be recovered only after lease expiry. |
| `ready` | Complete, verified private artifact. | It can be proxy-downloaded only by its reauthorized owner through its expiry timestamp. |
| `failed` | Truthful complete assembly was impossible. | Return a safe non-content error; requeue only while attempts remain. |
| `expired` | Ready window elapsed or authorization is no longer valid. | A reauthorized owner may receive truthful expired status; block download without ZIP body or artifact detail, then clean physical/staging artifacts idempotently. |

Leases are compare-and-set claims with a lease token and expiry, not process
flags. Recovery after a crash fences stale completion by lease token and
attempt, records the new bounded attempt, and never accepts stale output. The
provisional maximum is three attempts; the future contract must not retry
forever.

## Archive and consistency contract

The recommended v1 format is a ZIP with versioned UTF-8 JSON and NDJSON files.
The root `manifest.json` has `format: "peerslate.account.export"` and
`schema_version: 1`. It records server `requested_at_utc`, assembly start and
cutoff, SQL consistency markers, and a deterministically lexically ordered
file list. Every file entry declares path, schema identifier, disposition,
byte length, record count, SHA-256, provenance, and a read window with a
domain marker when supported. The job ledger separately records final archive
SHA-256 and byte size. JSON keys and NDJSON record order must be documented and
stable; the archive contains no unlisted files or bytes.

`requested_at_utc` is when the member asked, not a false promise of an atomic
cross-domain snapshot. The worker records assembly start/cutoff, captures SQL
`@@DBTS` at both, and records per-domain rowversion/change markers where the
domain has them. Each file reports its own read window. This is a bounded
assembly window, not an atomic request-time snapshot: an edit during assembly
may be before or after a particular domain read. Blob-backed data is hashed
only while read. Raw binaries are out of scope; a domain without a truthful
point-in-time/read-window contract is `unavailable` or `excluded`.

## V1 domain matrix

This is an architecture inventory, not evidence that a reader is implemented,
every source table is applied, or an export is available. `Included` means a
future allowlisted owner-scoped reader may be built only after revalidation.

| Domain | V1 disposition | Required truth boundary |
| --- | --- | --- |
| Account, profile, Living Resume | **Included by allowlist** | Member account/profile and existing owner Living Resume facts only; no credentials, sessions, claims, or unrelated rows. |
| Profile publication foundation | **Unavailable** | `PS-PROFILE-002` is registered but unapplied in the generated production-schema record. Do not infer Profile-native publication records. |
| Own publication versions/access grants | **Own versions included; grants unresolved** | Owner's own versions only after contract revalidation; joint access-grant/relationship context is excluded. |
| Capture/revisions | **Included by allowlist** | Canonical owner Capture records and revisions; no Journal duplication. |
| Voice/photo | **Metadata/transcripts included; raw binaries excluded** | No original/previews/raw bytes, Blob names, provider locators, URLs, or credentials. |
| Moments/versions/sources/placements | **Included by allowlist** | Canonical Moment plus provenance/derived placement facts, not another Journal body. |
| Journal | **Unapplied/legacy unresolved** | `PS-JOURNAL-001` is unapplied; legacy journal-like records must not be assumed equivalent to Moments. |
| Workshop / My Knowledge | **Included after schema revalidation** | Allowlisted private knowledge/version records only; current schema, owner reads, and use-disclosure dependencies must be rechecked. |
| Opportunity Slate | **Included with provenance** | Durable member records plus provenance and proposed/noncanonical status where applicable. |
| My Opportunities | **Unavailable/excluded** | No current canonical export contract; do not conflate it with Opportunity Slate. |
| Community authored content | **Included with strict redaction** | Member's own authored content/safe metadata only. Redact other-member bodies, identities, media, reactions, lists, and relationship context; exclude unsafe joint context. |
| Connection preferences | **Included, labeled dormant** | Safe member field allowlist with truthful dormant/not-generic-Settings labeling where applicable. |
| Connection/block/report/joint records | **Unresolved/excluded** | Joint or other-member state awaits relationship/privacy decisions. |
| Notifications inbox (`dbo.notifications`) | **Excluded pending a reviewed field allowlist** | Title, body, `related_entity_id`, and `metadata_json` can contain other-member, joint, entity-linked, or internal context. Exclude `metadata_json`, delivery internals, and all other-member/entity-linked content unless a later reviewed allowlist admits specific fields. |
| Notification preferences (`dbo.notification_preferences`) | **Included after owner-scoped/dormant field allowlist** | This is distinct from the notifications inbox. Export only defined, nonsecret, member-owned preference fields and label dormant behavior truthfully; do not promise unsupported email or quiet-hours behavior. |
| Consent history | **Included, evidence-minimized** | Member event facts/version identifiers only; exclude raw claims, secrets, excessive evidence, and third-party content. |
| Audit events | **Excluded** | Security/audit disclosure needs a separate qualified decision. |
| Browser-local Interview history | **Unavailable** | Server export cannot gather browser-local history. |
| Interview telemetry | **Excluded** | Operational telemetry is not a member-content export domain. |
| AI proposals | **Included only by allowlist, noncanonical** | Safe member-scoped proposals/provenance only; no prompts, system instructions, raw telemetry, cache, or provider-retained data. |
| Ask Pete public | **Unavailable/excluded** | Public Ask Pete is not private account-export content. |
| Ask Pete Direct | **Third-party visitor content excluded** | Do not reveal visitor questions/contact data through a member export. |
| Projects | **Unavailable except career projects under Profile** | General Projects remains unavailable; include career-project records only where already part of the Profile owner contract. |
| Home | **Not duplicated** | Export underlying canonical sources where included, never a Home projection copy. |
| File/evidence metadata | **Safe references only** | Provider locators, raw bytes, Blob names, object keys, direct URLs, and credentials are excluded. |
| Indexes/caches/provider-retained/backups/PITR | **Unresolved/excluded** | Not canonical member-domain files; require retention, backup/PITR, privacy, and security decisions. |

Every domain has an explicit `included`, `excluded`, or `unavailable`
manifest disposition with a stable safe reason. The future experience must
distinguish an intentional v1 exclusion from runtime failure.

## C1 foundation: ledger and procedures

C1 must add an explicitly governed additive job ledger. The names below are an
architecture target, not a migration proposal or authorization to modify the
current schema.

### `account_export_jobs`

One row represents a request and derived artifact, never a copy of exported
member content. The later contract must define at least:

- an opaque server-generated `job_key uniqueidentifier` using `NEWID()`;
- resolved `owner_user_id` and `owner_profile_id`, never caller-selected IDs;
- state, requested/started/completed/expired timestamps, attempt count, lease
  token/expiry, and bounded safe failure code;
- a safe idempotency fingerprint/correlation; it must not retain raw request
  secrets or client identity material;
- assembly/cutoff timestamps and SQL consistency markers;
- final private artifact reference, final SHA-256, compressed size,
  uncompressed byte total, and cleanup state; and
- content-free operational correlation fields. Logs/status history may not
  contain archive members, member content, object names, URLs, SAS, provider
  response bodies, credentials, or tokens.

C1 must enforce one active job per owner over at least `queued`, `running`, and
`ready` before expiry, using a reviewable filtered unique constraint or
transactional procedure. It must enforce the provisional per-owner request
limit of one request per 24 hours even when a browser retries. These values are
not current product policy; they remain owner decisions pending approval.

### `account_export_job_domains`

This child ledger records only domain code, schema/version, disposition, read
start/end, source/change marker, record count, byte count, SHA-256,
provenance, and safe omission/failure reason. It stores no full domain body. It
supports a traceable manifest without becoming a second canonical store.

### Owner, worker, and domain-reader procedures

1. **Owner request/status/download metadata procedures** accept only a trusted
   server-derived `@UserKey` and, where needed, opaque job key. They resolve
   `app_users.id` and `member_profiles.profile_id` internally and enforce owner
   predicates. They never accept `@OwnerUserId`, `@OwnerProfileId`, a source
   table, Blob URL, or caller-selected artifact reference.
2. **Worker claim/complete/fail/expire/cleanup procedures** are reserved for
   the later dedicated worker identity. They claim leases atomically and fence
   every mutation on lease token/attempt; they cannot read arbitrary member
   content simply because they can update job state.
3. **Domain-reader procedures** are a fixed allowlist of owner-scoped readers.
   They never use dynamic SQL or caller-selected table names. No domain reaches
   C2 until its reader, redaction, and proof contracts are separately approved.

Duplicate form submits safely return the member's existing active job rather
than make another artifact. The C1 worker identity is future and dedicated; it
must not reuse the web-app identity or an unrelated maintenance identity.
Least-privilege SQL grants are a C1 proof obligation.

## C2 private artifact and workload design

C2 requires a separate owner approval for resource, provider spend, private
container, workload identity, grants, scheduler, and cleanup. Its proposed
shape is:

- a dedicated private export container with public access disabled: no account
  key, public ACL, anonymous read, direct browser access, or SAS issuance;
- a dedicated worker workload identity with only the required container and
  job-procedure permissions, distinct from the application and maintenance
  identities;
- a server-generated staging prefix scoped to one `job_key` and attempt;
  staging objects can never be downloaded;
- streaming assembly with compressed and uncompressed counters that fails
  safely at an approved cap;
- final private-object promotion/commit only after recomputing and recording
  final SHA-256 and byte size and successfully changing the ledger to `ready`;
  and
- ledger expiry that blocks download before physical deletion, followed by
  content-free idempotent final/staging cleanup retries that never resurrect or
  redeliver an artifact.

| Control | Provisional, unapproved C0 value |
| --- | --- |
| Active jobs per owner | 1 |
| Request rate | 1 per 24 hours |
| Attempts | 3 |
| Compressed ZIP cap | 100 MiB |
| Uncompressed assembly cap | 250 MiB |
| Ready window | 7 days |
| Worker pickup target | 15 minutes |

These are planning controls, not service levels, capacity commitments, or
user-facing promises. C1/C2 must obtain resource/spend approval and validate
them with bounded data before an experience represents them as behavior.

## Protected child sequence

Every child remains a distinct Protected package with a fresh exact-SHA
independent review. A repository merge never grants a schema operation,
resource creation, identity/grant, schedule, provider spend, or production
deployment.

| Child | Scope and dependencies | Review, rollback, and production boundary |
| --- | --- | --- |
| C0 `PS-SETTINGS-ACCOUNT-EXPORT-ARCHITECTURE-001` | This documentation architecture; depends on current authority and Settings context. | Independent review of this doc SHA; rollback is reverting the two C0 documents; no production authority. |
| C1 `PS-SETTINGS-ACCOUNT-EXPORT-FOUNDATION-001` | Future job/domain ledger migration, owner/worker procedures, idempotency/rate/lease enforcement, migration proof. Depends on accepted C0, current schema revalidation, and required security/privacy decisions. | Independent review plus additive migration/rollback proof. Schema apply requires separate production authority; no container/worker schedule yet. |
| C2 `PS-SETTINGS-ACCOUNT-EXPORT-ASSEMBLY-001` | Future private container, dedicated identity, secure adapter, deterministic assembly, hash/size, expiry/cleanup. Depends on C1 plus separately approved resource, spend, grants, and schedule. | Independent review and failure/cleanup proof. Rollback disables its approved workload/read path and cleans approved test artifacts; production actions are separate. |
| C3 `PS-SETTINGS-ACCOUNT-EXPORT-EXPERIENCE-001` | Accessible request/status/error/expiry/download experience. Depends on C1/C2 contract proof and locked visual authority if material direction changes. | Independent privacy/access review. UI rollback is repository withdrawal, never deletion of member data; no deployment authority. |
| C4 `PS-SETTINGS-ACCOUNT-EXPORT-RELEASE-PROOF-001` | Exact-main release and operational proof. Depends on accepted C1–C3 plus separately approved production operations. | Independent release review and exact-main/schema/container/identity/schedule proof. Uses a preapproved disable/revoke/revert plan, not a merge as rollback. |

B1 and D–F remain inactive. C0 neither activates them nor blocks unrelated
work. At the refreshed C0 checkpoint, active
`PS-WORKSHOP-USE-DISCLOSURE-001` owns `services/database_service.py` and
`SQL FIles/Migrations/registry.json`. That is a drift-prone **C1 preflight
fact** to recheck on C1 activation; it is not a C0 blocker and C0 does not
coordinate or alter that program.

## Exact future proof plan

1. **C1 transitions:** prove state acceptance/refusal, lease fencing/recovery,
   duplicate idempotency, active-job/rate enforcement, expiry, and migration
   apply/verify/rollback.
2. **Two-member isolation:** with disposable synthetic members, prove request,
   status, every domain reader, and download refuse forged keys, guessed jobs,
   foreign rows, and deleted/inactive owners neutrally, while a reauthorized
   owner may see only that owner's truthful retained `expired` status.
3. **Delivery:** prove reauthorization before download, no cache exposure, no
   Blob/SAS URLs or direct container access, complete `application/zip`
   delivery only after final hash/size verification, and expiry download
   blocking with no ZIP body, provider/object name, or artifact disclosure.
4. **Artifact truth:** prove deterministic fixture assembly, manifest order,
   UTF-8/version/hash/count/byte facts, strict joint-data redaction, and
   explicit unavailable/excluded domain records.
5. **Failures and cleanup:** exercise worker crash/lease expiry, compressed or
   uncompressed oversize, timeout, hash mismatch, failed promotion, cleanup
   retry, and expiry-before-delete. Logs must remain content-free.
6. **Experience:** prove accessible queued/running/ready/failed/expired states,
   keyboard/assistive semantics, recovery, relevant no-JavaScript behavior,
   long content, narrow viewport, and no false readiness copy.
7. **C4 exact proof:** prove exact `origin/main`/deployed SHA, separately
   authorized schema action, private container, dedicated identity grants,
   schedule/workload, two-member isolation, expiry, final/staging cleanup,
   disabled/rollback path, and any provider/backup limitation.

## Decisions, qualified input, and evidence limit

**Recommended for later owner decision:** ZIP with versioned JSON/NDJSON; raw
media excluded from v1; raw audit/safety/moderation/provider telemetry excluded
from v1; and the listed controls treated as provisional. Provider resource or
spend approval is required before C2.

Joint-data redaction, provider retention/subprocessor disclosure, backups and
point-in-time restore, security/audit disclosure, legal holds, jurisdictional
access rights, and truthful wording for nonretrievable data require qualified
privacy/security input. This is not legal advice, privacy approval, or security
certification.

C0 performed no live production schema/domain inventory, two-member proof,
snapshot-isolation check, size/load test, container provisioning, grant or
schedule inspection, provider-retention review, professional review,
deployment, or cleanup proof. It does not claim matrix completeness, current
exportability, or an export available today.

Rollback is a repository revert of this record and its paired completion report.
There is no runtime, data, schema, provider, configuration, resource, schedule,
or production state to reverse.

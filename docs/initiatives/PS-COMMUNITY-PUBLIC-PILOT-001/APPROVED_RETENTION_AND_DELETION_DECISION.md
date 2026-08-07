# PS-COMMUNITY-PUBLIC-PILOT-001 — Proposed retention and deletion decision

## Decision status

- **Status: APPROVED by Pete on 2026-08-03**, exactly as proposed, scoped to
  this release wave.
- **Pete's exact words:** "This is alive for this update. We will readdress
  this when we hide this behind the signin experience." Given in reply to a
  restatement of the durations below (30-day content purge, 1-hour attachment
  byte deletion with 30-day metadata, 24-hour unattached uploads, 90-day
  body-free audit, 30-day idle draft expiry, no raw query retention, 7-day
  backup recovery with no long-term retention).
- **Scope of the approval:** the owner-authored public Community pilot in its
  current public-read shape. Pete has committed to re-examining this schedule
  when Community moves behind the sign-in experience, because that change
  alters who can reach the content and therefore what retention has to
  protect. Treat that as a scheduled revision trigger, not an open question:
  the durations below are live now.
- **Decision owner:** Pete
- **Still required before collection:** the matching deletion job, tests,
  production configuration, and live evidence must pass before the Community
  flag is enabled. Approval authorises that implementation; it is not by
  itself permission to collect content.
- **Legal status:** operational product decision, not legal advice or evidence
  of counsel approval.

## Revision trigger — sign-in gating

When Community moves behind the sign-in experience, this schedule must be
re-opened before that change ships. At minimum reconsider: whether "public
recipient copies" still applies when content is never anonymously readable;
whether the 30-day purge is still the right balance once the audience is
authenticated and known; and whether audit retention should lengthen when
actions are attributable to identified members. Any revision must be
versioned, dated, reflected in the public policy, and reverified before it
changes production behaviour, per "Legal holds and deletion exceptions" below.

## Proposed schedule

| Data or copy | While active | After removal, expiry, or completion | Enforced by |
|---|---|---|---|
| Public post and contribution bodies | Retain while the owner keeps the source published. | Revoke public access immediately. Permanently purge body and presentation fields after **30 days**, unless a scoped legal hold applies. Preserve only a body-free deletion tombstone needed to prevent stale reappearance. | Hourly SQL deletion job; authorization remains the immediate public gate. |
| Protected post and contribution revisions | Retain while the source is active so owner edits remain auditable. | Purge with the removed source after **30 days**, unless held. Revisions never remain publicly readable. | Hourly SQL deletion job. |
| Respond and Save rows | Retain while their referenced source remains accessible. | Delete immediately when the source is removed; private saves must not preserve inaccessible content. | Existing source-delete transaction plus verifier. |
| Ready attachment metadata and active Blob objects | Retain while the attached source remains active. Original PDF/XLSX bytes include any author-provided document content and properties that passed the narrow safety contract. | Revoke application delivery immediately. Claim physical deletion within **1 hour** and retry to completion. Purge SQL metadata with the source after **30 days**, except the minimum content-free cleanup state needed until Blob deletion succeeds. | SQL lease plus hourly cleanup worker. |
| Unattached, rejected, or failed uploads | Keep an unattached reservation for no more than **24 hours**; rejected and failed bytes are never public. | Claim physical deletion within **1 hour** after expiry or terminal scan result and retry to completion. | SQL lease plus hourly cleanup worker. |
| Azure Blob soft-deleted copies | None are intentionally retained as application-visible data. | Configure a **7-day** soft-delete recovery window; access remains denied and the provider purges the recoverable copy when that window expires. No permanent archive copy. | Production storage configuration evidence. |
| Body-free security/audit events | Retain only identifiers, action, actor, outcome, and timestamps; no post, reply, filename, or search body. | Purge after **90 days**, unless a scoped legal hold applies. | Daily SQL deletion job. |
| Transactional outbox rows | Retain pending rows until successfully processed. | Purge processed rows after **30 days**; purge abandoned rows after resolution and no later than **90 days**. No content body is stored. | Daily SQL deletion job with pending-row alerting. |
| Browser-local composer drafts | Keep only on the owner's current device; never send an unopened draft to PeerSlate. | Clear on successful publish or explicit clear. Automatically expire after **30 days without an edit**. | Versioned local-storage envelope and client cleanup. |
| Raw Community search queries | Do not retain. | Nothing to delete. Operational logs and audit rows must not contain the raw query. | Logging contract and negative tests. |
| Application caches and search indexes | The pilot creates no independent content cache or external search index. | Any later cache/index must authorize before projection and delete within **24 hours** of source removal; adding one requires a revised decision. | Current architecture plus future change gate. |
| Azure SQL point-in-time backups | Retain only the platform recovery copy needed for operations. | Configure a **7-day** short-term recovery window and **no long-term-retention copy** for the Community pilot. A purged row may remain in an access-restricted backup until that backup ages out; it is not restored except for authorized disaster recovery, after which deletion jobs rerun. | Production database retention/configuration evidence and restore procedure. |
| Malware-scan/provider metadata | Retain only the scan state and Blob tags required to keep unsafe files unavailable and complete cleanup. Community bytes are not sent to a generative AI provider. | Delete with the Blob/metadata lifecycle above, subject only to the provider's verified security-log retention contract. | Azure configuration/vendor register evidence. |
| Exports and Slate/Journal/AI projections | The pilot creates none. | Nothing to delete. Introducing any export or projection requires a new data-flow and schedule. | Negative integration tests and scope gate. |
| Public recipient copies | PeerSlate cannot recall screenshots, downloaded workbooks (including their document properties), browser caches, search-engine caches, or other copies made while content was public. | PeerSlate revokes its own routes immediately and handles supported takedown/de-index requests, but does not promise deletion from recipients' devices or independent services. | Plain-language policy and support process. |

## Known limit: a legal hold cannot save attachment bytes

Recorded 2026-08-04 after independent review (finding F5), because the
alternative is a hold that quietly does less than it appears to.

Attachment bytes are claimed for physical deletion within one hour of removal,
as this schedule requires. A legal hold placed after that hour therefore
cannot preserve the file — only the post text, revisions, and body-free
records the hold reaches. In practice a hold is almost always applied after a
removal is noticed, so **assume attachment bytes are already gone.**

Preserving attachments under hold would require deferring physical deletion
until the hold question is settled, which contradicts the one-hour commitment
Pete approved. That trade is deliberate and stays as approved; this note
exists so nobody relies on a hold to retain a file.

The same fact is why restoring a post returns its words but not its files,
which the Recently deleted screen and the public policy both state plainly.

## Legal holds and deletion exceptions

- A legal hold may suspend permanent purge only for specifically identified
  records, for a recorded reason, by an authorized operator, with a review
  date. A general “keep everything” hold is not allowed.
- Public access and attachment delivery remain revoked while a record is held.
- The hold marker and operational audit remain body-free. Held content remains
  access-restricted and is excluded from ordinary support access.
- Releasing a hold returns the record to its original deletion deadline; if
  that deadline already passed, the next job run purges it.
- Qualified legal requirements may require a revised schedule. Any revision
  must be versioned, dated, reflected in the public policy, and reverified
  before it changes production behavior.

## Implementation status — 2026-08-03

`PS-COMMUNITY-RETENTION-001` implements this schedule in SQL and **passes the
disposable proof at run 424** (`none_proof_passed`, cleanup confirmed,
retention lease 616 protects the evidence).

| Requirement | State |
|---|---|
| Purge-eligibility and Blob-completion state (item 1) | Done — reuses existing `deleted_at_utc` and `blob_cleanup_completed_at_utc`, adds `purged_at_utc` |
| Scoped legal hold, body-free (item 1) | Done — reason code, operator, timestamp, mandatory future review date; a partial hold is rejected by constraint |
| 30-day content purge (item 2) | Done — `usp_PurgeCommunityContent` nulls bodies and keeps a body-free tombstone so a purged post cannot reappear; revisions go with their source |
| Media metadata purge (item 2) | Done — only once the Blob bytes are confirmed deleted, so metadata never vanishes while bytes remain |
| 90-day body-free audit purge (item 2) | Done — `usp_PurgeCommunityAuditEvents` |
| 30/90-day outbox cleanup (item 2) | Done — `usp_PurgeCommunityOutbox` |
| Idempotent, bounded, concurrency-safe (item 2) | Done — batch-limited, `UPDLOCK`/`READPAST` claiming, range-checked parameters |
| Rollback safety | Done — refuses while any record is held, since dropping the hold columns would silently release it |

**Scheduler — superseded 2026-08-07.** The earlier request-cadence scheduler
created an avoidable site-wide failure and latency boundary. The recovery in
`COMMUNITY_REVIVAL_SAFETY_ARCHITECTURE_2026-08-07.md` removes all Community
maintenance from Flask request paths. `scripts/run_community_maintenance.py`
runs the same bounded purges on an hourly Azure schedule under a separate,
default-off maintenance flag. A failed batch fails the scheduler run, remains
eligible for retry, and cannot fail or delay a member request. Community
visibility and already-owed retention work are independent controls.

**Restore window — added 2026-08-03.** Pete: "I want people to be able to come
back and see what they did later on." Deletion was one-way, so the 30-day
window only delayed loss. `PS-COMMUNITY-RESTORE-001` turns it into a recovery
window: the author can list what is restorable and put a removed post or
contribution back. It refuses once the body is purged, while a record is under
legal hold, past the window, or when a contribution's parent post is still
removed. Other members' responses and saves are deliberately not resurrected —
they were deleted outright on removal and are not the author's to reinstate.
Proven at run 429 (`none_proof_passed`, cleanup confirmed, lease 622).

This does not change any approved duration. It changes what happens *during*
the 30 days from "waiting to be purged" to "recoverable by the author".

**All six implementation and evidence items are now complete.**

- **Item 3, draft idle expiry — done.** Both device-local draft surfaces carry
  a `saved_at` stamp and drop an expired draft on read, clearing its pending
  command too. An undated pre-upgrade draft is kept rather than discarded, and
  a backwards clock jump cannot delete a live draft. Nine behavioural cases in
  `tests/community_draft_expiry.test.js`, verified in a real JS engine.
- **Item 4, removal denies public reads — done.**
  `tests/test_community_removal_denies_public_routes.py` proves every public
  read procedure filters on a live publication state, excludes held and
  removed moderation, and that attachments additionally require their parent
  post to be published and public. The purge is proven to be later
  housekeeping rather than the protection.
- **Item 5, production configuration — done.** See
  `RETENTION_PRODUCTION_CONFIGURATION_EVIDENCE_2026-08-04.md`. Every approved
  commitment is met in live production; two honest gaps are recorded there
  (Defender for Storage is on the Free tier, and a *different* storage account
  used for transient Voice has soft delete off).
- **Item 6, public policy text — done.** The dated policy now states the
  implemented schedule plainly, including what PeerSlate *cannot* promise.
  `tests/test_community_policy_states_retention.py` pins every published
  number to the constant the software actually uses, so the policy cannot
  drift from the code.

**Still outstanding, but not retention items:**

- A member-facing entry point to Recently deleted. The page exists and is
  reachable, but nothing links to it yet.

## Required implementation and evidence after approval

1. Add SQL timestamps/state needed to distinguish public revocation, purge
   eligibility, Blob-cleanup completion, and a scoped hold without copying
   content into audit rows.
2. Add idempotent bounded jobs for the 30-day content/revision/media-metadata
   purge, 90-day audit purge, and 30/90-day outbox cleanup. Jobs must be safe
   across retries and concurrent workers.
3. Add the 30-day idle expiry to the device-local draft envelope.
4. Verify that removal immediately denies public detail, Feed, search, and
   attachment routes before any delayed purge runs.
5. Verify the exact production Azure SQL short-term retention, absence of
   long-term retention, Blob soft-delete window, private container/RBAC,
   Defender scan behavior, and deletion-worker schedule.
6. Update the dated public-pilot policy to state the implemented schedule
   plainly without promising deletion from recipient copies or unexpired
   recovery backups.
7. Record Pete's exact approval text/date and any qualified legal/security
   disposition in the completion record.

## Owner decision — recorded

Pete approved this schedule on 2026-08-03 exactly as proposed, live for this
release wave, with an explicit commitment to readdress it when Community moves
behind the sign-in experience. See "Decision status" above for his exact
words.

This authorizes implementation and verification of this schedule for the
narrow owner pilot. It does not approve broader member authoring, messaging,
AI use, or broad launch, and it does not by itself permit collecting content:
the deletion jobs and their evidence must pass first.

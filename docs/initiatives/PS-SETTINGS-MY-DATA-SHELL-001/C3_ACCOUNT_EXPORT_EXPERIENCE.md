# C3 account export experience

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-EXPERIENCE-001`
**Slice:** C3 — Protected, independent privacy/access review
**Status:** Implemented behind a default-off flag. Not deployed, no schema
applied, no container or worker identity provisioned.

## Decision

C3 is the member's own request, status, and download experience over the
already-merged C1 foundation and C2 assembly. It adds no canonical store, no
new procedure, no worker behaviour, and no second place that decides whose
data an export contains.

## Routes

| Route | Method | Purpose |
| --- | --- | --- |
| `/app/settings/export` | GET | Request control plus, if known, this member's current job |
| `/app/settings/export` | POST | Same-origin request; creates or returns the member's one active job |
| `/app/settings/export/<job_key>` | GET | Truthful status for one job this member owns |
| `/app/settings/export/<job_key>/download` | GET | Authenticated application proxy for the verified archive |

Every route returns `404` while `PEERSLATE_ACCOUNT_EXPORT_ENABLED` is false,
which is the default: no export can be requested, observed, or downloaded.

Merging is **not** a pure no-op, and an earlier draft of this document said it
was. Settings copy changes with the flag off — the single "Account-wide
export, deletion, and closure" row becomes a separate export row and deletion
row, both still saying not available. Independent review caught the
overclaim. What is true is narrower and worth stating precisely: merging adds
no capability a member can reach, and the reassurance that downloading does
not delete is rendered only when export actually exists, so a member is never
told about a feature that is switched off.

There is deliberately no "list my export jobs" read: C1 shipped no such
procedure, and inventing one would need a migration this claim does not own.
It is not required, because `usp_RequestAccountExportForOwner` returns the
member's existing active job under a lock rather than creating a second one,
so pressing Request again is the supported, idempotent way back to an
in-flight job after a lost session or on a new device. The session also
remembers the member's own job key as a convenience hint; ownership is
re-proved in SQL on every status and download read, so a stale or absent
hint can never widen access.

## Identity and authorization

- Identity is always derived server-side from `get_current_identity()`.
  No function in `services/account_export_experience_service.py` accepts a
  profile id, user id, email, or any other owner selector, so a route, form,
  query, header, cookie, or body value cannot influence whose export is read.
  Only `@UserKey` and `@JobKey` ever reach SQL, and a test asserts exactly
  that parameter list while supplying hostile form fields.
- Status and download re-derive identity and job ownership at access time.
  The procedures themselves filter every row by the resolved owner profile.
- Unknown, malformed, foreign, not-yet-ready, failed-and-cleaned, and expired
  jobs all produce the same neutral `404` with a byte-identical body, so a
  response cannot be used to learn whether a job key exists or belongs to
  somebody else. A member's own retained expired job is reported truthfully.
- `services/database_service.py` allowlists **only** the three member-facing
  procedures. The five worker procedures take no `@UserKey`, operate
  system-wide across owners, and belong to a separate worker identity, so
  nothing reachable from a browser request may name them. A test asserts both
  halves of that: the three present, the five absent.

## Delivery

Download is an authenticated application proxy, never a redirect:
`Content-Type: application/zip`, `Cache-Control: private, no-store`,
`Pragma: no-cache`, `X-Content-Type-Options: nosniff`. There is never a
public container URL, direct Blob URL, provider URL, or SAS URL.
`final_artifact_reference` is a private server-only locator that stops inside
the experience service; a test asserts it appears in neither the body nor any
header.

`AccountExportStorageService.read_final()` is the adapter's only read path.
It performs no authorization of its own — ownership is already proved in SQL
before it is called — and it recomputes the SHA-256 and compares it, with the
size, against the values the ledger committed at promotion. A replaced,
truncated, or corrupted object therefore fails closed rather than being
streamed to a member as if it were their verified export.

## Honesty

The screen renders domain truth from `DOMAINS` in
`services/account_export_domain_readers.py`, which states that it is the
single source of truth C3+ must read from, "never a second, hand-maintained
list". A member is told that an export contains **12 of the 30** kinds of
information PeerSlate holds about them, and every not-included domain is
listed with the ledger's own reason rather than a softened paraphrase.

Journal and Projects are among the omissions. The owner decided on
2026-08-31 to ship without them provided the screen says so plainly, and it
does — both on the export page and in Settings.

Settings previously carried one row reading "Account-wide export, deletion,
and closure — Not available today." After this slice those three no longer
share one truth, so the row is split: export becomes available while deletion
and closure remain honestly unavailable, with an explicit sentence that being
able to download your data does not delete it.

## Timing channel: mitigated structurally, residual recorded

A wall-clock assertion in a unit suite would be flaky and would offer false
comfort, so no timing test is claimed. What is asserted instead is the
structural property that carries most of the risk: the two cases an attacker
could actually learn from — "this job exists but is not yours" and "this job
does not exist" — refuse through an identical code path by construction. Both
issue the same procedure with the same parameters in the same order and return
the same refusal, with no cause-specific early return between them.

The malformed-key case deliberately short-circuits before any database call.
That is not a leak: it reveals only whether the value the caller themselves
supplied was a well-formed UUID, which they already know, and nothing about
any other member. A test asserts this asymmetry explicitly so it stays
intentional rather than drifting into an accident.

**Residual, honestly untested:** the database lookup's own timing. If the
procedure were measurably slower for a row that exists than for one that does
not, that difference would survive everything above. Proving or excluding it
needs a real database and a statistical harness, neither of which exists here.
Recorded as an open risk rather than silently assumed away.

## Recorded but not fixed here

- ~~DOMAINS reasons reach members verbatim, including internal package
  codes.~~ **Resolved by PS-SETTINGS-ACCOUNT-EXPORT-MEMBER-REASONS-001**: a
  presentation-only `_DOMAIN_REASONS` map now supplies plain-language
  sentences for every non-included domain, with a verbatim-truth fallback
  for anything unmapped and tests forcing coverage of every future domain.
  `DOMAINS` remains the single source of truth and was not edited.
- ~~No rate limit on the download proxy. It buffers a whole archive in
  memory per request.~~ **Resolved by
  PS-SETTINGS-ACCOUNT-EXPORT-AVAILABILITY-001**: the three export routes
  now carry per-client budgets (request POST 10/hour, page and status
  GETs 60/minute, download 30/hour) declared in `owner_routes.py` and
  applied by `app.py`'s post-registration limiter idiom, and `read_final`
  now refuses an oversized or ledger-disagreeing object from the
  provider-reported size BEFORE downloading a byte, keeping every
  post-read verification. Authorization was and is unaffected, and a 429
  is keyed on the caller, never the job. Budget reasoning — including why
  the download number is 30/hour — is in `CR10_EXPORT_AVAILABILITY.md`.
- ~~Expiry is not deletion. `usp_ExpireAccountExportJobs` marks a ready
  job expired, and `cleanup_final` can delete the object, but nothing
  schedules either.~~ **Resolved in code by
  PS-SETTINGS-ACCOUNT-EXPORT-WORKER-OPS-001**
  (`CR11_EXPORT_WORKER_OPS.md`): the worker's `--maintenance` mode runs
  `usp_ExpireAccountExportJobs`, then deletes the physical objects for
  exactly the past-ready jobs the ledger marks cleanup-pending —
  `cleanup_final` unconditionally plus per-attempt staging — marking
  each job cleaned through `usp_CleanupAccountExportJob` only after its
  deletes succeeded. Still scheduled nowhere: the worker-host decision
  remains separately gated, and enabling the feature for real members
  without scheduling maintenance would reopen this gap.

## Limitations

- No live database or Blob proof. Every test uses a fake cursor or a fake
  storage adapter; nothing here has run against a real database or container.
- The worker that actually produces an archive is C2's and is not running
  anywhere yet, so with the flag on and no worker, a requested job would stay
  `queued`. Enabling the flag is therefore not by itself a working feature.
- No migration, schema apply, container provisioning, worker identity,
  deployment, or production operation is claimed or performed here.

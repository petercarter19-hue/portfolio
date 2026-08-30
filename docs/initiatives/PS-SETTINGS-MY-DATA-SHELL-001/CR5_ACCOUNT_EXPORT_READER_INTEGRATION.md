# CR5 account export reader integration

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-READER-INTEGRATION-001`
**Slice:** CR5 -- Protected, reader-to-assembly wiring. No migration, no
gate: this package ships no SQL file and touches
`SQL FIles/Migrations/registry.json` nowhere, so there is no gate
machinery to run or record (unlike CR1-CR4, each of which added its own
reader migration).
**Depends on:** accepted C0 (`C0_ACCOUNT_EXPORT_ARCHITECTURE.md`),
accepted C1 (`C1_ACCOUNT_EXPORT_FOUNDATION.md`), accepted C2
(`C2_ACCOUNT_EXPORT_ASSEMBLY.md`), and the four accepted reader
packages CR1-CR4 (`CR1_ACCOUNT_EXPORT_CORE_READERS.md` through
`CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md`), which together left
`services/account_export_domain_readers.py`'s `DOMAINS` registry with
seven included domains and twenty-two readers, closed, tested, and
wired to nothing.
**Status:** Candidate. This writer's own commits made no database
connection, no Azure call, and no network call of any kind. Every test
in this package uses a fake DB cursor/connection; the private container
and workload identity C2's own report already recorded are untouched by
this candidate.

## Decision

CR5 replaces `scripts/run_account_export_worker.py`'s C2 fixture-only
content source with the real, closed reader program CR1-CR4 built: a
claimed export job now assembles the member's actual allowlisted
domains through `services/account_export_domain_readers.py`'s `DOMAINS`
registry, under the same owner-active check, lease-fenced claim, and
caps C2 already established. It creates no table, procedure, route,
UI, schedule, container, or identity, and authorizes no production
apply. It reads no real member data itself -- every test remains
offline, against fake cursors/connections -- and production authority
remains withheld.

The C2 fixture worker's own tripwire
(`ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED`, `build_fixture_domain_
files`) is retired in the same commit that wires the real readers in,
replaced by `tests/test_account_export_integration.py`'s own pinning
tests (every `DOMAINS` included reader invoked exactly once per job; no
fixture source left in the module).

## What changed, precisely

| Before (C2) | After (CR5) |
| --- | --- |
| `build_fixture_domain_files(start, end)` returns 3 hardcoded, obviously-synthetic entries (1 included, 1 excluded, 1 unavailable). | `build_domain_files_from_readers(connection, user_key)` returns 45 entries today: one per reader for all 22 readers across the 7 included domains, plus one per each of the 23 non-included domains, both counts derived from the live `DOMAINS` dict, not hardcoded in the builder itself. |
| `main()` refuses to run unless `ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED` is set. | That environment variable and its check are deleted. The mission brief's own instruction is explicit: retire the tripwire in the same commit that makes it false, "replacing it with tests," not with a new runtime confirmation flag. |
| `run_once(connection, *, fixture_domain_files)` -- the injected callable takes two ISO timestamp strings and returns a canned list. | `run_once(connection, *, domain_files_builder)` -- the injected callable takes `(connection, user_key)` and does the real reading. `main()`'s only call site is updated to pass the real builder; no other call site existed. |
| The assembly window (`assembly_started_at_utc` -> `assembly_cutoff_at_utc`) bracketed no real work -- the old fixture builder did no I/O. | The assembly window now actually brackets the real domain reads: `read_consistency_marker` (start) -> `domain_files_builder(...)` -> `read_consistency_marker` (cutoff), matching C0's own "assembly start and cutoff... SQL consistency markers" contract for the first time in this program. |
| `services/account_export_assembly_service.py`'s `_validate_domain_file` required an "included" file's `content` to be non-empty bytes. | Relaxed to require only that `content` is `bytes` -- empty is now valid. A real reader can truthfully find zero rows for a genuine member (e.g. never created a Capture); that is an honest "included, 0 records" fact, not an error. The old fixture never exercised this because it always fabricated exactly one row. |

## Identity: one path only

C0's trust boundary and this claim's own brief are explicit that there
is exactly one legitimate way to know which member an export belongs
to: the identity the job row itself carries, ultimately traceable to
the `@UserKey` the member's own original `POST` resolved through
`usp_RequestAccountExportForOwner`. The problem CR5 had to solve
without inventing a second path: `usp_ClaimAccountExportJob`'s own
result columns are `job_key, owner_user_id, owner_profile_id,
attempt_count, lease_token, lease_expires_at_utc` only (recorded in
`C2_ACCOUNT_EXPORT_ASSEMBLY.md`) -- no `@UserKey`/`user_key` string --
while every domain-reader procedure in
`services/account_export_domain_readers.py` accepts only that same
external `@UserKey` string, never an internal `owner_user_id`/
`owner_profile_id` pair.

`fetch_owner_user_key(cursor, owner_user_id, owner_profile_id)`
resolves this the same way C2 itself already resolved two structurally
identical gaps (`is_owner_active`, `fetch_requested_at_utc`): a direct,
parameterized, single-purpose `SELECT` scoped by the exact ids the
claim procedure itself just returned, never a caller-supplied value,
never a fresh credential/session check, never a second predicate that
could disagree with what the claim already decided. It is a format
translation of one already-settled identity, not a second resolution
of who the owner is -- the same row, the same two ids, one more column
read off it. The `active = 1` predicate is repeated in this query even
though `is_owner_active` already confirmed it immediately before this
call in `run_once`, so the function's own SQL text stays independently
correct regardless of call order.

**Considered and rejected:** merging this lookup into `is_owner_active`
itself (one round trip instead of two). Rejected because
`is_owner_active`'s exact boolean-returning signature is directly
pinned by `tests/test_account_export_storage.py`'s
`WorkerOwnerActiveHelperTests` -- a read-only sibling test this claim
must not modify -- so changing its shape was not available. Two small,
single-purpose reads is also more auditable than one wider one for a
"hand-run, bounded" worker where round-trip count is not a stated
concern.

## Manifest/ledger agreement -- the central proof, and its honest limit

C1's child ledger, `dbo.account_export_job_domains`, has a real schema
(confirmed by reading
`SQL FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_foundation.sql`
directly) but **no writer procedure at all** -- C1's own text: "No
procedure in this migration writes to this table... population is
deferred to a future, separately claimed domain-reader slice." This
claim's surfaces include no SQL file (confirmed: the claimed
non-governance surfaces are two service/script files, two test files,
these two documents, and -- via the two governed extend-surfaces
transitions -- `.env.example` and the C2 assembly design doc), so
nothing in this package can `INSERT` a real ledger row. This is a genuine tension between the mission's own wording
("the C1 ledger provably agreeing... the counts committed to the C1
ledger") and what this claim's surfaces can actually do -- disclosed
here rather than quietly reinterpreted:

- The **aggregate** facts that DO reach a real, live ledger row today
  (`compressed_size_bytes`, `uncompressed_size_bytes`,
  `final_artifact_sha256`, via `usp_CompleteAccountExportJob`) are
  unchanged by this package. They still come from
  `AccountExportStorageService.promote()`'s own independent readback of
  the actually-persisted bytes, never from a pre-upload estimate --
  this was already true in C2 and remains true here, now exercised
  against real-reader-shaped content instead of one fixture file
  (`ManifestLedgerZipThreeWayAgreementTests.
  test_full_pipeline_through_the_real_storage_adapter_agrees_on_final_bytes`
  in `tests/test_account_export_integration.py`).
- The **per-domain** facts C0's V1 domain matrix and
  `dbo.account_export_job_domains`'s own columns anticipate
  (`domain_code`, `disposition`, `record_count`, `byte_count`,
  `content_sha256`, `read_started_at_utc`/`read_ended_at_utc`,
  `omission_reason`/`failure_reason`) cannot be persisted by this
  claim. `summarize_domain_ledger(manifest)` and
  `domain_ledger_row_matches_check_shape(row)`
  (`scripts/run_account_export_worker.py`) instead compute, purely in
  Python from the manifest `assemble()` already produced, the EXACT row
  a future writer would need -- shaped and validated against
  `CK_account_export_job_domains_shape`'s real boolean logic, reimplemented
  faithfully (included requires every read fact and no reason; excluded
  requires only `omission_reason`; unavailable requires exactly one of
  the two reasons) -- and never write it anywhere.

What this package DOES prove, offline, end to end, across the real
22-reader/30-domain shape (`tests/test_account_export_integration.py`,
`ManifestLedgerZipThreeWayAgreementTests` and
`BuildDomainFilesFromRealReadersTests`):

1. Every manifest file entry's `record_count` equals the number of
   NDJSON lines actually reparsed out of that exact file's bytes inside
   the finished ZIP (`test_manifest_record_count_matches_actual_ndjson_
   lines_in_the_zip`).
2. Every manifest file entry's `byte_length`/`sha256` equal the
   reparsed content's own actual length/hash (same test).
3. `summarize_domain_ledger`'s per-domain totals equal the sum of that
   domain's own manifest file entries
   (`test_domain_ledger_summary_totals_match_manifest_totals_per_domain`).
4. Every one of the 30 domain rows the summary produces satisfies the
   real `CK_account_export_job_domains_shape` CHECK's logic
   (`test_domain_ledger_summary_rows_all_satisfy_the_real_check_constraint_shape`).
5. The grand total (`assembled["uncompressed_size_bytes"]`, the exact
   figure that will reach `usp_CompleteAccountExportJob`) equals the
   sum of every included domain's own `byte_count` in the summary
   (`test_aggregate_uncompressed_size_equals_sum_of_included_domain_
   byte_counts`), and equals what `AccountExportStorageService.
   promote()` independently recomputes from a full stage/promote round
   trip against a fake container
   (`test_full_pipeline_through_the_real_storage_adapter_agrees_on_
   final_bytes`).

`run_once` also runs the same shape check live (not only in tests) as a
defensive backstop: it refuses to complete a job whose own manifest
could not satisfy the real CHECK, before any storage write. Two tests
cover this region, each proving a different guard (corrected in the
independent-review round -- the original text credited the first test
with proving the backstop, which it never reaches):
`test_ledger_shape_backstop_fails_the_job_when_a_manifest_would_violate_the_check`
proves `summarize_domain_ledger`'s own mixed-disposition guard fires
first on conflicting inputs, and
`test_ledger_shape_backstop_itself_fails_the_job_on_a_shape_invalid_row`
reaches the backstop loop itself (by substituting the summary with a
shape-invalid row) and proves it fails the job before any storage
write. In ordinary operation the backstop is unreachable by
construction -- assembly's own `_validate_domain_file` already
guarantees every disposition's required and forbidden fields -- which
is exactly what makes it defence in depth rather than a code path with
business behavior.

**Disclosed gap, flagged for the manager:** actually persisting a
per-domain row into `dbo.account_export_job_domains` needs a new
stored procedure and an additive migration. This claim owns no SQL
surface and cannot author either. A future package would need to claim
`SQL FIles/Migrations/registry.json` (currently owned by another active
lane per this claim's own brief) and a new migration file, add exactly
one `INSERT`-capable procedure scoped by the worker's own dedicated
identity (never a caller-selected table or `@UserKey`, matching every
existing worker procedure's own shape), and call it once per domain
right where `run_once`'s shape-check backstop already runs today. This
package hands that future writer the exact row shape and validation
logic it would need (`summarize_domain_ledger`,
`domain_ledger_row_matches_check_shape`); it does not, and cannot,
finish the job itself.

## Determinism: the precise, honest statement

C2's own documented determinism claim was narrower than a casual
reading suggests: `AccountExportAssemblyService.assemble()` is a pure
function -- identical input always produces byte-identical output --
proved by calling it twice with the SAME hand-built `domain_files` list
in `tests/test_account_export_assembly.py`. That property is **unchanged
and still fully true** after this package
(`DeterminismStatementTests.
test_assemble_is_still_pure_given_identical_real_reader_shaped_input`
proves it again using real-reader-shaped input, not only the original
hand-built fixtures).

What was never separately true, and is now reachable for the first
time because real read-window timestamps flow into the manifest: **two
separate worker attempts at the same job are not byte-identical.**
Every included file's `read_window` carries the wall-clock timestamp
the reader call itself observed; a retry (a fresh `usp_ClaimAccountExportJob`
lease after a crash, a lease-expiry recovery) calls every reader again
and gets fresh timestamps even when every underlying row is completely
unchanged. Those timestamps are embedded in `manifest.json`, which is
hashed as part of the archive, so the final `sha256` legitimately
differs between attempts. `tests/test_account_export_integration.py`'s
`test_two_separate_attempts_with_different_read_windows_differ` proves
this directly: identical row VALUES, shifted read-window timestamps,
different manifests, different hashes.

This is not a regression this package introduced by carelessness -- it
is the literal, unavoidable consequence of C0's own instruction that
"each file reports its own read window" once that window is a REAL
timestamp instead of a fixed fixture string. Nothing in C0 actually
promises byte-identical re-assembly across attempts; that specific
phrase was always scoped to the assembly service's own pure-function
contract for testability, and this package makes the distinction
explicit rather than letting it be misread as a live-run guarantee.
What C0 actually requires, and what remains true across attempts, is
unchanged: every emitted byte is fully accounted for in the manifest,
every count/hash is independently recomputed from real content, and the
domain set/dispositions/reasons are stable for a given owner (`DOMAINS`
is a static Python dict, not a live query) -- "a bounded assembly
window, not an atomic request-time snapshot," exactly as C0 states.

One operational consequence worth naming (added in the
independent-review round): C2's storage contract is
one-final-object-ever (`overwrite=False`, a second promote surfaces
`storage_conflict`). Now that separate attempts legitimately differ in
bytes, a retry after an attempt that promoted and then crashed before
`complete_job` will collide with a genuinely different artifact, and
the ledger's recorded `sha256` belongs to whichever attempt promoted
first. Nothing here changes that contract or makes it false; it simply
means the first-promote-wins semantics are now doing real work, and a
future operational runbook should treat `storage_conflict` on retry as
"an artifact already exists for this job," not as corruption.

## Excluded/unavailable domains: the manifest contract, followed exactly

C0: "Every domain has an explicit included, excluded, or unavailable
manifest disposition with a stable safe reason. The future experience
must distinguish an intentional v1 exclusion from runtime failure."
`build_domain_files_from_readers` walks every one of `DOMAINS`' 30
entries (confirmed by direct inspection at write time: 7 included, 23
not) and, for each non-included one, emits exactly one manifest file
carrying that domain's own `disposition` and its own `reason` string
**verbatim** -- `excluded` maps to `omission_reason`, `unavailable`
maps to `failure_reason`, never reworded, never dropped, never merged
into a generic catch-all message.
`test_excluded_and_unavailable_domains_carry_the_domains_reason_verbatim`
asserts this for every one of the 23 non-included domains individually
(`self.assertEqual(file_entry["omission_reason"], domain["reason"])`,
or the `failure_reason` equivalent). This directly satisfies the
mission's own instruction: "The DOMAINS dict's excluded entries carry
`reason` strings -- surface them per contract, never silently drop."

## Caps and failure: unchanged mechanism, now proven against real shapes

C0's two approved caps (100 MiB compressed / 250 MiB uncompressed) and
C2's two-layer enforcement (assembly's own incremental-then-final check;
storage's independent re-check on readback) are untouched by this
package -- no cap constant, no enforcement call site, changed. What
changes is that a cap breach can now originate from REAL reader content
rather than only a hand-built fixture, and `run_once`'s existing,
unmodified generic exception handling already covers that case
correctly: `AccountExportAssemblyError`'s `.code` attribute (e.g.
`"oversize_uncompressed"`) already passes straight through
`choose_failure_code_for_error`'s existing duck-typed mapping, with no
code change needed. `RunOnceOrchestrationTests.
test_oversize_content_fails_the_job_not_crashes` proves the failure path
(fail the job through the C1 lease-fenced procedure, never a crash) at
the `run_once` orchestration layer, deliberately isolated from
re-proving the cap arithmetic itself (already proven at the exact
boundary in `tests/test_account_export_assembly.py`, unchanged).
A domain-reader-level exception (a raw DB error, not a cap breach) is
proven to fail the same safe way, mapped to `internal_error`, in
`test_a_domain_reader_exception_fails_the_job_not_crashes`.

## The retired fixture tripwire

C2's fixture worker refused to run at all unless
`ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED` was explicitly set --
its entire purpose was to stop this exact worker from ever completing a
REAL member's queued job with fake content. That premise is now false:
`build_domain_files_from_readers` reads real content through the closed
reader program. `build_fixture_domain_files`, `FIXTURE_MODE_ENV`, and
the `main()` check against it are deleted in the same commit that wires
the real builder in
(`scripts/run_account_export_worker.py`), replaced by
`tests/test_account_export_integration.py`'s own pins:
`FixtureTripwireRetiredTests` confirms the fixture builder and the env
gate no longer exist as module attributes, that their defining source
text (not merely their name in prose) is gone, and that `main()` wires
the real builder by name;
`BuildDomainFilesFromRealReadersTests.
test_every_included_reader_is_invoked_exactly_once_with_the_owners_user_key`
confirms every one of the 22 real readers is actually invoked exactly
once per job (`connection.cursor_calls == 22`, every scripted plan step
consumed).

**A disclosed, honest conflict with the mission's own literal
wording.** The mission brief says: "find the C2 test asserting the
assembly is fixture-only / wires no real readers." No such test exists
in the repository as written -- confirmed by reading
`tests/test_account_export_assembly.py` and
`tests/test_account_export_storage.py` (the only two C2 test files) in
full and grepping every sibling test file for `FIXTURE_MODE`,
`fixture_only`, and `build_fixture_domain_files`; nothing matched. The
actual tripwire was runtime machinery (the environment-variable gate in
`main()`) and a hardcoded fixture-returning function, not a pytest
assertion. The claim's own outcome -- replace the fixture content
source, retire what made it necessary, prove the replacement -- is
unaffected by this factual correction to the brief's premise, and is
fully delivered regardless of which artifact literally functioned as
"the tripwire."

## What remains fixture-free but still unproven live

- **No live database call by this writer, anywhere.** Every reader
  invocation in every test in this package is against a fake
  cursor/connection. `services/account_export_domain_readers.py`'s own
  procedures were proven against a real engine by CR1-CR4's own gate
  rounds (already sealed, per those packages' own completion reports);
  this package re-proves none of that and re-opens none of it.
- **No live Blob Storage call by this writer or by any test.**
  `tests/test_account_export_integration.py`'s own storage-adapter test
  uses a small, locally-defined fake container, matching
  `tests/test_account_export_storage.py`'s own established style.
- **No live end-to-end worker run.** `scripts/run_account_export_worker.py`
  has never been executed against a real database or container by this
  candidate -- only `run_once`'s full orchestration logic is now
  exercised end to end, offline, against fake doubles
  (`RunOnceOrchestrationTests`), closing the one gap C2's own completion
  report flagged ("`run_once`'s full orchestration... is not covered by
  an automated test").
- **No route, UI, or scheduler reaches any of this code**, unchanged
  from C2. Account-wide export remains unavailable to any real member
  today.
- **The two pending Azure grant layers C2's report recorded** (the
  workload identity's container-scoped RBAC role; the SQL-side
  `EXECUTE` grants for the five worker procedures) are untouched by
  this package and remain exactly as C2 left them: pending the owner's
  and the AAD-admin path's separate authorization.

## Protected child sequence

This package sits alongside CR1-CR4 in C0's Protected child sequence as
a reader-integration slice of C2/C3, not a new numbered child of its
own. Rollback is a repository revert of the files this candidate
changes (`scripts/run_account_export_worker.py`,
`services/account_export_assembly_service.py`, and their two test
files); there is no schema, data, resource, configuration, or
production state to reverse, because this candidate created none.

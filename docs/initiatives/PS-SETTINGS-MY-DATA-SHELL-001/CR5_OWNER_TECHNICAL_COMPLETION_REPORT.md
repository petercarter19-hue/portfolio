# CR5 owner technical completion report

## Core record

- **Task/package and delivery path:**
  `PS-SETTINGS-ACCOUNT-EXPORT-READER-INTEGRATION-001`, Protected. No
  migration, no gate: this package ships no SQL file and does not touch
  `SQL FIles/Migrations/registry.json` -- there is no `gate: null`
  machinery to author or execute here, unlike CR1-CR4, each of which
  added its own reader migration and registry entry.
- **Outcome and candidate scope:** Replaced
  `scripts/run_account_export_worker.py`'s C2 fixture-only content
  source with the real, closed reader program CR1-CR4 built
  (`services/account_export_domain_readers.py`'s `DOMAINS` registry: 7
  included domains, 22 readers). A claimed export job now assembles the
  member's actual allowlisted domains through those readers under the
  same owner-active check, lease-fenced claim, and 100 MiB/250 MiB caps
  C2 already established -- content source swapped, everything else
  preserved. The C2 fixture tripwire
  (`build_fixture_domain_files`, `ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_
  CONFIRMED`) is retired in the same commit that wires the real readers
  in, replaced by `tests/test_account_export_integration.py`'s own
  pinning tests. One new identity-translation read
  (`fetch_owner_user_key`) resolves the reader-required `@UserKey` from
  the job's own already-resolved `owner_user_id`/`owner_profile_id` --
  not a second identity-resolution path. A pure, offline
  manifest/ledger-agreement computation
  (`summarize_domain_ledger`, `domain_ledger_row_matches_check_shape`)
  proves per-domain counts agree across the manifest, the actual ZIP
  bytes, and the shape C1's real (currently writer-less)
  `dbo.account_export_job_domains` CHECK constraint would require,
  without ever writing to that table -- disclosed below as an
  out-of-scope gap needing a future SQL surface this claim does not
  have. `services/account_export_assembly_service.py`'s "included must
  be non-empty" rule was relaxed to allow a truthful zero-row domain.
  No table, procedure, route, UI, schedule, container, or identity is
  added or changed. No database connection, Azure call, or network call
  of any kind was made by this writer or by any test in this candidate.
- **Package manager and writer:** Sole writer
  `agent:claude-code/settings-int-writer`, working only in the durable
  worktree
  `C:\Users\peter\Documents\PeerSlateWorktrees\PS-SETTINGS-ACCOUNT-EXPORT-READER-INTEGRATION-001`
  on branch `work/2026-08-30-settings-account-export-reader-integration-001`.
  The claim named six non-governance surfaces this writer owned at the
  time of the writer's own round (two governed extend-surfaces
  transitions later added `.env.example` and the C2 assembly design
  doc — see the correction-round section); three sibling paths
  (the claim JSON, its evidence file, its receipts file) are reserved
  for the manager's gate/review stage and were not touched, matching
  every prior package's identical exclusion. `git status --short`
  before each commit confirmed no file outside the then-six claimed
  surfaces was ever staged.
- **Base SHA and branch:** Activated from `origin/main` `a7285103187386698f2518137eac7ed0a6853ff4`
  (`git rev-parse HEAD` on this worktree, confirmed clean and matching
  before any write). No other commit had landed on this branch before
  this candidate.
- **Final SHA:** This report is authored, per house convention (see the
  accepted `CR4_OWNER_TECHNICAL_COMPLETION_REPORT.md`'s identical
  practice), **before** its own commit exists -- it cannot record a
  SHA it has not yet produced. The four commits that make up this
  candidate up to and including this file are, in order:
  `3ebbc85c` (assembly relaxation), `24d0974b` (worker rewrite +
  integration tests), `032b36f4` (the CR5 design record), and this
  report's own commit, whose exact hash is in the writer's chat-turn
  final message and in `git log` on the pushed branch.
- **Candidate changed paths** (three modified, two new; nothing else in
  the worktree was touched):
  - `services/account_export_assembly_service.py` (modified, +39/-10
    lines including comments -- the "included may be empty" relaxation)
  - `scripts/run_account_export_worker.py` (modified, +490/-96 lines,
    921 total -- the real-reader wiring, identity translation, ledger
    summary, restated determinism, retired fixture)
  - `tests/test_account_export_assembly.py` (modified, +30 lines --
    two new tests for the relaxation)
  - `tests/test_account_export_integration.py` (new, 1,049 lines, 42
    tests / 176 subtests)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR5_ACCOUNT_EXPORT_READER_INTEGRATION.md`
    (new, 342 lines)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR5_OWNER_TECHNICAL_COMPLETION_REPORT.md`
    (this file, new)
- **Excluded actions and paths:**
  `docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-READER-INTEGRATION-001.json`,
  its `evidence/*.md`, and its `receipts/*.json` were not created or
  modified. `SQL FIles/Migrations/registry.json` and every SQL file
  under `SQL FIles/` were read (for `dbo.account_export_job_domains`'s
  exact column names and `CK_account_export_job_domains_shape`'s exact
  logic) but never modified -- confirmed by `git status --short`
  showing no changes under `SQL FIles/` at any commit. No route,
  template, worker scheduling, container, workload identity, grant,
  `.env.example` entry, or dependency changed. No database connection,
  Azure call, or network call of any kind was made by this writer or by
  any test in this candidate.

## Design decisions worth the reviewer's attention

Full reasoning for each lives in
`CR5_ACCOUNT_EXPORT_READER_INTEGRATION.md`; this section lists only the
decisions with the widest blast radius.

1. **The mission brief's own "find the C2 test asserting the assembly
   is fixture-only" instruction does not describe a real artifact.**
   Both C2 test files (`tests/test_account_export_assembly.py`,
   `tests/test_account_export_storage.py`) were read in full; neither
   contains such an assertion, and a repository-wide grep for
   `FIXTURE_MODE`, `fixture_only`, and `build_fixture_domain_files`
   across every test file found nothing outside
   `scripts/run_account_export_worker.py` itself. The actual tripwire
   was runtime machinery -- the `ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_
   CONFIRMED` environment-variable gate in `main()` and the
   `build_fixture_domain_files` function -- not a pytest assertion.
   Both are deleted in the same commit (`24d0974b`) that wires the real
   readers in, replaced by `tests/test_account_export_integration.py`'s
   `FixtureTripwireRetiredTests` and the reader-invocation-count tests.
   The claim's actual outcome (replace the content source, retire what
   made the confirmation necessary, prove the replacement with tests)
   is fully delivered; only the brief's own description of which
   artifact functioned as "the test" was corrected.
2. **`account_export_job_domains` gets no writer in this package --
   disclosed, not silently worked around.** The mission text asks for
   "the C1 ledger provably agreeing," but C1's own migration comment is
   explicit that no procedure writes that table, and this claim's six
   surfaces include no SQL file. Reading the real table DDL directly
   (`SQL FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_
   foundation.sql`) to get its exact column names and
   `CK_account_export_job_domains_shape`'s exact boolean logic,
   `summarize_domain_ledger`/`domain_ledger_row_matches_check_shape`
   compute and validate the EXACT row a future writer would need,
   purely in Python, from the manifest alone -- proving the strongest
   agreement this claim's surfaces allow (manifest per-file facts, the
   actual ZIP bytes, and the shape a real `INSERT` would need, all
   agree) without ever inserting anything. Flagged prominently in
   "What needs a surface extension" below, not glossed over.
3. **`fetch_owner_user_key` is a new, second database read, not merged
   into `is_owner_active`.** Merging them would save one round trip,
   but `is_owner_active`'s exact boolean-returning signature is pinned
   by `tests/test_account_export_storage.py`'s
   `WorkerOwnerActiveHelperTests` -- a read-only sibling test this claim
   must not modify -- so its shape could not change. Two small,
   single-purpose, independently-correct reads were chosen over one
   wider one that would have required touching an unclaimed test file.
4. **The assembly window now brackets real work for the first time.**
   The old fixture builder did no I/O, so `assembly_started_at_utc` ->
   `assembly_cutoff_at_utc` bracketed nothing. This candidate moved
   `domain_files_builder(...)`'s call to between the start and cutoff
   `read_consistency_marker` reads, so the window and the `@@DBTS`
   markers now actually describe the real domain-read work, matching
   C0's own contract for the first time in this program. This is a
   behavior change worth a reviewer's attention even though it required
   no new code beyond reordering three existing lines.
5. **`_iso_z` was changed to force fixed-width microseconds
   (`timespec="microseconds"`).** `datetime.isoformat()` silently omits
   the fractional-second field when it is exactly zero, which would
   make plain string comparison of two timestamps disagree with true
   chronological order whenever one has a zero microsecond component
   and the other does not. This was latent and harmless in C2 (nothing
   compared these strings), but `summarize_domain_ledger`'s
   `min()`/`max()` over per-file read-window strings depends on it
   being fixed-width. Verified this does not change any sibling test's
   expectations: neither `tests/test_account_export_assembly.py` nor
   `tests/test_account_export_storage.py` references `_iso_z` at all
   (confirmed by reading both files in full before this change).
6. **`account_export_assembly_service._validate_domain_file` no longer
   requires an included file's content to be non-empty.** A real reader
   can truthfully return zero rows for a genuine member; the old rule
   (`or not content`) would have rejected that truthful case with
   `invalid_domain_input`. Only the type check (`isinstance(content,
   bytes)`) remains. Two new tests pin both the newly-allowed case and
   that the type check still rejects `None`/`str`/other non-bytes
   values.
7. **A reader exception is never caught or partially tolerated inside
   `build_domain_files_from_readers`.** A partial export (some domains
   present, others silently missing because one reader failed) would be
   a truth violation -- a manifest that looks complete but is not. Every
   reader failure propagates to `run_once`'s existing, unmodified
   generic exception handler, which already fails the whole attempt
   safely and requeues while attempts remain.

## Validation and self-review

**Verbatim final run** (checked by exit code directly, output
redirected to a file rather than piped):

```
ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m pytest -q tests/test_account_export_assembly.py tests/test_account_export_integration.py tests/test_account_export_storage.py tests/test_settings_export_core_readers.py tests/test_settings_export_capture_moment_readers.py tests/test_settings_export_workshop_reader.py tests/test_settings_export_oppslate_reader.py tests/test_settings_account_export_migration.py
333 passed, 2282 subtests passed in 85.54s (0:01:25)
PYTEST_EXIT_CODE=0
```

(Figures are from the independent-review correction round's rerun of
the identical command; the pre-correction candidate's run was
`332 passed, 2282 subtests` — the delta is the one new backstop test
added for finding F1.)

Per-file breakdown from the same run (individually confirmed):

| File | Tests | Subtests |
| --- | --- | --- |
| `tests/test_account_export_assembly.py` | 21 (19 original + 2 new) | 9 |
| `tests/test_account_export_integration.py` (new) | 43 | 176 |
| `tests/test_account_export_storage.py` (unchanged) | 31 | 14 |
| `tests/test_settings_export_core_readers.py` (unchanged) | 42 | 583 |
| `tests/test_settings_export_capture_moment_readers.py` (unchanged) | 52 | 510 |
| `tests/test_settings_export_workshop_reader.py` (unchanged) | 48 | 354 |
| `tests/test_settings_export_oppslate_reader.py` (unchanged) | 55 | 530 |
| `tests/test_settings_account_export_migration.py` (unchanged) | 41 | 106 |
| **Total** | **333** | **2282** |

**Also run via `python -m unittest`** (the actual CI mechanism, output
redirected to a file, exit code read directly, never through a pipe):

```
ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m unittest -q tests.test_account_export_assembly tests.test_account_export_integration tests.test_account_export_storage tests.test_settings_export_core_readers tests.test_settings_export_capture_moment_readers tests.test_settings_export_workshop_reader tests.test_settings_export_oppslate_reader tests.test_settings_account_export_migration
Ran 333 tests in 83.497s
OK
UNITTEST_EXIT_CODE=0
```

**Full-repository collection check.** `pytest --collect-only -q tests/`
against this worktree's own (narrow, cone-mode) sparse-checkout first
reported 95 collection errors -- confirmed, by reading the errors
directly, to be entirely `ModuleNotFoundError`/`FileNotFoundError`
against top-level modules and docs this worktree's sparse-checkout
simply never materialized (`app`, `db`, `ask_pete_direct_routes`, the
`qa` package, `docs/AI_MODEL_AND_ROLE_ROUTING.md`), none of them
account-export-related and none of them touched by this candidate.
Confirmed by temporarily running `git sparse-checkout disable` to
materialize the full repository and re-running the identical command:
**4,622 tests collected, exit code 0, zero collection errors.** The
sparse-checkout was then restored to its original narrower footprint
(`git sparse-checkout set --skip-checks <original file list>`), and a
follow-up run of this package's own two test files (63 tests, 185
subtests, exit 0) confirmed the restore did not disturb anything.

**Real defects found and fixed during self-review, before this report
was written:**

1. A test-authoring bug (not a bug in the shipped code) in this
   package's own `DeterminismStatementTests.
   test_two_separate_attempts_with_different_read_windows_differ`: an
   early draft used `hasattr(value, "replace")` to detect a `datetime`
   worth shifting, which is also true of a plain `str` (Python strings
   have their own, differently-shaped `.replace`), raising
   `AttributeError: 'str' object has no attribute 'hour'` on the
   unrelated `"UNUSED-FALLBACK-START"` marker strings. Fixed with an
   explicit `isinstance(value, datetime)` check.
2. A test-authoring bug (not a bug in the shipped code) across four
   `RunOnceOrchestrationTests` methods: the fake `"clock"` plan steps
   standing in for `read_consistency_marker`'s `@@DBTS` reads were
   given `datetime` values, but `read_consistency_marker` calls
   `bytes(value)` on whatever comes back -- `bytes(datetime(...))`
   raises `TypeError`, which `choose_failure_code_for_error` correctly,
   if confusingly, mapped to `internal_error` regardless of which real
   failure a given test was trying to isolate (masking, for example,
   the intended `oversize_uncompressed` code in
   `test_oversize_content_fails_the_job_not_crashes`). Fixed by using
   bytes-shaped fake marker values (`FAKE_DBTS_MARKER_START`/`_CUTOFF`)
   for every consistency-marker plan step, distinct from the
   `datetime`-shaped values correctly used for the separate
   `SYSUTCDATETIME()`-style clock reads inside the domain-reader fakes.
3. A dangling documentation cross-reference in this package's own edit
   to `services/account_export_assembly_service.py`'s module docstring
   (a `(see "Included may be empty" below)` pointer to a section
   heading that was never actually created). Caught on a re-read before
   committing; corrected to point at the actual code comment instead of
   an invented heading.
4. An overly strict test in this package's own
   `FixtureTripwireRetiredTests.
   test_fixture_source_text_is_gone_from_the_module`: the first draft
   asserted the bare string `"build_fixture_domain_files"` appeared
   nowhere in the file, which failed against this package's OWN
   rewritten module docstring (which names the retired function in
   explanatory prose, exactly as this report and the CR5 design record
   also do). Corrected to check for the actual code-level constructs
   (`"def build_fixture_domain_files"`,
   `os.environ.get(FIXTURE_MODE_ENV`, etc.) rather than a bare
   substring match against prose.
5. A manual smoke-test script (never committed, scratchpad-only, used
   to validate `build_domain_files_from_readers`/`summarize_domain_
   ledger` before writing the full test suite) surfaced the same
   `bytes(datetime(...))` mismatch described in item 2, one level
   earlier -- confirming the shipped code's own calling convention
   (real read-window values must be `datetime`-shaped, not strings)
   was correct and the bug was confined to test scaffolding both times.

No defect was found in the shipped, non-test code beyond what the five
items above already describe as test-authoring corrections.

## Independent-review correction round (manager, 2026-08-30)

The independent review of candidate `1352a0e9` returned **CONDITIONAL**:
C1 lease/owner-active discipline, the single identity path, the
three-way manifest/content agreement, zero-row honesty, tripwire
retirement, scope exactness, and excluded-domain handling all PASSED,
with 11 of 12 mutation probes caught. Six findings were addressed in
this round, in one commit:

1. **F1 (MEDIUM):** the design record credited
   `test_ledger_shape_backstop_fails_the_job_when_a_manifest_would_violate_the_check`
   with proving the CHECK-shape backstop fires; in fact that test trips
   `summarize_domain_ledger`'s mixed-disposition guard before the
   backstop loop, which had zero coverage (the reviewer's probe deleted
   the backstop and the suite stayed green). Fixed with substance, not
   wording alone: a new test
   (`test_ledger_shape_backstop_itself_fails_the_job_on_a_shape_invalid_row`)
   substitutes a shape-invalid summary row, reaches the backstop
   itself, and proves the job fails before any storage write; the
   design record now credits each test with exactly what it proves.
2. **F2 (MEDIUM):** a new Limitations bullet names the
   concurrent-cursors-on-one-connection (MARS) question as a
   pre-first-live-run item — a failure mode offline fakes cannot
   exercise, new in this package because the builder now does database
   work inside the job loop.
3. **F3 (LOW):** stale "six claimed surfaces" counts corrected in both
   CR5 documents after the two governed extensions.
4. **F4 (LOW):** `C2_ACCOUNT_EXPORT_ASSEMBLY.md`'s fixture-warning
   section stated the retired tripwire as current fact; a
   superseded-by-CR5 pointer now fronts it (the claim was extended to
   that file through a second append-only extend-surfaces transition,
   PR 747, before this commit; the C2 completion report — historical
   evidence by policy — is deliberately untouched).
5. **F5 (LOW):** the one surviving unqualified reproducibility sentence
   (`services/account_export_assembly_service.py`,
   `_write_fixed_entry`'s docstring, inherited from C2 unchanged) now
   carries the identical-input qualifier.
6. **F6 (advisory):** the Determinism section now names the
   first-promote-wins consequence for retries after a
   promoted-then-crashed attempt.

**Manager acceptance of the disclosed ledger-persistence gap.** The
claim outcome's words "the C1 ledger provably agreeing" are satisfied
in this package as a disclosed, offline, shape-level proof: the
aggregate facts that do reach the real job ledger are unchanged and
independently read back, and the per-domain row is computed and
validated against the real CHECK's logic but cannot be inserted,
because `dbo.account_export_job_domains` has no writer procedure in the
schema and this claim holds no SQL surface. I accept that as the
correct delivery under the frozen surfaces rather than a shortfall:
inventing an unreviewed write path would have been the actual failure.
The missing writer procedure is the program's next SQL work item,
queued behind the current external hold on
`SQL FIles/Migrations/registry.json`, and the integration is built so
that procedure wires in at the exact point the shape backstop already
runs.

## Protected and release state

- **Independent review:** A first-round independent review of
  candidate `1352a0e9` returned CONDITIONAL; its findings are addressed
  in the correction-round section above, and the reviewer confirmed the
  corrected candidate `501ecd67` (the confirmation itself is recorded
  in the claim's receipt and evidence files, not restated here).
- **Repository state:** Candidate on the claimed branch, pushed. The
  writer's own round ended per the writer brief (push and stop; no PR,
  no merge); the manager's review/extension/correction commits followed
  on the same branch.
- **Deployment/schema/resource state:** Withheld entirely
  (production authority withheld per this claim's own brief). No
  database was contacted by this writer or by any test -- every reader
  invocation in every test uses a fake cursor/connection, and every
  storage-adapter test in this package's own new file uses a small,
  locally-defined fake container. No Azure resource, workload identity,
  grant, schedule, route, or template changed. `SQL FIles/Migrations/
  registry.json` was read but never modified.
- **No migration, no gate, registry untouched.** This package ships no
  SQL file of any kind. There is no `gate: null` placeholder to author,
  no registry entry to append, and no gate to run -- stated explicitly
  because every sibling reader package (CR1-CR4) carried exactly that
  machinery and this one deliberately does not.
- **Current product truth:** Account-wide export remains unavailable to
  any real member today. This candidate changes what a hand-run worker
  script would produce if pointed at a real database and container --
  real member content instead of a synthetic fixture -- but nothing in
  the repository calls that script from a route, UI, or scheduler, and
  the required Azure grant layers C2's own report recorded as pending
  (the workload identity's storage RBAC role; the SQL-side `EXECUTE`
  grants) remain exactly as pending as C2 left them. No member-visible
  behavior changed.

## Limitations, rollback, and next action

- **No live database or Blob Storage proof of any kind from this
  writer.** Every test in this candidate mocks the Azure Blob SDK
  (via a locally-defined fake container, matching
  `tests/test_account_export_storage.py`'s own established style) and
  fakes DB cursors/connections (a shared-queue variant of
  `tests/test_settings_export_core_readers.py`'s own fake, needed
  because a single worker run now calls many readers in sequence over
  one shared connection). `services/account_export_domain_readers.py`'s
  own procedures were proven against a real engine by CR1-CR4's own
  already-sealed gate rounds; this package re-proves none of that and
  re-opens none of it.
- **Manifest/ledger agreement's real-persistence gap, surfaced for a
  manager decision.** `dbo.account_export_job_domains` has no writer
  procedure in the current schema, and this claim's surfaces (eight
  non-governance files after the two extensions)
  include no SQL file, so nothing in this package can `INSERT` a real
  per-domain ledger row -- only compute and validate, in Python, the
  exact row a future writer would need. **This needs a surface
  extension**: a future package would have to claim
  `SQL FIles/Migrations/registry.json` (owned by another active lane
  per this claim's own brief) plus a new migration adding one
  `INSERT`-capable procedure for the dedicated worker identity, wired
  in at the exact point `run_once`'s shape-check backstop already runs
  today. Recorded in detail in
  `CR5_ACCOUNT_EXPORT_READER_INTEGRATION.md`, "Manifest/ledger
  agreement."
- **Determinism across attempts is no longer byte-identical, by
  necessity, not by regression.** Once real per-reader read-window
  timestamps flow into the manifest, two separate attempts at the same
  job will generally produce different archive bytes and a different
  sha256 even when every underlying row is unchanged. Proven directly
  (`tests/test_account_export_integration.py`,
  `test_two_separate_attempts_with_different_read_windows_differ`) and
  stated precisely in both `scripts/run_account_export_worker.py`'s own
  module docstring and `CR5_ACCOUNT_EXPORT_READER_INTEGRATION.md`,
  "Determinism," rather than left for a future reader to discover by
  surprise.
- **Concurrent cursors on one connection are untested against a real
  driver and must be settled before the first live run** (recorded per
  independent-review finding F2). `run_once` holds its own cursor open
  across the whole job while `build_domain_files_from_readers` opens a
  fresh `connection.cursor()` per reader -- twenty-two of them -- on
  the same connection, and the outer cursor's last result set is not
  necessarily drained (`fetchone()` calls). C2's fixture worker did no
  database work inside the builder, so this pattern is new here.
  Without MARS (or an equivalent driver setting), SQL Server refuses a
  second active command on a busy connection. No offline fake can
  prove this either way; it is a named pre-first-live-run item for C4
  alongside the pending grants.
- **`build_domain_files_from_readers` has never been exercised against
  the real, applied `DOMAINS` procedures over a live connection.**
  Every test uses a fake cursor scripted to match each reader's own
  declared `fields` tuple; if a real procedure's actual output columns
  ever silently drifted from that tuple, this package's own tests would
  not catch it (that drift-detection responsibility belongs to each
  reader package's own migration-text-vs-`DOMAINS` pinning tests, which
  this package did not touch and re-confirmed still pass unmodified).
- **Deviations from the brief:**
  1. **No test literally titled or shaped as "the C2 test asserting the
     assembly is fixture-only" existed to retire.** Disclosed in full
     in "Design decisions" item 1 above and in
     `CR5_ACCOUNT_EXPORT_READER_INTEGRATION.md`'s "The retired fixture
     tripwire" section. The actual runtime tripwire was retired in the
     exact commit the brief specified; only the brief's own description
     of the artifact was factually corrected.
  2. **The mission's literal "the counts committed to the C1 ledger"
     wording is not fully achievable under this claim's frozen, SQL-
     less surfaces.** Disclosed in full in "Design decisions" item 2
     above and flagged as a surface-extension need, not silently
     reinterpreted or hidden.
  3. **`_iso_z`'s output format changed** (fixed-width microseconds).
     A narrow, disclosed fix needed for `summarize_domain_ledger`'s
     correctness; confirmed to not affect either sibling test file that
     could have depended on its old, variable-width shape.
  4. **No other deviation.** Every deliverable path the brief names was
     created or modified at its exact claimed location; no unclaimed
     path was touched, confirmed by `git status --short` before every
     commit; no sibling test file needed a scope correction, confirmed
     by running all eight required files together, unmodified except
     for `tests/test_account_export_assembly.py`'s own two new tests.
- **What needs a surface extension or a manager decision:**
  1. **A future SQL surface to actually populate
     `dbo.account_export_job_domains`** -- see "Manifest/ledger
     agreement's real-persistence gap" above. This is the single most
     important open item this package leaves behind.
  2. **`.env.example`'s stale entry — RESOLVED by a governed surface
     extension in this same candidate.** The writer flagged that
     `ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED`'s description
     ("every job this worker completes today uses synthetic fixture
     content, never real member data") was no longer true once the gate
     reading it was deleted, and correctly left the unclaimed file
     untouched. The manager then extended the claim to `.env.example`
     through the extend-surfaces control transition (append-only, under
     the writer task context, merged to `main` before this commit) and
     removed the stale entry and its comment block here, completing the
     tripwire retirement this package exists to perform. The variable
     now appears only in historical C2 records, this package's own
     retirement records, and the test pinning that the code constructs
     never return.
  3. **The two Azure grant layers C2's own report recorded as pending**
     (workload identity storage RBAC; SQL-side `EXECUTE` grants for the
     five worker procedures) remain exactly as pending as C2 left them
     -- unrelated to this package's own scope, but still blocking any
     future live run of this worker regardless of this candidate's own
     completeness.
  4. Independent review of this exact candidate has not yet occurred.
- **Rollback:** Every file this candidate adds or touches is a
  reversible source-code or documentation change; no schema, data,
  resource, or configuration exists anywhere to roll back. Rollback is
  a repository revert of the files listed under "Candidate changed
  paths."
- **Next action:** (This bullet originally read "push this branch and
  stop" — the writer's own stopping point, since executed and
  superseded by the review, extension, and correction rounds recorded
  above.) What remains after this candidate merges: the
  `dbo.account_export_job_domains` writer procedure as the program's
  next SQL package (the manager's acceptance of the interim shape-level
  proof is recorded above — no longer an open decision); the
  concurrent-cursors/MARS question and the two pending Azure grant
  layers C2 already flagged, both settled at C4 before any live worker
  run of any kind could be attempted by anyone.

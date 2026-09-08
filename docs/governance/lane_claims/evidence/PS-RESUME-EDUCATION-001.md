# PS-RESUME-EDUCATION-001 repository evidence

## Outcome and contract

Adds `create_education`, `update_education`, and `remove_education` to the
existing private Resume command service and API boundary. Education stays in
`career_chapters` (`chapter_type=education`) and `career_education`; it is not
a credential or a second career store. The first five editor result sets are
preserved; the sixth returns zero, one, or many owner education rows.

Supported values come from the canonical schema: title, institution_name,
degree_name, field_of_study, education_status, grade_text, location_text,
summary, start_date, end_date, and date_precision. Title, institution, and an
explicit education status are required. Nullable degree and other optional
fields remain supported. All six education statuses and all five canonical
date precisions, including approximate, are retained. End-only education
dates are valid; reversed known dates are rejected. Existing role date rules
and credential statuses remain unchanged. Text uses existing UTF-16 limits
and date normalization. Education edits preserve retained original wording.

The existing server-derived owner, subtype and parent locks, expected chapter
row version, digest-bound immutable receipt, replay, serializable transaction,
private/unpublished guard and publication/history/dependency refusal paths
apply to education. Removal follows the existing private chapter removal
pattern, including guarded private children and relations. No publication,
hide/delete/AI permission policy or public read adapter changes are selected.

`PS-RESUME-EDIT-002` is a separate proposed additive migration depending on
`PS-RESUME-EDIT-001`. It extends only the two closed receipt vocabulary checks
with checked constraints and replaces the two editor procedure definitions.
Existing canonical data is not migrated or backfilled. All predecessor SQL
files remain byte-identical. Rollback restores the exact predecessor procedure
bodies and old receipt vocabulary; it refuses once any education receipt
exists, preserving idempotency evidence. Both migration gates remain null.

## Exact source and review

- Refreshed initial Azure main: `a2aaa65b1ef9e37783b0d085c98ceb5fbc739661`.
- Admission: PR 965, CI 2653, merge `eb76b45100f6da746a713640922af693e382f91a`.
- Implementation base: `eb76b45100f6da746a713640922af693e382f91a`.
- Final independently reviewed candidate: `bdd4811b2ff39da2ccbb00f69b884d5a1b992953`.
- Branch: `work/2026-09-07-resume-education-001`.
- Writer: `session:01a07e6b-67aa-76f3-a7c1-accdb9feb151`.
- Reviewer: `agent:01a07e6b-67aa-76f3-a7c1-accdb9feb151/education_review`.
- Final independent verdict: **PASS**, with the sole P1 corrected.
- Initial review of `7a0a141fd8c7e71edf31556cf91749c384e8ce9e` found education
  update could replace hidden `original_member_wording` with summary. The
  final two-file correction leaves that source field unchanged on update,
  retains create initialization, and adds a preservation regression. The same
  reviewer passed the exact correction and reused unaffected review evidence.
- Required CI 2656 then exposed a test-runner mismatch: the new module imported
  pytest, absent from the repository's unittest CI environment; standalone
  function tests would also be undiscovered. The final test-only correction
  uses TestCase/subTest/assertRaises without adding dependencies. Runtime and
  SQL remain identical to accepted `a2fe90be868eff15bce7aef3df3ea20ce5395946`.
  The same reviewer passed the exact final candidate, checked semantic parity
  of all 19 test bodies and parameter sets, and proved actual discovery with
  pytest imports deliberately refused.

Writer runtime `gpt-6-astra` / `medium` was verified in this exact task's
structured runtime and lifecycle usage record. This is Pete's assignment-only
exception. Independent review was explicitly configured `gpt-6-astra` / `high`
for consequential canonical-data removal/privacy SQL review. The reviewer did
not have independently exposed runtime telemetry; configured is not claimed
as separately runtime-verified.

## Verification

- Writer initial suite: 157 tests and 52 subtests passed across education,
  existing editor, existing migration, database-service and migration-registry
  contracts; all 21 existing API tests and 6 subtests also passed.
- Writer final correction: 68 education/service/API/migration tests and
  9 subtests passed. The service's malformed education database-value
  hardening was separately rerun with all 41 education tests passing.
- Independent initial verification: 89 focused tests plus 42 subtests and
  21 API tests plus 6 subtests passed. Final narrow recheck: all 9 education
  migration tests passed against the exact corrected candidate.
- Final writer validation using the actual repository unittest runner:
  **148 tests passed** across both new test modules, existing editor/service,
  database, migration registry and API tests. Final independent discovery:
  **19 methods and 38 subtests passed** with pytest absent. Prior pytest-run
  counts above are historical local evidence, not CI-runner coverage claims.
- Coverage includes zero/one/many rows, canonical status/precision values,
  end-only dates, long Unicode wording, invalid/forged fields, server identity,
  same-origin/auth refusal, version conflict/current state, removal and replay,
  owner/subtype SQL predicates, unchanged shared dependency guards, checked
  receipt vocabularies, exact rollback procedure restoration and null gates.
- `git diff --check` passed. Independent read preflight and exact local/remote
  candidate checks passed. SQL tests are lexical/static checks and service/API
  tests use mocked procedures. No SQL Server or provider was called.

## Delivery and outstanding boundaries

Runtime PR 966 carries this candidate. Required CI and accepted merge are
recorded separately by Azure and the final closed claim; this pre-merge
evidence tail alone does not establish either. Only the fixed evidence and
receipt files follow the reviewed candidate.

SQL compilation, actual transactions/concurrency, rollback/reapply,
verification-script execution and driver serialization remain unproven and
require separate authorization before schema application. The updated service
requires the education-capable proposed reader; it must not be enabled against
the predecessor five-set reader. No schema apply, infrastructure, provider,
identity, configuration, deployment or live enablement was performed.

UI, first-use composer/guide, education presentation, Profile presentation,
onboarding/intake and AI permission mappings remain outside this package.
The intake architecture remains unapproved/inactive. Repository completion
does not establish complete MVP1, pilot, production or live readiness.

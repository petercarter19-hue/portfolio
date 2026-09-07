# PS-RESUME-STUDIO-001 — repository candidate evidence

Runtime-inert Protected delivery record. This evidence does not apply a SQL
migration, enable a flag, use a member identity, contact a provider or live
database, deploy code, or establish pilot or production readiness.

## Outcome

The reviewed repository candidate adds the backend foundation for an owner to
read and edit private Living Resume roles, accomplishments, skills, and
credentials in the existing career domain. The API derives identity on the
server, returns private no-store responses, preserves member wording, and uses
an explicit credential completion state. The command service accepts a closed
12-command vocabulary, canonical UUID idempotency keys, expected parent row
versions for updates and removals, bounded UTF-16 text, and typed safe errors.

The proposed SQL performs each command and its digest-bound owner receipt in
one transaction. It locks matching owner subtypes, orders accomplishment
parent and child locks consistently, and refuses foreign, exposed,
publication-history-bearing, access-bearing, or unsafe relation-bearing
records before mutation. Private removal covers the owned private relation and
child rows admitted by the contract. The migration remains in `proposed` with
`gate: null`.

## Candidate and independent review

- Implementation base: `11fad4a9b6a58bb5133acdbbc4d5316bc5f36c66`.
- Reviewed source candidate: `8de1f650563723e4d391c944bef42e2b3a3dc0ef`.
- Branch: `work/2026-09-06-resume-studio-private-commands`.
- Writer: `agent:codex/mvp1-resume-backend/01a07722-6290-7751-811e-4c4767adfadd/resume_backend_writer`.
- Independent reviewer: `agent:codex/mvp1-resume-backend-review/01a07722-6290-7751-811e-4c4767adfadd`.
- Manager-recorded receipt UTC: `2026-09-07T00:48:50Z`.
- Verdict: **PASS** after the six findings recorded in the matching receipt
  were corrected by the original writer.
- The reviewer independently reported 58 focused tests passing after the first
  correction and 18 migration tests passing for the final two-path lock-order
  recheck. After CI exposed the repository-required rollback ledger-delete
  syntax, the same reviewer independently passed the exact one-line source
  delta and 19 focused tests at `8de1f650563723e4d391c944bef42e2b3a3dc0ef`,
  confirming that the earlier review remained applicable.

Only this evidence file and its matching receipt were updated after the final
independent review. No reviewed source candidate byte changed.

## Writer verification

- Using the existing project virtual environment and a process-local synthetic
  provider-key placeholder only to satisfy application import, 59 focused
  tests passed: all tests in `test_living_resume_editor_service`,
  `test_living_resume_editor_migration`, and `test_database_service`, plus the
  exact owner API regression for malformed command type, unsupported Unicode,
  and malformed verification URL. The API regression exercised all three
  requests through Flask and verified typed `400 invalid` and
  `Cache-Control: private, no-store`. It made no provider or database call.
- The migration registry checker exited successfully and `git diff --check`
  passed.
- Pinned Gitleaks 8.30.1 found no leak in the five current correction files or
  the final two lock-order files. CI 2582's full-history secret scan succeeded
  with Recovery's accepted exact historical false-positive allowlist for the
  two deleted synthetic UUID fixture lines in the earlier branch commit.
- Required CI run 2582 executed 5,752 tests and failed one repository contract:
  the proposed rollback used `DELETE FROM dbo.schema_migrations`, which the
  migration registry test did not recognize as ledger cleanup. The equivalent
  repository-recognized `DELETE dbo.schema_migrations` form now preserves the
  same exact migration predicate and transaction. The writer and independent
  reviewer each passed the exact failed registry test plus all 18 Living Resume
  migration tests after the correction. Pinned Gitleaks 8.30.1 also passed the
  corrected rollback file.
- Static migration tests extract both dynamic procedure bodies, check balanced
  SQL delimiters, and prove the checker rejects the reviewed extra-closing
  shape. These checks do not prove SQL Server compilation, transaction
  behavior, rollback, serialization, or driver behavior.

## Outstanding gates and boundaries

- No SQL engine or disposable-database proof was authorized or performed. The
  migration registry gate is intentionally null. SQL compilation, real
  transaction/concurrency behavior, rollback/reapply, verification-script
  execution, and driver serialization remain outstanding before any schema
  application or pilot.
- Required Azure CI is outstanding for the final candidate. Draft PR 942 still
  points to the earlier source SHA while the Workflow and Recovery validation
  queue has priority. The reviewed candidate and this evidence tail remain
  local and unpushed until that queue releases.
- The package is not merged, deployed, enabled, schema-applied, authenticated
  against live data, pilot-ready, production-ready, or live-verified.
- UI, templates, CSS, JavaScript, navigation, public Profile adapters,
  providers, identities, configuration, flags, deployment, and production are
  outside this repository-only backend candidate.

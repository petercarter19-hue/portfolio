# PS-WORKSHOP-PROVENANCE-VISIBILITY-001 — completion evidence

Runtime-inert Protected delivery record. Production, deployment, schema-apply,
identity-use, private-live-verification, and Workshop G authority remain
withheld. The review time below is the writer-recorded UTC immediately after
receipt of the independent verdict.

## Outcome

The reviewed repository candidate makes Workshop's already-retained wording
history inspectable by the signed-in owner. The selected private My Information
detail now contains a closed-by-default history disclosure showing at most the
newest 50 retained versions. Each row displays its version, save timestamp,
exact approved wording, and exact stored `original_member_wording` under the
label **Source wording on record**. The interface truthfully explains that some
older AI-assisted rows may show refined wording because the original wording
was not retained then; it never infers or backfills missing certainty.

The additive `PS-WORKSHOP-003` migration requires `PS-WORKSHOP-002` and adds
only `dbo.usp_ListKnowledgeItemVersionsForOwner`. The procedure resolves the
member from the server-supplied user key, authorizes the private item before
reading versions, and returns exact wording bytes, timestamp, and truthful
total/truncation metadata. Its one materialized source statement binds the
newest-50 window and full count to the same observed database state. Foreign,
forged, unknown, and missing-owner inputs remain existence-neutral; anonymous
Workshop requests remain database-free. Private/no-store responses, escaping,
existing edit/archive/restore/delete actions, and the Workshop D use disclosure
remain intact.

## Candidate and independent review

- Base/current PR target at review:
  `f3a1e28ee26cded71e0dc75821a8f3274147bb42`.
- Reviewed candidate: `ec7519a9feee41b7850d2d29a6cc7e94f55d2fff`.
- Branch: `work/2026-08-28-workshop-provenance-visibility-001`.
- Writer: `agent:/root/workshop_f_implementer`.
- Independent reviewer: `agent:/root/workshop_f_reviewer`.
- Writer-recorded receipt UTC: `2026-08-28T07:34:33Z`.
- Verdict: **unconditional PASS**, read-only, with no findings on the exact
  replacement SHA.

The earlier candidate `c3bd3a0b6c1e87f91ecff69adeeb375b846a304e`
received an unconditional fail with four concrete findings. The replacement
candidate binds rows and metadata to one materialized SQL statement, appends
`PS-WORKSHOP-003` after the current production registry tip, narrows verifier
evidence to deterministic contents without claiming unordered capture proves
delivery order, and rejects boolean, float, and string substitutes for SQL
integer fields. The fresh reviewer independently confirmed all four defects
closed, reran 270 focused tests and 666 Workshop tests with one expected skip,
confirmed the migration digest and cleanup proof, and issued the unconditional
pass above.

The reviewed candidate changes exactly these implementation surfaces:

- `SQL FIles/Migrations/PS-WORKSHOP-003_knowledge_version_history_read.sql`
- `SQL FIles/Migrations/PS-WORKSHOP-003_knowledge_version_history_read_rollback.sql`
- `SQL FIles/Migrations/registry.json`
- `SQL FIles/Verification/PS-WORKSHOP-003_owner_isolation_verify.sql`
- `services/database_service.py`
- `services/knowledge_service.py`
- `static/css/workshop.css`
- `templates/partials/workshop/_item_detail.html`
- `tests/test_database_service.py`
- `tests/test_knowledge_service.py`
- `tests/test_workshop_checkpoint.py`
- `tests/test_workshop_polish.py`
- `tests/test_workshop_provenance_visibility_migration.py`
- `workshop_routes.py`

Only this evidence file and its matching receipt are added after review; no
reviewed candidate byte changes.

## Disposable migration proof

The single post-correction governed disposable-database gate recorded
executable SHA-256
`18e764fbc15cdfe3f00c54d318e48067dad97430afcf8df2fe685fc396708736`
at `2026-08-28T07:28:18Z` against
`ps-workshop-003-gate-20260828-r2` on server `peerslate`. It applied the exact
prerequisite chain through `PS-WORKSHOP-002`, applied the target, proved
reapply was a no-op, ran
`PS-WORKSHOP-003_owner_isolation_verify.sql` with `verified = 1`, rehearsed
rollback, and reapplied successfully. The verifier proved two-owner and
foreign/forged/unknown neutrality, exact approved/source wording byte
canaries, the deterministic newest-50 contents from 55 versions, timestamp,
and truthful total/truncation metadata. The registry contains this exact proof.

Cleanup removed the exact disposable database and temporary `/32` firewall
rule. Final read-back proved database count `0`, rule count `0`, and the
canonical firewall baseline restored to SHA-256
`df443804a0cb38ffbc381bfe6350618573ed69faa2098e7ea5893ead55a39c3a`.
No production database was contacted and no production schema was applied.

## Writer verification

- Focused database/service/route/UI/migration/schema validation: **270 tests
  passed; OK**.
- Workshop regression discovery: **666 tests passed with one expected skip;
  OK**.
- Shared database, knowledge-service, and schema-path validation: **148 tests
  passed; OK**.
- `scripts/govern_sql_migrations.py check` reported all 22 gated migrations
  matching their executable files, including `PS-WORKSHOP-003` at the digest
  above.
- Python compilation, `git diff --check`, fetched target/base proof, clean
  write preflight, and exact local/remote branch-tip checks passed.

## Release state and boundaries

At this evidence-tail state the reviewed candidate is pushed and accepted but
not yet merged, deployed, schema-applied, or privately live-verified. The next
authorized action is the guarded repository merge PR and automatic validation
CI. No production deployment or schema action is authorized. Edit provenance
remains reserved for Workshop G and is not part of this delivery.

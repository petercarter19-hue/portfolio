# PS-WORKSHOP-EDIT-PROVENANCE-001 — completion evidence

Runtime-inert Protected delivery record. Production, deployment, schema-apply,
identity-use, and private-live-verification authority remain withheld. The
review time below is the writer-recorded UTC immediately after receipt of the
independent verdict.

## Outcome

The reviewed schema-only candidate adds `PS-WORKSHOP-004`, requiring
`PS-WORKSHOP-003`, and replaces only
`dbo.usp_UpdateKnowledgeItemForOwner`. Its input signature and success/changed
result shapes remain byte-identical to the Workshop W1 contract. Inside the
existing server-derived owner, private/non-archived, expected-rowversion,
`UPDLOCK`/`HOLDLOCK` transaction fence, the procedure reads the owned current
version by knowledge item, owner profile, and current version number. Each edit
appends the member's edited approved wording while copying the exact stored
`original_member_wording` and recording `authored_via = typed`.

There is no browser/app original-wording input, inference, backfill, or old-row
mutation. The parent advance repeats the complete admitted scope and requires
exactly one affected row, keeping version insertion, parent advancement, and
the update audit atomic. Unknown, foreign, forged, archived, and stale inputs
retain the neutral changed result with no mutation. The missing-current-version
invariant throws transactionally. Workshop D saved-version use behavior,
Workshop F history reads, anonymous session behavior, and all Python, route,
template, CSS, and allowlist bytes remain unchanged.

## Candidate and independent review

- Base/current PR target at review:
  `c9b5e027505e0f093aeebfc3553a3e04b2f868e7`.
- Reviewed candidate: `2b9bffbec4a1a88f9406ef0ffe85662adda8f111`.
- Branch: `work/2026-08-28-workshop-edit-provenance-001`.
- Writer: `agent:/root/workshop_g_implementer`.
- Independent reviewer: `agent:/root/workshop_g_reviewer`.
- Writer-recorded receipt UTC: `2026-08-28T08:59:49Z`.
- Verdict: **unconditional PASS**, read-only, with zero findings on the exact
  candidate SHA.

The reviewer independently confirmed the exact six authorized implementation
paths, the W1-to-W4 signature and drift guards, lock and owner/current-version
predicates, exact source-byte retention, parent CAS and atomicity, exact W1
rollback literal and hash restoration with no member-row mutation, registry
ordering and digest, verifier coverage, the two-connection race proof, test
results, and disposable cleanup baseline.

The reviewed candidate changes exactly these implementation surfaces:

- `SQL FIles/Migrations/PS-WORKSHOP-004_knowledge_edit_provenance.sql`
- `SQL FIles/Migrations/PS-WORKSHOP-004_knowledge_edit_provenance_rollback.sql`
- `SQL FIles/Migrations/registry.json`
- `SQL FIles/Verification/PS-WORKSHOP-004_owner_isolation_verify.sql`
- `tests/test_workshop_edit_provenance_migration.py`
- `tests/test_workshop_provenance_visibility_migration.py`

Only this evidence file and its matching receipt are added after review; no
reviewed candidate byte changes.

## Migration, rollback, and concurrency proof

The governed disposable-database gate recorded executable SHA-256
`53561ce3275599cd7d4f34c234a8455313ac82d1d967194f449d9e25e7c2fcba`
at `2026-08-28T08:38:02Z` against
`ps-workshop-004-gate-20260828-r1` on server `peerslate`. It applied the exact
prerequisite chain through `PS-WORKSHOP-003`, applied the target, proved
hash-validated reapply was a no-op, ran
`PS-WORKSHOP-004_owner_isolation_verify.sql` with `verified = 1`, rehearsed the
guarded rollback restoring the exact W1 procedure body and hash, and reapplied
successfully.

The verifier proved exact stored source-byte retention over byte-distinct v2
and v3 edits, stable prior versions, typed provenance, atomic parent/version/
audit advancement, Workshop F history content and metadata, and mutation-free
foreign/forged/unknown/archived/stale neutrality. A real two-connection test
held A's update lock, observed B's bounded lock timeout, committed A, then
proved B's old token returned the full neutral changed shape with exactly one
new version, one parent advance, and one update audit.

Cleanup removed the exact disposable database and temporary `/32` firewall
rule. Final read-back proved database count `0`, rule count `0`, and the
canonical firewall baseline restored to SHA-256
`df443804a0cb38ffbc381bfe6350618573ed69faa2098e7ea5893ead55a39c3a`.
No production database was contacted and no production schema was applied.

## Writer verification

- Focused W4/W3 contracts: **24 tests passed with one expected disposable-gate
  skip; OK**.
- Cross-migration W1/W2/W3/W4, Workshop D, and schema-path contracts: **195
  tests passed with two expected disposable-gate skips; OK**.
- Full Workshop regression discovery: **681 tests passed with two expected
  disposable-gate skips; OK**.
- The real two-connection disposable SQL proof passed separately.
- `scripts/govern_sql_migrations.py check` reported 36 registered migrations
  and all 23 gate proofs matching their executable files, including
  `PS-WORKSHOP-004` at the digest above.
- `git diff --check`, fetched target/base proof, clean guarded write preflight,
  self-review, and exact local/remote candidate-tip checks passed.

## Lifecycle residue and release boundaries

The activation control checkout initially contained only the generated regular
file `scripts/__pycache__/worktree_lifecycle.cpython-314.pyc`. Under the owner's
exact cleanup authority, the intact directory was moved—not deleted—to
`/private/tmp/ps-workshop-g-control-pycache.BqjJo2/__pycache__/`. The preserved
file is 253,769 bytes with SHA-256
`544c482a928631575b07f6d0c499e5fbd8169acd288034c7f43653f79e90407f`;
the quarantine contains no symlink, directory, or unrelated entry. It remains
preserved and is not authorized for deletion by this package.

At this evidence-tail state the reviewed candidate is pushed and accepted but
not yet merged, deployed, schema-applied, or privately live-verified. The next
authorized action is the guarded repository merge PR and automatic validation
CI. Production currently lacks Workshop W3 and W4; neither migration is
authorized for production by this delivery.

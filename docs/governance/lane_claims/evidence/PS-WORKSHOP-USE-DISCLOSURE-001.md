# PS-WORKSHOP-USE-DISCLOSURE-001 — completion evidence

Runtime-inert Protected delivery record. Production, deployment, schema-apply,
identity-use, and live-verification authority remain withheld. The review time
below is the manager-recorded UTC immediately after receipt of the independent
verdict.

## Outcome

The reviewed repository candidate implements the accepted Workshop D use
disclosure. A signed-in member can see whether any version of their own
explicitly saved Opportunity Slate cites the selected private Workshop item,
including whether the latest saved version cites it. The read derives identity
server-side, returns no private text, keeps foreign, forged, unknown, uncited,
and no-slate cases existence-neutral, and degrades truthfully when the schema or
database is unavailable. Anonymous Workshop remains database-free. Edit,
archive, restore, and permanent-delete authority are unchanged and never
blocked by the disclosure.

The single durable authority is `dbo.opportunity_saved_evidence`; transient
analysis citations are not treated as durable use. The additive migration adds
one owner-scoped read procedure and one online, low-priority-lock supporting
index. The current-save comparison and evidence aggregate are one SQL
statement. Application decoding accepts the database layer's exact ISO
timestamp serialization and normalizes native or serialized values to aware
UTC while refusing malformed rows, counts, bits, and timestamps.

## Candidate and independent review

- Base/current PR target at review: `cc1a74159d0a22f05d6148807b716db614620582`.
- Reviewed candidate: `852e2bccd918e952b753e0008632d3f4a879484c`.
- Branch: `work/2026-08-27-workshop-use-disclosure-001-recovery`.
- Writer: `agent:/root/workshop_implementer`.
- Independent reviewer: `agent:/root/workshop_final_reviewer`.
- Manager-recorded receipt UTC: `2026-08-27T23:04:54Z`.
- Verdict: **unconditional PASS**, read-only, with no findings.
- Reviewer-reported checks: 50 focused tests passed; direct database-serialization
  seam, migration-digest, and provenance checks passed. No literal reviewer
  command was supplied to the writer, so none is invented here.

The reviewed candidate changes exactly these implementation surfaces:

- `SQL FIles/Migrations/PS-OPPSLATE-USE-001_opportunity_slate_use.sql`
- `SQL FIles/Migrations/PS-OPPSLATE-USE-001_opportunity_slate_use_rollback.sql`
- `SQL FIles/Migrations/registry.json`
- `SQL FIles/Verification/PS-OPPSLATE-USE-001_owner_isolation_verify.sql`
- `services/database_service.py`
- `services/opportunity_use_service.py`
- `templates/partials/workshop/_item_detail.html`
- `templates/workshop_add.html`
- `templates/workshop_delete_confirm.html`
- `tests/test_database_service.py`
- `tests/test_opportunity_use_disclosure.py`
- `workshop_routes.py`

Only this evidence file and its matching receipt were added after review; no
reviewed candidate byte changed.

## Disposable migration proof

The governed disposable-database gate recorded executable SHA-256
`fe7e929fa12a32d9b0d4a78be04330b6e144ddf8c3ea8aff9fcf06016353374e`
at `2026-08-27T22:20:06Z` against
`ps-oppslate-use-001-gate-20260828-r2` on server `peerslate`. It applied the
exact prerequisite chain, applied the target, proved reapply was a no-op, ran
`PS-OPPSLATE-USE-001_owner_isolation_verify.sql` with `verified = 1`, rehearsed
rollback, and reapplied successfully. The registry contains that exact proof
and the offline registry checker reports 21 gated migrations matching their
files.

The temporary `/32` firewall rule was
`WorkshopGate-PS-OPPSLATE-USE-001-01a04348-20260828-r2` for the authorized gate
client. The exit cleanup's first rule-delete invocation rejected an unsupported
`--yes` option; the database cleanup succeeded, and the writer immediately
removed that same literal rule with the supported command without repeating
the gate or database operation. Final read-back proved rule count `0`, database
count `0`, and the complete canonical firewall state restored byte-for-byte to
baseline SHA-256
`f48298cd571e07ed542770418e6486bee207541d7d8bea2008c292b0324688e0`.
No production database was contacted and no production schema was applied.

## Writer verification

- `ANTHROPIC_API_KEY=test-key-for-ci-only PYTHONDONTWRITEBYTECODE=1 uv run --with-requirements requirements.txt python -B -m unittest tests.test_opportunity_use_disclosure tests.test_database_service`
  — **50 tests passed in 0.072 seconds; OK** on the reviewed candidate.
- `PYTHONDONTWRITEBYTECODE=1 uv run --with-requirements requirements-sql.txt python -B scripts/govern_sql_migrations.py check`
  — **21 gated migrations matched their executable files**, including the
  Workshop use-disclosure digest.
- The two final Python correction files compiled successfully; `git diff
  --check` passed; the fetched clean write preflight passed at the exact
  candidate; and the pushed branch tip was independently re-read as that SHA.

## Release state and boundaries

At this evidence-tail state the reviewed candidate is pushed and accepted but
not yet merged, deployed, enabled, schema-applied, or live-verified. The next
authorized action is the guarded repository merge PR and its CI. Automatic CI
is validation only; production, schema, candidate, and deployment actions must
remain skipped. Repository rollback, if ever needed, is an ordinary reviewed
revert of the merge and is distinct from deployment or schema rollback.

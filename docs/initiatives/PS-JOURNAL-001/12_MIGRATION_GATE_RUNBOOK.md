# PS-JOURNAL-001 — J1 Migration Gate Runbook

**Author:** Claude Code (Fable), designated manager · 2026-07-21
**Status:** Prepared ahead of need. Execution requires (1) Pete's visual
acceptance of the J1 frontend, and (2) Pete's explicit go for the live-database
step. This runbook changes nothing by existing.

## Purpose

Apply `PS-JOURNAL-001_journal_reads.sql` to the live Azure SQL database and
prove the privacy contract there, before `PEERSLATE_JOURNAL_ENABLED` is ever
turned on. This closes the Opus review note from PR 129: *the two-owner
isolation verification must execute against the real database, not only be
reviewed statically.*

## Preconditions (all must be true)

1. J1 frontend merged after Pete's visual acceptance (or explicitly approved
   for flag-off merge ahead of acceptance).
2. `origin/main` green: full unittest suite passes at the release SHA.
3. The migration trio present on `main`:
   `SQL FIles/Migrations/proposed/PS-JOURNAL-001_journal_reads.sql`,
   `..._rollback.sql`,
   `SQL FIles/Verification/PS-JOURNAL-001_owner_isolation_verify.sql`.
4. A same-day Azure SQL point-in-time restore reference recorded (PITR is
   Azure-default; note the current UTC timestamp in the evidence log before
   applying).
5. Pete's explicit "apply it" for the live step, in chat, that day.

## Execution steps

1. **Snapshot state.** Record UTC time, `origin/main` SHA, and
   `SELECT COUNT(*) FROM dbo.moments` (and `dbo.captures`) via the established
   secure operator path (same path used for PS-MOMENT-001/PS-HOME-001 applies).
2. **Apply the migration** with the repo's established mechanism
   (`scripts/apply_sql_migrations.py` optional-migration pattern — register
   `PS-JOURNAL-001` in `APPROVED_OPTIONAL_MIGRATIONS` in the same release; the
   script's guards keep ordinary runs inert).
3. **Re-run the migration a second time** — it must no-op cleanly (idempotency
   proof).
4. **Run the verification script** `PS-JOURNAL-001_owner_isolation_verify.sql`.
   It creates two synthetic owners, proves: idempotent replay returns one
   Moment; per-owner idempotency namespace; derived confirmed-only membership;
   archive filter; keyset pagination order; forged-owner truthfulness; no
   auto-publish/placement; no private content in audit metadata — then rolls
   back its synthetic rows. **Every THROW must be absent; capture the full
   output.**
5. **Application smoke (flag still off).** Confirm production behavior is
   unchanged: `/api/journal/moments` → 404; `/app/journal` → 404; site 200s.
6. **Record evidence** in the package: timestamps, SHAs, row counts before/
   after (must be unchanged except the new empty ledger table), verification
   output, pipeline/build IDs.

## Rollback

- Guarded rollback script only: it refuses if member Journal data exists, if a
  later migration is present, or if protected procedures drifted — so it is
  safe in exactly the window where rollback is legitimate.
- If rollback is itself blocked and the database is impaired: Azure PITR to the
  recorded pre-apply timestamp is the recovery path (owner decision required —
  it rewinds everything, not just this migration).
- The application needs no rollback for a SQL-only revert while the flag is
  off: no code path reaches the new procedures unless enabled.

## Failure stops

Stop and report (no improvisation) if: any verification THROW fires; the
second apply is not a clean no-op; row counts change unexpectedly; the apply
path errors mid-transaction; or production smoke shows any public change.
The flag stays off in every failure case.

## Recorded gate conditions from Opus reviews (PRs 129 and 140)

1. **The SQL trio must execute live before flag-on** — migration, second-apply
   idempotency no-op, rollback-readiness, and the full verification script
   (sections 1–15, now including search isolation §10–15). Static review is
   not a substitute; this is where escaping literalness, two-owner isolation,
   pagination order, and forged-owner behavior get executable proof.
2. **Collation decision RESOLVED (Pete, 2026-07-21): accent-INSENSITIVE.**
   Search comparisons now force `Latin1_General_CI_AI` — "cafe" finds "café".
   Recorded here so the gate applies the current script text.
3. **Performance note to record:** search is a leading-wildcard LIKE over
   nvarchar(max) narrative — non-SARGable, owner-bounded scan. Acceptable for
   the pilot; revisit (full-text or trigram index) before broad enablement.
4. **Optional API polish (J1.x):** the endpoint length-checks `q` before
   stripping while the service checks after — a whitespace-padded 200-char
   query 400s at the API. Harmless; align when convenient.

## After the gate

Only after this runbook's evidence is recorded and Pete accepts it may
`PEERSLATE_JOURNAL_ENABLED=true` be set — first for the owner pilot
(Pete + Danielle per the real-member validation in doc 05's sequence).

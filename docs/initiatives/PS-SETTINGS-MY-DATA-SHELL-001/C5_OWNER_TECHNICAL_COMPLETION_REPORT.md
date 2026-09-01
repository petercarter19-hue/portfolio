# PeerSlate Completion Record — C5 (C0's C4 child): account export release and operational proof

## Core record

- Task/package and delivery path:
  `PS-SETTINGS-ACCOUNT-EXPORT-RELEASE-PROOF-001`, **Protected**
  (production release, identity/authorization grants, shared
  infrastructure). C0's C4 child; `C5_*` filenames because `C4_*` belongs
  to the closed domain-ledger package.
- Outcome and member/site effect: production gates 6-9 of the account
  export program executed and proven under
  `pete-chat-2026-09-01/five-through-nine`. **Member-visible effect:
  none.** The export feature is deployed dark; every export route
  returns 404 because `PEERSLATE_ACCOUNT_EXPORT_ENABLED` is absent.
  Gate 10 (enablement) is a separate, unauthorized, future owner
  decision.
- Package manager and why: coordinator session (parent) routed
  activation, pre-execution grant review, approval releases, and the
  independent exact-SHA review; writer executed within the claim.
- Triggered specialists and return target: independent pre-execution
  review of the SQL authority script — CLEAR on `ad1d8e34`
  (`agent:review-ps-settings-account-export-release-proof-001:ad1d8e34:sql-authority-grant`)
  plus delta re-CLEAR on `f591be37`
  (`...:f591be37:sql-authority-grant-delta`); the script is
  byte-identical to the cleared `f591be37` blob at freeze. Independent
  exact-SHA package review: routed by the coordinator after freeze; its
  reference lands in the claim receipt.
- Branch, base SHA, final SHA, and changed paths:
  `work/2026-09-01-settings-account-export-release-proof-001`, base
  `672d122855b2103fdfdd2257ed5e63e57f47944f`; final = the frozen
  candidate SHA recorded with the review receipt (this file is part of
  that commit and cannot name it). Changed paths:
  `scripts/configure_account_export_worker_sql_authority.py` (new),
  `docs/governance/PRODUCTION_SCHEMA_STATE.md` (regenerated),
  `tests/test_workshop_provenance_visibility_migration.py` (tip pin
  moved; surface added by extend-surfaces PR 847), this file and
  `C5_ACCOUNT_EXPORT_RELEASE_PROOF.md` (new), plus the package
  claim/receipt/evidence records.
- Verification performed and result: full unittest suite green (2156
  tests); grants plan-before/apply/plan-after exact (49/49/0/0);
  schema-state live read (ledger 40); deploy run 2221 succeeded with
  smoke verified against the exact SHA + build id; flag proven absent by
  names-only listing; all three export routes 404 signed-out; both
  Container Apps Jobs proven live under the UAMI (idle worker run exit 0,
  maintenance run completed with zero counts, logs content-free) —
  details in `C5_ACCOUNT_EXPORT_RELEASE_PROOF.md`.
- Release state: **live verified dark** — run 2221 (main
  `672d1228...44f`) is the current live release, re-verified by
  /healthz identity recomputation at re-freeze (2026-09-01T16:03:32Z);
  repository work not yet merged (independent exact-SHA review in
  progress); feature **not enabled**.
- Known limits, deferred work, or owner decision needed:
  - Both owner-executed role grants landed 2026-09-01 and are verified
    live: AcrPull (verified before job creation) and the web-app
    `Storage Blob Data Reader` on the export container (granted
    14:59:37Z; the first frozen candidate mis-stated it as pending —
    the independent reviewer caught the stale check and the corrected
    record carries the live verification). No pending-owner item
    remains.
  - Gate 10 enablement checklist requires the maintenance job to be
    scheduled with flag-on (CR11 retention warning).
  - 7-day blob soft-delete: cleanup is ledger-truthful, not immediate
    byte destruction.
  - EXPORT-010 rollback window closes at the first real completed
    export after enablement.
- Next action: owner review; then (future, separately authorized)
  gate-10 enablement per the checklist.

## Protected additions

- **Data, identity, privacy, authorization:** dedicated UAMI database
  principal with exact-set grants (no roles; 1 CONNECT + 36 EXECUTE
  (5 lifecycle + 31 readers) + 12 column SELECTs = 49 rows);
  independent pre-execution review before production apply;
  negative-path evidence = verify's exact-set refusals and the flag-off
  404 proof. Rollback = preapproved disable/revoke/redeploy plan
  (release-proof doc), not a merge revert.
- **Shared infrastructure or broad release:** ACR `peerslateacr` +
  environment `peerslate-jobs-env` + jobs
  `peerslate-account-export-worker` (*/5) and
  `peerslate-export-maintenance` (daily 03:00 UTC), digest-pinned;
  deployment and rollback evidence in the release-proof doc;
  operational owner: Pete (single-operator product); independent
  exact-SHA review required by the claim, routed post-freeze.
- **Actual handoff:** none — single writer through merge.

# PS-SETTINGS-ACCOUNT-EXPORT-RELEASE-PROOF-001 review evidence

Protected, independently reviewed: C0's C4 release-and-operational-proof
child executed production gates 6-9 under
`pete-chat-2026-09-01/five-through-nine` and recorded them in the two
`C5_*` initiative documents (C5 filenames because the closed
domain-ledger package owns `C4_*`). Full gate evidence lives in
`docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C5_ACCOUNT_EXPORT_RELEASE_PROOF.md`;
this file is the fixed runtime-inert review record.

## What shipped in the repository

- `scripts/configure_account_export_worker_sql_authority.py` (new):
  plan|apply|verify worker SQL authority with computed bytes_le SID,
  runtime-enumerated domain readers, tripwire pins (31 readers, 49
  direct-permission rows), and class-1 column-grant exact-set verify.
- `docs/governance/PRODUCTION_SCHEMA_STATE.md`: regenerated from a live
  governed read (ledger 40; `PS-SETTINGS-EXPORT-010` applied by run
  2212). The empty pipeline source/build header is the disclosed shape
  of a governed operator-shell read.
- `tests/test_workshop_provenance_visibility_migration.py`: production
  tip pin moved EXPORT-009 -> EXPORT-010 with dated rationale (surface
  added via extend-surfaces control PR 847).
- The two `C5_*` initiative records.

## Production facts at freeze (proven, not implied)

- Gate 6: grants applied 2026-09-01T13:39:20Z from the cleared tree,
  inside the transient firewall window 13:38:28Z-13:40:39Z (rule
  `c4-operator-20260901` created and deleted; baseline rule set
  re-confirmed). Plan-after exact: 49 present / 0 missing / 0
  unexpected; zero role memberships.
- Gate 7: ACR `peerslateacr` (Basic, admin disabled) + env
  `peerslate-jobs-env` + two digest-pinned Container Apps Jobs
  (worker */5, maintenance daily 03:00 UTC). First image lacked
  `libltdl7` (five failed pre-repin executions, all pre-SQL
  driver-load); rebuilt and repinned. Proofs on the fixed image: manual
  idle run exit 0 (also the as-the-principal SQL verification),
  maintenance run completed with zero counts, first post-repin
  scheduled tick succeeded, Log Analytics lines content-free.
- Gate 8: container private, account hardened, worker Contributor at
  exact container scope. Web-app Storage Blob Data Reader: owner
  executed 2026-09-01T14:59:37Z; verified live.
- Gate 9: run 2221 deployed main `672d1228...44f` dark
  (schemaAction=none; no schema stage ran; no environment approval was
  requested because only the schema environment carries one). Smoke
  verified; EXPORT_BLOB_* set output-free; enablement flag proven
  absent by names-only listing; export routes 404 signed-out; run 2221
  re-verified as the current live release at 2026-09-01T16:03:32Z by
  independent /healthz identity recomputation.
- Gate 10 (enablement + live member proof) was NOT authorized and was
  not performed; `PEERSLATE_ACCOUNT_EXPORT_ENABLED` is set nowhere.

## Review history

1. Pre-execution independent review of the grants script (Protected
   identity surface) before any production apply: CLEAR on `ad1d8e34`
   (`agent:review-ps-settings-account-export-release-proof-001:ad1d8e34:sql-authority-grant`),
   three low findings taken (tripwire pins; dropping the callerless
   `usp_CompleteAccountExportJob` grant; stale-SID remediation note),
   delta re-CLEAR on `f591be37`
   (`agent:review-ps-settings-account-export-release-proof-001:f591be37:sql-authority-grant-delta`).
   The applied script is byte-identical to the cleared blob.
2. Package review on frozen `d43598cb`: REVISE with two doc-only
   findings (stale pending-owner claim; grant arithmetic), both taken;
   the reviewer's moved-release inference was retracted after the
   writer's recomputation proved run 2221 still live.
3. Confirm on `e058484d`
   (`agent:review-ps-settings-account-export-release-proof-001:e058484d:release-proof-confirm`);
   receipt in this package's receipts file.

## Operational incidents, recorded not hidden

- A duplicate deploy run (2222) was queued when the first queue
  command's client-side JSON parse failed after a successful POST;
  cancelled within one minute, run 2221 proceeded alone.
- The first frozen candidate under-claimed the web-app Reader grant
  (stale check); caught by the reviewer, corrected with live
  re-verification.

## Out-of-scope note for the program (no action in this package)

The closed `PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-LEDGER-WRITER-001` claim
JSON names `usp_CompleteAccountExportJobWithDomains`; the real
procedure everywhere else is `usp_CompleteAccountExportWithDomains`.
Candidate for a future owner-authorized `evidence-errata` on that
closed claim; recorded here because the release-proof reviewer
re-surfaced it.

## Open items

None for this package. Gate-10 enablement remains a separate future
owner decision whose checklist (in the C5 release-proof doc) requires
the scheduled maintenance job to accompany flag-on. The remote
implementation branch is retained through and beyond close.

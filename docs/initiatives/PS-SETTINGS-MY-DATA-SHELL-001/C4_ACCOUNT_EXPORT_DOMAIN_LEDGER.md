# C4 account export domain ledger

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-LEDGER-WRITER-001`
**Migration:** `PS-SETTINGS-EXPORT-010` (`gate: null` until the disposable-gate
proof runs; `PS-SETTINGS-EXPORT-002` remains burned and unreused)
**Status:** Implemented; not gated, not applied, nothing deployed.

## Decision

`dbo.account_export_job_domains` — the per-domain truth ledger C1 created
"written by no procedure" — gets its one writer:
`dbo.usp_CompleteAccountExportWithDomains`, added **alongside** C1's
untouched `usp_CompleteAccountExportJob`. The worker calls only the new
procedure. C1 stays byte-identical; this package's rollback is a clean DROP.

One call does everything or nothing: validate the canonical 30-domain JSON
payload, derive job and owner identity from the locked row (no owner
parameter exists), re-check owner-active under the lock, insert exactly 30
rows, transition the job to ready — one transaction.

## The four owner-delegated design decisions, recorded

1. **Add-alongside, not replace** — C1 is a closed, gate-pinned artifact
   with standing text assertions; redefining it would poison its rollback
   and its proofs.
2. **Owner-active re-checked inside the transaction** — closing the
   deactivation window between claim and completion for the completion
   itself.
3. **`schema_identifier`** is the stable per-domain id
   `peerslate.account_export.<domain>.v1`; **`source_change_marker`** is the
   job's cutoff marker on included rows, NULL otherwise — no per-domain
   marker exists and none is invented.
4. **Populating the ledger permanently blocks C1's rollback** (its data
   guard refuses when the table holds rows). Accepted: the ledger is
   member-facing truth, and destroying it to un-apply a foundation would be
   the wrong trade in every scenario we can name.

## The storage-conflict trap, closed

The final object's name is job-scoped and promote refuses overwrite, so a
payload defect discovered after promote would strand the job permanently
(every retry burns an attempt on `storage_conflict` until the reaper fails
it). The worker therefore validates **canonical completeness before any
storage write** (`assert_domain_ledger_complete`), leaving only
infrastructure failures possible post-promote — which retries can cure. The
procedure re-validates everything server-side regardless: the worker is the
belt, the procedure the braces. An orchestration test proves an incomplete
set fails with **zero** storage calls.

## Refusal matrix

`57230–57235` reused verbatim for C1's argument validations; new numbers:
`57270` table absent (forward guard), `57271` payload not JSON, `57272` not
the canonical set, `57273` duplicate domain, `57274` disposition outside the
closed vocabulary, `57275` shape-arm violation, `57276` bad digest, `57277`
negative counts, `57278` window out of order, `57279` lease fence, `57280`
owner inactive, `57281` over-long reason refused rather than truncated. The
verification file exercises the numbers a live caller can actually reach
through real fixtures — 57272/57273/57275/57279/57280/57281 — plus the
success path, replay fencing, and isolation; the remaining argument-level
numbers are pinned by offline text assertions and shared verbatim with
C1's independently proven procedure.

## The reason bound (review finding, closed)

Seven real `DOMAINS` reasons exceed the ledger column's 200 characters, and
the draft parsed reasons at `nvarchar(200)` — the engine would have
truncated them silently, storing a ledger record that disagreed
mid-sentence with the manifest: exactly the divergence this package exists
to prevent, caught by independent review running the real pipeline. Now:
the payload parses wide, the procedure refuses anything over the bound
loudly (`57281`), and the worker bounds explicitly with an ellipsis marker
(`_bound_ledger_reason`) — the manifest keeps the full text, the ledger a
declared excerpt, and silent narrowing is structurally impossible.

## Honest limitations

- Offline tests are text and fake-cursor proofs; the live proof is the
  verification file, which requires a disposable gate database and has not
  yet run — `gate: null` says so.
- The ledger rows' truthfulness is exactly as good as
  `summarize_domain_ledger`'s aggregation, which is pinned by the existing
  integration suite's three-way manifest/ZIP/ledger agreement.
- The new procedure needs its own EXECUTE grant to the dedicated worker
  identity — a separate admin operation under C1's grant model, not
  performed by this migration and called out here so it cannot be missed
  at C4 release time.
- `build_domain_ledger_payload`'s timestamp strings are the worker's ISO
  form and have not been round-tripped through a real engine's
  `OPENJSON`/`datetime2` parse; the verification file constructs its own
  JSON via `FOR JSON PATH`, which emits a different form. The gate run is
  where any format mismatch would surface, loudly (57231-style parse
  failure), not silently.
- The worker's stale "7 domains, 22 readers" prose corrected to 12/31,
  and its module prose now describes the writer truthfully.

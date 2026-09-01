# PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-LEDGER-WRITER-001 review evidence

Runtime-inert review-tail record for C4's ledger writer: EXPORT-010, the
one procedure that fills `dbo.account_export_job_domains` and transitions
a job to ready atomically. Paired receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-LEDGER-WRITER-001.json`.

- **Boundary:** Protected, independent exact-SHA review, production
  authority withheld. Migration pair + verification file + registry entry
  (`gate: null` — not gated, not applied), worker integration, tests,
  docs. C1 byte-untouched throughout.

- **Delivered candidate:** `f93b3e9d` on
  `work/2026-09-01-settings-export-domain-ledger-writer-001`, after three
  review rounds, every finding re-proven by execution rather than read.

- **Round one (REVISE, two HIGH).** The reviewer ran the real pipeline
  and found seven `DOMAINS` reasons longer than the ledger's 200-character
  column being silently narrowed — every real export would have stored a
  ledger record disagreeing mid-sentence with the member's manifest, the
  exact divergence this package exists to prevent. And the verification
  file structurally could not run: `INSERT...EXEC` against
  CATCH-ROLLBACK procedures (C1's own recorded gate lesson, unread), with
  an outer transaction whose refusal rollbacks voided later assertions.

- **Round two (REVISE, one blocker).** The rewritten cleanup hit
  `FK_audit_events_app_users` — the bare request calls durably audit — so
  the proof could never finish and stranded synthetic rows. Plus editing
  residue and two missing offline pins.

- **Round three: PASS.** Truncation probe re-run end-to-end (the seven
  domains bounded with true prefixes and ellipsis, manifests retaining
  full texts, bounding tests proven non-vacuous by mutation); the
  void-proof structure shown impossible; the FK fix verified in both
  cleanup sections.

- **What held under attack all three rounds:** atomicity (no
  rows-without-ready or ready-without-thirty path), locked-row identity
  derivation with no owner parameter, the four-way lease fence, the
  pre-promote completeness ordering (the storage-conflict trap fix), the
  canonical 30 set-equal to `DOMAINS` by execution, C1's 41 assertions
  green, and the registry's truthful `gate: null`.

- **Honest limitations.** The live proof has not run — it needs a
  disposable gate database under recorded authority. The new procedure
  needs its own EXECUTE grant to the dedicated worker identity at release
  time. `_bound_ledger_reason` counts Python code points where SQL LEN
  counts UTF-16 units — divergent only on non-BMP characters, none in any
  reason today. The worker still runs nowhere; nothing here is deployed,
  gated, applied, or granted.

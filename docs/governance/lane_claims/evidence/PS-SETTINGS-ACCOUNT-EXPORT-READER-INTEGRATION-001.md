# PS-SETTINGS-ACCOUNT-EXPORT-READER-INTEGRATION-001 review evidence

Runtime-inert review-tail record for replacement package 6 — the
reader-integration package wiring the four closed content-reader
packages into the C2 export worker. Paired receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-READER-INTEGRATION-001.json`.

- **Boundary:** Protected, independent review, repository authority
  through merge, production authority withheld. No migration, no gate:
  this package ships no SQL (the migrations registry was held by
  another active lane throughout), and the governed gate applies only
  to schema movement. Nothing wired to any schedule; no live database,
  storage, or member data touched by writer, manager, or reviewer.
- **Delivered candidate:** `11dc3c03` on
  `work/2026-08-30-settings-account-export-reader-integration-001`,
  activated from main `a7285103`. Custody: four writer commits
  (agent:claude-code/settings-int-writer, Sonnet, final `3848cf50` —
  real readers wired via the C1 lease procedures, fixture path retired
  same-commit, manifest/ledger shape validators, CR5 doc pair), two
  governed append-only extend-surfaces transitions (PR 746 →
  `.env.example`; PR 747 → the C2 assembly design doc; both under the
  writer task context), two manager merge/records commits, the
  review-directed correction commit `501ecd67`, and `11dc3c03` folding
  in the confirming reviewer's three sanctioned doc-only
  understatement fixes (explicitly stated by the reviewer to need no
  further round).
- **Independent review (fresh Opus, read-only, no-fetch brief with
  supplied release state):** `1352a0e9` → CONDITIONAL. C1
  lease/owner-active discipline, the single identity path, the
  three-way manifest/ZIP-content/would-be-ledger-row agreement,
  zero-row included-domain honesty, tripwire-retirement completeness,
  scope exactness, and excluded-domain reason handling all PASSED;
  11 of 12 mutation probes caught. Findings: F1 the CHECK-shape
  backstop had zero test coverage and the doc credited a test that
  never reaches it (MEDIUM — fixed with a new test that reaches the
  backstop and fails the job pre-storage); F2 the
  concurrent-cursors/MARS live-run question, new because the builder
  now does database work inside the job loop (MEDIUM, recorded as a
  named C4 pre-live item); F3/F4/F5/F6 doc-truth corrections
  (surface counts, a superseded-pointer fronting C2's fixture warning,
  an identical-input qualifier, the first-promote-wins retry
  consequence). `501ecd67` → **CONFIRMED**: the reviewer re-probed the
  backstop (5/5 probes caught, including deleting it — now caught by
  exactly the new test), verified both extensions append-only and the
  merge commits empty of content, and confirmed figures (333 passed /
  2282 subtests, exit 0, both runners). Three LOW doc-only
  understatements from the correction round itself were folded into
  `11dc3c03` under the reviewer's explicit no-further-round sanction,
  and the reviewer then explicitly confirmed `11dc3c03` itself in a
  dedicated micro-pass (verifying all three fixes and independently
  recounting the surface tally), so the receipt binds the exact final
  content SHA and everything after it is records-only.
- **Manager acceptance on the record (reviewer's point 2c):**
  `dbo.account_export_job_domains` has no writer procedure in the
  schema, so the per-domain ledger row is computed and validated
  offline against the real CHECK's logic but cannot be inserted by
  this package. Accepted as the correct delivery under the frozen
  surfaces (an unreviewed write path would have been the real
  failure); the writer procedure is the program's next SQL package,
  queued behind the current external hold on
  `SQL FIles/Migrations/registry.json`.
- **Standing forward notes:** (a) the concurrent-cursors/MARS question
  must be settled at C4 before the first live worker run, alongside
  the two pending Azure grant layers C2 recorded; (b) cross-attempt
  archive bytes legitimately differ once real read windows flow —
  `storage_conflict` on a retry after a promoted-then-crashed attempt
  means "an artifact already exists," not corruption; (c) determinism
  remains a pure-function guarantee of `assemble()` for identical
  input, never a cross-attempt byte guarantee.

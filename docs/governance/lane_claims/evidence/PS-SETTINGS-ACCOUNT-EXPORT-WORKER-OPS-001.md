# PS-SETTINGS-ACCOUNT-EXPORT-WORKER-OPS-001 review evidence

Runtime-inert review-tail record for CR11, the export worker's retention
maintenance mode: the package that makes the owner-approved seven-day
expiry mean deletion on disk, not only in the ledger. Paired receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-WORKER-OPS-001.json`.

- **Boundary:** Protected (deletes member-facing artifacts), independent
  exact-SHA review, production authority withheld. One worker script, one
  new test file, the two CR11 documents, and — via a mid-package
  extend-surfaces transition (PR 841) — the C3 experience document's gap
  bullet. No SQL surface of any kind.

- **Delivered candidate:** `e8abf1cef904cc59061fe6b22c1e7a64cf1c5c57` on
  `work/2026-09-01-settings-export-worker-ops-001`, after one REVISE
  round. First freeze `20f1897e`; review corrections `a4ae2e76`
  (F1/F3/F4); merge of main `13de7eb2` plus the C3 bullet retirement
  (F2) completed the candidate.

- **Round one (REVISE, one HIGH).** The reviewer proved the sweep's
  "failed jobs never had a final artifact" premise false by tracing the
  real promote path: the final blob is committed before hash
  verification and completion, so a post-promote failure orphans a
  member's complete archive on disk while the job terminates `failed`
  with a NULL ledger reference — permanently invisible to an
  expired-only sweep. `cleanup_final` now runs unconditionally for every
  swept job, five prose sites were corrected, and the failed-job test
  asserts the delete happens. Also taken: the unconfirmed-mark branch
  pinned by a test (F3), per-row isolation of job-key normalization so
  one malformed row cannot abort the sweep (F4), and the C3 bullet
  retirement routed through a real surface claim instead of an
  unowned deferral (F2).

- **Round two: CONFIRM** on `e8abf1ce`
  (reviewer `agent:claude-code/independent-review/ps-settings-account-export-worker-ops-001/confirm-9c4d2e1a`).

- **What held under attack, certified by mutation testing:** the sacred
  ordering through all three layers — the sweep SELECT structurally
  excludes `ready`, the runtime guard refuses any non-expired/failed row
  without touching storage, and `usp_CleanupAccountExportJob`'s own
  57257 refuses a still-ready job server-side — and the delete-then-mark
  discipline: no path marks a job cleaned before its deletes succeeded,
  one failing job leaves itself `pending` for the next run while the
  sweep continues and the run exits nonzero.

- **Reviewer notes recorded here, deliberately without editing CR11 or
  any implementation surface (this tail may carry only receipt and
  evidence):**
  1. The failed+pending deletion branch is forward-looking: no current
     procedure produces a failed+pending row
     (`usp_FailAccountExportJob` never sets `cleanup_state`), so the
     branch is correct-by-construction for the future fail-time marking
     CR11 already books as the named follow-up. The chartered gap —
     expired ready jobs with a real final object on disk — is genuinely
     closed.
  2. CR11 describes the retired C3 bullet's closing warning as
     "preserved verbatim"; it was preserved as a semantically equivalent
     rephrase. Clarified here rather than reopening the frozen documents
     for a one-word nit.

- **Honest limits, unchanged from the CR11 record:** this code runs
  nowhere until the owner's separately gated worker-host decision;
  enabling the export feature for real members without scheduling
  `--maintenance` would reopen the retention gap; every proof is offline
  (house fakes, no live database or container); merge is repository
  truth only — nothing here deploys, schedules, or enables anything.

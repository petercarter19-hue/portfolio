# PS-SETTINGS-ACCOUNT-EXPORT-CAPTURE-MOMENT-READERS-001 review evidence

Runtime-inert review-tail record for replacement package 2 of the accepted
2026-08-29 reader topology. Paired receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-CAPTURE-MOMENT-READERS-001.json`.

- **Boundary:** Protected, independent review, repository authority through
  merge, production authority withheld. Six read-only Capture/Moment text
  readers; media, hashes, transcripts, and blob linkage structurally out of
  scope (none of the six tables carries such a column — reviewer-verified
  against all four source migrations). Nothing wired, nothing live.
- **Delivered candidate:** `9e0cb6334c2c331028f91a3d442aedd0326964ac` on
  `work/2026-08-29-settings-account-export-capture-moment-readers-001`,
  base `aeffc6f5`. Custody: three writer commits
  (agent:claude-code/settings-cm-readers-writer, Sonnet, final `b85a4ed6`),
  extend-surfaces control PR 706 (one path lawfully appended, precedent
  PR 699), manager gate commit `7b604e0f` (registry seal + placeholder test
  replaced in the same commit per its own five-step docstring),
  review-round records commit `91103f4f`, then the claim-reconciliation
  ceremony: a byte-copy of main's 12-surface claim (post extend-surfaces)
  plus a `--no-edit` merge of `origin/main` at `47cc5bda`, producing the
  final candidate — required because branch-claim parity must hold at merge
  time while post-review commits may only be receipt/evidence, so
  reconciliation joins the reviewed candidate (the recorded C0-era
  ceremony).
- **Gate proof:** FIRST-RUN full pass — 13-migration chain incl.
  `PS-AUTH-001` named from the start, digest
  `679af4674478db72933ffea49311d000d95b1a9113791cb461dc9671dfb721c3`,
  disposable `ps-migration-path-20260829-cm` (deleted after),
  `verified = 1`, rollback rehearsed, forward re-applied.
- **Independent review (fresh Opus, read-only, zero mutations across all
  rounds):** `7b604e0f` → CONDITIONAL (1 MAJOR records-truth: the gate
  commit's lockstep had covered registry and test but not the completion
  report; 1 MINOR surface-count staleness; 1 LOW Journal forward-note).
  Reviewer verified 74/74 columns accounted across the six tables,
  three-way SQL/contract/DOMAINS agreement on all 47 content fields,
  byte-identical identity headers across all 16 program procedures, nine
  mutation probes all caught, media-absence proven structurally,
  extend-surfaces usage lawful, manager gate commit clean.
  `91103f4f` → **PASS** (records-only corrections).
  `9e0cb633` → **CONFIRMED PASS** (ceremony round: the reviewer diffed
  all nine package files byte-for-byte against the PASS candidate —
  identical — verified the claim byte-matches main's 12-surface copy and
  that the merge introduced no conflict-resolution edits anywhere).
  Suites at every candidate: 185 passed / 1176 subtests, exit 0, both
  runners. Point-in-time note: repo-wide collection measured 4,420 tests
  at the writer's run and 4,430 at the final candidate — the difference
  is another lane's tests arriving via the reconciliation merge.
- **Standing doctrine recorded for future packages:** a gate commit's
  lockstep set is registry + test + REPORT; placeholder gate tests are
  pre-scripted with their own replacement steps; a branch that forks
  before a surfaces extension reconciles its claim BEFORE review, never
  after; `PS-JOURNAL-001`, if ever applied, must revisit the moments
  allowlist in the same motion.

## Errata (2026-08-31, owner-authorized): recorded merged_sha is wrong

The closed claim's `merged_sha` field records
`1f701263c9c1ad2a06e13de71e17dfef7cf9a761`. **No such object exists in this
repository.** It is a transcription error: correct 40-hex prefix `1f701263`,
corrupt from character 9 onward.

The true merge commit for this package is
`1f7012637dc5d897842a7d451ce39782ebadb695` — "Merge pull request 708 from
work/2026-08-29-settings-account-export-capture-moment-readers-001 into main",
2026-08-29T14:08:16Z, an ancestor of main, and the commit that introduced
every one of this claim's eleven non-receipt surfaces.

Three independent confirmations: (1) the merge subject names this claim's
exact `branch`; (2) the paired receipt's `candidate_sha`
`9e0cb6334c2c331028f91a3d442aedd0326964ac` is the reviewed branch tip that
`1f701263…` squashed onto main; (3) the delivery-close merge that wrote the
wrong value, `65c64db2bf163be496b49a728710851f7f49ce6e` (PR 709), has exactly
one parent — `1f7012637dc5d897842a7d451ce39782ebadb695`.

An audit of all 57 closed claims on main found this defect in exactly this
one record; every other closed claim's `merged_sha` resolves and is an
ancestor of main.

The closed claim is not amended: a closed claim is never reopened or changed,
and the evidence-errata transition forbids any claim delta. No delivered
work, review outcome, or gate proof changes; only the merge commit identity
is corrected, and only here.

Related observation, recorded not remedied: `scripts/delivery_preflight.py`
`--intent close` checks the merged_sha's ancestry, which fails closed on a
nonexistent object. This value could not have passed that gate, so the close
preflight for PR 709 was either not run or its failure was not honored.

<!-- evidence-errata-authorization: session:947efb44-60f4-4728-b5c6-a0f7e1d9b296/pete-full-authorization-2026-08-31/cm-readers-merged-sha-errata -->

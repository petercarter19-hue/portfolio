# PS-GOV-TRUTH-RECONCILIATION-001 — Governance record reconciliation

**Designated session manager:** Claude Code, designated by Pete on 2026-07-21.
**Writer:** same session (self-managed governance lane).
**Branch:** `work/2026-07-21-governance-truth-reconciliation`.
**Base:** authoritative Azure `origin/main` at
`0717e03c9f1d4e6b67f355fd1556651086ddc351`.
**Type:** governance records only. No route, schema, feature flag, template,
service, migration, application behavior, or member-facing capability changes.

## Why this package exists

A manager session on 2026-07-21 completed the mandatory pre-work gate and found
that the controlling governance pointers no longer matched authoritative
`origin/main`.

### Defect 1 — fifteen released pull requests were never recorded

Azure PRs **103, 104, 105, 106, 107, 108, 109, 110, 112, 113, 114, 116, 117,**
and **119** are completed, squash-merged, and deployed with green pipelines
(151–173). None of them appeared in `CURRENT_BASELINE.yaml`,
`CURRENT_STATE.md`, or `ACTIVE_INITIATIVES.md`. Only PR 111 and PR 118 were
recorded.

The July 20 governance releases (PRs 116–119) rewrote all three pointer files
but recorded only their own lineage, so each rewrite carried the gap forward.

### Defect 2 — a closed lane was recorded as open

`PS-HOME-INTERVIEW-PARITY-001` was recorded across all three files as
`architecture_checkpoint_pushed_manager_review_pending`, with product edits "not
started" and homepage parity "open".

In fact the package was implemented at source
`6625b52ca4620b503ec56dcc15567470b6ef2499`, squash-merged by **Azure PR 105** at
`4deb0a07b6faf2d93d445e212207aeb84b1a71c4`, released by automatic **pipeline
154** (`20260720.25`), and closed out by **PR 106** / **pipeline 156**. Its own
completion report reads *"Complete, released, and verified live"* with a `Pass`
self-certification, and live `https://peerslate.com/` serves the converged
assets `homepage-scenes.css?v=interview-parity-1` and
`homepage-interview-demo.js?v=int-parity-1`, matching `main`.

`PS-CAPTURE-PHOTO-LIFECYCLE-001` was similarly complete through PRs 107, 108,
and 109 while still being listed as an open task.

### Defect 3 — the guardrail suite asserted the stale state

`tests/test_governance_pointers.py` required the baseline to contain
`status: "architecture_checkpoint_pushed_manager_review_pending"`, required
`ACTIVE_INITIATIVES.md` to contain `architecture checkpoint / manager review`,
required exactly four specific `active_packages` entries, and pinned
`application_behavior_pipeline: 149`.

This is the most serious of the three. The guardrail that exists to protect
governance truth had been written against a snapshot rather than against
invariants, so it actively blocked the correction. Any writer attempting to fix
the record would have been met with a failing required suite.

### Defect 4 — pushed work outside every lane record

Four branches are pushed to `origin`, unmerged, not abandoned, and named in no
lane record. One of them carries an owner decision that contradicts `main`.
See `docs/governance/OPEN_BRANCH_REGISTER.md`.

## Scope

**Writable in this package**

- `docs/governance/CURRENT_BASELINE.yaml`
- `docs/governance/CURRENT_STATE.md`
- `docs/governance/ACTIVE_INITIATIVES.md`
- `docs/governance/MANAGER_SESSION_HANDOFF.md`
- `docs/governance/NEXT_TASK_BOARD.md`
- `docs/governance/OPEN_BRANCH_REGISTER.md` (new)
- `docs/initiatives/PS-GOV-TRUTH-RECONCILIATION-001/**` (new)
- `tests/test_governance_pointers.py`

**Forbidden in this package**

- Any application code, template, stylesheet, script, service, or migration.
- The Bible, the Roadmap, `DOCUMENT_CONTROL.md`, and `DECISIONS.md` — this
  package corrects the *record of what shipped*, not a product decision.
- Any other initiative's package files.
- Merging, reworking, or deleting any branch in the open-branch register.
- `BRANCH_DISPOSITION_RECORD.md`, which is awaiting Pete's row-by-row approval.

## Anti-drift requirement

Correcting today's snapshot is not sufficient; the same drift would recur. This
package adds a guardrail expressing an **invariant** rather than a snapshot: no
package listed in `active_packages` may have a package completion report
declaring it complete, released, or live.

That check would have caught Defect 2 the moment PR 106 merged.

## Explicitly out of scope

- Executing any branch, worktree, or stash deletion.
- Resolving the Defender choice A/B contradiction — that is Pete's decision.
- Dispatching `PS-JOURNAL-001` or any other implementation lane.
- Claiming any planned or flag-off capability is live.

## Acceptance

Governance-only, so there is no visual authority and no homepage-impact
assessment. Acceptance requires Pete's confirmation that the corrected record
matches his understanding of what shipped, after which the same session may
complete the Azure pull request, pipeline, and closeout.

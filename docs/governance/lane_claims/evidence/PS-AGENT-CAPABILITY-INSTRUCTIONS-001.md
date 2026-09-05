# PS-AGENT-CAPABILITY-INSTRUCTIONS-001 - candidate completion and self-review

- Outcome: apply Pete's approved capability recommendations in the existing
  agent guidance; keep one canonical policy for Codex and Cursor.
- Package manager and sole writer: `session:01a06e5b-05d4-7023-8266-2bd5d6abccbd`. This Routine documentation
  assignment is self-managed; no product architecture or production change.
- Owner decision: `session:01a06e5b-05d4-7023-8266-2bd5d6abccbd/pete-2026-09-05/capability-instructions`.
- Activation base: `42d1a505f4ae895b66e65dabc7dc6e178df4960b`.
- Implementation base: `30839f7a2e5223bf4e7e869633b875724c422ff6` (PR 927).
- Reviewed candidate: `5820a8fe60125b6df84d557b1718d2d534b6db29`.
- Branch: `work/2026-09-05-agent-capability-instructions-001`.

## Changes and review

Changed only `AGENTS.md`, `docs/AI_MODEL_AND_ROLE_ROUTING.md`,
`docs/AI_WORKFLOW.md` and `docs/governance/DECISIONS.md` in the candidate.
Astra is the default OpenAI model across assigned roles, with optional Sol and
proportional effort. Cursor can be an assigned writer or independent reviewer.
One capability section covers useful parallelism, browser evidence, exact
review, governed worktrees, continuity, explicitly requested goals/schedules,
and stopping after required evidence. Existing package-specific, credential,
privacy, visual, review and production boundaries remain intact. No duplicate
Cursor rules or new policy document was created.

The writer reviewed the complete four-file diff, including the unchanged
Synthetic and material-visual boundaries. Read-only capability research used a
bounded helper; that was not an independent candidate acceptance or a new
review requirement. The Routine claim requires this self-review.

## Verification

- Read, activation and write preflights passed against fresh Azure main.
- `python -B -m unittest tests.test_governance_pointers
  tests.synthetic_member_qa.test_browser_operator_boundary -q`: **31 passed**.
- The first local run found the workflow word limit exceeded. Wording was
  shortened, the unchanged limit was preserved, and the final run passed.
- `git diff --check`: passed.
- No new tests, runtime files, host settings or integrations changed.

The existing lifecycle tool created this task's registered durable worktree.
It inherited sparse settings from the control checkout; this task disabled
sparsity only in its own worktree-specific configuration to materialize the
intended full checkout. No lifecycle code, old checkout or other custody changed.

## Release truth and next action

This is a frozen candidate record. The candidate is pushed; ordinary Azure PR
checks, accepted merge and claim close follow this record. The later receipt
and this evidence are runtime-inert. Current terminal state belongs to the
claim and Azure PR evidence, not this candidate-era wording.

No application deployment, schema, identity, feature enablement, account-export
retry, historical proof, configured goal or scheduled job occurred. The approved
instruction change does not activate the remaining MVP or cleanup proposals.
The return target is Pete in the central site-audit task with the plain-English
approval sequence. Retire only this task's eligible worktree after formal close.

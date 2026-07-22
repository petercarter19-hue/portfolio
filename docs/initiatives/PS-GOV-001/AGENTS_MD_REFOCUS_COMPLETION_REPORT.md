# PeerSlate Completion & Handoff Report — AGENTS.md Refocus

## A. Status

- Package: `PS-GOV-001` governance maintenance — `AGENTS.md` refocus
- Status: Complete for implementation; Azure PR, squash merge, pipeline, and final SHA are recorded in the release handoff after this report is committed
- Branch and base commit: `work/2026-07-22-agents-md-refocus` from `d573b23d78eba1b398bb52952e695fe595d12d7b`
- PR / pipeline / environment: Pending at the time this self-referential report is committed
- Production state: No website runtime or production data change
- Visual authority and status: Not Applicable
- Homepage product projection: Not Applicable — no product or presentation behavior changed
- Pete / designated session manager visual acceptance: Not Applicable
- Designated session manager: Codex, acting on Pete's explicit instruction to reduce, save, commit, and merge the file
- Manager handoff status and next receiver: Ready for Azure PR and release verification
- Lane owner and self-managed authority: Codex; bounded governance-document writer
- Self-certification: Pass
- Complete-diff review: Issues corrected — three initial governance links were corrected to their repository paths
- Acceptance requested: Release

## B. What changed technically

`AGENTS.md` was changed from a duplicated mini-specification into the short always-on instruction router required by the current PeerSlate Bible. It retains the mandatory startup gate, authority order, role and branch ownership, trust invariants, task-specific authority routing, delivery guardrails, quality requirements, and completion-report obligation.

Feature-level prose for Journal, Projects, Story, Résumé, Slate Board, navigation, branding, and visual implementation was removed from `AGENTS.md`. Those rules remain in their authoritative governance, site-rule, and initiative documents, which the new router links directly. No application code, route, template, style, script, schema, environment setting, or dependency changed.

The file changed from 299 lines / 2,586 words to 83 lines / 1,036 words. That is a reduction of 216 lines and 1,550 words, or approximately 60 percent by word count.

## C. What this means in plain English

An AI or developer still receives the non-negotiable rules immediately, but it no longer has to work through several competing copies of detailed product instructions. It is directed to the current source for the specific area being changed. Future product decisions can therefore be updated once, in the governing document, without leaving stale versions embedded in `AGENTS.md`.

## D. What the website or member can do now

Nothing about the live website or member experience changed. This is repository guidance only. It makes future work less likely to drift because the working agent must follow the current Bible, Roadmap, state records, initiative package, and relevant specialist standard.

## E. How this connects to PeerSlate

The current Bible explicitly requires `AGENTS.md` and `CLAUDE.md` to contain short mandatory pointers to `START_HERE.md` instead of duplicated or competing project instructions. This change implements that requirement while preserving PeerSlate's multi-user, private-first, evidence-backed, human-authorized product boundaries.

The refocus does not amend product direction. Capture-to-Moment, Journal, Story, Projects, Résumé, Slate Board, navigation, design, and homepage parity remain controlled by their existing authority and assigned packages.

## F. Verification and validation

- `python3 -m unittest tests.test_governance_pointers`: passed, 23 tests.
- `git diff --check`: passed.
- Required-pointer inspection: passed for the mandatory gate, startup and baseline pointers, document control, ChatGPT Work, Claude Co-Work, visual and Story standards, homepage parity, and self-managed writer language.
- Linked-authority path check: passed; every file linked from `AGENTS.md` exists in the repository.
- Complete-diff review: passed after correcting the three baseline/state/initiative links to `docs/governance/`.
- A broader combined governance/site-rules run executed 33 tests; the governance assertions passed, while one unrelated site-rule test could not import the application because Flask is not installed in this clean documentation worktree. No dependency was installed for a document-only change.
- Production verification: limited to post-release site health because no runtime artifact changed.
- Real-member validation: Not Applicable.

## G. Known gaps, risks, and exclusions

- `CLAUDE.md` was not changed; this task was specifically limited to the bloat identified in `AGENTS.md`.
- The detailed product documents remain intentionally detailed. This change removes their duplication, not their authority.
- GitHub backup synchronization remains on hold because `CURRENT_BASELINE.yaml` requires explicit owner approval for the public mirror.
- No claim is made that this documentation-only change adds, removes, or deploys a member-facing feature.

## H. Clear next step

Complete the Azure pull request with a squash merge, verify the resulting pipeline and production site health, then record the exact PR, merge commit, and pipeline in the owner handoff.

## I. What Pete needs to do or decide

None for this bounded refocus. Any later change to PeerSlate's product direction should be made in the current Bible/Roadmap or an approved initiative package, not added back into `AGENTS.md`.

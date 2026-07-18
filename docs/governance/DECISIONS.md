# PeerSlate Manager Decision Log

This is an append-only operational decision record. The current Bible and Roadmap remain the product authority.

## 2026-07-18 — Adopt Bible and Roadmap v2.3

- Bible v2.3 and Roadmap v2.3 are the current product and sequencing authority.
- Older v1.1-v1.4 and Iris/Direction C material remains history or non-conflicting supporting detail.
- Deep Navy Gold is the approved shared theme.

## 2026-07-18 — Assign ChatGPT Work as PeerSlate manager

- Owner decision: ChatGPT Work coordinates the program.
- Manager responsibilities: authority records, package definitions, lane sequencing, file-boundary review, completion-report review, merge readiness, and release verification.
- ChatGPT Codex is the backend convergence writer. Claude Code is the public front-end writer.
- The manager does not absorb product implementation unless the owner explicitly reassigns a package.

## 2026-07-18 — Start Capture and résumé as the first parallel wave

- PS-CAPTURE-002 and PS-RESUME-PUBLIC-REFINE-001 may run in parallel after PS-BASELINE-001 merges.
- They must start from the same then-current `origin/main`, use separate branches, and not share writable files.
- Interview Studio work is not bundled with the résumé. It waits for PS-INTERVIEW-PUBLIC-GATE-001.

## 2026-07-18 — Bound the Capture lifecycle package

- The original text in `dbo.captures` remains the preserved source input. Corrections create owner-scoped revisions rather than overwriting the original.
- Archive is reversible through restore. Delete is explicit and irreversible for source text and its revisions; only a body-free audit tombstone may remain.
- Export is a versioned, owner-scoped per-capture JSON contract in this package. Account-wide portability/deletion remains a later data-rights package.
- Minimal controls inside the protected Capture page belong to the backend package. Public templates, global theme/navigation, authentication architecture, Journal UI, Moment, and placement are excluded.

## 2026-07-18 — Close the first parallel wave

- PS-RESUME-PUBLIC-REFINE-001 was manager-reviewed, squash-merged through Azure PR 62, deployed by successful pipeline 83, and verified at `/petec/resume`.
- PS-CAPTURE-002 passed responsive mobile proof, isolated SQL apply/verify/rollback/reapply, production forward migration/verification, manager review, Azure PR 63, successful pipeline 85, and protected production-route checks.
- The résumé and Capture task branches are released. Their local worktrees may remain only as preservation references until deliberate cleanup; they are not active writing lanes.

## 2026-07-18 — Start the second parallel wave

- Claude Code owns PS-INTERVIEW-PUBLIC-GATE-001. `/interview-studio` remains a public demonstration; `/interview-studio/history` is browser-local demonstration state. `/app/interview-studio` is the reserved future authenticated owner route and must not be simulated by the public package.
- ChatGPT Codex owns PS-MOMENT-001. The required boundary is one pinned Capture source version → editable private proposal → explicit member confirmation → source-linked canonical Moment.
- A Capture correction never silently rewrites a Moment. Moment confirmation never publishes or places content. PS-PLACEMENT-001 remains the next backend gate.
- The two packages use separate branches and file reservations and may proceed in parallel after this manager setup is on current `origin/main` with a green pipeline.
- Voice and other media intake remain later packages; the next backend work proves the review/canonicalization boundary using the shipped text source first.

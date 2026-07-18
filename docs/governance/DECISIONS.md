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

# PS-BOARD-001 — Slate Board Living Whiteboard

Status: **implementation complete on review branch; Peter visual review required**
Owner: Peter Carter / PeerSlate
Working branch: `work/2026-07-16-slate-board-interview-ux`
Base SHA: `1002383a9788e40a21021bc579a09998d96bce86` (`origin/main` at task start)

## Outcome

Replace the current Slate Board page presentation with a semantic, accessible
web implementation that looks like Peter's attached **Photo 1**: a bright room,
a large physical framed whiteboard, a restrained control rail on the left, four
handwritten board areas, sticky notes, and a real marker tray. Keep PeerSlate's
existing shared header and preserve the approved product organization:
**Short Term, Projects, Long Term, and Work**.

Photo 1 is the highest visual authority for this work package. The selected
`image3.jpeg` in the original implementation brief depicts the same scene and
composition; Photo 1 supersedes every later mockup or direction that would turn
the page into a flat blue canvas, card dashboard, or conventional four-column
board. The other storyboard images remain authorities for behavior and state,
not for replacing Photo 1's visual language.

Durable copies of both approved visual references are stored in
`visual-references/`; see its README for authority and SHA-256 checksums.

## Scope boundary

This package is an experience baseline. It can prove board, list, note,
Chalk It Up, proposal-review, focus, and sharing-preview states with honest
fixtures or browser-local behavior. It does **not** establish production-grade
authentication, canonical persistence, collaboration, invitations, upload,
voice transcription, AI writes, or public publication.

There will be **no merge, Azure pull request completion, production navigation
change, or deployment until Peter reviews and approves the desktop and mobile
result**.

## Artifact map

| File | Purpose |
| --- | --- |
| `01-requirements.md` | Locked visual reference and product requirements |
| `02-current-state.md` | Experience workflow and state map |
| `03-architecture.md` | Information architecture and component boundaries |
| `04-data-model.md` | Data and trust contract |
| `05-security-privacy.md` | Accessibility, mobile, privacy, and threat boundaries |
| `06-test-plan.md` | Test matrix and acceptance plan |
| `07-implementation-plan.md` | Current implementation notes and refinement order |
| `08-decisions.md` | Decisions plus open/deferred backend work |
| `09-verification.md` | Review handoff and evidence checklist |
| `10-handoff.md` | Release gate, rollout, and rollback |

## Governing sources

1. Peter's attached `Photo 1.jpg`, supplied July 16, 2026.
2. `PeerSlate_Slate_Board_Living_Whiteboard_Implementation_Brief.md` and its
   storyboard states.
3. Repository `AGENTS.md` and `docs/AI_WORKFLOW.md`.
4. The Design Bible, Living Résumé blueprint, Product Backlog, and the separate
   feature-flagged Focus Stage experiment.

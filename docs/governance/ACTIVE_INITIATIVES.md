# PeerSlate — Active Initiatives & Lane Assignments

_Last updated: 2026-07-18. This is the coordination record for parallel work across
three delivery lanes. Update it whenever a package changes owner or status._

## How we run in parallel (the operating model)
Three lanes run at once under **one writer per branch** and **separate file ownership**,
so the lanes never collide. **Cowork / Claude is the manager:** it assigns work, keeps
this file and `CURRENT_STATE.md` current, and reviews each lane's completion report
before the next package starts.

| Lane | Owner (tool) | Branch prefix | Owns these files | Must NOT touch |
|---|---|---|---|---|
| **Governance / orchestration** | Cowork / Claude (Pete's manager) | `work/YYYY-MM-DD-gov-*` | `START_HERE.md`, `docs/governance/*`, `CLAUDE.md`, `AGENTS.md`, guardrail tests | product routes, migrations, theme |
| **Public experience (front-end)** | **Claude Code** | `work/YYYY-MM-DD-resume-*`, `work/YYYY-MM-DD-studio-*` | `templates/resume2.html`, `templates/interview_studio.html`, their CSS/JS, `tests/test_resume2.py`, `tests/test_interview_studio.py` | auth, DB, capture backend, migrations |
| **Backend convergence (behind-the-scenes)** | **Codex / GPT** | `work/YYYY-MM-DD-capture-*`, `work/YYYY-MM-DD-moment-*` | capture / Moment / placement services, migrations, `dbo.*`, backend tests | public HTML templates, theme, nav |

Rules that keep it safe (from Sync Standard v1.1 and `docs/AI_WORKFLOW.md`):
- Start every branch from current `origin/main`. **Never work on `main`.**
- **One writer per branch.** Do not continue or merge another agent's branch without an explicit handoff naming the branch and the exact full commit SHA.
- Every package closes with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` (technical record **and** plain-English owner translation).
- Merge through an **Azure pull request (squash)**; delete the source branch after merge.

## Active now
- **PS-GOV-001 — Repository authority + startup enforcement**
  - Owner: Cowork / Claude · Branch: `work/2026-07-18-ps-gov-001` · Status: **In Build → ready for PR**
  - Outcome: every tool and PC starts from one authority chain without a verbal handoff from Pete.

## Authorized next (in order)
1. **PS-BASELINE-001** — close only the remaining audit gaps; refresh `CURRENT_STATE.md`. · Owner: Cowork/Claude + Pete.
2. **PS-RESUME-PUBLIC-REFINE-001** — tighten the public résumé (fix repeated hierarchy, shorten the default scan), preserve meaning, no backend-source fork. · Owner: **Claude Code**. · Runs in parallel with #4.
3. **PS-INTERVIEW-PUBLIC-GATE-001** — separate the public demo from authenticated private practice; progressive layering. · Owner: **Claude Code**. · Start only after route + identity boundaries are verified.
4. **PS-CAPTURE-002** — capture lifecycle: correction / archive / delete / export over the existing private source. · Owner: **Codex**. · Separate branch + file lane from the résumé work.
5. **PS-MOMENT-001 → PS-PLACEMENT-001** — reviewed canonical Moment boundary, then create-once / place-many via references (no copied text). · Owner: **Codex**.

## Held
- **PS-JOURNAL-001 (Journal UI)** — on hold by explicit owner decision until restarted.

## Do-not-do list (from Roadmap v2.3 §20)
- No second résumé dataset; no private history on the public Studio route.
- No raw-capture text duplicated straight into surfaces (follow Capture → review → canonical Moment → placement).
- No auth rewrite; no Journal UI until restarted; no FitSlate / job feed / opaque fit score.

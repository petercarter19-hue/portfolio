# PS-HOME-INTERVIEW-PARITY-001 — Released Studio Homepage Convergence

## Assignment

- Status: manager activation in progress; product implementation must not begin
  until this activation is merged and its Azure pipeline passes.
- Designated session manager: ChatGPT Work/Codex.
- Architecture and implementation writer: Claude Code, sole writer after
  activation.
- Manager activation branch:
  `work/2026-07-20-home-interview-parity-manager`.
- Manager activation base:
  `2e811f4eec3e915bdb6a0aefa7bd744d6bc7553b`.
- Required writer branch after activation:
  `work/2026-07-20-home-interview-parity-001`, freshly created from the exact
  then-current Azure `origin/main`.
- Entry gate: satisfied. The accepted public Studio released through Azure PR
  101 at `39002f5130a1766d2090007c16582e0dbe07226c`; pipeline 149
  (`20260720.20`) passed and production verification passed. Release-governance
  PR 102 merged at `2e811f4eec3e915bdb6a0aefa7bd744d6bc7553b` and pipeline 150
  (`20260720.21`) passed Build and Deploy.

## Plain-language outcome

The homepage already has a useful four-step Interview walkthrough. Keep its
pop-out behavior, but make it visibly and verbally belong to the Interview
Studio that is live today:

- written **Interview Me** practice is primary;
- light mode reads as the Editorial Studio Ledger;
- dark mode becomes the real Cinematic Studio instead of a white sheet floating
  over a dark page;
- the fixed steps mirror the released answer, processing, review, and improve
  journey; and
- the walkthrough remains an honest, fictional demonstration that collects,
  sends, and stores nothing.

This is convergence, not a homepage redesign and not a second Interview Studio.

## Authority

The exact live Studio is upstream product and visual authority. The writer must
read the complete authority chain named by `CURRENT_BASELINE.yaml`, then:

- `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md`;
- `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/10_REAL_STUDIO_AND_HOMEPAGE_DEMO_CONVERGENCE.md`;
- `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/11_REAL_STUDIO_IMPLEMENTATION_ARCHITECTURE.md`;
- `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/15_REAL_STUDIO_IMPLEMENTATION_COMPLETION_REPORT.md`;
- `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/16_MANAGER_IMPLEMENTATION_ACCEPTANCE.md`;
- the complete `PS-HOME-INTERVIEW-DEMO-001` package; and
- [01_CLAUDE_ARCHITECTURE_AND_IMPLEMENTATION_BRIEF.md](01_CLAUDE_ARCHITECTURE_AND_IMPLEMENTATION_BRIEF.md).

The old homepage implementation and screenshots are authority for the accepted
interaction shell only. They do not control current copy, written-practice
hierarchy, or dark-mode treatment.

## Reserved product files

Claude Code may reserve only these files on the later writer branch:

- `templates/homepage.html` — Interview include and asset references only;
- `templates/partials/homepage/_interview_demo_scene.html`;
- `static/css/homepage-scenes.css` — bounded Interview scene rules only;
- `static/js/homepage-interview-demo.js`;
- `tests/test_homepage_scenes.py`;
- `docs/initiatives/PS-HOME-INTERVIEW-DEMO-001/04_REAL_STUDIO_CONVERGENCE.md`;
- this package's writer completion report; and
- `artifacts/ps-home-interview-parity-001/`.

Any other file requires a manager-approved reservation before editing. In
particular, do not modify the real Studio, routes, authentication, databases,
Capture, Photo, Owner Home, Placement, global navigation, global tokens, or the
theme controller.

## Gates

1. This manager activation merges and its Azure pipeline passes.
2. Claude creates the exact fresh writer branch and records its base SHA before
   product edits.
3. Claude writes `04_REAL_STUDIO_CONVERGENCE.md` as the implementation
   architecture and receives manager confirmation that it respects scope.
4. Claude implements, self-reviews, tests, captures evidence, and returns a
   clean pushed exact SHA plus owner-format completion report.
5. Codex compares the result against the released Studio and approves or denies
   visual-product acceptance. Pete may make the final owner call directly.
6. Only an accepted implementation receives its own Azure PR, pipeline, live
   homepage verification, and governance closeout.

No product code is authorized on this manager branch.

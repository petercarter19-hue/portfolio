# Community authoring runtime completion record

Candidate status: **draft-preservation correction verified; not merge-ready or
release-ready until a fresh different reviewer accepts the exact candidate.**

## Core record

- **Task/package and delivery path:** `PS-COMMUNITY-AUTHORING-RUNTIME-001`,
  Protected, non-production.
- **Outcome and member/site effect:** implemented the Pete-locked responsive
  Mine / Ours / Beyond Community composition, compact white authoring modal
  and mobile bottom sheet, semantic tool colors, compact published
  attachments, private saves, and three-item reply previews while preserving
  the current owner-authoring and signed-in-member read boundaries.
- **Package manager and why:** the current root Codex session. After the prior
  writer pushed and relinquished exact SHA `dd372fea`, Pete transferred the
  existing lane to this session with the direction "Fix and complete it."
  The transfer changed no package surface, domain, audience, or product scope.
- **Triggered specialists and return target:** Original ChatGPT supplied the
  owner-accepted material visual authority. The visual integrity standard,
  Community trust contracts, and accessibility requirements applied. A fresh
  different reviewer must inspect the corrected exact SHA; this correction
  writer's verification is not presented as independent acceptance.
- **Branch and SHAs:** branch
  `work/2026-08-17-community-authoring-runtime-001-r2`; current authoritative
  original product base `ec65f4c3341056978d73534d74e5555e030f3c12`;
  current merge-control base `ffbeca40868e4aee414b68bf48a486d833d1a0e3`;
  independently rejected prior implementation SHA `04c3dff5985bb4c07350a2c3c669602addf192a0`;
  independently rejected incomplete correction SHA
  `4dc1cba43bb3dedc602a3affd0061f359610299d`;
  corrected implementation-content SHA
  `887bd087e722562fd4c78f4d75a3b128d1cd74d9`.
- **Changed paths:** `templates/community_feed.html`,
  `static/css/community-v1.css`, `static/js/community-v1.js`,
  `scripts/preview_community_primary_feed.py`, the four focused Community
  test files including the draft behavioral harness,
  `docs/governance/PACKAGE_REGISTRY.json`, this runtime package
  including `REVIEW_RECONCILIATION.md`, and the exact visual package at
  `../PS-COMMUNITY-VISUAL-REFINEMENT-001/` including its ten locked images.
- **Verification performed and result:**
  - JavaScript syntax and Python compilation: pass.
  - Focused Community plus package-registry suite: 198 tests, pass.
  - Repository-wide suite: 3,834 tests, pass; 24 expected skips.
  - Dependency-free integrated draft/close harness: 17 behavioral checks,
    pass.
  - `git diff --check`, JSON parse, and package-registry one-to-one inventory:
    pass.
  - Exact review reconciliation: both visually hidden selects remain enabled
    submission controls with `tabIndex: -1`; the Community confirmation is
    compact and centered at 320x800, 390x844, and the 768x480 200%-reflow
    equivalent; Active Questions and My Mix render truthful empty states; and
    both a 2,044-character restored draft and 2,258-character edited post open
    at the bounded 240px editor height with active internal scrolling.
  - Browser review: no console errors or horizontal overflow at 320, 390, 901,
    1024, 1180, or the 768x480 zoom-equivalent reflow viewport. Both rails
    remained visible at 901, 1024, and 1180. Current desktop, empty-composer,
    and mobile-bottom-sheet states were compared against locked visuals 01,
    03, and 09. Detailed geometry is recorded in
    `REVIEW_RECONCILIATION.md`.
  - Correction browser proof: a successful fixture-only create consumed the
    restored 511-character draft and reopened Create post empty with Post
    disabled. A subsequent 443-character create draft survived a successful
    existing-post edit intact with Post enabled. The console contained no
    warning or error.
- **Release state:** local candidate committed on a pushed review branch only.
  It is not in a runtime PR, not merged, not deployed, not enabled, and not
  live.
- **Known limits and deferred work:** authoring remains owner-only; stored
  `public` remains the transitional signed-in Community token; Connections and
  anonymous Public are disabled; Video and AI actions are truthfully
  unavailable; Voice produces text proposals, not public audio; no bounded
  post undo is claimed; no schema change exists; whole-site color refinement
  remains a later accepted review.
- **Next action:** a fresh different reviewer performs the read-only exact-SHA
  review described in `CLAUDE_REVIEW_HANDOFF.md`. Only an ACCEPT result can
  enter the separate governed grant, PR, deployment, live verification, and
  close sequence.

## Protected-path evidence

- **Identity, privacy, authorization, publication, and AI:** identity continues
  to be derived server-side before Community retrieval or mutation. The
  candidate does not widen author eligibility or read audiences. Only the
  enabled Community row can enter the existing deliberate confirmation path;
  Private is explanatory and Connections/Public are disabled. Drafts remain
  per-member local recovery data. AI sends no provider request and never
  saves, replaces, or publishes member text. Existing negative-path Community
  tests remain green.
- **Migration and rollback:** no schema or stored-procedure change was needed.
  Rollback is source rollback to the prior Community template/CSS/JavaScript;
  no production apply or data conversion exists.
- **Material visual authority:** exact comparison authority is
  `../PS-COMMUNITY-VISUAL-REFINEMENT-001/visual-authority/2026-08-17-pete-lock/`.
  Pete accepted the compact family and current color direction for this
  implementation, with later whole-site color refinement deferred. Writer
  comparison passed; a fresh different reviewer must inspect the exact
  corrected candidate.
- **Review reconciliation:** the prior content SHA
  `6e3936f89c28edb2e34ecf35fd1ceb33c1b74e91`. All four confirmed findings were
  accepted and corrected. The claimed 901-1288px rail disappearance was
  rejected because the later equal-specificity `display: block` declaration
  controls the cascade; browser evidence and a regression contract confirm
  that result. `REVIEW_RECONCILIATION.md` records every disposition and its
  evidence. No rail breakpoint change was made. The fresh review of `04c3dff5`
  found the edit draft-loss blocker. A second review rejected `4dc1cba4`
  because create cleanup was undone by the dialog close event. Both mutation
  branches and the delayed close event are corrected at `887bd087` with
  integrated behavioral and browser coverage.
- **Actual handoff:** review corrected implementation-content SHA
  `887bd087e722562fd4c78f4d75a3b128d1cd74d9` from the pushed r2 branch. After
  pushing the documentation-only handoff commit, this writer relinquishes
  edits until the different reviewer returns findings or Pete gives a new
  instruction.

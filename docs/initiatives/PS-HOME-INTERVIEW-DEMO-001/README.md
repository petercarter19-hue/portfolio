# PS-HOME-INTERVIEW-DEMO-001 — Homepage Interview Studio Illustrative Walkthrough

## Assignment

- **Writer:** Claude Code (architecture by Fable; implementation may continue in a
  successor Claude session against these records)
- **Designated session manager:** current ChatGPT Work/Codex control-room session
- **Branch:** `work/2026-07-19-home-interview-demo-001`
- **Worktree:** `C:\Users\peter\Documents\portfolio-home-interview-demo`
- **Base:** `origin/main` at `31864e43287d7cefb5a0d1c0441e94bec0bd6b1f` (verified current tip at architecture time; re-fetch at execution time)
- **Owner authorization:** Pete, 2026-07-19 (recorded below)
- **Final source tip:** `90d035a25344c850e6ed732c1efb6e4d0a240787`
- **Release:** Azure PR 86; squash merge
  `a98cced519a1f853ad9f4462fd438efa67d6f260`; automatic pipeline 122
  (`20260719.30`) passed Build and Deploy.
- **Current status:** accepted, deployed, and verified live as a fixed
  pre-convergence illustrative walkthrough. Final 5A/5C homepage projection
  parity remains open under the real-Studio convergence gate.

## Owner authorization — 2026-07-19

Pete authorizes implementation of PS-HOME-INTERVIEW-DEMO-001 as a **separate
homepage walkthrough package**. The authorization applies **only** to the
illustrative homepage Interview Studio scene. It does **not** authorize changes
to the real `/interview-studio` experience, which is being redesigned
independently under its own initiative. Voice-first emphasis applies only to
this homepage demonstration; the two full-Studio correction references in the
design ZIP are **not** authorization to edit the real Interview Studio
(this records option 2 of the Gate 2.4 authority-conflict finding).

## Design authority

- **Package:** `PS-HOME-INTERVIEW-DEMO-001_Design_Authority_Package.zip`
  (owner-supplied, outside the repository)
- **SHA-256 (verified 2026-07-19):**
  `968BFD9723A216939AB078C77D9725102A47746DB10D35D5DE07AEF6EEC082E3`
- **Visual authority:** Direction A — Editorial Studio Ledger, the four-state
  homepage walkthrough (desktop 1600×1000, mobile portrait 390×844, mobile
  landscape 844×390, plus focus/reduced-motion/no-JS proofs).
- The PNGs control composition and quality. The supplied `_shared.css` is
  **not** to be copied literally; its mobile/landscape sizing violates the
  accessibility floor and is corrected by this package (see
  [02_ARCHITECTURE_AND_IMPLEMENTATION_MAPPING.md](02_ARCHITECTURE_AND_IMPLEMENTATION_MAPPING.md) §7).
- The prior Gate 2.4 review branch is **evidence only**:
  `origin/work/2026-07-19-interview-gate-24-review` at
  `ca4af35117a4e3bb8bef0c8e98a26756677fc6cc`. Do not branch from or cherry-pick
  it. Its accessibility and truth findings are incorporated here.

## Package purpose

Insert a four-state illustrative Interview Studio scene into the existing
homepage **after Living Résumé and before My Story/Future**:

1. Question
2. Fictional sample answer
3. Fixed coaching review
4. Improved retry

The scene explains how Interview Studio works and ends with a normal
server-generated link to the real public `/interview-studio` route. The real
Interview Studio remains a separate package and is untouched.

## Truth boundary (binding)

The homepage walkthrough must:

- use only fixed fictional content;
- never activate a microphone;
- never accept or record a visitor answer;
- never call an AI or Interview API;
- never use `fetch`, `XMLHttpRequest`, or any other network request;
- never create localStorage, sessionStorage, cookies, drafts, attempts, goals,
  transcripts, or history;
- never upload or retain audio, video, or camera media;
- never imply the fictional answer belongs to Pete or the visitor;
- never imply account-backed, private, or authenticated Interview history;
- use a normal server-generated link to `/interview-studio` as the final action.

The full state/DOM/no-JS contract is in
[01_BOUNDARY_AND_STATE_CONTRACT.md](01_BOUNDARY_AND_STATE_CONTRACT.md).

## Writable files

- `templates/homepage.html` (one include line + asset references only)
- `templates/partials/homepage/_interview_demo_scene.html` (new)
- `static/css/homepage-scenes.css` (appended, clearly-marked scene section)
- `static/js/homepage-interview-demo.js` (new)
- `tests/test_homepage_scenes.py` (extended)
- `docs/initiatives/PS-HOME-INTERVIEW-DEMO-001/` (this package)
- `artifacts/ps-home-interview-demo-001/` (screenshots and evidence)

If another file is genuinely necessary, **stop and report the exact reason
before editing it.**

## Forbidden files and domains

`templates/interview_studio.html`, `static/css/interview-studio.css`,
`static/js/interview-studio.js`, `tests/test_interview_studio.py`, `app.py`
and route registration, APIs and model prompts, authentication/sessions,
databases/migrations, Capture/Moment/Placement/Story/résumé/Voice-Capture
behavior, `base.html`, global navigation, shared theme tokens, deployment
configuration, and the independent real Interview Studio upgrade branch.

Shared governance files (`CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`,
`ACTIVE_INITIATIVES.md`, etc.) are **not** edited by this package; the manager
serializes shared-governance activation and closeout separately.

## Package documents

1. [01_BOUNDARY_AND_STATE_CONTRACT.md](01_BOUNDARY_AND_STATE_CONTRACT.md) —
   the four deterministic states, exact fixed copy, no-input/no-request/no-storage
   boundary, DOM and JS state ownership, no-JS behavior, focus and announcements.
2. [02_ARCHITECTURE_AND_IMPLEMENTATION_MAPPING.md](02_ARCHITECTURE_AND_IMPLEMENTATION_MAPPING.md) —
   file-by-file implementation mapping, CSS/JS architecture, responsive reflow,
   required corrections to the design source, parity/deviation matrix, rollback.
3. [03_ACCESSIBILITY_AND_VALIDATION_PLAN.md](03_ACCESSIBILITY_AND_VALIDATION_PLAN.md) —
   accessibility contract, test plan, screenshot/evidence inventory, commands.
4. [COMPLETION_REPORT.md](COMPLETION_REPORT.md) — completed at closeout using
   the owner technical completion template.

## Delivery gates

Architecture (this package's records) → implementation on this branch →
self-review with Pass/Conditional/Fail → commit/push to Azure → Pete and
designated-manager visual/product acceptance → Azure PR/pipeline → live
verification.

That sequence passed for the package's fixed illustrative purpose. The
walkthrough remains static, fictional, and no-side-effect. Its current
Voice-default framing and paper-light modal in dark theme are accepted
pre-convergence limitations, not the controlling real-Studio design. After the
real 5A/5C Studio is accepted, released, and verified live, a fresh downstream
branch must converge and separately release the homepage projection.

## Gate 4 activation — 2026-07-20

The real Studio and release-governance gates have passed through PRs 101/102
and pipelines 149/150. Downstream convergence is now activated under
`PS-HOME-INTERVIEW-PARITY-001`. Claude Code must use a fresh post-activation
branch, write `04_REAL_STUDIO_CONVERGENCE.md` as the architecture before product
edits, preserve this package's accepted interaction shell and truth boundary,
and return the bounded implementation for manager visual-product acceptance.
The existing illustration remains live until that separate result is accepted,
released, and verified.

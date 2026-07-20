# Claude Architecture and Implementation Brief — Homepage Interview Parity

## Start gate

Open the authoritative Azure repository, follow `START_HERE.md` and
`docs/AI_WORKFLOW.md`, fetch `origin`, and verify the activation package and
pipeline are on current `origin/main`. Create
`work/2026-07-20-home-interview-parity-001` from that exact SHA. Record the
writer, branch, base, clean status, and reserved files in
`docs/initiatives/PS-HOME-INTERVIEW-DEMO-001/04_REAL_STUDIO_CONVERGENCE.md`
before touching a product file.

Do not reuse the deleted historical demo branch or disturb its preserved
worktree. Do not branch from the manager activation branch.

## Released manifest to reconcile

- Accepted implementation checkpoint:
  `39bc9a3f890ec8020eb84c4e3e416db6cd6912d2`.
- Final release source:
  `0aaf41768a33810b089f5fea3a66a5272e8b61d8`.
- Azure PR: 101.
- Squash merge: `39002f5130a1766d2090007c16582e0dbe07226c`.
- Pipeline: 149 / `20260720.20`, Build and Deploy passed.
- Live assets: `studio-5a5c-2` and `ps-theme-001-2`; released and live bytes
  matched during closeout.
- Release-governance merge:
  `2e811f4eec3e915bdb6a0aefa7bd744d6bc7553b`, pipeline 150 /
  `20260720.21` passed.
- Production: `/interview-studio` and `/interview-studio/history` verified.

Reconfirm the manifest from Azure and current production. Do not rely only on
this transcription.

## Architecture deliverable before implementation

Write `04_REAL_STUDIO_CONVERGENCE.md` first. It must contain:

1. exact writer branch and base SHA;
2. released manifest and live-verification timestamp;
3. complete reserved-file map;
4. old-demo-state to released-Studio-state parity matrix;
5. semantic DOM and fixed-state controller design;
6. light/dark token and component mapping without importing the production
   Studio stylesheet;
7. modal, background-inertness, focus, theme-switch, state-retention,
   responsive, reduced-motion, and no-JavaScript behavior;
8. exact truth-copy inventory and banned claims;
9. automated and browser-evidence plan; and
10. every intended deviation, with a reason.

Stop and return the architecture for manager review if any product decision,
visual authority, or file reservation is unclear. Architecture may clarify how
to implement the accepted experience; it may not redesign or weaken it.

## Recommended fixed journey

Preserve the existing always-visible poster as orientation. Inside the modal,
keep four deterministic server-rendered states:

1. **Write your answer** — a fixed written-answer surface matching Interview
   Me; dictation appears only as an optional aid, never the default.
2. **Submit for coaching** — the same fixed answer remains visible while a
   static three-part coaching-status sequence explains what the real Studio
   does after explicit submit.
3. **Bottom line first** — fixed review copy maps to the released review
   hierarchy, with the practice-signal disclaimer visible.
4. **Improve and practice again** — show the original and a fixed stronger
   retry, then provide the real `/interview-studio` CTA.

This maps poster + four modal states to the released orientation, active
written practice, processing, bottom-line review, and improvement journey.
Adjust only if the architecture proves a different count is necessary; record
the reason before implementation.

## Visual parity contract

Light must be recognizably **Editorial Studio Ledger**:

- warm paper canvas and restrained rules;
- navy editorial typography and answer outline;
- quiet cards and sparse gold emphasis;
- a clear written-answer focal surface; and
- right-rail information compressed into the bounded demo rather than copied
  wholesale.

Dark must be recognizably **Cinematic Studio**:

- layered deep-navy canvas and navy card surfaces;
- fine gold rules and restrained glow/depth;
- gold primary action, current stage, and answer focus treatment;
- readable light text with muted blue secondary copy; and
- no paper-white modal floating over the dark homepage.

Both themes use the same DOM, steps, copy, controls, truth, accessibility, and
state. Use the existing `body[data-theme]` and `ps-theme` mechanism. Do not add
a second theme system, new global tokens, a permanent navigation rail, or a
full Studio runtime on the homepage.

## Interaction and accessibility contract

Preserve the accepted shell: bounded trigger, portaled modal, Escape and close,
backdrop close, focus entry/trap/restoration, scroll lock, responsive mobile
bottom sheet, live-region step announcement, 44-pixel controls, 200% reflow,
reduced motion, and a useful no-JavaScript poster plus normal Studio link.

Correct the background contract: while open, non-dialog page regions must be
programmatically inert and restored exactly on close. Because the global header
switch becomes unavailable during a properly modal interaction, include a
modal-local `data-theme-toggle-proxy` using the already-released global theme
controller. Switching theme inside the modal must preserve the open dialog,
current step, fixed answer, focused control, and scroll position.

The controller remains bounded and deterministic. It may toggle modal state,
step visibility, accessibility attributes, inertness, and presentation only.
It must not use `fetch`, `XMLHttpRequest`, storage, cookies, input/form APIs,
microphone, camera, speech, media, timers, observers, or animation frames.

## Truth contract

The homepage walkthrough itself:

- uses fixed fictional content;
- accepts no visitor input;
- sends no AI or network request;
- stores nothing; and
- opens the real public Studio through a normal link.

When explaining the real Studio, state only released truth:

- Pete Carter is a **Public demo profile**; the visitor is not signed in as
  Pete;
- written Interview Me is primary and dictation is optional;
- the question and answer go to PeerSlate only after explicit submit;
- drafts, goals, attempts, and History are browser-local and clearable there;
- Video Practice media remains local and is not uploaded or analyzed; and
- scores are practice signals, not employer predictions.

Do not imply login, private cloud history, account sync, media analysis,
account-backed storage, Capture, Moment, Placement, Story, résumé edits,
sharing, publication, saved results, or authenticated
`/app/interview-studio`.

## Reserved implementation map

- `templates/homepage.html`: Interview include and cache-key references only.
- `_interview_demo_scene.html`: poster, fixed states, truth, modal theme proxy.
- `homepage-scenes.css`: only the bounded Interview scene/parity section;
  preserve unrelated homepage selectors byte-for-byte.
- `homepage-interview-demo.js`: deterministic modal/step/accessibility
  controller only.
- `tests/test_homepage_scenes.py`: extend exact product, truth, security,
  accessibility, theme, state, cache-key, and no-side-effect guardrails.
- `04_REAL_STUDIO_CONVERGENCE.md`, writer completion report, and parity
  evidence.

Do not touch the real Studio template, CSS, JavaScript, tests, route code,
`base.html`, `theme-toggle.js`, auth, database, Capture/Photo, Owner Home,
Placement, global navigation/tokens, deployment, or shared governance files.

## Evidence and return contract

Run focused homepage tests and the complete configured suite. Capture both
themes at desktop and 390×844 for the poster and all four modal states, plus
mobile landscape, 200% reflow, visible keyboard focus, theme switch with modal
and state retained, background inertness, reduced motion, long content, and
no-JavaScript fallback. Compare the converged result side-by-side with the
exact released Studio implementation evidence.

Return:

- exact base, branch, clean pushed full SHA, and changed files;
- completed architecture and parity/deviation matrices;
- complete-diff self-review with every finding and correction;
- every test command and result;
- evidence inventory and console result;
- known gaps;
- `Pass`, `Conditional`, or `Fail`; and
- an explicit statement that the result is branch-only—not merged, deployed,
  live, or parity-closed.

Relinquish the branch at handoff. Do not open or complete an Azure PR before
Pete or the designated manager accepts the implementation and visuals.

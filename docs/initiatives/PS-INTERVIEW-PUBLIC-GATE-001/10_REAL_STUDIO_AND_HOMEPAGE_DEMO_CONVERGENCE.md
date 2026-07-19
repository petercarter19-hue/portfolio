# PS-INTERVIEW-PUBLIC-GATE-001 - Real Studio and Homepage Demo Convergence

_Owner sequence recorded 2026-07-19. The real public Studio is upstream. The
homepage walkthrough is a later static projection of the accepted real
product._

## Controlling decision

The real `/interview-studio` is the visual and product source of truth for the
homepage Interview Studio walkthrough. The walkthrough may simplify the real
journey into a short, fixed demonstration, but it may not preserve an older
composition, theme treatment, product emphasis, control hierarchy, or truth
claim after the real Studio changes.

The selected Studio authority remains:

- Image 5 Concept A, **Editorial Studio Ledger**, for default/light;
- Image 5 Concept C, **Cinematic Studio**, for optional dark; and
- the exact source and identity recorded in
  `09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md`.

The sequence is therefore:

1. complete and accept the real Studio design;
2. architecture and implement the real Studio;
3. accept, merge, deploy, and verify the real Studio; and only then
4. converge the homepage walkthrough on the exact accepted and live Studio.

The walkthrough is not a second visual authority. It is downstream evidence of
the real product.

## Current evidence ledger

At the time this decision was recorded:

- the real Studio's 5A-light/5C-dark visual authority was recorded, but the
  complete 18-export Gate 2.4 design package was not yet accepted;
- real Studio implementation had not been authorized, started, merged,
  deployed, or verified live;
- the separate homepage walkthrough branch was
  `work/2026-07-19-home-interview-demo-001`;
- its clean pushed checkpoint was
  `358e7eea304a2b4d4008031ea8f51c523380ee4f`;
- that checkpoint contained a useful modal interaction shell, four-state
  walkthrough, focus/background controls, no-JavaScript fallback, responsive
  bottom sheet, static fictional content, truth strip, tests, and screenshots;
  and
- its light paper treatment in dark mode and Voice-first copy predated the
  final 5A/5C decision and the controlling written-practice-first product truth.

The homepage checkpoint is therefore a **prototype/interaction shell**. It is
not accepted, merged, deployed, or live. It must not be released unchanged.
If Claude has produced a newer clean pushed checkpoint before receiving this
instruction, Claude must return that newer full SHA and use it as the parked
checkpoint instead; the status remains the same.

## Statuses that must remain separate

| Layer | What proves it | Current state at this decision |
|---|---|---|
| Visual design | complete editable source, 18 primary exports, responsive/accessibility/truth review, feasibility, Pete and manager approval | In progress |
| Real Studio implementation | exact implementation branch/SHA, complete diff, tests, 18-state implementation evidence, writer `Pass` | Not authorized |
| Homepage demonstration | exact demo branch/SHA, fixed-state parity map, responsive/theme evidence, writer `Pass` | Prototype checkpoint only |
| Deployment | Azure PR, squash-merge SHA, Build and Deploy pipeline for that SHA | Not started for either change |
| Live production | route and asset verification against the deployed SHA, plus accepted visual evidence at production URLs | Unchanged |

Neither a design export nor a local screenshot proves implementation. A clean
implementation branch does not prove deployment. A green pipeline does not by
itself prove the live visual result. The completion report must name each layer
honestly.

## Required gate sequence

### Gate 1 - complete the dual-theme real Studio design

Complete the nine current-public screens in both themes, responsive and
accessibility evidence, truth review, semantic component/state inventory,
theme-persistence/no-state-loss plan, and Claude/Fable feasibility required by
`09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md`.

Gate 1 passes only after Pete and the designated manager explicitly approve the
actual complete design evidence. Until then, product code remains blocked.

### Gate 2 - architecture and implement the real Studio

After Gate 1 approval, Claude Code starts one fresh implementation branch from
then-current `origin/main`. Claude first records the implementation architecture
on that same branch, then implements and self-manages the complete slice. The
architecture is not a second design gate and may not weaken the accepted visual
or truth baseline.

Gate 2 passes only after Claude returns a clean pushed exact SHA, complete-diff
self-review, configured tests, required visual/accessibility evidence, and a
coherent `Pass`. Pete and the designated manager then perform focused product
and visual acceptance.

### Gate 3 - release and verify the real Studio

Only after Gate 2 acceptance may the real Studio branch enter an Azure pull
request. Record the implementation tip, Azure PR, squash-merge SHA, Build and
Deploy pipeline, and live `/interview-studio` and
`/interview-studio/history` verification. Verify both themes and representative
desktop/mobile states against the accepted implementation.

The demo remains parked until this gate passes.

### Gate 4 - converge the homepage walkthrough

After the real Studio is verified live, resume the existing homepage demo branch
with the same writer. Fetch `origin`, merge then-current `origin/main` into the
published demo branch without rebasing or force-pushing, and update only the
owned demo package and reserved homepage files. If branch ownership changes,
the prior writer must first return the clean pushed full SHA and explicitly
relinquish; the manager then assigns a fresh successor branch.

The updated walkthrough must be based on the exact released Studio evidence,
not on memory, an earlier mockup, or the pre-convergence demo checkpoint.

Gate 4 passes only after the demo's parity map, responsive/theme evidence,
tests, complete-diff self-review, and `Pass` are accepted. It receives its own
Azure PR, pipeline, and live homepage verification. The real Studio release and
the demo release remain separate closeouts even if the same writer completes
both.

## Paste-ready Claude instruction - real Studio architecture and implementation

Use this instruction only after the complete Gate 2.4 design, truth and
accessibility review, Claude/Fable feasibility review, and Pete plus designated
manager visual approval are explicitly recorded as passed.

> Open the authoritative Azure repository. Follow `START_HERE.md` and
> `docs/AI_WORKFLOW.md`, fetch `origin`, verify current `origin/main`, and read
> every current authority named by `docs/governance/CURRENT_BASELINE.yaml` plus
> the complete `PS-INTERVIEW-PUBLIC-GATE-001` package through
> `10_REAL_STUDIO_AND_HOMEPAGE_DEMO_CONVERGENCE.md`.
>
> Create a fresh `work/YYYY-MM-DD-interview-public-gate-001` branch from the
> exact current `origin/main`. You are the sole writer. Do not use or edit the
> parked homepage demo worktree or branch during this phase.
>
> Before product edits, record
> `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/11_REAL_STUDIO_IMPLEMENTATION_ARCHITECTURE.md`
> on your implementation branch. Map the accepted components, semantic DOM,
> state machine, theme tokens, responsive behavior, accessibility behavior,
> storage/media/request failure paths, and tests to the existing reserved files:
> `templates/interview_studio.html`, `static/css/interview-studio.css`,
> `static/js/interview-studio.js`, and `tests/test_interview_studio.py`.
> Identify the exact accepted design asset hashes and every approved deviation.
> Stop for manager reservation before touching any unreserved file.
>
> Implement one current public Studio, not two themed products. Light must be
> recognizably Image 5 Concept A, Editorial Studio Ledger. Dark must be
> recognizably Image 5 Concept C, Cinematic Studio. Both use the same semantic
> DOM, information architecture, controls, route behavior, state machine,
> browser-local data, truth, responsive behavior, and accessibility behavior.
> Use the existing global `body[data-theme]` / `ps-theme` mechanism. A theme
> change must not recreate the Studio or reset answers, drafts, goals, selected
> modes, history, media, focus, caret/selection, dialog state, or scroll.
>
> Preserve all real current functionality and truth: written Interview Me is
> primary; dictation is an optional aid; coaching sends the question and answer
> only on submit; Pete is `Public demo profile`; Interview AI keeps explicit
> generic/public-profile/compare source labels; Video Practice media stays local
> and is not uploaded or analyzed; drafts, goals, attempts, and History remain
> only in this browser and clearable there; practice scores remain practice
> signals, not employer predictions; and no action creates Capture, Moment,
> Placement, Journal, Story, resume changes, sharing, publication, account
> history, or `/app/interview-studio`.
>
> Self-manage the branch end to end. Run the complete configured suite and
> focused Interview Studio tests. Exercise all nine required screens in both
> themes, desktop, mobile portrait, mobile landscape, 200% reflow, keyboard
> focus, reduced motion, long content, JavaScript unavailable, local-storage
> unavailable, media unavailable/denied, request error, retry, and recovery.
> Capture implementation evidence; design exports alone do not count.
>
> Return a completed owner technical completion report with: exact base SHA;
> branch and clean pushed full tip SHA; changed files; architecture mapping;
> complete-diff self-review; every test command and result; 18 primary
> implementation screenshots plus responsive/accessibility/failure evidence;
> theme no-state-loss evidence; truth and 5A/5C parity matrices; known issues;
> and a final `Pass`, `Conditional`, or `Fail`. State explicitly that the work is
> implemented but not merged, deployed, or live. Explicitly relinquish the
> branch only when you are handing it off. Do not merge or deploy before Pete
> and the designated manager accept the implementation and visuals.

## Paste-ready Claude instruction - homepage walkthrough convergence

Use this instruction only after the real Studio has passed Azure deployment and
live visual verification, and after the exact released Studio manifest is
available.

> Open the authoritative Azure repository. Follow `START_HERE.md` and
> `docs/AI_WORKFLOW.md`, fetch `origin`, verify current `origin/main`, and read
> the complete current Interview Studio and homepage walkthrough packages.
>
> Confirm the exact released real Studio manifest before editing: implementation
> branch and full tip SHA, Azure PR, squash-merge SHA, successful Build and
> Deploy pipeline, live verification timestamp, and accepted production
> screenshots for 5A light and 5C dark. Record that manifest in the demo package.
>
> Resume `work/2026-07-19-home-interview-demo-001` only if you remain its sole
> writer. The observed parked checkpoint was
> `358e7eea304a2b4d4008031ea8f51c523380ee4f`; if you pushed a later clean
> checkpoint before the pause, report and use that exact SHA. Merge the current
> `origin/main` into the published demo branch. Do not rebase, force-push, or
> disturb another worktree. If ownership has changed, stop and return the exact
> checkpoint so the manager can assign a successor branch.
>
> Preserve the good interaction shell: a bounded homepage modal, clear trigger,
> focus trap and restoration, inert/hidden background behavior, Escape/close,
> responsive mobile bottom sheet, no-JavaScript poster/link, static fictional
> content, visible truth strip, and no network, API, input, storage, microphone,
> camera, or real coaching behavior inside the walkthrough.
>
> Converge the visuals and content on the released real Studio. Light must use
> the accepted 5A Editorial Studio Ledger composition and hierarchy. Dark must
> use the accepted 5C Cinematic Studio composition, depth, surfaces, restrained
> gold, and contrast; do not leave a paper-light modal floating in dark mode.
> Use the existing global `body[data-theme]` / `ps-theme` mechanism. Theme
> switching must preserve the walkthrough step, focused control, modal state,
> and scroll position.
>
> Replace the stale Voice-first framing. The demo must truthfully show written
> Interview Me as primary and any dictation/voice control only as an optional
> aid where the released Studio supports it. Match the real names, visible truth
> labels, action hierarchy, question/progress treatment, answer surface,
> processing treatment, review structure, score disclaimer, and final link to
> the live Studio. Do not invent login, private cloud history, account sync,
> media upload/analysis, Capture, Moment, Placement, Story, resume edits,
> sharing, publication, or saved results.
>
> Add
> `docs/initiatives/PS-HOME-INTERVIEW-DEMO-001/04_REAL_STUDIO_CONVERGENCE.md`.
> It must map every fixed walkthrough step to the exact released Studio
> screen/state it projects. A recommended concise journey is orientation,
> active fixed written answer, submitted/processing with the answer preserved,
> bottom-line review, and an improved retry or direct invitation to use the real
> Studio. Adjust the count only when the released state machine requires it;
> record the reason. The demo remains illustrative and static.
>
> Do not import the whole production Studio stylesheet or run the production
> Studio state machine on the homepage. Reuse semantic tokens and faithfully
> project the accepted components through bounded demo styles and a fixed demo
> controller. The production Studio and demo remain separately testable and
> must not share mutable runtime state.
>
> Self-review the complete branch and update the completion report. Return the
> exact base/released-Studio manifest, clean pushed branch and full SHA, changed
> files, step-to-screen parity map, tests, desktop/mobile/200%/keyboard/reduced-
> motion/no-JavaScript evidence in both themes, light/dark comparison images,
> known deviations, and `Pass`, `Conditional`, or `Fail`. State explicitly that
> this proves an implemented demonstration only; it is not merged, deployed, or
> live until its own Azure PR, pipeline, and production homepage verification
> are complete. Explicitly relinquish the branch at handoff.

## Convergence acceptance criteria

The combined sequence passes only when all of the following are true:

1. The real Studio visibly matches the accepted 5A light and 5C dark design
   across the nine current-public screens.
2. The real Studio's current functionality, truth, responsive behavior, and
   accessibility remain intact.
3. The real Studio is released through Azure and verified live before demo
   convergence begins.
4. Each demo step identifies the exact released Studio state it projects.
5. The demo is recognizably the same product composition in both themes, not an
   earlier design with updated colors.
6. The demo remains a static, no-side-effect walkthrough with visible truth and
   a direct path into the real public Studio.
7. Written practice is primary in both real product and demo; optional voice or
   dictation is not falsely elevated.
8. Mobile reflows and scrolls in both experiences; neither shrinks desktop UI
   until it becomes unreadable.
9. Real implementation and demo implementation each have their own exact
   branch/SHA, acceptance, PR, pipeline, and live verification evidence.
10. The final governance closeout names what is designed, implemented,
    demonstrated, deployed, and verified live without collapsing those states.

## Immediate instruction for the active demo writer

Commit and push any current in-scope demo progress, return the exact full SHA
and a short checkpoint report, and pause the branch. Do not merge, deploy, or
continue visual convergence until the real Studio has passed Gates 1 through 3.
Preserve the worktree and all evidence so the shell can be resumed at Gate 4.

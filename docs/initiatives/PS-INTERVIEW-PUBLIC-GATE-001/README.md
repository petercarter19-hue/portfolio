# PS-INTERVIEW-PUBLIC-GATE-001 — Interview Studio Public Gate and Progressive Layering

## Assignment

- Current status: owner-delegated manager acceptance passed; writer-owned merge
  preparation and Azure release remain.
- Designated session manager: ChatGPT Work/Codex for the 2026-07-20 acceptance
  and cross-computer closeout.
- Implementation/release writer: Claude Code, sole writer of
  `work/2026-07-19-interview-public-gate-001`.
- Accepted implementation SHA:
  `39bc9a3f890ec8020eb84c4e3e416db6cd6912d2`.
- Entry gate: PS-NEXT-WAVE-MANAGER-001 is squash-merged, its Azure pipeline is green, and the branch starts from the resulting current `origin/main`.
- Depends on: PS-INTERVIEW-002, PS-RESUME-PUBLIC-REFINE-001, and the verified public/auth route audit.

## Outcome

Make the existing Interview Studio an unmistakably honest public demonstration. A visitor must understand which public profile is grounding an answer, what is stored only in this browser, what is sent to PeerSlate for coaching, what camera/voice behavior remains local, and that account-backed private practice is a future authenticated workspace rather than a feature on the public route.

This package also improves progressive layering so the public Studio opens with one clear practice choice and reveals settings, history detail, secondary controls, and deeper explanation only when useful. It is a focused refinement, not a new Studio, authentication project, or backend persistence system.

## Owner-approved Gate A decision — updated 2026-07-19

Pete approved the manager recommendation to preserve the current interactive public experience while truth-labeling and simplifying it. The current package follows **Approach A**:

- keep written practice, real coaching requests, Interview AI modes, comparison, browser-local history, and local camera rehearsal;
- keep the current public route light-first Deep Navy Gold, with an optional
  dark theme of the same public product;
- label Pete Carter as the named public demo profile rather than authenticated identity;
- use **Interview Me**, **Interview AI**, and **Video Practice** as the current mode names;
- exclude the optional worked-example tour from this implementation;
- keep the scripted homepage demonstration and any future authenticated Studio
  separate from this real public route.

The controlling product scope and design allocation are recorded in
[05_OWNER_APPROVED_DESIGN_SCOPE.md](05_OWNER_APPROVED_DESIGN_SCOPE.md). The
newer exact visual authority and definitive Claude package are in
[09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md](09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md):
Image 5 Concept A controls default/light and Image 5 Concept C controls optional
dark. It supersedes the earlier assumption that the dark expression must wait
for an authenticated Studio. That earlier design-only boundary governed the
architecture phase; the later implementation and manager acceptance records
now control the active release state.

The real-Studio-first implementation and homepage-walkthrough sequence is in
[10_REAL_STUDIO_AND_HOMEPAGE_DEMO_CONVERGENCE.md](10_REAL_STUDIO_AND_HOMEPAGE_DEMO_CONVERGENCE.md).
The real Studio is upstream visual/product authority. Status update
2026-07-19: Pete accepted the fixed illustrative homepage walkthrough for an
interim live release; source tip `90d035a25344c850e6ed732c1efb6e4d0a240787`
squash-merged through Azure PR 86 at
`a98cced519a1f853ad9f4462fd438efa67d6f260`, and automatic pipeline 122 passed
Build and Deploy. That release is an honest pre-convergence demonstration
only — it is not final 5A/5C homepage parity, and its Voice-default framing
and paper-light dark modal remain known downstream convergence work. After
the real Studio passes doc-10 Gates 1–3 (accepted, implemented, released,
verified live), a fresh downstream branch converges the walkthrough on the
exact released product in a separate closeout (Gate 4).

The Gate 2.4 review, Claude/Fable feasibility, implementation, and designated
manager acceptance have occurred. The durable acceptance is recorded in
[16_MANAGER_IMPLEMENTATION_ACCEPTANCE.md](16_MANAGER_IMPLEMENTATION_ACCEPTANCE.md).
Claude Code must now merge current `origin/main`, correct the one stale version
sentence in its completion report, rerun evidence, and complete the Azure
release. Homepage convergence remains blocked until that release is live.

The historical 2026-07-19 pre-implementation final-image submission review is
recorded in
[08_GATE_24_FINAL_VISUAL_REVIEW.md](08_GATE_24_FINAL_VISUAL_REVIEW.md). Pete's
approval of the supplied visual direction is recorded, and the seven
PUBLIC-03-through-PUBLIC-V02 states are accepted as the target. The formal Gate
2.4 result is `Conditional` because the package still needs a bounded
PUBLIC-01/02 authority/source correction, complete responsive/accessibility
evidence, shared shell/component/token mapping, and Claude/Fable feasibility.
No product implementation is authorized by that review.

The 2026-07-19 Claude/Fable correction-and-feasibility response is recorded in
[11_REAL_STUDIO_IMPLEMENTATION_ARCHITECTURE.md](11_REAL_STUDIO_IMPLEMENTATION_ARCHITECTURE.md)
(the Gate 2 architecture record: shell resolution, semantic tokens with
measured contrast, component/state contract, screen-by-screen mapping, theme
no-state-loss proof plan, file mapping, risks, deviations D1–D22) and
[12_GATE_24_CORRECTION_AND_FEASIBILITY_ADDENDUM.md](12_GATE_24_CORRECTION_AND_FEASIBILITY_ADDENDUM.md)
(closure of all eleven Codex corrections; implementation feasibility **Pass**).
After a second Codex review returned `Conditional`, the round-2 closure
(addendum §H) added the separate PUBLIC-01/02 exports, the editable evidence
source, and the pre-implementation responsive/accessibility state evidence
under `artifacts/ps-interview-public-gate-001/gate-24-fable-evidence/`
(hash-pinned in its `EVIDENCE_INDEX.md`), and reconciled this README and the
completion report with the live homepage-demo status and Bible v2.5 /
Roadmap v2.4.

**Gate 1 closed 2026-07-19** (addendum §I): Pete reviewed the round-2
package directly and gave explicit approval, ratifying board 1 and
recording an owner-authorized exception to the parallel designated-manager
sign-off for this package's design gate only. Product implementation is
authorized. The separate real-implementation visual acceptance required by
`OWNER_VISUAL_INTEGRITY_STANDARD.md` V3 still applies before the built
product may merge or deploy.
The next-phase instructions are packaged in
[13_SONNET_IMPLEMENTATION_BRIEF.md](13_SONNET_IMPLEMENTATION_BRIEF.md)
(self-managed implementation writer) and
[14_OPUS_REVIEW_CHARTER.md](14_OPUS_REVIEW_CHARTER.md) (independent
reviewer). Product implementation stays blocked until the addendum §E
blockers are recorded as resolved.

Those pre-implementation blockers are now resolved. The current controlling
state is the manager acceptance in
`16_MANAGER_IMPLEMENTATION_ACCEPTANCE.md`, with only writer-owned merge
preparation, Azure release, live verification, and closeout remaining.

## Route and identity decision

- `/interview-studio` remains the public demonstration route.
- `/interview-studio/history` remains public and may show only records stored in the current browser for the public demonstration.
- Existing legacy aliases continue to redirect to `/interview-studio`.
- `/app/interview-studio` is reserved for a future authenticated owner workspace. This Claude package must not create, link to as working, or simulate that route.
- Public “Use history” behavior may use only the published profile data already supplied by the server. It must identify the public profile by name and never imply access to the visitor's private history.

## Acceptance criteria

1. The opening clearly says this is public practice and identifies the public profile used for any history-grounded example.
2. The visitor can distinguish “practice as yourself” from “generate an example using this public profile.” Generic best-practice output remains explicitly illustrative.
3. Drafts, goals, and completed-attempt records on the public route are labeled as current-browser data, not an account, private cloud history, or cross-device sync.
4. The settings/privacy explanation states when the active question and submitted answer are sent to PeerSlate for coaching. Camera recording remains local and unretained; microphone behavior is described accurately for the implemented browser path.
5. The default view has one dominant practice object. Secondary configuration and history depth use accessible progressive disclosure without hiding essential truth labels.
6. Written practice, model-answer modes, compare behavior, browser-local history, camera rehearsal, legacy redirects, and existing API failure states continue to work.
7. No public page exposes private Capture/Moment/member data, and no public action writes to Capture, Moment, Journal, résumé, or another canonical surface.
8. Keyboard, visible focus, screen-reader names/states, 200% zoom, reduced motion, 390×844 mobile, unavailable-media fallbacks, and no-JavaScript truthfulness are reviewed.
9. Focused Interview Studio tests, navigation/site rules, governance guardrails, and the complete configured suite pass.

## Writable files

- `templates/interview_studio.html`
- `static/css/interview-studio.css`
- `static/js/interview-studio.js`
- `tests/test_interview_studio.py`
- package-specific screenshots under `artifacts/ps-interview-public-gate-001/`
- This initiative directory and its completion report

If implementation requires another file, stop and ask the manager to reserve it before editing.

## Read-only and forbidden domains

- Treat `app.py`, public API endpoints, route registration, entitlement resolution, public profile data, and shared base/navigation files as read-only.
- Do not create authenticated routes, sessions, server persistence, migrations, database calls, private history, or account sync.
- Do not touch Capture, Moment, Journal, résumé, owner templates/styles, global theme tokens, navigation, deployment configuration, or backend tests.
- Do not claim privacy merely because data is in browser storage; explain the actual boundary.
- Do not add a fake sign-in destination, disabled owner workspace, second profile dataset, or invented member activity.

## Required reading

Follow `START_HERE.md`, then read the current governance records, Document Control, Bible/Roadmap/Sync Standard, `docs/PEERSLATE_SITE_RULES.md`, PS-INTERVIEW-002, [route and truth boundary](01_BOUNDARY_CONTRACT.md), [experience/accessibility contract](02_EXPERIENCE_ACCESSIBILITY.md), [validation plan](03_VALIDATION_PLAN.md), [implementation sequence](04_IMPLEMENTATION_PLAN.md), [owner-approved design scope](05_OWNER_APPROVED_DESIGN_SCOPE.md), [Fable design brief](06_FABLE_CURRENT_PUBLIC_DESIGN_BRIEF.md), [Gate 2.4 review contract](07_GATE_24_SESSION_REVIEW.md), [dual-theme visual authority and Claude brief](09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md), and [real Studio/demo convergence sequence](10_REAL_STUDIO_AND_HOMEPAGE_DEMO_CONVERGENCE.md).

Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` and the exact branch plus full commit SHA.

The manager record for the real-Studio/demo sequencing update is
[10_CONVERGENCE_MANAGER_COMPLETION_REPORT.md](10_CONVERGENCE_MANAGER_COMPLETION_REPORT.md).

## Gate 2 V3 acceptance — 2026-07-20

Pete explicitly directed Codex to recover the interrupted acceptance work,
independently review the complete branch, correct any blocker, and proceed
through release when green. That current owner instruction is recorded as a
bounded delegation for this implementation gate and for the necessary
shared-file correction described in D22. Codex reviewed the 5A/5C evidence,
the complete implementation diff, current Bible v2.6 / Roadmap v2.5
authority, and the narrow `tests/test_site_background.py` exception. The
visual/product implementation and that test exception are **accepted**.

The acceptance pass found one real blocker before approval: the header theme
switch cannot be operated while a native modal is open. The correction adds
synchronized modal-local switch proxies through the existing global theme
controller, preserves modal semantics and focus containment, and leaves
`static/js/interview-studio.js` theme-agnostic. Focused automated tests and
desktop/mobile real-browser verification are green. Release is authorized
subject to the complete configured suite and Azure release pipeline passing;
the result must still be verified on production before it may be called
live. The separate coaching-backend variability, manual screen-reader AT
pass, sitewide theme-toggle scroll drift, and Gate 4 homepage convergence
remain disclosed follow-ups rather than claims of this UI release.

## Release closeout — 2026-07-20

Final source `0aaf41768a33810b089f5fea3a66a5272e8b61d8` squash-merged through Azure
PR 101 at `39002f5130a1766d2090007c16582e0dbe07226c`; Azure deleted the source
branch. Automatic pipeline 149 (`20260720.20`) passed Build and Deploy for the
exact merge. Production then served the new `studio-5a5c-2` and
`ps-theme-001-2` assets, whose bytes matched the release; desktop and 390px
browser verification passed the public truth, orientation/History, stage,
modal theme/focus/state-retention, overflow, and console gates.

PS-INTERVIEW-PUBLIC-GATE-001 is implemented, demonstrated, accepted, merged,
deployed, and live. The real Studio is now the released upstream authority for
a separately assigned Gate 4 homepage-convergence package. Homepage parity,
the coaching-response follow-up, and the manual screen-reader AT pass remain
open and are not claimed complete by this closeout. The GitHub backup mirror
also remains behind because it is public and requires explicit owner approval
before this session may advance it.

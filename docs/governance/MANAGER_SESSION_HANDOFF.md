# PeerSlate Manager Session Handoff

_Prepared 2026-07-18 and updated 2026-07-19 for self-managed delivery lanes,
the released Voice implementation, and its reopened visual gate. Repository and
branch facts are a snapshot; fetch `origin` before acting._

## Start here on any computer

1. Open the authoritative Azure clone and follow root `START_HERE.md` exactly.
2. Fetch `origin`, inspect the current branch/worktree, and fast-forward a clean
   `main`. Never disturb a dirty task worktree to make it current.
3. Read `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`,
   `ACTIVE_INITIATIVES.md`, this handoff, the current Bible/Roadmap, and the
   assigned initiative.
4. Treat the merged repository as authority. Chat memory, downloaded ZIPs,
   local worktrees, and this dated snapshot do not replace current `origin/main`.

## Manager role and lane model

- **ChatGPT Work:** task manager, shared-authority/file-boundary coordinator,
  visual authority, exception escalation point, and final product-acceptance
  room. It does not routinely repeat a coherent writer self-audit.
- **ChatGPT Codex:** self-managed writer for assigned backend packages.
- **Claude Code / Fable:** self-managed writer for assigned front-end packages,
  including a protected owner surface when the package explicitly assigns it.
- Each writer owns implementation, complete-diff review, correction, tests,
  evidence, PR readiness, and, after Pete/ChatGPT Work acceptance, Azure
  release/closeout. Every report states `Pass`, `Conditional`, or `Fail`.
- One writer per branch remains mandatory. A branch/SHA handoff is required when
  a different writer continues; it is not required merely because the same
  self-managed writer reached self-review or PR readiness.

## Verified released foundation

Before this visual-integrity governance package, Azure `main` was
`5488819ad13d3f411319d7e184fde3779d62b8d2` after PR 70 and pipeline 97.
Always fetch for the actual current tip.

The visual-integrity governance package then squash-merged through Azure PR 71
at `28ec01097677219bbe466ff2c731707d0e4a2b89`; pipeline 99
(`20260719.7`) passed Build and Deploy. This released Bible v2.4, the Owner
Visual Integrity Standard, and this handoff without changing website behavior.

The later Story-composition direction adopts Bible v2.5 and Roadmap v2.4. The
next manager must treat the current baseline pointers as controlling and fetch
`origin` for the exact release evidence.

That direction squash-merged through Azure PR 73 at
`aaee6e563a94e19d1786ded3f636d8376e20d500`; pipeline 102
(`20260719.10`) passed Build and Deploy. Production behavior remained
unchanged, including the canonical My Story redirect and the protected Capture
sign-in boundary.

- Public résumé refinement: PR 62 / pipeline 83.
- Capture lifecycle: PR 63 / pipeline 85.
- Canonical Moment: PR 66 / pipeline 91.
- Private placement reference foundation: PR 68 / pipeline 93.
- Placement governance closeout: PR 69 / pipeline 95.
- Voice activation package: PR 70 / pipeline 97.
- Visual-integrity governance and manager handoff: PR 71 / pipeline 99.
- Member-directed Story composition authority: PR 73 / pipeline 102.
- Private Voice Capture implementation: PR 75 at
  `eede8565d703a466bd788962d494e8b385b53409` / pipeline 105.
- Production checks after PR 70: `/`, `/petec/resume`, and
  `/interview-studio` returned 200; `/app/capture` redirected a signed-out
  visitor to sign-in.

Reusable and not to be rebuilt: real identity and two-owner isolation, Owner
Settings, private text Capture lifecycle, canonical Moment confirmation,
private exact-version Placement reference foundation, refined public résumé,
public browser-local Interview Studio, and Deep Navy Gold foundations.

## Active lane 1 - PS-VOICE-001

### Honest current state

Voice is implemented and deployed. Production private Blob/RBAC, managed-
identity Speech, SQL migration/verification, Azure PR 75, pipeline 105, and the
protected functional path passed. Pete completed the signed-in workflow and
confirmed that it works.

Pete then withdrew visual acceptance because the protected desktop and mobile
experience is clunky and does not match the approved homepage/feed walkthrough.
Voice is therefore technically deployed but product/visual status remains In
Progress.

Preserve `C:\Users\peter\Documents\portfolio-voice-001`; do not switch, clean,
edit, stash, or reuse it. Claude Code now owns a fresh self-managed visual-
parity branch from current `origin/main` under
`docs/initiatives/PS-VOICE-001/06_VISUAL_PARITY_CORRECTION.md`.

The active Claude branch is `work/2026-07-19-voice-visual-parity-001` in
`C:\Users\peter\Documents\portfolio-voice-visual-parity`. Its observed pushed
checkpoint `0158daf22d26e7c38be494e2b32e6b51fdaca0fb` contains design
instructions only. The manager answers are recorded in the correction addendum;
Claude may implement after synchronizing current `origin/main` without another
pre-build manager pause.

### Required product outcome

The first slice is short private voice recording (3 minutes / 20 MB, `en-US`),
private original audio in Azure Blob Storage, Azure Speech transcription through
managed identity, editable transcript review, and explicit **Save private
Capture** into the existing lifecycle. Text remains available. No Moment,
Placement, Journal, résumé, Studio, share, audience, or publication is created
automatically.

### Owner visual correction and final acceptance

Claude self-reviews and corrects the returned UI against
`OWNER_VISUAL_INTEGRITY_STANDARD.md`:

- the homepage Voice walkthrough is the minimum visual/interaction authority;
- the real protected UI must be recognizably the same or better;
- Speak and Type are both first-class opening choices;
- switching paths must not silently destroy member work;
- microphone, waveform/timer, stop, playback/retry, editable transcript,
  privacy, explicit save, failures, desktop/mobile/keyboard/zoom evidence, and
  owner/manager visual acceptance are mandatory.

The approved future Community, Connections, selected-audience, My Story, Slate
Board, résumé, attachment, AI-draft, and publication affordances may appear as
polished, disabled `Coming later` scaffolding. **Save private Capture** remains
the only live completion action. Claude returns exact evidence and a
`Pass`/`Conditional`/`Fail` report. Pete and ChatGPT Work perform a focused
real-product acceptance review rather than a second complete technical audit.

## Active lane 2 - PS-INTERVIEW-PUBLIC-GATE-001

### Product decision already approved

Keep the current interactive, unauthenticated `/interview-studio` under Approach
A. Preserve written answers, real coaching requests, Interview AI, comparison,
browser-local history, and local camera rehearsal. Keep the route light-first
Deep Navy Gold. Pete is a clearly labeled public demo profile, not signed-in
identity. Current mode names are Interview Me, Interview AI, and Video Practice.

### Design state and selected direction

The Gate 2.2/2.3 visual-art-direction package proposed three directions. Direction
A, **Editorial Studio Ledger**, is selected. It is a strong art direction but
not yet implementation authority. Known corrections remain:

- use one dominant opening CTA;
- keep **Interview Me** as the mode name; "written practice" may describe it;
- show Continue local draft only when a real browser draft exists;
- split video permission, recording, and playback/delete into truthful states;
- map Improve Answer to the existing public coaching behavior and do not invent
  a save or account capability.

### Required next design gate

The assigned ChatGPT visual-authority session must return Gate 2.4: the complete
nine current-public screens,
editable responsive source, mobile portrait/landscape, 200% reflow, keyboard
focus, reduced motion, long content, failure and media-denied states, component
inventory, truth/accessibility review, and implementation mapping. It should
also design a separate homepage Interview Studio walkthrough using Direction A.
That homepage walkthrough is illustrative only and belongs to a later separate
package/branch; it must not replace the real public Studio.

Then:

1. ChatGPT Work reviews the complete package.
2. Claude/Fable performs feasibility review only.
3. Pete and ChatGPT Work approve the final visual baseline.
4. Only then may Claude receive implementation authorization on a fresh branch.

Do not authorize Claude implementation from the three-direction art package
alone.

## Owner-wide visual decision

The current Bible is v2.5 and the
`OWNER_VISUAL_INTEGRITY_STANDARD.md` is part of mandatory startup. Selected
demonstrations are visual promises: the real experience must match or exceed
them. Visual polish is a release gate across all user-facing PeerSlate work,
alongside function, privacy, security, accessibility, tests, and deployment.
The current homepage overall is not the target; a broader homepage redesign is
still future work.

## Owner Story composition decision

The future authenticated My Story editor is member-directed. Members shall be
able to move and resize supported notes, text, pictures, and media; control
overlap/layering; undo and restore; preview desktop/tablet/mobile and exact
audiences; save a private layout draft; and publish separately. Dragging requires
keyboard and structured-editor equivalents. AI may propose a layout but may not
silently apply, save, overwrite, or publish it.

Pete's concrete acceptance case is the current **I went back at 36** card: he
must be able to make it smaller or move it so the sailboat in the Maui image
remains visible. `PS-STORY-COMPOSER-001` is planned future work, not active, and
does not interrupt Voice or Interview.

## Roadmap looking forward

Near-term sequencing is:

1. finish and release the PS-VOICE-001 visual correction after Claude's
   self-certified evidence and focused Pete/ChatGPT Work acceptance;
2. finish Interview Gate 2.4, feasibility review, owner approval, and then the
   bounded public Studio implementation;
3. define the separate homepage Interview walkthrough package after its design
   freezes;
4. choose the next backend consumer or owner-shell slice without automatically
   starting Journal;
5. build the real owner Home/viewer modes and authenticated Studio only through
   separately approved identity, persistence, authorization, and lifecycle
   packages;
6. conduct the broader public/homepage visual convergence after its entry gate;
7. schedule PS-STORY-COMPOSER-001 only after its full authenticated projection,
   layout persistence, accessible interaction, and publication design gate;
8. run a two-member founding alpha with Pete and Danielle, then structured
   feedback, fixes, a small invited cohort, and measured rollout.

Journal UI remains on hold. Do not duplicate Capture or Moment text, create a
second résumé dataset, imply account-backed public Studio history, or treat a
backend reference as a visible member feature.

## First actions for the next manager session

1. Fetch `origin` and verify the exact current `main`, current Bible pointer,
   pipeline, and production routes.
2. Confirm the self-managed delivery workflow is merged and green.
3. Inspect all worktrees without changing them; confirm each active branch has
   one writer and non-overlapping files.
4. Give Claude the current-main Voice visual-correction package and let Claude
   self-manage implementation, self-review, tests, evidence, and PR readiness.
5. Review Claude's real Voice result and `Pass`/`Conditional`/`Fail` report with
   Pete; do not recreate the entire technical audit by default.
6. After acceptance, let Claude complete its Azure PR, pipeline, production
   verification, and package closeout.
7. Obtain and review the complete Interview Gate 2.4 package.
8. Send it to Claude/Fable for feasibility review, then obtain Pete's final
   visual approval before code.
9. Keep Voice and Interview status, holds, decisions, and next gates current in
   the repository after each material handoff or release.

## Paste-ready kickoff for a new ChatGPT Work session

> You are the PeerSlate manager. Open and follow `START_HERE.md`, then read
> `docs/governance/MANAGER_SESSION_HANDOFF.md` and every authority file it names.
> Fetch authoritative Azure `origin/main` and inspect all worktrees before any
> write. Apply the self-managed lane model: each assigned writer implements,
> reviews its complete diff, corrects issues, runs tests/evidence, prepares the
> PR, and returns `Pass`, `Conditional`, or `Fail`; after focused Pete/ChatGPT
> Work acceptance the same writer completes Azure release/closeout. Preserve the
> original PS-VOICE-001 worktree and assign Claude the fresh protected Voice
> visual correction under `06_VISUAL_PARITY_CORRECTION.md`. The real UI must
> match or exceed the homepage/feed walkthrough on desktop and mobile, with
> Speak and Type first class and future controls truth-labeled as disabled.
> Continue Interview only at Gate 2.4 design review until its complete package
> and approvals pass. Maintain honest implementation, demonstration, deployment,
> and live-production boundaries.

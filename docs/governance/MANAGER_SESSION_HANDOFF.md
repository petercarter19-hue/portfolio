# PeerSlate Manager Session Handoff

_Prepared 2026-07-18 for the next ChatGPT Work manager session. Repository and
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

- **ChatGPT Work:** PeerSlate manager. Owns authority records, package
  sequencing, design and handoff review, merge readiness, Azure PRs, production
  migrations/infrastructure gates, deployment, and release verification.
- **ChatGPT Codex:** backend convergence writer. Owns only its assigned private
  Capture/Moment/Placement/service/migration package and returns a pushed branch
  plus exact full SHA without merging or changing production.
- **Claude Code / Fable:** public-experience design feasibility and approved
  front-end implementation. It does not change auth, private data, migrations,
  or backend contracts.
- One writer per branch. Voice and Interview may proceed in parallel because
  their writable files do not overlap.

## Verified released foundation

Before this visual-integrity governance package, Azure `main` was
`5488819ad13d3f411319d7e184fde3779d62b8d2` after PR 70 and pipeline 97.
Always fetch for the actual current tip.

The visual-integrity governance package then squash-merged through Azure PR 71
at `28ec01097677219bbe466ff2c731707d0e4a2b89`; pipeline 99
(`20260719.7`) passed Build and Deploy. This released Bible v2.4, the Owner
Visual Integrity Standard, and this handoff without changing website behavior.

- Public résumé refinement: PR 62 / pipeline 83.
- Capture lifecycle: PR 63 / pipeline 85.
- Canonical Moment: PR 66 / pipeline 91.
- Private placement reference foundation: PR 68 / pipeline 93.
- Placement governance closeout: PR 69 / pipeline 95.
- Voice activation package: PR 70 / pipeline 97.
- Visual-integrity governance and manager handoff: PR 71 / pipeline 99.
- Production checks after PR 70: `/`, `/petec/resume`, and
  `/interview-studio` returned 200; `/app/capture` redirected a signed-out
  visitor to sign-in.

Reusable and not to be rebuilt: real identity and two-owner isolation, Owner
Settings, private text Capture lifecycle, canonical Moment confirmation,
private exact-version Placement reference foundation, refined public résumé,
public browser-local Interview Studio, and Deep Navy Gold foundations.

## Active lane 1 - PS-VOICE-001

### Honest current state

Voice is authorized and actively being implemented, but it is not live. The
production Capture experience remains text-only until the full manager release
gate passes.

At the manager snapshot:

- local worktree: `C:\Users\peter\Documents\portfolio-voice-001`
- branch: `work/2026-07-18-voice-001`
- base/HEAD: `5488819ad13d3f411319d7e184fde3779d62b8d2`
- state: active dirty worktree with Voice routes, services, SQL, infrastructure,
  UI, and tests in progress
- pushed remote branch: none yet

Do not switch, clean, edit, stash, or reuse that worktree. ChatGPT Codex owns it
until it supplies a clean pushed branch, exact full SHA, test evidence, SQL and
Azure proof, screenshots, completion report, and explicit relinquishment.

### Required product outcome

The first slice is short private voice recording (3 minutes / 20 MB, `en-US`),
private original audio in Azure Blob Storage, Azure Speech transcription through
managed identity, editable transcript review, and explicit **Save private
Capture** into the existing lifecycle. Text remains available. No Moment,
Placement, Journal, résumé, Studio, share, audience, or publication is created
automatically.

### Owner visual addendum that the manager must enforce at review

Codex started before the new visual-integrity authority was merged. The manager
must therefore review the returned UI against `OWNER_VISUAL_INTEGRITY_STANDARD.md`:

- the homepage Voice walkthrough is the minimum visual/interaction authority;
- the real protected UI must be recognizably the same or better;
- Speak and Type are both first-class opening choices;
- switching paths must not silently destroy member work;
- microphone, waveform/timer, stop, playback/retry, editable transcript,
  privacy, explicit save, failures, desktop/mobile/keyboard/zoom evidence, and
  owner/manager visual acceptance are mandatory.

If that evidence or parity is missing, return the branch for rework rather than
merging a merely functional UI.

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

ChatGPT Pro must return Gate 2.4: the complete nine current-public screens,
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

The current Bible is updated to v2.4 and the new
`OWNER_VISUAL_INTEGRITY_STANDARD.md` is part of mandatory startup. Selected
demonstrations are visual promises: the real experience must match or exceed
them. Visual polish is a release gate across all user-facing PeerSlate work,
alongside function, privacy, security, accessibility, tests, and deployment.
The current homepage overall is not the target; a broader homepage redesign is
still future work.

## Roadmap looking forward

Near-term sequencing is:

1. finish and release PS-VOICE-001 after manager technical and visual review;
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
7. run a two-member founding alpha with Pete and Danielle, then structured
   feedback, fixes, a small invited cohort, and measured rollout.

Journal UI remains on hold. Do not duplicate Capture or Moment text, create a
second résumé dataset, imply account-backed public Studio history, or treat a
backend reference as a visible member feature.

## First actions for the next manager session

1. Fetch `origin` and verify the exact current `main`, current Bible pointer,
   pipeline, and production routes.
2. Confirm this visual-integrity governance package is merged and green.
3. Inspect all worktrees without changing them; identify the active Voice writer.
4. Wait for or obtain the exact Codex Voice handoff branch/SHA.
5. Review Voice scope, SQL, infrastructure, privacy, tests, and rollback.
6. Review Voice UI against the homepage demonstration and Speak/Type decision.
7. Return Voice for rework if visual or technical gates are incomplete; otherwise
   run production infrastructure/migration, Azure PR, pipeline, and live checks.
8. Obtain and review the complete Interview Gate 2.4 package.
9. Send it to Claude/Fable for feasibility review, then obtain Pete's final
   visual approval before code.
10. Keep Voice and Interview status, holds, decisions, and next gates current in
    the repository after each material handoff or release.

## Paste-ready kickoff for a new ChatGPT Work session

> You are the PeerSlate manager. Open and follow `START_HERE.md`, then read
> `docs/governance/MANAGER_SESSION_HANDOFF.md` and every authority file it names.
> Fetch authoritative Azure `origin/main` and inspect all worktrees before any
> write. Preserve the active PS-VOICE-001 worktree and require Codex's exact
> pushed branch/SHA handoff before review. Enforce the Voice visual addendum:
> the real protected UI must match or exceed the homepage Voice walkthrough and
> keep Speak and Type first class. Continue PS-INTERVIEW-PUBLIC-GATE-001 only at
> Gate 2.4 design review; do not authorize Claude implementation until the full
> nine-screen Direction A package, feasibility review, and Pete/manager visual
> approval are complete. Maintain honest implemented-versus-demonstration-versus-live
> boundaries and close every material package through Azure with full evidence.

# PS-CAPTURE-MEDIA-001 - Capture Media Manager Architecture

## Assignment

- Owner decision: Pete, 2026-07-19
- Designated session manager: ChatGPT Work/Codex manager session
- Manager transfer: Pete reassigned this package from Claude Co-Work to this
  session on 2026-07-19. No authoritative Capture Media implementation branch,
  commit, or writer handoff existed at transfer.
- Manager branch: `work/2026-07-19-capture-media-manager`
- Entry base: Azure DevOps `origin/main` at
  `229bfba4cd31e0eb56b99a94e90f16aa3fabb396`
- Synchronized baseline before closeout: Azure DevOps `origin/main` at
  `6a96878069e717b8b5455bf19729e9972cc435fa` (Bible v2.6 / Roadmap v2.5)
- Current status: Architecture, default-off Photo backend, and accepted Photo 1
  experience are released; Photo enablement gates remain open.
- Released implementation: backend PR 95 / pipeline 139, governance closeout
  PR 96 / pipeline 140, and experience PR 98 / pipeline 143.
- Current writer: Unassigned. A new package and branch are required for the
  signed-in lifecycle, two-owner, homepage-parity, and enablement gates.
- Production status: Photo code is deployed with the flag off; Photo, video,
  and document Capture are not member-visible.

This package-local assignment supersedes the earlier Claude Co-Work name for
PS-CAPTURE-MEDIA-001. Shared governance files remain read-only on this branch;
their assignment/status pointers are updated only through a separately reserved
governance closeout after this package is accepted.

## Decision

Build **private Photo Capture first**, followed by Document Capture and then
Video Capture. The first product chain is:

`take or choose photo -> private quarantine -> malware scan -> safe preview -> owner writes/reviews note -> explicit Save private Capture -> existing Capture lifecycle`

Photo is the smallest complete media slice that gives members immediate value
and proves the reusable private-media, provenance, scan, preview, export, and
deletion contracts. It deliberately adds no OCR, AI caption, matching,
publication, placement, Moment automation, document extraction, or video
transcoding.

## Delivery order and progress

1. Accept and squash-merge this manager package.
2. Activate `PS-CAPTURE-PHOTO-BACKEND-001` for ChatGPT Codex on
   `work/2026-07-19-capture-photo-backend-001`.
3. In parallel with backend work, complete and accept the photo-specific V1
   desktop/mobile visual-state package. Do not change runtime UI on that design
   branch.
4. After the backend merge and visual acceptance, activate
   `PS-CAPTURE-PHOTO-EXPERIENCE-001` for Claude Code on a fresh dated branch.
5. Release only after SQL, isolated Azure, security, accessibility, visual,
   pipeline, and signed-in production gates pass.
6. Run the required homepage parity package in the same release wave. The real
   protected product remains upstream authority.

Steps 1-4 are complete. The accepted flag-off release boundary in step 5 is
complete through PR 98/pipeline 143. Signed-in production lifecycle evidence
and step 6 remain open and block Photo enablement.

Only one writer owns one implementation branch at a time. Home/owner-viewer and
Interview Studio may continue in parallel because their product decisions are
separate, but shared files remain serialized as described in
`09_IMPLEMENTATION_DECOMPOSITION.md`.

## Package documents

1. [Current-state inventory](01_CURRENT_STATE_INVENTORY.md)
2. [Vertical-slice decision](02_VERTICAL_SLICE_DECISION.md)
3. [Shared media architecture](03_SHARED_MEDIA_ARCHITECTURE.md)
4. [Photo requirements](04_PHOTO_REQUIREMENTS.md)
5. [Security, privacy, and lifecycle](05_SECURITY_PRIVACY_LIFECYCLE.md)
6. [Experience and accessibility](06_EXPERIENCE_ACCESSIBILITY.md)
7. [Schema, infrastructure, and rollout](07_SCHEMA_INFRASTRUCTURE_ROLLOUT.md)
8. [Test and release evidence](08_TEST_RELEASE_PLAN.md)
9. [Implementation decomposition and handoff](09_IMPLEMENTATION_DECOMPOSITION.md)
10. [Completion report](COMPLETION_REPORT.md)

## Truth boundary

- Existing text and Voice Capture remain the only live Capture inputs.
- PS-VOICE-001 is released and protected. This package reuses its contracts but
  does not migrate, absorb, or rewrite its tables, storage adapter, Speech
  provider, or accepted UI.
- Photo code is deployed but unavailable while its flag remains off. Video and
  document upload are not implemented. Photo enablement still requires the
  accepted signed-in lifecycle and homepage-parity packages.
- New media always starts private and owner-scoped. It never creates a Moment,
  Placement, downstream room object, share, audience grant, public URL, or
  publication automatically.
- Journal, Story composition/publication, résumé, Slate Board, Interview Studio,
  Feed, global navigation/theme, and owner Home/viewer mode are outside this
  package.

## Blocking enablement entry gates

Recorded 2026-07-21 by `PS-GOV-TRUTH-RECONCILIATION-001` under Pete's delegated
decision. These are **gates, not plans**. Photo enablement may not be scheduled
or approved until each is satisfied and the result is recorded here.

| # | Gate | State 2026-07-21 |
|---|---|---|
| 1 | Universal composer / Save Moment / derived-Journal integration, or an explicit owner-approved temporary exception | Open. Controlled by `PS-GOV-JOURNAL-SYSTEM-001/04_ACTIVE_LANE_COMPATIBILITY_AND_TRANSITION.md` |
| 2 | Real signed-in Azure lifecycle proof and two-owner denial in production | Open |
| 3 | **Defender production malicious-path proof (choice A)** | **Open and blocking. See below.** |
| 4 | Homepage Capture Photo parity | Open |
| 5 | Explicit owner-and-manager enablement decision | Open |

### Gate 3 — Defender choice A, deferred not cancelled

The production Defender-malicious row is `Conditional` because **choice B is the
controlling decision** as of 2026-07-21. Two contradictory decisions were
recorded on 2026-07-20: `main` recorded choice B, and
`work/2026-07-20-photo-proof-readiness-001` recorded a same-day reversal to
choice A. Pete delegated the resolution; the manager resolved it as **B controls
now, A runs at enablement**.

This gate exists so that resolution cannot be quietly lost. Enablement requires
**one** of:

- **(a)** executing the prepared choice-A plan in
  `PS-CAPTURE-PHOTO-LIFECYCLE-001/04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md`
  inside an attended window, having first obtained the six-party written
  acknowledgement it requires — including a security contact who "must be a real
  second person", an on-call rotation holder, and a SIEM/MDR provider or written
  confirmation that none is connected; or
- **(b)** a fresh, explicit, written owner decision that enablement may proceed
  with the production malicious path left `Conditional`, recorded here with its
  reasoning.

**Neither has happened. No production Defender test is authorized.** A future
session must not read the merged choice-A operational plan as authorization: the
plan is deliberately merged in a prepared-and-deferred state so it is ready when
this gate is worked, rather than drifting on an unmerged branch.

Reasoning for the deferral is recorded in
`docs/governance/OPEN_BRANCH_REGISTER.md`. In short: the coordinating parties do
not currently exist for PeerSlate, and a production proof evidences
configuration at the moment it runs rather than at enablement, so running it far
ahead of enablement would very likely need repeating.

## Manager acceptance record

Pete accepted this architecture on 2026-07-19: Photo first, the isolated Azure
Storage plus Defender for Storage cost envelope, and backend before runtime
experience implementation. The separate Photo V1 visual-state gate may proceed
in parallel with backend work, but runtime frontend implementation still waits
for both the backend merge/proof and visual acceptance. This acceptance does not
authorize a direct `main` write, production member-data access, hidden release,
or a visual claim.

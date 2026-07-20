# PS-GOV-CONNECTED-SYSTEM-001 — Connected-System and Return-Value Authority

## Assignment and control boundary

- Package: `PS-GOV-CONNECTED-SYSTEM-001`
- Work type: documentation and governance only
- Status: **staged — owner-supplied handoff preserved; writer unassigned**
- Owner decision date: 2026-07-20
- Source handoff: `source/PeerSlate_Connected_System_and_Hooks_Bible_Update_Handoff_v1.md`
  (handoff version 1.0, prepared 2026-07-20), with the rendered PDF and the
  architecture diagram preserved beside it
- Designated session manager: unassigned — Pete to name a manager before the
  writer opens a branch
- Writer: unassigned. The source handoff names Codex; Pete may reassign to a
  Claude session. Whoever is assigned is the sole writer.
- Required branch: `docs/connected-system-return-value-authority`, created from
  the exact then-current Azure `origin/main`
- Runtime impact: **none permitted**

This package exists so the owner-supplied connected-system strategy is visible
in the repository to every agent and session. Staging it here is not approval of
its contents and does not make Bible v2.7 controlling.

## Governing product decision

> Every page should feel like a different use of the same life.

PeerSlate does not need more destinations. It needs a stronger visible trunk:
original sources become member-confirmed canonical records; canonical records
connect by reference to focused rooms; focused rooms show truthful origin,
relationship, and one best next move; useful outcomes return to the member
through memory, preparation, and gentle momentum.

The high-level loop, preserved as `source/peerslate_connected_system_architecture.png`:

`Original Source → Member Review + Canonical Slate → Authorized Relationship /
Placement → Focused Rooms / Projections → Activation → Outcome + Learning →
Return Value → New Contribution`

## Required deliverables

Section 13 of the source handoff is the authoritative deliverable list. In
summary the assigned writer produces a candidate Bible v2.7, a candidate
Roadmap revision, an updated Architecture and Data Standard carrying the
connected-room logical contract, an updated Experience System carrying the six
connective patterns, this initiative package, a Decision Register entry, a
traceability matrix, a supersession record, and a change report.

## Hard exclusions

Taken from Section 3 of the source handoff. The writer shall not:

- change any feature flag, route, schema, deployment, or production setting;
- enable Owner Home, Photo Capture, Projects, or any other gated capability;
- describe planned, browser-local, flag-off, or unassigned capability as live;
- create another top-level destination for hooks, insights, engagement, or AI;
- create a second source of truth for résumé claims, Story copy, Studio
  examples, Project content, or return-loop history;
- assume a new table, provider, API, notification system, or AI model;
- use engagement language implying addiction, guilt, loss, or public
  performance;
- convert the Bible into an implementation specification; or
- update `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, or any controlling pointer
  to claim v2.7 is current. Activation is a separate explicit step after Pete
  approves the candidate.

## Entry gate

Before a writer begins:

1. Pete names the designated session manager and the sole writer.
2. The writer fetches `origin` and confirms the exact current `main`.
3. The writer confirms no shared-governance-file reservation is held by an
   active lane. As of staging, `PS-CAPTURE-MEDIA-001`,
   `PS-HOME-INTERVIEW-PARITY-001`, and `PS-HOME-FRONTEND-001` are active under a
   ChatGPT Work/Codex manager, so governance-pointer edits must be serialized
   against them.
4. The open decisions in Section 8.2 of the source handoff are acknowledged as
   open. They are not for the writer to silently close.

## Relationship to the unresolved v1.5.1 question

A separate owner document, `PeerSlate_Company_and_Product_Bible_v1.5.1.pages`,
sits untracked in the repository root. It is dated July 17, 2026, presents
itself as an implementation baseline superseding v1.3 and v1.4, and appears in
no supersession list in `DOCUMENT_CONTROL.md`, which stops at v1.4. It also
carries at least two positions that collide with current authority: "the Journal
is the member profile" while Journal UI is held, and Iris Foundry color
direction, which Deep Navy Gold retired.

That authority question is unresolved and is **not** in this package's scope.
It should be settled before a candidate v2.7 is approved, so the new Bible
supersedes a known set rather than an ambiguous one. Tracked separately on the
next-task board.

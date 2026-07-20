# Architecture and Data Standard — connected-system section (PROPOSED)

> **STATUS: PROPOSED.** This is a candidate section for PeerSlate's Architecture
> and Data Standard, the Layer-2 controlled artifact named in Bible Section
> "The PeerSlate product operating system." The repository does not yet carry a
> standalone Architecture and Data Standard document; this file is its
> connected-system section, held package-local until the standard is
> established or until Pete approves the candidate and an activation change
> places it.
>
> **This is a logical contract, not a committed schema.** No table, column,
> stored procedure, migration, route, API, provider, index, queue, or
> notification channel is created, approved, or implied by this document.

## 1. Scope and authority

This section allocates the connected-system requirements proposed in candidate
Bible v2.7:

`PS-CORE-IA-013`, `PS-CORE-IA-014`, `PS-CORE-IA-015`, `PS-CORE-IA-016`,
`PS-CORE-FR-009`, `PS-CORE-FR-010`, `PS-CORE-DATA-007`, `PS-CORE-AI-007`,
`PS-CORE-NFR-008`, `PS-CORE-NFR-009`, `PS-CORE-VAL-005`, `PS-CORE-GOV-008`.

It creates no exception to the seven non-negotiable architecture rules in Bible
Section 12. It is an application of rules 1 (canonical Slate is truth), 2
(authorization before retrieval), and 3 (deterministic controls own trust).

## 2. High-level architecture

The connected experience is one compounding loop, not separate feature trees.

```
Original Source
  → Member Review
    → Canonical Slate
      → Authorized Relationship / Placement
        → Focused Room / Projection
          → Activation
            → Outcome + Learning
              → Return Value
                → New Contribution  ─┐
  ┌──────────────────────────────────┘
  └→ (back to Original Source)
```

| # | Layer | Contents |
|---|---|---|
| 1 | Original source | Voice, text, photo, file, imported context. |
| 2 | Review and canonical | Original preserved; proposal reviewed; member-confirmed Moment and related canonical objects. |
| 3 | Authorized relationship and placement | Exact-version references, provenance, lifecycle, audience, purpose, sensitivity, eligibility. |
| 4 | Focused rooms and projections | Journal, Story, Work, Projects, Resume, Studio, Slate, Feed, public or permissioned views. |
| 5 | Activation | Use This Moment, practice, manager/update draft, share, export, Project connection, Story selection, next step. |
| 6 | Outcome and learning | Completion, usefulness, correction, dismissal, staleness, contradiction, revocation, deletion. |
| 7 | Return value | Finite Home, recent and resurfaced Moment, Then and Now, Replay, source-linked prompt, Focus Theme, future revisit. |
| 8 | New contribution | The member captures the next Moment because prior contribution became useful. |

**Cross-cutting controls:** trusted server identity; authorization before
retrieval; private-by-default storage; exact audience preview;
canonical / interpretation / projection separation; AI proposal and evaluation
lifecycle; accessibility and failure parity; privacy-safe telemetry; feature
flags, rollout, rollback, and deletion propagation.

**Source diagram:** `source/peerslate_connected_system_architecture.png`,
preserved with the owner handoff on the staging branch described in
`00_WRITER_ASSIGNMENT_AND_BASE.md`.

### 2.1 Where the loop is real today

Stating this precisely matters, because the diagram above describes the intended
model, not current capability.

| Layer | Recorded state at base `531013dd8c1a05e2443becd881a226755f27ca14` |
|---|---|
| 1 Original source | Private text and voice Capture are released and live. Photo is released **flag-off**. Video and document intake do not exist. |
| 2 Review and canonical | `PS-MOMENT-001` released; member-confirmed Moment boundary is live. |
| 3 Relationship and placement | `PS-PLACEMENT-001` backend released. **No website control creates or displays a placement.** |
| 4 Focused rooms | Public Resume and Interview Studio are live. Journal UI is on hold. Projects are planned. Owner Home is default-off. |
| 5 Activation | Use This Moment is not implemented. |
| 6 Outcome and learning | Not implemented. |
| 7 Return value | Not implemented. |
| 8 New contribution | Not implemented. |

No connective pattern in this document is implemented, assigned, deployed,
enabled, or live.

## 3. Connected-room logical contract

A room requests context from a server-side resolver. The resolver returns one
`ResolvedRoomContext` or nothing.

```text
ResolvedRoomContext
- room_id
- room_role
- viewer_mode
- audience_state
- truth_state
- primary_object_reference
- permitted_source_summary
- authorized_relationships[0..2]
- primary_continuation_action
- secondary_actions[0..2]
- optional_temporal_context
- status_or_limitation_copy
- explanation_or_reason
```

### 3.1 Field intent

| Field | Intent |
|---|---|
| `room_id` | Stable identifier for the room instance being rendered. |
| `room_role` | One concise statement of what this room helps the member do. |
| `viewer_mode` | Owner, selected person, connection, authenticated member, or public. Server-derived only. |
| `audience_state` | The audience the current view actually represents, matching the server-enforced result. |
| `truth_state` | Live, browser-local, illustrative, flag-off, processing, failed, stale, or unavailable. |
| `primary_object_reference` | Reference to the dominant canonical object or projection — a reference, never a copy of its facts. |
| `permitted_source_summary` | Provenance the current viewer is authorized to see, at the permitted depth. |
| `authorized_relationships[0..2]` | Zero, one, or two governed relationships. Never more. |
| `primary_continuation_action` | The single best safe next move. |
| `secondary_actions[0..2]` | At most two. |
| `optional_temporal_context` | Source-linked temporal cue, or absent. Never a diagnosis. |
| `status_or_limitation_copy` | Honest statement of what is unavailable, local-only, or future. |
| `explanation_or_reason` | Why this context appeared now, when material. |

### 3.2 Rules

1. The context resolver receives trusted session identity and route purpose. It
   never receives an ownership claim from the browser.
2. Authorization occurs **before** data, search, media, cache, or AI retrieval.
   Filtering an already-retrieved private result is not authorization.
3. A room may render **no** connective module when no truthful relationship
   exists. An empty spine is correct; an invented one is a defect.
4. Public mode may use only approved public-safe context.
5. Owner mode may use private context only for the current owner.
6. Relationship type, audience, source version, lifecycle, and staleness must be
   explicit in the resolved payload.
7. The UI cannot infer or broaden relationships from labels or client data. A
   shared component renders what it is handed.
8. Each primary action declares what it uses, what it changes or creates,
   whether AI is involved, where it is stored, and who can see it.
9. The connective budget is one primary and at most two secondary actions per
   state.
10. A resolver failure degrades to the room without connective context. It never
    degrades to a fabricated relationship or a broken room.

### 3.3 Required behavior states

Any implementation must resolve and render all of these:

public approved relationship; owner private relationship; no relationship
available; source deleted or unavailable; source revoked; source stale relative
to the referenced version; action unavailable or `Coming later`; browser-local
limitation; restricted audience; AI unavailable; provider outage; empty; long
content; processing; failed; retry; recovered.

## 4. Candidate relationship vocabulary

Preserved as **logical vocabulary for Architecture and Data Standard review**.
Do not commit these to schema. The standard must later classify each as
canonical, placement, projection, interpretation, or operational.

- supports Resume claim
- appears in Story chapter
- belongs to Project
- demonstrates skill in practice
- useful for interview or Moment Lab prompt
- derives from or links to source
- changed from earlier Moment
- influenced outcome
- continues unfinished thread
- appropriate for audience or purpose
- selected as Progress Keepsake

## 5. No new system of record

The "proof graph" is not a separate product, destination, or database truth. It
is the governed relationship and placement capability that emerges from the
canonical Slate.

- It must be recorded as an explicit **acceptance outcome** of
  `PS-PLACEMENT-001` and later connected-view packages.
- It must not become a new aggregate, a second truth store, or a room-specific
  copy of authoritative facts.
- Relationships never grant access by themselves. Access remains a separate
  server-enforced audience grant.
- Correction, deletion, revocation, and audience changes must propagate to
  derived connective context.

## 6. Privacy-safe event and measurement taxonomy

**Do not log content.** Candidate event names:

`connected_room_context_rendered`, `connected_room_primary_action_selected`,
`connected_room_secondary_action_selected`, `resume_backstory_opened`,
`resume_practice_bridge_started`, `studio_return_ticket_rendered`,
`studio_return_ticket_selected`, `resurfaced_moment_opened`,
`resurfaced_moment_dismissed`, `then_and_now_inspected`, `focus_theme_selected`,
`keepsake_reference_added`, `voice_capture_review_started`,
`voice_capture_confirmed`, `return_after_absence_completed`.

**Allowed dimensions** must be coarse and non-content-bearing: route family,
audience mode, component version, action type, feature flag, success or failure,
latency bucket, and source-state category.

**Never log:** names, titles, transcript text, answer text, private identifiers,
source snippets, relationship content, or AI prompts.

## 7. Explicit non-assumptions

This document does **not** assume or request:

- a new database table, view, stored procedure, index, or migration;
- a new API surface, route, or route family;
- a new provider, model, embedding store, or semantic retrieval layer;
- a notification system, channel, scheduler, or background job;
- a change to any feature flag, deployment, or production setting;
- enablement of Owner Home, Photo Capture, Projects, or any gated capability.

Logical needs are documented first. Implementation allocation happens only after
repository inspection and explicit package approval, per Section 3 of the source
handoff.

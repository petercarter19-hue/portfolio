# PS-GOV-JOURNAL-SYSTEM-001 — Journal System Authority Reconciliation

**Status:** Owner-authorized authority candidate; Azure activation pending

**Owner decision date:** July 20, 2026

**Designated session manager and sole writer:** ChatGPT Work/Codex

**Task branch:** `work/2026-07-20-journal-system-authority`

**Authoritative base:** Azure DevOps `origin/main` at
`efd34335284d6c823d47cd7bac3cd2f901533612`

**Runtime effect:** Governance, requirements, and sequencing only. No route,
schema, feature flag, deployment setting, or member-visible behavior is created
by this package.

## Purpose

This package converts Peter's July 20 decisions into one durable PeerSlate
system contract. It resolves contradictions among Bible v2.7, Roadmap v2.6,
the restarted Journal package, the connected-system package, the current Story
standard, Ask Pete AI discovery, and the supplied research documents.

The controlling product sentence is:

> Capture anywhere → Save one private Moment → find it in the one Journal →
> use the same Moment anywhere now or later by governed reference.

That sentence does not create a new user-facing Capture page, a second Journal
content record, an automatic public post, or an AI-controlled fact.

## Activated decisions

1. Capture is a persistent action and context-preserving composer available
   from eligible signed-in rooms. It is not a destination, page, or permanent
   navigation tab.
2. The user-facing commit is **Save Moment**. Technical source preservation,
   media processing, revision, and proposal states may remain underneath the
   experience, but they may not become a separate navigation journey or an
   unnecessary “add to Journal” gate.
3. Every saved owner Moment belongs to the owner's one Journal by definition.
   Journal membership is derived; it is not a Placement and does not copy the
   Moment into a `journal_entry` truth record.
4. The owner Journal is complete. Selected-person, Connection, member, and
   public views are server-authorized, owner-curated projections over the same
   canonical Moments. They never retrieve the private Journal and filter it in
   the browser.
5. My Story remains distinct. Journal is the complete, chronological,
   searchable working record; My Story is a finite, authored, visually composed
   explanation built from selected references. They share truth without
   becoming redundant.
6. Feed, résumé, Work, Story, Projects, Board, Studio, public Journal, and
   messaging are downstream consumers. They may not create independent
   canonical facts or bypass the Journal-first Moment path.
7. Replay and resurfacing, Momentum, the Prompt and Ritual Service, What
   PeerSlate Noticed, and Slate Mirror are committed return-value architecture.
   They are staged, private-first, source-linked, non-diagnostic, and
   non-punitive.
8. Purposeful private acknowledgements and badges may recognize meaningful
   continuity or completion. Daily-reset streaks, loss framing, shame,
   leaderboards, public comparison, invented achievement, and trophy spam are
   prohibited.
9. Ask Slate AI is the signed-in intelligence umbrella. Ask My Slate is an
   owner action; Ask [Name] AI is an audience-authorized public pattern; Ask
   Pete AI remains the existing public Pete instance. Specialist workflows are
   modes, not competing bots.
10. Messaging is a committed future capability, although not required for the
    first Journal release. It requires consent, relationship, safety,
    moderation, retention, deletion, notification, and authorization contracts
    before implementation.
11. Exact navigation remains open. Journal's centrality and Capture's status as
    an action are locked; the route/tab map is not.
12. Original retained-audio playback may be supported when permitted.
    Synthetic or cloned own-voice playback is not committed. Life
    Constellation/worldbuilding remains a later revisit item.
13. Early legal and product-site readiness starts now. Formal counsel and
    security gates occur before public Journal, messaging, multimodal private
    AI, and broad launch.

## Durable sources of detail

This reconciliation deliberately avoids repeating the complete specification
in every file:

| Domain | Controlling detailed record |
|---|---|
| Universal Capture, one Journal, lifecycle, authorization | `docs/initiatives/PS-JOURNAL-001/` |
| Replay, resurfacing, Momentum, prompts, rituals, Noticed, Mirror | `docs/initiatives/PS-RETURN-VALUE-001/` |
| Signed-in intelligence and assistant naming | `docs/initiatives/PS-ASK-SLATE-AI-001/` |
| Future member messaging | `docs/initiatives/PS-MESSAGING-001/` |
| Journal versus My Story | `docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md` and PS-JOURNAL-001 file 04 |
| Legal and site readiness | `docs/governance/EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md` |
| Claude/Codex model and role routing | `docs/AI_MODEL_AND_ROLE_ROUTING.md` |
| Active Home, Photo, and Projects transition | `04_ACTIVE_LANE_COMPATIBILITY_AND_TRANSITION.md` |
| Binary/release trace and cross-computer proof | `05_AUTHORITY_ACTIVATION_AND_TRACEABILITY.md` |
| DOCX template and final-render evidence | `evidence/` |
| Technical and release handoff | `COMPLETION_REPORT.md` |
| Constitutional product language | Bible v2.8 |
| Phase/package sequencing | Roadmap v2.7 |

## Source material reviewed

The supplied research is an option library, not direct user validation. Its
ideas were accepted, combined, staged, revisited, tabled, or rejected through
the owner decisions above.

| Source | SHA-256 | Disposition |
|---|---|---|
| [`1-PeerSlate-Hooks-and-Connected-Site-Research-Report-2.docx`](source/1-PeerSlate-Hooks-and-Connected-Site-Research-Report-2.docx) | `1cf16a02a33a6b73be13ad60361a4ddf3ffef5d33c3f7cc7af2b4ee54f4aa63f` | Connective patterns and return-value inputs |
| [`2-PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx`](source/2-PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx) | `e9c8b8102c6416ac9739da427726cf09907142f34082ea1930d621446ec003e6` | Historical architecture comparison |
| [`3-Deep-Research-Report-on-Hooks-for-a-Voice-First-Journaling-and-Growth-Website-2.docx`](source/3-Deep-Research-Report-on-Hooks-for-a-Voice-First-Journaling-and-Growth-Website-2.docx) | `9c485b71906fb643d1f418478d21ca4c3e19a41b74c1fef770a57437c76cfce6` | Hook inventory and revisit inputs |

The exact binaries are preserved under `source/`. Repository-local summaries,
decisions, requirements, and the revisit register carry the actionable content
so later agents do not need the original chat.

## Files reserved by this governance lane

- Bible v2.8 and Roadmap v2.7 plus their build sources and verification evidence.
- `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, `ACTIVE_INITIATIVES.md`,
  `DECISIONS.md`, `DOCUMENT_CONTROL.md`, and `MANAGER_SESSION_HANDOFF.md`.
- `AGENTS.md`, `CLAUDE.md`, `docs/PEERSLATE_SITE_RULES.md`, and the shared AI
  role-routing record.
- The PS-JOURNAL-001, PS-RETURN-VALUE-001, PS-ASK-SLATE-AI-001,
  PS-MESSAGING-001, and PS-ASK-PETE-AI-001 governance files changed here.

No product source file is reserved or modified.

## Acceptance and release boundary

This package passes only if all of the following are true:

- the current authority no longer locks Capture as a destination;
- no active requirement asks a member to add a saved Moment to Journal;
- Journal has no second fact-bearing body;
- owner-complete and audience-filtered Journal views are both defined;
- My Story remains distinct and non-duplicative;
- the elevated return-value services and signature observations are allocated;
- all remaining research ideas have a durable disposition;
- Ask Slate, Ask Pete, specialist AI, and messaging boundaries are explicit;
- exact legal and release gates are recorded;
- Codex/Claude routing has one manager, one writer, and risk-based review;
- versioned DOCX files render and pass structural/accessibility checks;
- active Home/Photo/Projects lanes cannot re-lock superseded target behavior;
- repository tests and complete-diff review pass; and
- the branch is merged through Azure with remote-main and pipeline evidence.

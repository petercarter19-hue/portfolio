# Owner decision record — Workshop direction and five product answers

**Date:** 2026-08-01
**Initiative:** PS-SLATE-STUDIO-IA-001
**Recorded by:** Claude Code (Fable architecture lane) from Pete's direct
session instruction
**Status:** owner direction recorded; **documentation only**. This record
authorizes no runtime code, route, schema, migration, feature flag,
deployment, visual lock, or live capability.

This is an additive correction record. It preserves documents 12–15 as history
and resolves the questions Pete answered on 2026-08-01. Where it conflicts with
an earlier Workshop assumption, this record controls.

## 1. Provenance of this direction

The controlling input is the owner-supplied ChatGPT handoff package
`PeerSlate Workshop Claude Handoff 2026-07-31.zip`, package-copied and
hash-pinned at
`visual-authority/workshop-candidate-2026-07-31/`. It was verified against Azure
`origin/main` at `2494aa73ed95bfbe97d8cf42f712b9929759e0b2`, which remained the
authoritative tip when this record was written.

That package deliberately resets parts of the earlier Workshop/Slate Studio
discussion: Journal is not a near-term dependency, whiteboard and Goal Board are
back-burnered, Workshop becomes one private two-mode surface, and outward use is
limited to existing site surfaces. Claude's independent audit of the package is
retained at `CLAUDE_AUDIT_2026-08-01.md`.

## 2. Product model (as reset)

Workshop is one authenticated, private, AI-assisted surface where a member adds,
strengthens, reviews, and controls information about themselves in small units
of work. Two modes share the surface:

- **Work on Something** — the active AI-assisted contribution mode.
- **My Information** — the member-controlled private library.

Four data classes remain permanently distinct: member source; AI interpretation
or suggestion; confirmed private information; and purpose-specific downstream
use. The governing sequence is
`Contribute → review → confirm privately → optionally update an existing site
surface`. It is never `AI infers → silently saves → silently publishes`.

## 3. Owner answers of 2026-08-01

### D1 — Canonical wording after an accepted AI refinement

**Decision.** Option (b). The **member-approved wording is canonical.** The
member's original words are retained as inspectable history, but the approved
text is the item's truth.

**Decision.** PeerSlate does **not** label accepted refinements as
AI-changed in the member-facing product. Pete's rationale: AI proofreading is
ordinary and long-standing practice — equivalent to a word processor's markup —
and surfacing it as a provenance event is noise, not honesty.

**Architectural consequence.** This decision is only truthful if the member
actually sees and approves the exact final wording before it is saved. It is
therefore **coupled to D6 below**: the missing explicit save-consent state is
what makes "your words" an honest label. The two decisions must ship together.
Retention of the original text in history is required and is not optional; it is
simply not surfaced as an AI-attribution badge.

### D2 — AI-use permission default

**Decision.** Keep the candidate set's default: a saved item is
`Available for private PeerSlate suggestions`. The setting stays visible at the
save moment and remains changeable per item at any time from My Information.
The permission is bounded to **private** suggestions and grants no publication,
sharing, or external use.

### D3 — Member-source formatting

**Decision.** Keep formatting as drawn in the candidate set for now. The
rich-text affordances remain; their downstream rendering rules are an
implementation detail to be defined by the architecture, not a product change.

Pete's framing: Workshop is not a résumé builder and not a document product, so
formatting carries no document-production burden.

### D4 — Naming, navigation, and route

**Decision.** Workshop **coexists with Interview Studio**. Place it in the
primary navigation next to Interview Studio for now.

**Decision.** A later rename to **My Slate** is anticipated but **not** made
now. The architecture must not hardcode the surface name in data, routes, or
contracts in a way that makes a later rename expensive.

**Decision.** Page/service consolidation — deciding which pages and services
belong together — is explicitly deferred until the surfaces exist and can be
seen together. Do not pre-optimize for it.

### D5 — Primary purpose

**Decision, and the controlling emphasis for the whole package.** The primary
purpose of Workshop is to **build up the member's knowledge areas** — the
information PeerSlate holds about the member — in ways that are enjoyable to
use and directly beneficial to the member. Pete: "that's the fun part."

The knowledge base is the product. Downstream use is secondary and optional.

### D6 — Destinations: PeerSlate does not create résumés

**Decision.** `Create a résumé bullet` / `Create résumé draft` as drawn on
candidate screen 04 is **corrected**. PeerSlate is **not** creating résumés and
is **not** competing with word processors or résumé-builder sites.

**What downstream use actually means:** confirmed information may **update what
already exists on the PeerSlate site** — the member's résumé page content, My
Story, or the Feed — when the member explicitly chooses it. It does not
generate, assemble, format, or export a résumé document.

**Reconciliation.** This is consistent with the already Pete-approved inventory
in `13_WORKSHOP_PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md`, which records
`Resume bullet` as a "resume-page content update … not a template builder" and
removes "Resume templates, template picker, template gallery" outright. The
candidate mockup drifted toward document production; this decision returns it to
the approved inventory. It is a **correction of the candidate visual, not a new
product direction.**

**Noted, out of scope:** a member uploading their own existing résumé PDF was
raised as a possible future capability. It is recorded here so it is not lost.
It is **not** in scope, not designed, and not authorized.

## 4. Resulting status of the candidate visual set

The set remains `CANDIDATE — NOT OWNER-LOCKED`. Two changes now block a lock in
addition to the audit's existing findings:

1. **A new screen is required.** The explicit final-review and `Save privately`
   consent state does not exist in the set. D1 depends on it.
2. **Screen 04's destination card is superseded by D6** and must be re-created:
   the offer becomes an update to an existing site surface, and it is demoted
   from primary visual weight so it no longer competes with the completed
   private save.

Both are **material visual changes**. Under the owner's 2026-07-24 decision they
return to the **ChatGPT visual-creation lane**, and Pete locks the corrected
exact files and hashes. Claude does not originate them.

## 5. Delivery lane for the implementation that follows

Pete confirmed the Claude ecosystem lane on 2026-08-01, matching the lane already
recorded in this package's README:

| Role | Model | Scope |
|---|---|---|
| Architect | **Claude Fable 5** | This package's product/technical architecture |
| Implementer | **Claude Sonnet 5** | Bounded implementation, tests, evidence, closeout |
| Independent reviewer | **Claude Opus 5** | Exact-SHA risk-triggered review |

`docs/AI_MODEL_AND_ROLE_ROUTING.md` currently names **Claude Opus 4.8** as the
Claude independent reviewer. That row requires a documentation-only update to
**Claude Opus 5** to match this owner decision. The routing document remains the
central version authority; this record does not edit it.

Independent review is **mandatory** for this package rather than discretionary:
it meets the `docs/AI_WORKFLOW.md` risk triggers for architecture-heavy work,
privacy and cross-user data, schema and migration work, and consequential AI.

## 6. What this record does not do

It locks no visual, authorizes no runtime implementation, opens no route,
creates no schema or migration, enables no flag, claims no deployment, and makes
no statement that any Workshop behavior exists today. Workshop is not
implemented, not deployed, and not live.

# Candidate PeerSlate Product Strategy and Architecture Roadmap v2.6 — source text

> **STATUS: PROPOSED.** Roadmap **v2.5** remains the current controlling sequence
> named in `docs/governance/CURRENT_BASELINE.yaml`. This document is the
> authoritative source text for every change v2.6 would make. It changes **no**
> live status, package status, phase status, release record, or production
> claim.

**Candidate title:** PeerSlate Product Strategy and Architecture Roadmap v2.6 —
Connected-System Sequencing
**Candidate date:** July 20, 2026
**Basis:** v2.5 + the owner-supplied Connected-System and Hooks handoff v1.0
(Section 7)
**Rendered candidate:** `candidate/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6_PROPOSED.docx`

## How to read this file

v2.5 supplies every word that is not listed here. Phases 0–12, phase 15A, the
release gates, the Azure crosswalk, the immediate execution plan, and Appendices
A–F are unchanged. The candidate adds sequencing for the connected-system
direction and nothing else.

**Explicit non-change:** every existing phase status, package status, pipeline
number, merge SHA, release record, and evidence claim in v2.5 is preserved
exactly. This candidate advances nothing to Complete and starts nothing.

---

## 1. Front matter

### 1.1 Version table (replaces the v2.5 values)

| Field | Candidate value |
|---|---|
| VERSION | v2.6 — Connected-System Sequencing (PROPOSED) |
| DATE | July 20, 2026 |
| STATUS | PROPOSED — CANDIDATE AWAITING OWNER APPROVAL; v2.5 REMAINS CURRENT |
| SOURCE SYNTHESIS | v2.5 sequencing + July 20 owner connected-system and return-value decision |

### 1.2 Roadmap authority callout (replaces the v2.5 LOCKED authority callout)

> **PROPOSED** — Roadmap authority: v2.6 is a candidate. v2.5 remains the current
> sequence and architecture until Pete approves this candidate and
> `CURRENT_BASELINE.yaml` names it. Historical package IDs and release evidence
> remain preserved. `PS-STORY-COMPOSER-001`, `PS-PROJECTS-001`,
> `PS-ASK-PETE-AI-001`, and every connective package named in Appendix G are
> planned or candidate work, not active.

---

## 2. Section 18 — Work-package register additions

Three candidate package IDs are appended to the register as **candidate,
unassigned** rows. No existing row changes. None of these has a manager, writer,
branch, entry gate, schema, mockup, or start date.

| Package ID | Phase | Name | Primary output | Status |
|---|---|---|---|---|
| `PS-PUBLIC-CONNECTIVE-001` | 1 / 10 / cross-phase | Public connectedness pilot | Shared connected-room orientation on selected public Resume, Story, and Studio states; three to five Resume Backstory Drawers; public-safe practice bridges; a Studio Return Ticket truthful to browser-local behavior | **CANDIDATE — not authorized, unassigned** |
| `PS-CONNECTIVE-COMPONENT-001` | 10 / cross-phase | Shared connective component foundation | One reusable server-rendered component contract that accepts a resolved authorized view model | **CANDIDATE — blocked behind the public pilot** |
| `PS-RETURN-VALUE-001` | 9 / 10 | Private return-value engine | One Capture action, one small prompt, one recent and one resurfaced Moment, one source-linked observation when warranted, one next step, and welcome-back behavior with no loss framing | **CANDIDATE — blocked behind Owner Home frontend and real confirmed history** |

**Register note to append:** Appendix G carries the priority bands and entry
conditions for these candidates. Presence in the register is not authorization.

---

## 3. Section 20 — "What not to do next" additions

Appended to the existing list. Existing entries are unchanged.

- Do not build a generic "related content," "explore more," or "you may also
  like" rail in place of a meaningful, authorized relationship.
- Do not build a streak meter, points, badges, or a loss-framed return mechanic.
- Do not start a connective pattern before the public pilot's entry gate,
  production-intent mockups, and an assigned manager and writer exist.
- Do not implement Then and Now before confirmed history, source authorization,
  contradiction handling, and correction behavior are mature.

---

## 4. New Appendix G — Connected-system and return-value direction amendment

Appendix lettering continues from v2.5, which ends at Appendix F. No existing
appendix is re-lettered.

**Opening statement:**

> The connected-system direction is a sequencing amendment, not a new phase and
> not a new product tree. Every item below is documentation-stage work or a
> candidate package. Nothing here is authorized, assigned, scheduled, started,
> deployed, enabled, or live.

### 4.1 Priority 0 — Do now: documentation and authority synchronization

This is the only band with active work, and that work is this package.

| # | Action | State |
|---|---|---|
| 1 | Create candidate Bible v2.7 with the connected-system constitutional language | Delivered as PROPOSED by `PS-GOV-CONNECTED-SYSTEM-001` |
| 2 | Update the Roadmap candidate for connected-system priorities without changing live statuses | Delivered as PROPOSED by this document |
| 3 | Add the high-level architecture map to the Bible appendix and the detailed logical contract to the Architecture and Data Standard | Delivered as PROPOSED (Bible Appendix N; package file `03_…`) |
| 4 | Add the six connective patterns to the Experience System | Delivered as PROPOSED (package file `04_…`) |
| 5 | Add a Decision Register entry with rationale, alternatives, risks, and supersession language | Staged for append at activation (package file `05_…`) |
| 6 | Create the research → principle/requirement → phase/package → artifact crosswalk | Delivered (package file `06_…`) |

### 4.2 Priority 1 — First bounded implementation candidates after explicit assignment

**A. Public connectedness pilot — candidate `PS-PUBLIC-CONNECTIVE-001`**

*Scope:*

- A shared Slate Spine or connected-room orientation pattern for selected public
  Resume, Story, and Studio states.
- Three to five Resume Backstory Drawers for anchor achievements only.
- "Practice telling this" bridges from selected Resume claims to the exact live
  Studio route and its current public behavior.
- A public-safe "Behind this answer" relationship in Studio where support
  already exists.
- A post-review Studio Return Ticket appropriate to public / browser-local
  truth.

*Out of scope:* account-backed Studio history; private Journal or owner history;
new persistence; new database schema unless separately approved; broad public
redesign; generic related-content rails; more than one primary and two secondary
actions per state.

*Entry gate:* the repository confirms current Resume and Studio routes and
active initiative boundaries; production-intent mockups are accepted; every
relationship is public-safe and either curated or sourced from an approved
projection; no current package is silently reopened or modified without owner
assignment.

*Dependency note:* `/interview-studio` is released and live as of PR 101 /
pipeline 149. `/petec/resume` is released and live as of PR 62 / pipeline 83.
The pilot must consume those exact live behaviors and must not change them.

**B. Homepage Interview convergence**

`PS-HOME-INTERVIEW-PARITY-001` remains a separate bounded package under its own
manager and writer, exactly as recorded in `ACTIVE_INITIATIVES.md`. This
amendment does not expand, absorb, reassign, accelerate, or alter it. It must
continue to map the accepted homepage walkthrough to the exact live Studio
without changing Studio behavior or implying private history.

**C. Shared connective component foundation — candidate
`PS-CONNECTIVE-COMPONENT-001`**

Create one reusable server-rendered, Jinja-compatible component contract **only
after** the public pilot is approved. It must accept resolved authorized view
models rather than query arbitrary data in the template or the browser.

### 4.3 Priority 2 — Build next: canonical relationship foundation

The connected / proof graph is an **acceptance outcome** of packages that
already exist. It is not a new package, aggregate, or destination.

| Package | Contribution | Current recorded state |
|---|---|---|
| `PS-CAPTURE-002` | Lifecycle and original preservation | Complete; PR 63 / pipeline 85 |
| `PS-MOMENT-001` | Member-confirmed canonical Moment | Complete; PR 66 / pipeline 91 |
| `PS-PLACEMENT-001` | Exact-version create-once / place-many references | Backend foundation live; PR 68 / pipeline 93; no UI consumer |
| `PS-ACTION-CORE-001`, `PS-ACTION-STUDIO-001` | Truthful continuation actions | Candidate IDs; not defined, assigned, or authorized |

*Required outcomes before the graph can be claimed:*

- Correction, deletion, revocation, and audience changes propagate.
- Relationships never grant access by themselves.
- Relationship labels derive from governed types, not copied prose.
- Connected rooms request authorized context through shared services.
- Public and owner payloads use the same grammar with different permitted
  context.

### 4.4 Priority 3 — Build after Owner Home frontend and real confirmed history

**Private return-value engine — candidate `PS-RETURN-VALUE-001`** (or an
explicitly scoped extension of the Owner Home / Replay packages).

*First slice:* one obvious Capture action; one small prompt or check-in; one
recent and one resurfaced Moment; one concise source-linked observation when
warranted; one next step; welcome-back behavior after absence with no loss
framing.

> Do not start with a streak meter. Validate that memory, usefulness, and one
> clear next action create return value first.

*Then and Now:* implement as a Replay or Home/Story/Studio pattern only after
confirmed history, source authorization, contradiction handling, and correction
behavior are mature.

*Replay:* `PS-MIA-REPLAY-001` remains the preferred finite weekly / monthly /
period narrative. It must show movement, a few Moments, missing context, and one
next action rather than a dashboard of scores.

*Blocking dependency:* `PS-HOME-FRONTEND-001` is activated with a writer branch
pending and Owner Home remains default-off. Nothing in this band may begin while
that is true.

### 4.5 Priority 4 — Later experiments after the return loop is proven

Focus Themes as a private cross-room overlay; Progress Keepsakes as references
rather than copied records or a new destination; voice delight rituals after
transcript, review, privacy, retention, and failure behavior are proven; Future
Voice Mail, Duet With Your Past Self, Voice Keepsakes, and private growth reels;
Prompt DNA and Signal Cards after enough history and model-governance evidence
exists; optional challenge-free journeys with no failure state.

### 4.6 Priority 5 — On the fence: preserve for later evaluation

Companion or worldbuilding layer; private constellation, archive, path, room,
garden, or trail that evolves; Buddy Reflection or trusted-person
accountability; small private circles or prompt swaps; soft consistency
visualization; future-self messages; soundscape pairing; celebration readback.

> These ideas are preserved, not authorized. Each requires an explicit
> hypothesis, prototype, trust review, and evidence that it strengthens the
> private owner loop without infantilization, distraction, privacy burden, or
> engagement pressure.

### 4.7 Verification and validation expectations for any derived package

Every implementation package derived from this amendment must include: route and
payload tests for owner, selected person, connection, authenticated member, and
public modes; cross-user negative tests and no-client-filtering evidence;
exact-version reference and no-content-copy tests; deleted, revoked, stale,
restricted, and unavailable source behavior; AI unsupported-claim and
provider-outage behavior; browser-local versus server-persistent truth tests;
mobile, keyboard, screen-reader, 200-percent zoom, reduced-motion, long-content,
empty, error, and retry states; privacy-safe telemetry tests proving no private
payload, transcript, answer, source content, or relationship detail leaks into
logs; visual comparison to the named production-intent authority; and rollback
and feature-flag behavior where applicable.

### 4.8 Validation scenarios

1. A public visitor opens a Resume Backstory, understands how it relates to
   Story or Studio, and sees no private material.
2. A public Studio user finishes Review and receives a truthful Return Ticket
   that does not imply account-backed persistence.
3. An owner sees the same component grammar with private authorized context and
   understands who can see the result.
4. Pete and Danielle cannot retrieve each other's private relationships,
   prompts, history, or Returns.
5. A deleted or revoked source disappears from downstream connection modules and
   Keepsakes according to policy.
6. A user can ignore or dismiss a resurfaced item with no pressure.
7. A user returns after an absence and completes one useful action without
   seeing loss language.
8. A user can explain in plain language how the current room relates to the
   larger Slate.
9. A user completes the primary room task at least as quickly as before the
   connective layer.
10. AI or speech failure leaves the essential room, source inspection, and safe
    next action usable.

### 4.9 Current control

The connected-room logical contract is maintained in
`docs/initiatives/PS-GOV-CONNECTED-SYSTEM-001/03_ARCHITECTURE_AND_DATA_STANDARD_CONNECTED_SYSTEM.md`.
The connective patterns are maintained in
`…/04_EXPERIENCE_SYSTEM_CONNECTIVE_PATTERNS.md`. Both are PROPOSED. No
connective package is active, and no live status in this Roadmap changed.

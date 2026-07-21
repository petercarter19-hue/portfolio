# PS-JOURNAL-001 — Universal Capture and the One Journal

**Status:** Architecture complete and controlling; product implementation not
started

**Owner decision:** Peter Carter, July 20, 2026

**Authority-activation manager:** ChatGPT Work/Codex

**Architecture writer:** ChatGPT Work/Codex on
`work/2026-07-20-journal-system-authority`

**Runtime manager and implementation writer:** Both unassigned; the runtime
package requires a fresh manager assignment, one sole writer, and a fresh
branch after the entry gate

**Roadmap position:** Core owner loop before broad return-value intelligence,
public Journal, Story Composer, or messaging

**Runtime status:** The target universal composer, Journal experience, public
Journal, and return-value services are not live.

## Controlling experience

> Capture anywhere → Save one private Moment → find it in the one Journal →
> use the same Moment anywhere now or later by governed reference.

The Journal is everything in the sense that it is the complete member-owned
record and longitudinal home. It is not everything in the sense of replacing
every focused room. Story, Work, résumé, Studio, Board, Projects, Feed, and
messaging remain purpose-specific uses of the same governed Moments.

## Locked architecture

- **Capture is an action, not a place.** Eligible signed-in pages expose the
  same context-preserving composer. There is no target Capture page or
  permanent Capture navigation destination.
- **Save Moment is the single member commit.** Technical source, revision,
  processing, transcription, and proposal states remain underneath or inside
  the composer. They do not force a separate route or a later Add to Journal
  decision.
- **Moment remains canonical.** The exact member-authored content accepted by
  Save Moment is an owner-scoped canonical version. AI enrichment is a separate
  proposal and never delays, replaces, or silently rewrites it.
- **Journal membership is derived.** The owner's Journal includes every saved
  owner Moment by definition. Confirmation creates no Journal Placement and no
  copied Journal body.
- **One Journal, authorized views.** Owner sees the complete record. Other
  viewers receive only an owner-curated, server-authorized projection of the
  same Moments for their actual audience mode.
- **My Story remains distinct.** Journal is complete, chronological,
  searchable, editable, and lifecycle-oriented. My Story is finite, authored,
  visually composed, and purpose/audience-oriented.
- **Reuse follows save.** The origin room may suggest a relevant next use, but
  destination choice is optional. Feed, résumé, Story, Work, Projects, Board,
  Studio, and messaging never bypass canonical Moment creation.
- **Navigation remains open.** Capture-as-action and Journal-as-core are locked;
  exact routes, tabs, and desktop/mobile composition require the route-map gate.

## Detailed records

1. `00_OWNER_RESTART_AND_V151_RECONCILIATION.md` — historical restart plus
   July 20 supersession.
2. `01_REQUIREMENTS_AND_ARCHITECTURE_GATE.md` — normative requirements.
3. `02_EXPERIENCE_AND_INFORMATION_ARCHITECTURE.md` — composer, Journal, viewer,
   and route behavior.
4. `03_DATA_AUTHORIZATION_AND_LIFECYCLE.md` — canonical records, transactions,
   authorization, propagation, migration, and failure handling.
5. `04_JOURNAL_MY_STORY_AND_PROJECTION_BOUNDARY.md` — exact non-redundancy and
   public/permissioned projection model.
6. `05_IMPLEMENTATION_TEST_AND_RELEASE_SEQUENCE.md` — bounded slices, gates,
   evidence, and stop conditions.

## Adjacent packages

- `PS-RETURN-VALUE-001` owns Replay/resurfacing, Momentum, Prompt/Ritual,
  What PeerSlate Noticed, and Slate Mirror.
- `PS-ASK-SLATE-AI-001` owns signed-in intelligence and source-grounded asks.
- `PS-MESSAGING-001` owns future direct member communication.
- `PS-STORY-COMPOSER-001` remains future member-directed composition.
- `PS-ASK-PETE-AI-001` remains the public Pete-specific assistant.

## Product-code entry gate

The first implementation branch may start only after:

- the active Owner Home/frontend writer relinquishes any overlapping shell
  files or the Journal slice selects non-overlapping files;
- exact route ownership and legacy `/app/capture`/`/api/journal/*` disposition
  are approved;
- schema/procedure allocation proves derived membership and no copied body;
- Save Moment transaction, retry, stale-state, and partial-failure contracts are
  approved;
- the owner/selected-person/Connection/member/public authorization matrix is
  approved before any viewer projection;
- a production-intent universal-composer and owner-Journal visual authority is
  accepted under the Visual Integrity Standard;
- desktop/mobile/keyboard/touch/screen-reader/200%-zoom/reduced-motion and
  failure/recovery designs exist;
- migration, rollback, telemetry, export, and deletion propagation plans are
  testable; and
- exactly one implementation writer, branch, base SHA, file reservation, and
  designated manager are recorded.

# PS-JOURNAL-001 — Requirements and Architecture Gate

## Gate status

**Activated, not yet approved for product code.** This file fixes the minimum
allocation the architecture branch must complete. It is not evidence that the
Journal is implemented.

## Reusable deployed foundations

| Foundation | Current evidence | Journal use |
|---|---|---|
| Trusted identity and owner isolation | PS-AUTH-001 / PS-OWNER-001 | Resolve owner from the trusted session; never accept an owner ID from the browser |
| Capture source and lifecycle | PS-CAPTURE-001 / PS-CAPTURE-002 | Preserve original input, revisions, archive, deletion, and export |
| Canonical Moment | PS-MOMENT-001 | Present member-confirmed meaning without copying it into Journal |
| Exact-version Placement | PS-PLACEMENT-001 | Reference a confirmed Moment version in eligible destinations |
| Text and Voice Capture | Released private Capture paths | Feed one review contract; neither auto-creates Journal content |
| Owner Home backend | Released default-off `owner-home.v1` | Provide a bounded shell/entry point; do not expand its contract silently |
| Approved owner visual baseline | Journal/My Slate board | Control hierarchy and quality, not fixture data or unsupported behavior |

Legacy `/api/journal/today`, `/api/journal/history`, and
`/api/journal/responses` are audit targets only. Their prompt/response model is
not accepted as the target memory-profile contract.

## Target conceptual flow

```text
private Capture source
        ↓ explicit review
confirmed source-linked Moment
        ↓ owner-authorized Journal presentation/reference
private Journal memory profile
        ↓ explicit Use This Moment approval
placement | content link | private draft | reminder | Studio scenario
        ↓ later, separately authorized
permissioned profile projection | Story | Work | Project | Feed | Replay
```

Memory Intelligence is adjacent to, not inside, canonical truth:

```text
permitted confirmed records → private insight proposal → member review
                                           ↓ confirm/correct/dismiss
                                      explicit activation only
```

## Minimum requirements

### Product and information architecture

- **PS-JOURNAL-R01:** Journal shall be the member's private-first memory profile
  and chronological home for reviewed Moments and connected context.
- **PS-JOURNAL-R02:** The owner Journal and any permissioned Journal view shall
  resolve from the same member-owned Slate and shall not use separate private
  and public truth databases.
- **PS-JOURNAL-R03:** The authenticated first slice shall provide a protected
  Journal route within the owner shell. Exact public/profile routes require the
  route-collision and viewer-mode decision before implementation.
- **PS-JOURNAL-R04:** Filters shall remain local to Journal and shall not create
  new top-level destinations.
- **PS-JOURNAL-R05:** Story shall remain curated meaning, while Journal remains
  chronological memory; one may reference the other without copying facts.

### Canonical data and lifecycle

- **PS-JOURNAL-R06:** Journal rendering shall use confirmed Moment versions and
  source relationships. Journal-specific presentation metadata may not copy the
  authoritative narrative.
- **PS-JOURNAL-R07:** The owner shall be able to list, inspect, search, filter,
  edit through approved versioning, archive, restore, export, and delete
  eligible Journal material with documented propagation behavior.
- **PS-JOURNAL-R08:** Original Capture language and source state shall remain
  inspectable where policy permits, including when an AI-polished proposal is
  shown.
- **PS-JOURNAL-R09:** Duplicate submit, interrupted retry, stale edit, deleted
  source, revoked source, and partial downstream failure shall have explicit,
  testable states.

### Privacy, audience, and security

- **PS-JOURNAL-R10:** All owner and viewer retrieval shall be authorized before
  data retrieval using trusted server identity and relationship/audience state.
- **PS-JOURNAL-R11:** Unauthorized payloads shall omit private records, source
  data, intelligence, media metadata, and counts; client hiding is insufficient.
- **PS-JOURNAL-R12:** New Journal material and all Member Intelligence shall
  default to Only Me. AI and placements may not broaden audience.
- **PS-JOURNAL-R13:** Audience change, unpublish, relationship removal, block,
  archive, restore, and deletion shall define propagation across projections,
  indexes, caches, media authorization, and intelligence outputs.

### Memory Intelligence and activation

- **PS-JOURNAL-R14:** Insights shall remain private, source-linked,
  time-bounded interpretations with proposed, confirmed, corrected, dismissed,
  expired, invalidated, and deleted states.
- **PS-JOURNAL-R15:** Use This Moment shall act only after member review and
  shall create references or reviewable private drafts without duplicating the
  canonical Moment or publishing automatically.

### Accessibility, resilience, and truth

- **PS-JOURNAL-R16:** Essential Journal capture, retrieval, inspection,
  correction, archive, export, and deletion shall remain usable with text,
  keyboard, assistive technology, and during AI or speech unavailability.
- **PS-JOURNAL-R17:** Desktop, mobile, touch, keyboard, screen reader, reduced
  motion, 200% zoom, long content, missing media, empty, loading, restricted,
  failure, retry, and recovery states shall be designed and verified.
- **PS-JOURNAL-R18:** Fixtures and disabled future controls shall be labeled and
  shall not imply persistence, analysis, sharing, or authorization that is not
  implemented.

## Architecture decisions the next branch must close

1. Exact protected route and its integration with the active Owner Home shell.
2. Exact permissioned profile route family and collision handling.
3. Journal presentation/reference metadata versus canonical Moment/version
   ownership.
4. Search strategy using structured data/full text before semantic retrieval.
5. Edit/version behavior and how newer Moment versions affect a Journal item.
6. Archive/restore/delete/export and propagation contracts.
7. Relationship/link allocation and whether existing Placement is sufficient
   for the private first slice.
8. Legacy journal endpoint retirement, compatibility, or isolation plan.
9. Feature flag, migration order, monitoring, rollout, and rollback.
10. Exact split between private Journal core, Use This Moment, audience/viewer
    projection, and later Memory Intelligence packages.

## Verification matrix

The architecture must allocate at least:

- unit tests for validation, transitions, filters, and serializer contracts;
- integration tests from Capture review through confirmed Moment and Journal
  retrieval/lifecycle;
- two-owner and guessed-ID isolation tests;
- payload-level negative tests for every viewer mode;
- exact-version, stale-write, retry, conflict, archive/restore, deletion, and
  export tests;
- no-automatic-publication and no-duplicate-authoritative-text tests;
- AI outage and speech-unavailable tests;
- accessibility and responsive browser evidence;
- privacy-safe telemetry and performance budgets; and
- rollback plus production verification plans that do not inspect or print
  private member content.

## Member validation

Pete and Danielle, using separate accounts, must each be able to:

1. capture one real work or life Moment by text or voice;
2. review/correct it and understand that it remains private;
3. deliberately add it to the private Journal;
4. find it later through the timeline and search/filter;
5. inspect original language and connected context;
6. edit or archive it and understand the effect;
7. export and delete eligible material;
8. complete the core tasks with AI unavailable; and
9. predict what the other person and a logged-out visitor can retrieve.

The private first slice cannot be accepted if either member needs developer
coaching to understand whose memory profile they are viewing, whether an item
is private, or what an action will change.

## Stop conditions

Stop before product code or release if:

- the owner shell or route ownership conflicts with an active branch;
- the proposed model copies Moment narrative into a new authoritative Journal
  body;
- the trusted-session owner or cross-user isolation cannot be proven;
- a public/viewer path relies on CSS or browser filtering;
- deletion/export/propagation behavior is unresolved;
- the visual proposal materially downgrades the approved Journal/My Slate board;
- homepage impact is ignored; or
- a missing backend is represented as working through fixture UI.

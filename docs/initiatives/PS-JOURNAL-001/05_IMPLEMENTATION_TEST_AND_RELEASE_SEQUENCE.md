# PS-JOURNAL-001 — Implementation, Test, and Release Sequence

## Sequencing rule

Do not attempt the universal composer, complete Journal, audience projections,
return-value engine, Story Composer, and messaging in one implementation
branch. Build one end-to-end truth path at a time while preserving the final
architecture.

## Slice J0 — Audit and allocation

**Output:** no product behavior.

- inventory routes, APIs, services, stored procedures, tables, migrations,
  exports, queues, flags, owner shell, fixtures, and tests;
- identify active-writer overlaps and reserve exact files;
- define route/legacy compatibility map;
- allocate Save Moment orchestration and derived Journal query;
- produce production-intent composer and owner-Journal visuals;
- approve migration/rollback and two-owner verification;
- record homepage impact.

**Exit:** one writer/branch, approved architecture and visuals, no unresolved
canonical-data/authorization conflict.

## Slice J1 — Save Moment orchestration and private owner Journal

**Includes:**

- composer mechanics from a bounded set of owner-shell contexts as a
  default-off internal/owner pilot;
- Type and Speak parity using released foundations;
- one idempotent Save Moment operation;
- derived owner Journal list/detail and immediate retrieval;
- source/version inspection, basic search/filter;
- edit/version, archive/restore, export/delete behavior required by the slice;
- AI/provider-unavailable survival;
- feature flag default off and guarded migration/rollback.

**Excludes:** public/permissioned Journal, Story Composer, broad intelligence,
messaging, all media types, and navigation redesign beyond the approved map.

J1 does not satisfy the universal-anywhere promise by itself. It may not be
broadly enabled, marketed, or accepted as Universal Capture while eligible
signed-in origins remain unproved. Every surface in the approved eligible-origin
matrix must either open the same context-preserving composer or record an
explicit, owner-approved exception before the universal claim can pass J2.

## Slice J2 — Universal composer expansion and Use This Moment

- add and verify every approved eligible signed-in origin in the maintained
  eligible-origin matrix;
- preserve origin context and focus;
- provide one relevant primary and at most two secondary post-save shortcuts,
  plus a complete keyboard/screen-reader-accessible Use This Moment chooser for
  every currently supported and authorized destination/purpose;
- implement exact-version reference/projection drafts for selected existing
  downstream domains;
- prove downstream failure cannot lose or duplicate the Moment;
- update homepage projection or activate exact downstream parity.

## Slice J3 — Curated and audience-resolved Journal

- Journal curation/presentation metadata;
- selected-person, Connection, member, and Public authorization services;
- exact audience preview and publication/revocation;
- payload-negative search/count/media/AI tests;
- legal/site, moderation/contact, accessibility, and privacy gates;
- public profile/timeline visual acceptance.

This slice may be split further. Public Journal shall not be bundled merely to
make an owner route look complete.

## Slice J4 — Downstream projections

Story, Work, résumé, Projects, Board, Studio, Feed, and messaging consume the
governed Moment/Journal architecture through their own active packages. My
Story Composer and public Journal remain different release gates.

## Slice J5 — Return value

Follow `PS-RETURN-VALUE-001`. First return-value slices may begin after J1 has
real, trustworthy owner history and correction/suppression controls. Signature
Noticed/Mirror behavior requires additional history and trust validation.

J-labels allocate scope; they do not impose one serial train. After J1's
private Journal and authorization foundation is trustworthy, bounded J5 Return
foundations and the separately packaged owner-only typed Ask My Slate first
slice may proceed in parallel with J2 planning. Neither waits for J3 public
Journal. J3 remains its own audience, legal, security, moderation,
accessibility, and visual release gate.

## Automated verification allocation

### Save and lifecycle

- valid text and voice saves;
- duplicate click/retry/idempotency;
- source succeeds/Moment fails and Moment succeeds/enrichment fails;
- stale edit/curation conflict;
- archive/restore/delete retry and propagation;
- export contents and ownership;
- source deleted/restricted/tombstone behavior;
- AI, speech, queue, search, and media-provider outages.

### Journal completeness and no duplication

- every eligible owner Moment appears exactly once without Journal Placement;
- absence of presentation metadata does not hide a Moment;
- no fact-bearing Journal body is written;
- removing a projection keeps the Moment in Journal;
- exact-version downstream references remain traceable;
- direct Feed/résumé bypass paths are absent or explicitly transitional.

### Authorization and privacy

- two-owner list/detail/search/filter/source/media/version/export isolation;
- guessed IDs/slugs and pagination/facet/count leaks;
- each viewer mode and grant expiry/revoke;
- block/relationship removal/unpublish cache invalidation;
- public Ask [Name] and comparison grounding restricted to permitted payload;
- neutral errors and no private identifiers in logs.

### Accessibility and responsive behavior

- keyboard open/compose/save/close/focus restoration;
- screen-reader labels, status, chronology, error recovery;
- Type/Speak parity and text fallback;
- 390px mobile, touch targets, rotation, long content;
- 200% zoom/reflow and no clipped controls;
- reduced motion;
- empty, many-year, many-item, missing-media, partial, slow, and error states.

### Performance and resilience

- bounded first content and pagination over long history;
- structured/full-text search budget;
- no N+1 source/audience retrieval;
- authorization predicate included in query/index path;
- retry storms do not duplicate records;
- telemetry contains no private content.

## Real-member validation

Pete and Danielle, using separate accounts and no developer coaching, each
complete:

1. open Capture from at least two different rooms;
2. save by Type and Speak and understand the private state;
3. return to the origin room without a forced Journal trip;
4. find the Moment immediately in Journal;
5. inspect source/original language and accepted version;
6. edit, search/filter, archive/restore, export, and delete an eligible Moment;
7. use one Moment in one downstream context without re-entering facts;
8. predict what the other member and a logged-out viewer can retrieve;
9. complete essential work with AI unavailable; and
10. explain the difference between Journal, curated/public Journal, and My
    Story.

## Release evidence

- exact branch and full SHA;
- current-origin merge base and diff inventory;
- schema/procedure scripts and guarded rollback;
- focused/full tests with exact commands;
- desktop/mobile/zoom/focus/reduced-motion/failure screenshots compared with
  named visual authority;
- two-owner synthetic and real-member results;
- feature-flag/default state;
- Azure PR, squash merge SHA, pipeline build, migration verifier;
- canonical and direct-host live route/auth-boundary checks;
- signed-in product validation before enablement;
- homepage parity state; and
- owner/designated-manager product and visual acceptance.

## Stop conditions

Stop rather than implement or release when:

- another writer owns an overlapping branch/file;
- the route map would create a new Capture destination;
- the schema copies Moment text into Journal;
- Save Moment can claim success without a retrievable Moment;
- a saved Moment requires Add to Journal;
- authorization occurs after retrieval;
- public Journal is conflated with My Story;
- AI controls facts, audience, publication, deletion, or downstream actions;
- lifecycle/export/deletion propagation is unresolved;
- required accessibility/failure/long-history visuals are missing;
- a homepage projection becomes materially stale without a sequenced package;
  or
- tests, migration, visual comparison, or real-member evidence are incomplete.

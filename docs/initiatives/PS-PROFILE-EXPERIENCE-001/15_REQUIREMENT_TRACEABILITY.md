# Requirement-to-Release Traceability

Status legend:

- **Locked** — accepted architecture/visual direction in this package.
- **Conditional** — required for implementation or enablement; not yet passed.
- **Deferred** — deliberately outside Profile v1 and must stay hidden.

| Requirement | Authority | Architecture | Required implementation proof | Status |
|---|---|---|---|---|
| One living whole-person Profile, not Résumé Overview 2.0 | Owner direction; independent visual review | 01-03, 06 | Route/body comparison, six destinations | Locked |
| Home, Posts, Projects, Media, Voice, About | 33-board visual set | 02, 03, 06, 14 | Destination routes, zero/one/typical/many | Locked |
| Public, Connections, Owner same body | Constitution/privacy; boards 01-04, 25-26, 33 | 03-06 | Two-owner payload/DOM tests | Locked |
| Private by default; exact audience choice | Constitution; legal standard | 04, 05, 09-10 | Preview/publish/widen/withdraw tests | Locked |
| Authorization before retrieval | Site rules; viewer gate | 04, 12 | SQL/service/API/search/media byte isolation | Locked |
| Canonical truth/proposal/projection/placement/version separation | Constitution; Placement/Project/Voice foundations | 05, 07-09, 12 | Schema constraints, exact version, where-used | Locked |
| Profile is command surface, not warehouse | Owner direction | 02, 07, 09 | Adapter and source-change behavior | Locked |
| Posts remain canonical Community conversations | Community authority | 06-07 | Reference-only/thread authorization tests | Locked |
| Projects show role, outcomes, proof | Projects authority; boards 05-06 | 06-07 | Exact Project Projection adapter | Conditional |
| Media/album `+N`, collections, video | Boards 07, 15, 27 | 06, 08 | Media pipeline, audience counts, captions | Conditional |
| Voice-first, text-equal; four voice modes | Owner direction; Voice authority | 02, 08 | Retention disclosure, transcript/version/player tests | Locked |
| No voice/emotion/hiring inference | Trust/legal direction | 08, 10 | Product and prompt negative tests | Locked |
| Exact anonymous Public preview | Boards 12-13; viewer gate | 03-05, 09 | Serializer equivalence and no private DOM | Locked |
| Add/Manage/Review/Publish lifecycle | Boards 10-18, 30-31 | 05, 09 | Idempotency/conflict/failure/rollback | Locked |
| Search current authorized Profile only | Visual/function map | 06, 10, 12 | Revision-bound index and no hidden counts | Conditional |
| Block/report/relationship lifecycle | Boards 25-26; legal | 04, 10, 12-13 | PS-CONNECT-002 and two-owner lifecycle tests | Conditional; hard dependency of complete release |
| Messaging | Owner discussion/visual fixture | 01, 04, 07, 10 | Separate L4 package | Deferred |
| Generic Ask `[Name]` | Ask Pete boundary | 05, 07, 10 | Reusable public-source authorization/abuse gate | Deferred until separately released |
| Resume/My Story remain deeper destinations | Live product authority | 01-03, 07 | Current-route regression and explicit links | Locked |
| Workshop/My Knowledge remains private engine | Workshop direction | 01, 07 | No private retrieval; owner-only doorway | Locked |
| Capture remains private-first input layer | Capture/Voice direction | 07-08 | No auto-publication; source adapter | Locked |
| Capture/Slate global-shell prominence | Program Review open decision | 03, 14 | Separate shared-shell visual/runtime authority | Deferred from Profile package |
| 320/390/tablet/desktop; mobile app runway | Boards 19-24, 31, 33 | 11 | Responsive/device evidence | Conditional |
| WCAG 2.2 AA | Constitution; visual integrity | 06, 08, 11 | Manual/automated accessibility evidence | Conditional |
| Performance budgets and scale | Visual review; boards 29, 32 | 06, 11, 13 | Production-like measurements | Conditional |
| Legal/privacy/moderation readiness | Early legal standard | 10 | Actual counsel/security/operational L2 evidence | Conditional; blocks enablement |
| Default-off dark deployment | Owner delegation; governance | 03, 12-13 | Exact release, flag-off/current-route smokes | Locked sequence |
| Pete review immediately before enablement | Owner direction | README, 13-14 | Recorded exact-candidate decision | Mandatory stop |
| Bounded dependency ownership and complete-candidate release train | Site rules; package boundary | 07, 13, 17 | D0-D4 exact package/dependency evidence | Locked sequence |

## Visual-control traceability

Every board must map to a real contract before implementation:

- 01-09: destination body and dominant object;
- 10-18: owner workflows and contextual controls;
- 19-24: mobile/responsive composition;
- 25-27: audience, relationship, album authorization;
- 28-32: lifecycle, scale, accessibility, consequential, failure, AI, long
  content; and
- 33: Profile-local shell modes only.

The implementation state matrix must name the exact test, route, fixture class,
viewport, and evidence artifact for each required board. If a depicted function
is not released, omit it; do not substitute a dead control.

## Remaining owner decisions before implementation activation

No further product decision is required to complete this direction package.
The runtime activation must confirm exact path ownership after Interview Studio
closure and current-main refresh. Any material change forced by that inventory
returns to Pete/ChatGPT under the visual authority rule.

The runtime may be built and deployed dark in safe slices. It may not call a
Public + Owner-only slice the complete Profile, and it may not silently remove
Connections from the owner outcome. Any proposal to enable a narrower release
is a new owner decision.

## Remaining gates before public enablement

1. implementation lane activation and exact surface ownership;
2. migration/schema gate and verification;
3. complete reusable runtime and two-owner trust proofs;
4. exact visual/accessibility/mobile/performance review;
5. actual Gate L2 counsel/security/moderation/privacy/incident readiness;
6. Protected merge and dark release authority;
7. exact production dark deployment and current-route verification; and
8. Pete's explicit acceptance and separate enablement record.

Until all eight are evidenced, the Profile is not live.

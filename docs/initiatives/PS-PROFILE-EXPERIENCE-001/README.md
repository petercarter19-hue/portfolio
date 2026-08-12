# PS-PROFILE-EXPERIENCE-001 — Living Whole-Person Profile

## Status

- Delivery path: **Protected**
- Package state: **active direction and product architecture**
- Runtime effect: **none**
- Branch: `work/2026-08-11-profile-experience-direction-001`
- Authoritative base: Azure `origin/main` at
  `f745b39b72d2c8e5a3595f88d7f9524d8d8e41cf`
- Writer: Codex, as the sole Profile direction/architecture writer
- Visual direction: the exact 33-file ChatGPT-created Profile candidate is
  adopted as production direction under Pete's 2026-08-11 delegation. Pete's
  final material acceptance remains the mandatory stop immediately before
  public enablement.
- Implementation authority: **not created by this package**. A separate
  implementation activation is required after the Interview Studio lane
  relinquishes the production-capable slot and shared application surfaces.

## Owner outcome

Build one reusable, living whole-person Profile that a member can use as:

1. the front door to who they are;
2. a social and professional place friends, connections, recruiters, and other
   visitors can explore according to the member's exact audience choices; and
3. the signed-in command surface from which the member adds, arranges,
   previews, publishes, withdraws, and understands the use of Profile material.

Profile is not Résumé Overview 2.0, a second Community feed, a private file
cabinet, or a new canonical warehouse. It connects purpose-built rooms through
exact, versioned references and deliberately published projections.

## Locked architecture decisions

- Public, Connections, and Owner use one recognizable Profile body. The server
  resolves viewer identity and audience before retrieval; owner controls are
  not sent to visitors.
- Profile has six first-class destinations: **Home, Posts, Projects, Media,
  Voice, and About**. Résumé, My Story, and Ask `[Name]` remain connected deeper
  paths or actions rather than duplicate Profile sections.
- Home is a finite, member-curated front room. Posts owns chronology. Projects,
  Media, Voice, and About are deep, browsable destinations.
- Canonical source, AI proposal, member-approved projection, audience,
  placement, exact version, and where-used state remain distinct.
- Public and Connections are independent publication branches. Owner is a
  working mode, not an audience. `Only me` is private source/draft state.
- Community owns posts and conversations. Projects owns Project truth. Capture
  owns private source media. Voice owns retained audio and transcript truth.
  Résumé and My Story remain their own published records.
- Speak to type is transient dictation. A Voice post retains playable audio
  and a member-approved transcript. They are never treated as the same action.
- `/app` remains PeerSlate's stable authenticated ingress. After approved
  enablement it routes a signed-in member to their canonical Profile; valid
  deep links continue to win.
- The current global shell is reused for the first implementation. The broader
  Capture/Slate global-shell decision is a separate program package.
- Runtime is built behind one default-off flag, deployed dark, and verified in
  production without changing current public routes. Pete reviews that exact
  deployed candidate before a separate enablement decision.

## Package map

1. [Current truth and supersession](01_CURRENT_TRUTH_AND_SUPERSESSION.md)
2. [Purpose, destinations, and journeys](02_PURPOSE_DESTINATIONS_AND_JOURNEYS.md)
3. [Routes, shell, and compatibility](03_ROUTES_SHELL_AND_COMPATIBILITY.md)
4. [Audience, relationships, and authorization](04_AUDIENCE_RELATIONSHIP_AUTHORIZATION.md)
5. [Source, projection, placement, and version model](05_SOURCE_PROJECTION_PLACEMENT_VERSION.md)
6. [Destination and state contracts](06_DESTINATION_STATE_CONTRACTS.md)
7. [Adapters and room boundaries](07_ADAPTERS_AND_ROOM_BOUNDARIES.md)
8. [Media, albums, video, and Voice](08_MEDIA_ALBUM_VIDEO_VOICE.md)
9. [Owner draft, preview, and publication lifecycle](09_OWNER_DRAFT_PREVIEW_PUBLISH.md)
10. [Search, moderation, privacy, and legal readiness](10_SEARCH_MODERATION_PRIVACY_LEGAL.md)
11. [Mobile, app runway, accessibility, and performance](11_MOBILE_APP_ACCESSIBILITY_PERFORMANCE.md)
12. [Schema, API, migration, and compatibility architecture](12_SCHEMA_API_MIGRATION_COMPATIBILITY.md)
13. [Implementation, validation, release, and rollback](13_IMPLEMENTATION_TEST_RELEASE_ROLLBACK.md)
14. [Visual authority and traceability](14_VISUAL_AUTHORITY_AND_TRACEABILITY.md)
15. [Requirement-to-release traceability](15_REQUIREMENT_TRACEABILITY.md)
16. [Verification and completion record](16_VERIFICATION_AND_COMPLETION_RECORD.md)
17. [Release train and dependency ownership](17_RELEASE_TRAIN_AND_DEPENDENCY_OWNERSHIP.md)

## Controlling and triggered authority

- [PeerSlate Site Rules](../../PEERSLATE_SITE_RULES.md)
- [Owner Visual Integrity Standard](../../governance/OWNER_VISUAL_INTEGRITY_STANDARD.md)
- [Early Legal and Product-Site Readiness Standard](../../governance/EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md)
- [Projects authority](../PS-PROJECTS-001/README.md)

The current Constitution and Roadmap remain those named by
`CURRENT_BASELINE.yaml`. Historical Profile branches, packages, and handoffs
are provenance and supersession evidence only where document 01 names them.

## Release-state vocabulary

These words are not interchangeable:

- **Direction complete:** this package is accepted and merged.
- **Implemented:** runtime exists on an implementation branch.
- **Merged:** the implementation PR is on `main`.
- **Deployed dark:** production runs the exact merged release with Profile off.
- **Pete accepted:** Pete reviewed the exact dark candidate.
- **Enabled:** the feature flag and route cutover were separately approved and
  applied.
- **Live verified:** anonymous Public, authenticated Connections, Owner,
  revocation, compatibility, and rollback smokes passed against the exact live
  release.

## Stop boundaries

This package authorizes no code, schema, migration, route, shell, deployment,
or public behavior. Runtime must not begin until a separately activated
implementation lane names its exact surfaces. Public enablement must stop for
Pete even after implementation, merge, and dark deployment have succeeded.

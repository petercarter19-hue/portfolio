# Implementation, Validation, Release, and Rollback

## Activation prerequisites

Runtime begins only after all of the following are true:

1. this direction package is independently reviewed, its exact visual
   authority is adopted under Pete's end-to-end Codex delegation,
   merge-authorized, and merged;
2. Interview Studio is officially removed from `active_lanes` and explicitly
   relinquishes its production-capable slot plus `app.py`/auth surfaces;
3. current `origin/main`, baseline, lane ledger, migration registry, live routes,
   and active PRs are re-fetched and reconciled;
4. one exact Profile implementation outcome, branch, writer, exclusive domain,
   production-capable status, migration IDs, and writable paths are activated;
5. Opportunity Slate or another lane has not claimed a conflicting shared
   surface; and
6. package write preflight passes in a clean worktree from the activated main.

At this package base, Interview remains active; its writer transfer was not a
closure. Runtime is therefore blocked today even though Profile architecture
continues lawfully.

## Complete implementation target

The target is one reusable, multi-user Profile, built through the release train
in document 17. It is not a Pete-only page and not a fixture reskin. The slices
below describe technical order, not one omnibus writer lane or permission to
absorb separately governed Projects, Connections, media, or Voice foundations.

### Slice 1 — foundation and flags

- Default-off `PEERSLATE_PROFILE_EXPERIENCE_ENABLED`.
- Profile blueprint/route namespace, typed contracts, feature-unavailable
  behavior, dependency health, and configuration tests.
- No route/nav/metadata/sitemap cutover while false.

### Slice 2 — additive identity, relationship, and publication data

- `PS-CONNECT-002` hardening and `PS-PROFILE-002` governed publication schema,
  after fresh registry reservation and protected schema delivery.
- Owner isolation, expected version, idempotency, atomic revision, epoch, and
  rollback proofs.
- No inferred legacy publication or audience.

### Slice 3 — reader and viewer authorization

- Slug resolution, immutable viewer context, authorization-before-retrieval,
  Public/Connections/Owner serializers, neutral failure, exact Public preview,
  media/audio byte authorization, and private/no-store handling.

### Slice 4 — owner draft and publication commands

- Add/Manage contextual flows, exact audience preview, review/diff, publish,
  withdraw, revision history, conflict/retry, where-used, source-change, and
  consequential confirmations.

### Slice 5 — destinations and adapters

- Home, Posts/Community adapter, Projects adapter, Media/albums/video, Voice,
  About, Resume/My Story/Ask deeper paths, and dependency-aware availability.
- Profile-local CSS/JS/components follow exact visual authority; shared global
  shell remains unchanged unless separately authorized.

### Slice 6 — scale, mobile, accessibility, safety, and release proof

- Authorized search/pagination, long/zero/many states, 320/390/tablet/desktop,
  WCAG, performance, moderation/reporting, privacy telemetry, deletion/export,
  failure/revocation, and exact visual comparison.

Implementation packages are split by release-train ownership and lane
boundaries. No
partial slice may claim Profile is usable/live without the complete release
contract. Each split names its dependency and keeps one writer per surface.

## Complete release versus safe dark slices

The complete Profile release promised by this package includes all six
destinations plus Public, Connections, and Owner behavior. Implementation and
dark deployment may proceed in independently safe slices, but product status
must remain exact:

- a Public + Owner foundation without the hardened relationship service is an
  incomplete dark slice, not the complete Profile;
- Connections routes, preview, controls, indexes, and counts stay absent until
  `PS-CONNECT-002` and the document-04 authorization fence pass;
- a destination whose canonical adapter is not released stays absent rather
  than becoming a decorative empty page or a second truth store;
- the final Pete review package must distinguish every present, hidden, and
  intentionally deferred function; and
- public enablement of a narrower slice would require Pete to explicitly
  change the release outcome and visual/function contract. It is not implied
  by this architecture.

The mandatory Pete pre-enable review occurs only after the complete candidate
in document 17 has been integrated, deployed dark, and verified. Earlier dark
milestones are engineering evidence, not a request to accept an incomplete
Profile.

## Expected runtime surface inventory

Exact paths are locked only after Interview closure and a fresh inventory.
Likely Profile-owned additions:

```text
profile_routes.py
profile_api.py
services/profile_*.py
templates/profile/*
templates/partials/profile/*
static/css/profile-experience.css
static/js/profile-experience.js
tests/test_profile_*.py
tests/profile_*.test.js
SQL Files/Migrations/PS-CONNECT-002*
SQL Files/Migrations/PS-PROFILE-002*
SQL Files/Verification/PS-CONNECT-002*
SQL Files/Verification/PS-PROFILE-002*
SQL Files/Migrations/registry.json
```

Potential shared edits—`app.py`, `auth_routes.py`, `templates/base.html`, global
navigation/search/mobile JS/CSS, sitemap/metadata, and deployment configuration—
must be explicitly named in the later lane. They cannot be inferred from this
architecture and cannot overlap another active writer.

## Automated validation matrix

### Identity and authorization

- anonymous Public equals signed-in-unrelated Public;
- Owner A cannot read/mutate Owner B through route, API, key, search, count,
  media/audio, download, preview, cursor, cache, or command replay;
- active connection receives only its exact Connections revision;
- pending/declined/disconnected/blocked receive no Connections data;
- block in either direction invalidates every protected read and byte route;
- unblock never restores prior access.

### Publication integrity

- Public and Connections revisions advance independently;
- candidate digest, expected version, and idempotency fencing;
- concurrent publish produces one winner and one truthful conflict;
- timeout/retry returns original command result;
- failed publish leaves prior revision current;
- stale source never silently rewrites a projection;
- withdraw/revoke/delete removes every affected placement/index/cache;
- rollback creates a new validated revision and never resurrects deleted data.

### Destination and adapter truth

- zero/one/typical/many and unavailable dependency for all six destinations;
- Community thread is referenced, not copied;
- Project/Resume/Story/Workshop/Voice/Capture private truth never leaks;
- mixed-audience album cover and `+N` are audience-correct;
- approved Voice transcript and audio versions stay pinned;
- speak-to-type audio is not retained;
- generated fixtures never become member defaults.

### Browser, accessibility, and performance

- 320/390/768/1024/1280/1440; 200% zoom/320 CSS px; text spacing;
- keyboard, visible focus, screen-reader names/states/live regions, focus return,
  forced colors, reduced motion, touch, long text/bidi;
- media permission/interruption/failure/retry, no autoplay, transcript/captions;
- Back/Forward, deep links, safe return, session expiry, bfcache revalidation;
- performance and payload budgets from document 11.

### Regression

With flag false and after dark deploy:

- `/`, `/healthz`, `/auth/session`, `/auth/sign-in`, `/app`;
- `/petec`, `/petec/resume`, `/petec/my-story`, `/petec/about`;
- Ask Pete, Community, Workshop, Interview Studio, Opportunity Slate;
- legacy Projects/work redirects, sitemap, canonical/Open Graph, global search,
  mobile navigation, error pages, and static caching.

## Visual implementation proof

- Compare exact required states to the 33 hash-bound boards at 1440, 1280,
  1024, 768, 390, 320, 200% zoom, forced colors, and reduced motion.
- Use truthful production-like synthetic fixtures across zero/one/typical/many.
- Image-generation artifacts control composition, hierarchy, material, and
  state intent—not fixture copy or fabricated capabilities.
- Resolve every control against the functional control map; hide unavailable
  functions rather than styling dead controls.
- A fresh reviewer inspects the exact candidate SHA after the writer's one
  complete self-review.

## Protected delivery and dark deployment

1. Complete code/schema validation and full diff review.
2. Obtain required independent exact-SHA security/visual/functional review and
   close every material finding.
3. Record merge and release authority; open Azure PR; require policy/CI/Pete
   review as configured; merge through the approved strategy.
4. Verify automatic main pipeline and exact release identity. Do not call the
   merge deployed.
5. Confirm the flag remains false in every production slot/instance.
6. Verify `/healthz` exact release, current public routes, anonymous no-leak,
   owner auth, database compatibility, and monitoring.
7. Label the result **deployed dark**, not live Profile.
8. Prepare an exact authenticated Owner/Public-preview review using the same
   server serializers as the future audience.
9. **Stop for Pete.** Do not change the flag, `/petec` root, `/app` default,
   navigation, sitemap, metadata, or indexing before his explicit decision.

## Rollback

Primary rollback is the feature flag plus current-route compatibility. If a
dark release harms unrelated routes, roll back to the known-good artifact and
verify exact release identity; do not improvise a same-SHA deployment while an
automatic pipeline is active.

Schema rollback is additive and separately governed. Never edit migration
history or drop shared foundations. Before enablement, prove the application
works with the Profile flag false even when additive tables exist. After
enablement, rollback must preserve member private sources and publication
history unless an exact, approved data disposition says otherwise.

## Enablement and final smoke

After Pete explicitly approves the exact dark candidate, record one separate
enablement outcome and release authority. Enable with rollback ready, then
verify anonymous Public, authenticated Connections, Owner, exact preview,
block/disconnect/revocation, search/media/Voice, canonical/metadata/sitemap,
mobile, performance, policies/support, and current routes against the exact
live release. Only then use **enabled and live verified**.

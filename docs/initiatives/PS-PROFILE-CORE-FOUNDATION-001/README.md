# PS-PROFILE-CORE-FOUNDATION-001 â€” D0 Profile Core Foundation

## Status and boundary

> **Current-status correction (2026-08-13):** This accepted D0 checkpoint is
> `paused_preserved` at `aa1fc7e`. It has no active writer and must not be
> independently registered or released. Reconcile what the later merged
> Profile integration lineage consumed before classifying this separate
> foundation as historical.

- Delivery path: **Protected** (owner isolation, publication contract, and
  material visual authority are involved).
- Runtime state: **unregistered and non-production**. Neither `app.py` nor a
  shared application module imports or registers this foundation.
- Profile scope: **D0 only** â€” Profile-native identity/current chapter/About,
  a finite Home, Community post references, exact Public preview/publication,
  and local Home/Posts/About rendering.
- This is **not a complete Profile** and does not change `/app`, `/petec`,
  public routing, metadata, navigation, storage, data schema, or deployment.

## What this foundation supplies

1. A typed Profile-native draft contract with explicit owner scope and opaque
   versions.
2. Immutable Public publication revisions: a review produces a digest; an
   owner explicitly confirms a version-fenced, idempotent publish; withdrawal
   advances to a new empty revision and never edits history.
3. An exact Public reader reused by owner Public preview, so preview is not a
   CSS-hidden owner page.
4. A narrow Community adapter that stores only an exact source reference,
   source revision, canonical path, and publication timeâ€”not a copied post,
   reply, attachment, count, or conversation body.
5. Isolated Home, Posts, and About blueprints/templates and local assets for
   test-only composition. The canonical runtime paths are deferred to Profile
   integration.

## Visual scope

The accepted 33-board authority in `PS-PROFILE-EXPERIENCE-001` is binding.
D0 implements the Profile-local portions of boards **01-04** (Home/Posts
Public and Owner shape) and **09** (About), while preserving their editorial
light-canvas, near-black ink, forest action, bronze hierarchy, and restrained
plum Voice language. It does not claim visual completion for Media, Voice,
Projects, Connections, full owner workflows, responsive board suite, or the
global shell. Those remain D1-D4/D4 evidence work.

## Truth and authorization rules

- Every owner command compares server-supplied actor and subject before any
  draft/read/write access. A browser cannot set actor, owner, mode, or
  audience.
- Public reads derive only from one immutable Public revision. They never read
  an owner draft and then remove fields.
- Public preview calls the same reader/serializer as a visitor read.
- Community remains canonical for posts and conversations. Profile uses exact
  references only, and a later source change is an owner-visible stale signal;
  it never rewrites a publication automatically.
- `InMemoryProfileCoreStore` is a test adapter only. The later Profile
  integration package must supply a SQL-backed port, trusted identity
  resolution, CSRF registration, route registration, flags, and release proof.

## Deferred dependencies

- `PS-PROFILE-002` publication schema and durable optimistic/concurrency
  storage;
- trusted identity, exact registered Profile routes, `/app` cutover, flag,
  app/global-shell registration, sitemap/metadata/search;
- D1 Media/Voice, D2 Projects, D3 Connections, D4 complete integration; and
- dark deployment, Pete review, signed-in enablement, public exposure, and
  live verification.

## Verification target

The focused suites prove owner isolation, immutable revision behavior,
idempotency, exact preview equivalence, neutral absence, Community-reference
isolation, same-origin write fencing, semantic rendering, focus/reflow/reduced
motion static coverage, unregistered source behavior, and local visual-token
traceability. Complete 33-board browser evidence is intentionally deferred to
D4 rather than fabricated by this isolated D0 foundation.

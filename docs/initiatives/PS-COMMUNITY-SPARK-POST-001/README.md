# PS-COMMUNITY-SPARK-POST-001 - Spark question as a first-class post source

**Status:** Planned - not active.
**Dependency:** Community Authoring direction must be accepted first.
**Risk path:** Protected data/API/publication package when activated.
**Runtime status:** No schema, endpoint, rendering, count, or publication change
is authorized.

## Owner outcome

A member can answer a Spark as a post and optionally carry the originating
question into the published composition. A Spark is more than a decorative
tag: the question/source relationship remains understandable over time.

## Proposed experience

1. A Spark offers **Answer as post**.
2. The Community composer opens with a removable Spark prompt chip.
3. A clear control offers `Include Spark question in my post`.
4. The post may render a compact `SPARK` label, the question, and the member's
   response as distinct elements.

Defaulting inclusion to on is a proposal for Pete/visual review, not permission
to publish the question silently. Opening or dismissing the composer never
saves or publishes anything.

## Required data truth

The implementation design must define a prompt identifier and version plus a
question snapshot bound to the response post. It must decide what a reader sees
if the source Spark is edited, retired, deleted, or made unavailable, and what
happens when the member edits or removes the relationship later.

Audience authorization, moderation, post deletion, Spark deletion, and source
provenance apply independently. Response counts, if ever added, must derive from
real relationships and should avoid engagement-pressure design.

## Acceptance gate

A protected architecture must cover schema, API, authorization, rendering,
edit/delete/version behavior, moderation, privacy, accessibility, and migration
of any existing Spark responses. A new Community visual lock is required. No
fake posts, fake counts, or inferred source relationships are allowed.

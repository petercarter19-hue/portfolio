# Source, Projection, Placement, and Version Model

## Truth classes

These classes remain permanently distinct:

1. **Canonical source** — the authoritative private or purpose-built record.
2. **AI/provider proposal** — an interpretation, transcript, summary, label,
   or suggestion that has not become member-approved wording.
3. **Projection version** — exact, member-approved content suitable for one
   defined downstream use.
4. **Publication revision** — an immutable audience-specific manifest of exact
   projection versions.
5. **Placement** — where and how one exact projection version appears within a
   publication revision.

Profile does not copy canonical Community threads, Projects, Résumé facts, My
Story chapters, Workshop/My Knowledge, Capture blobs, or Voice transcripts
into a second truth store.

## Logical object model

```text
ProfileContentItem
  stable member-owned logical item
       |
       +-- ProfileContentVersion
              exact source adapter + source version
              the one exact member-approved Profile wording/metadata body
              immutable after creation
                     |
                     +-- ProfileProjectionVersion
                            audience eligibility, asset references, and digest
                            no duplicate fact/body copy
                                    |
ProfilePublication(public|connections)
       +-- immutable ProfilePublicationRevision
              +-- immutable ProfilePublicationRevisionItem
                     exact projection + destination/region/rank/feature
```

The implementation may consolidate tables where integrity remains provable,
but it may not collapse these meanings or store content-bearing snapshots as
the sole authority.

## Required identifiers

- Public routes use an opaque `projection_key`, never a source primary key.
- Internal references include owner/subject, source adapter, source object key,
  exact source version, content version, and projection version.
- Publication roots are unique per `(profile_id, audience)`.
- Publication revisions are monotonically versioned within their own audience
  branch. Public and Connections do not share one sequence.
- Owner/profile/audience relationships are protected by composite foreign
  keys; a projection or revision item cannot cross subjects or audiences.
- Exactly one current revision pointer exists per `(profile_id, audience)`.
- Projection keys are opaque, nonsequential, and unique within a Profile.
- Draft placement is mutable and version-fenced. A published placement is the
  immutable destination, region, rank/order, featured state, and exact
  projection reference stored on its revision item.
- A publication revision cannot contain duplicate `(destination, region,
  rank)` positions or the same projection twice in one destination unless an
  explicitly allowlisted composition requires it.

`ProfileContentVersion` is the sole Profile-owned content-bearing version for
approved wording/metadata. `ProfileProjectionVersion` does not repeat that
body; it binds one exact content version to audience eligibility, authorized
derivative references, and a digest. When Public and Connections wording must
differ, the member approves two distinct content versions. Canonical source
bodies still remain in their source-owning rooms.

## Publication revision rule

A visitor response is derived from one current immutable publication revision.
It must not combine “latest” rows from different sources at request time. This
provides an exact preview, atomic publication, reliable rollback, and a stable
answer to “what could this audience see?”

Publishing a new revision:

1. validates owner, expected draft and current-publication versions;
2. validates every referenced projection is owned by the subject and approved
   for the target audience;
3. validates destination availability and placement rules;
4. writes the immutable revision and its item/placement references;
5. advances the audience publication root atomically; and
6. advances the authorization/publication epoch for cache/search invalidation.

If any step fails, the prior revision remains current and complete.

## Placement rules

- Placement changes presentation only; it never changes canonical source.
- One projection may be placed on Home and its deep destination without a
  second copy.
- A Post placement may link to its canonical Community conversation.
- Removing a Home placement does not unpublish the deep object.
- Unpublishing a projection creates and atomically advances to a new audience
  revision that omits every affected immutable revision item. It never edits
  the old revision in place and it retains the private source.
- Reordering is version-fenced and accessible through keyboard/touch controls,
  not drag-only behavior.
- Every consequential change shows affected destinations and where-used links
  before confirmation.

## Source-change and stale truth

A canonical source changing later does not silently rewrite a published
projection. The owner sees:

```text
Current published projection: version P3
Canonical source used: version S7
Source now available: version S9
State: source changed; publication remains P3
```

The owner may keep P3, create a proposed update from S9, edit it, and publish a
new audience revision. Deleting or revoking S7 follows the explicit lifecycle
in the owner-publication contract; no dangling placement is hidden.

## Where used

Where-used is derived from current and retained publication-revision items and
placements. It answers:

- which audience revisions contain this exact projection;
- which Profile destinations and Home regions use it;
- whether Ask `[Name]` is separately authorized to use it;
- which canonical source/version supports it; and
- what withdrawal or deletion would affect.

Where-used never claims every historical consumer if retention has lawfully
expired. Export and deletion reports state their included scope and timestamp.

## AI and transcript boundary

AI may propose Profile wording, a current-chapter draft, alt text, transcript,
collection label, Project summary, or search metadata. Each remains visibly a
proposal until the member reviews exact wording. AI may not silently save,
merge, classify, order, feature, publish, widen audience, authorize public AI,
withdraw, or delete.

Public Ask `[Name]` authorization is separate from Profile publication. It
references exact Public projection versions; private and Connections sources
are never retrieved and filtered after the fact.

## Legacy handling

- Existing `member_profiles` remains the identity/slug foundation.
- Existing `entity_publication_versions.snapshot_json` remains intact for
  compatibility and is not rewritten into the new Profile authority.
- Ambiguous legacy audiences such as `shared` and `recruiter` are quarantined
  and require explicit owner review; they are never auto-mapped to Public or
  Connections.
- Historical Profile branches and fixture JSON remain evidence only.
- Migration is additive and rollback preserves the prior live routes and data.

# D0 Traceability â€” PS-PROFILE-CORE-FOUNDATION-001

This is an implementation-ready **foundation**, not an assertion that the
complete Profile or any Profile route is released. The accepted architecture
remains `PS-PROFILE-EXPERIENCE-001`.

| D0 requirement | Foundation surface | Focused proof | Deferred integration dependency |
|---|---|---|---|
| Profile-native identity/current chapter/About stay separate from Resume and My Story truth | `ProfileIdentityDraft`, `ProfileCurrentChapterDraft`, `ProfileAboutDraft` | `test_profile_core_service.py` draft/publication tests | Durable `PS-PROFILE-002` storage and real member identity lookup |
| Public comes from one immutable audience revision | `ProfilePublicationRevision`, `public_read` | publication/withdrawal tests | SQL transaction, auth epoch, cache invalidation |
| Owner preview is exact Public, not CSS-hidden owner data | `owner_preview_public` calls `public_read` | preview equivalence service/API tests | Easy Auth + registered owner preview route |
| Explicit owner draft/review/publish/withdraw lifecycle | `update_native_draft`, `review_publication`, `publish_publication`, `withdraw_publication` | version, digest, confirmation, and idempotency tests | CSRF, durable command ledger, concurrent transaction proof |
| Posts remain canonical Community truth | `CommunityPostReferenceAdapter` and `CommunityPostReference` | adapter and no-copied-body tests | Community-owned eligible-source query and visitor conversation authorization |
| Source changes never silently alter publications | `source_status` returns `current`, `source_changed`, or `unavailable` | adapter stale-source test | owner inspector and future revoke lifecycle |
| Home is finite, not a latest-activity feed | immutable revision items and Home serializer | finite placement/test fixtures | complete D4 Home manifest/manage workflow |
| Home, Posts, and About preserve Profile visual language | `templates/profile/`, local CSS/JS | static visual/a11y tests, local manual inspection against boards 01/03/09 | D4 exact 33-board browser comparison and global-shell integration |
| Current live application remains unchanged | blueprints export only; no `app.py` import/registration | source/static tests; lane path scope | later production-capable route/app/flag package |

## Controlled visual regions in this D0 slice

The writer inspected boards `01_HOME_PUBLIC.png`, `03_POSTS_PUBLIC.png`, and
`09_ABOUT_PUBLIC.png` from the immutable external authority. D0 carries
forward the following non-material, truthful parts:

- editorial identity/current-chapter split rather than a generic dashboard;
- a calm light canvas with near-black editorial type, forest action, bronze
  hierarchy, and restrained plum accent; no blue wash or card soup;
- Home as finite, selected material; Posts as a readable authored timeline;
- About as Profile-specific orientation plus deeper paths, rather than a My
  Story duplicate; and
- semantic/mobile reflow adaptations that omit unavailable destination
  controls instead of showing dead interactions.

D0 intentionally does **not** reproduce generated portraits, names, post
bodies, dates, media, projects, or unpublished controls. It uses a neutral
initial-based portrait treatment only in isolated contract rendering; the
integrated product uses member-authorized imagery or collapses it.

## Exact next boundary

The next production-capable Profile integration package must own and inventory
the previously excluded application/data surfaces before it may register these
blueprints: trusted identity context, `app.py`, durable schema/operation
allowlist, default-off flag, actual canonical paths, global-shell composition,
dependency health, migration/release proof, and dark deployment. It must also
complete D1-D3 contracts before D4 claims the complete Profile.

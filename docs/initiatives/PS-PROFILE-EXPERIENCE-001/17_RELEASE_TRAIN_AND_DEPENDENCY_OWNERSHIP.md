# Release Train and Dependency Ownership

## Why this exists

The complete Profile connects several real product rooms. It must not become a
single hidden mega-package that quietly reimplements Community, Projects,
Capture, Voice, Connections, search, moderation, and the global shell. It also
must not ship as a polished but hollow shell with dead destinations.

The release train below permits bounded implementation, independent review,
merge, and flag-off dark deployment while preserving one final product promise:
Pete reviews the complete six-destination Public/Connections/Owner candidate
immediately before any enablement.

## Milestones

| Milestone | Member/product value while dark | Owning package/domain | Exit evidence | May enable? |
|---|---|---|---|---|
| **D0 — Profile Core** | Reusable identity/current chapter, Home curation, Posts adapter, About, Resume/My Story/Ask paths, Owner draft/exact Public preview/publish, flag-off route compatibility | Profile implementation | Public/Owner isolation, canonical Community reference, publication revision, mobile/a11y, current-route regression | No; incomplete candidate |
| **D1 — Media and Voice projections** | Private-source-first photo/album/video and retained-Voice adapters, authorized derivatives/player/transcript, destination states | Separate bounded media/Voice foundation or Profile adapter package with exact source-owner boundaries | upload/retention/derivative/audience/revoke/delete/two-owner byte proofs | No; incomplete candidate |
| **D2 — Projects projection dependency** | Projects workspace/projection authority supplies exact role/outcome/proof objects for Profile Projects | Separate `PS-PROJECTS-001`-governed package; Profile only integrates adapter | Project private-first lifecycle, exact projection versions, cross-owner and source-change proofs | No; incomplete candidate |
| **D3 — Connections foundation** | Complete request/accept/decline/cancel/expire/disconnect/block/unblock/reconnect service and authorization epochs | Separate relationship-foundation package using a freshly reserved migration ID | lifecycle/race/idempotency/moderation/neutral failure/two-owner proofs | No; incomplete candidate |
| **D4 — Complete Profile integration** | Home, Posts, Projects, Media, Voice, About; Public, Connections, Owner; authorized search; moderation, scale, mobile/app runway, complete critical states | Profile integration package after D0-D3 | all 33 visual boards mapped; full trust/accessibility/performance/regression suite; Gate L2 status exact | Dark only |
| **D5 — Pete review and enablement** | Exact production dark candidate is shown with present/hidden/deferred inventory | Separate owner acceptance and enablement record | Pete decision; required L2/counsel/security/operations; rollback-ready enablement smoke | Yes, only after explicit approval |

Milestone labels are release-train names, not claims that migration or package
IDs are already registered.

## Ownership rules

- Profile owns Profile-native identity/current-chapter/About/curation versions,
  audience publication revisions, placements, owner controls, Profile readers,
  and Profile search over already-authorized projections.
- Community owns authored posts, questions, replies, and conversations.
- Projects owns private Project truth and exact Project projections.
- Capture/media owns original media, processing, retention, and authorized
  derivatives.
- Voice owns retained audio, provider transcript attempts, approved transcript
  versions, playback source lifecycle, and deletion.
- The relationship foundation owns requests, connections, blocks, reports,
  epochs, and lifecycle history.
- Profile adapters validate and reference exact eligible versions. They do not
  copy or silently mutate another room's canonical truth.

Each milestone requires a fresh current-main/lane inventory and its own exact
writable surfaces. Two milestones may run concurrently only when their domains
and actual diffs are disjoint under the lane policy. Shared `app.py`, auth,
global shell, migration registry, and deployment configuration are serialized
through explicit ownership.

## Navigation and availability during dark work

The outer Profile flag stays false throughout D0-D4, so no intermediate route,
navigation, sitemap, metadata, or public claim appears in production. In exact
authenticated review environments:

- unavailable destinations are absent, not dead tabs;
- synthetic fixtures are labeled and never treated as member data;
- present destinations state their real persistence/audience behavior; and
- no incomplete milestone is called live, released, or the complete Profile.

## Final integration rule

D4 consumes released contracts from D0-D3; it does not reopen their canonical
data ownership. If a dependency is unavailable, D4 stops or hides that
destination in engineering review. It cannot replace the dependency with
Profile-owned copied data, fixture content, or a generic JSON snapshot.

The final Pete review is against D4 deployed dark. A proposal to enable D0, D1,
or any narrower subset is a material owner decision outside this package and
must return to Pete before enablement work begins.

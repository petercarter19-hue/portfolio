# PS-OWNER-HOME-VIEWER-GATE-001 Current-State Inventory

Audit date: 2026-07-19. Repository authority: Azure DevOps origin/main at 31864e43287d7cefb5a0d1c0441e94bec0bd6b1f. Azure pipeline 112 (20260719.20) succeeded for that exact source version. This inventory distinguishes code, deployed behavior, fixture evidence, schema foundations, and missing capability.

## Executive truth

PeerSlate has a real signed-in owner boundary and real private source/canonical foundations. It does not yet have the finite Owner Home, reusable viewer authorization/projection service, generic viewer routes, exact My Slate preview, or operational sharing/publication contracts required by this package.

The database contains early profile, entity, access-grant, publication-version, connection, block, consent, and notification tables. Those tables are reusable candidates. Their presence is not proof that an authorized viewer can retrieve a Slate, that an owner can publish one, or that revocation is complete across responses and caches.

## Repository, pipeline, and live-route evidence

| Evidence | Current result | What it proves | What it does not prove |
|---|---|---|---|
| origin/main | 31864e43287d7cefb5a0d1c0441e94bec0bd6b1f | Exact source baseline for this package | Signed-in member behavior by itself |
| Azure pipeline 112 | Succeeded for the exact origin/main SHA | Current main passed the configured Build/Deploy pipeline | Every future Home/viewer state |
| GET / | 200 | Public homepage reachable | Approved final homepage or signed-in Home |
| GET /app | 302 to /auth/sign-in?return_to=/app when signed out | Owner landing is protected | Finite Home content or signed-in visual acceptance |
| GET /app/settings | 302 to sign-in when signed out | Settings route is protected | Management of visibility, retention, export, or deletion |
| GET /app/capture | 302 to sign-in when signed out | Capture route is protected | Any viewer/public access |
| GET /auth/session | 200 with signed_in=false and available=true when anonymous | Production auth edge is enabled and reports anonymous state | A particular signed-in member or viewer grant |
| GET /api/dashboard | 401 when anonymous | Legacy database dashboard API is protected | Suitability as the finite Home contract |
| GET /petec/my-story | 200 | Pete fixture-driven Story is public | Generic multi-user Story or viewer projection |
| GET /my-story | 302 to /petec/my-story | Canonical public Pete Story redirect | Authenticated My Slate preview |
| GET /the-slate/my-slate | 200 | Public static My Slate preview page is reachable | Owner-scoped persistence, authorization, or projection |
| GET /api/public/profiles/petec/living-resume | 404 | Database-backed generic public resume API is feature-flagged off in production | Absence of the separate fixture-backed public resume |
| GET /petec/resume | 200 | Canonical fixture-backed Pete resume is live | Reusable publication service |
| GET /interview-studio | 200 | Public browser-local Studio is live | Authenticated owner history or viewer-mode support |

## Capability inventory

| Area | Implemented in repository | Deployed/live evidence | Fixture-only or limited truth | Missing for this package |
|---|---|---|---|---|
| Identity | Trusted Easy Auth principal parsing; issuer and subject mapping; opaque account UUID/user_key; private profile provisioning; optional development identity only under explicit test/dev controls | Current state records real sign-in and two-owner isolation; auth session is enabled in production | Display name/email are identity snapshots, not a viewer grant | Reusable subject-viewer-purpose authorization context and authorization epoch |
| Owner landing | Protected GET /app renders owner_workspace.html | Signed-out production redirect works | Landing links to Capture, public/static Slate Board, public Studio, and Settings; it is not the finite Home | Real bounded Home aggregation, truthful category states, performance budget, retry, and Home tests |
| Owner Settings | Protected GET /app/settings shows display name, email, signed-in state, private default, sign-out | Signed-out production redirect works; route/tests exist | Settings is informational. The template labels profile/privacy/sign-in preferences as upcoming | Visibility-default editing, retention choices, consent controls, account export/deletion entry points, concurrency, and exact impact preview |
| Text Capture | Owner-scoped create/list; correction versions; archive/restore; explicit delete; JSON export; row-version concurrency; private visibility | Current state records PR 63/pipeline 85 and production migration verification | No publication or viewer retrieval | Home-safe summary/list procedure; no raw body in Home payload by default |
| Voice Capture | Owner-only upload/transcription/review/explicit private save; private audio proxy; retry/delete | Current state records PR 75/pipeline 105 and Pete's signed-in functional validation | Product visual acceptance is withdrawn and correction is active | Home adapter must wait for fixed lifecycle/visual lane and must not modify Voice files |
| Canonical Moment | Owner proposal/review/save/confirm/discard; exact Capture revision pin; deleted-source tombstone; private versioned canonical fields | Current state records PR 66/pipeline 91 and production SQL verification | Only single-Moment review route exists; no owner Moment list or public viewer service | Bounded Home list summaries; audience projection serializer; published/reference selection |
| Placement | Body-free reference to one exact confirmed Moment version and one eligible owner Slate entity; create/list/remove stored procedures | Current state records PR 68/pipeline 93 and production SQL verification | No route, UI, downstream consumer, audience change, or publication | Projection consumer that independently authorizes viewer and target; payload serializer; cache/revocation behavior |
| Profile/entity foundation | member_profiles, slate_entities, slate_entity_relations, entity_access_grants, and entity_publication_versions exist through PS-PLAT-002 | Migration ledger and later packages depend on the foundation | Vocabulary and constraints predate current Roadmap; entity publication snapshots are not an approved viewer API | Current audience vocabulary, reference-only manifest rules, grant versioning/opaque keys, service/procedure contracts, lifecycle tests |
| Connection foundation | connection_preferences, connection_requests, member_connections, user_blocks, reports, notifications, consents exist through PS-PLAT-004 | Identity provisioning creates private/discovery-off defaults | No current product route/procedure proves a usable connection loop | Relationship-state service, block precedence, projection integration, revocation, validation, and Phase 8 release |
| Legacy database dashboard/API | Authenticated /api/dashboard, feed, board, journal, Slate-space, badge, and challenge endpoints call allowlisted procedures | /api/dashboard rejects anonymous access | Contract includes feed/polls/badges/boards and older Journal/Slate concepts; governance does not authorize it as Home | Do not rename or wrap this as Owner Home; build a bounded Home-specific contract |
| Public Pete surfaces | Fixture-backed resume, Story, project/work redirects, Slate/Community previews, Studio | Representative public routes return 200 | Profile registry is effectively Pete-only; Story uses static/data/story_data.json; My Slate/Feed pages are static, browser-local, or sample-member previews | Generic subject resolution, published projection data, audience authorization, withdrawal/revocation, payload-level privacy |
| Living Resume DB API | Owner and public stored procedures plus feature-flagged JSON endpoints exist | Public JSON endpoint returns 404 with production flag off | It is a distinct Living Resume slice, not a generic Slate viewer service | Do not treat as proof of public projection availability; future convergence must preserve one canonical dataset |
| What PeerSlate noticed | Governing lifecycle and requirements exist in Bible/Roadmap | No implementation/release evidence | Homepage/demo copy or deterministic suggestions are not governed insights | Insight records, authorized retrieval, sources, uncertainty, controls, staleness, revocation, evaluation, and service |
| My Slate preview | Roadmap and storyboard direction exist | Public static /the-slate/my-slate returns 200 | Existing page is not owner-scoped and does not share real viewer logic | Owner-only preview endpoint/service using the exact live viewer query and serializer |

## Reusable contracts

### Identity

- get_current_identity() resolves a request to PeerSlateIdentity only from a trusted Easy Auth principal or an explicitly enabled test/development identity.
- The durable tenant selector is identity.user_key, mapped in SQL to one active app_users record and member_profiles row.
- Browser profile slugs, account IDs, emails, entity keys, relationship IDs, and query parameters are selectors only. None establishes ownership or audience.
- Every future authenticated viewer query must start from the same current identity boundary. Do not create a second session or token model in this package.

### Owner Settings

- Reuse the protected route, identity display, private first-account profile, connection_preferences defaults, and sign-out boundary.
- Treat discovery defaults as discovery settings, not as content audience authorization.
- A future default audience is a default for newly created projection drafts. It must not publish, broaden, or retroactively mutate existing content.
- Current Settings has no write contract for visibility, grants, export, deletion, retention, or consent; those remain PS-SETTINGS-001 work.

### Capture

- dbo.captures is the private source aggregate. dbo.capture_revisions contains immutable numbered corrections; the original remains in captures.body.
- All current procedures resolve @UserKey to the owner profile and do not accept owner_profile_id from the client.
- Home may receive bounded metadata and a purpose-specific summary only through a new owner-scoped procedure. It should not receive original/revision bodies unless the owner opens the existing Capture review path.
- Capture visibility stays private. No Home or viewer route may infer sharing from status, revision, archive state, or Voice state.

### Moment

- dbo.moments is the private owner aggregate; dbo.moment_versions stores immutable proposal/member-approved canonical versions; dbo.moment_sources pins exact Capture provenance or a body-free deleted-source tombstone.
- Only confirmed Moments may be considered for a future projection. A proposal is owner-only and may appear only as a bounded review item.
- Confirmation is not publication. Source deletion does not automatically delete a confirmed canonical Moment, but viewer payloads must disclose only audience-approved lifecycle state.
- Existing procedures support one Moment review, not a Home list or audience projection. New read procedures are required.

### Placement

- dbo.moment_placements is a private, body-free reference from one exact confirmed Moment version to an owner-owned Slate entity.
- Placement does not grant access, publish, copy content, or create a downstream page.
- A future projection may use a placement as an item reference only after independently authorizing the target Slate entity, viewer, audience, relationship, publication state, and exact Moment version.
- Removed or target-unavailable placement rows must disappear from viewer payloads immediately and remain visible to the owner only as allowed lifecycle metadata.

### Projection, grants, and connections

- Reuse member_profiles.profile_key for authenticated subject selection and profile_slug only for deliberately public lookup.
- Reuse slate_entities as owner-scoped projection targets and moment_placements as exact-version item references.
- Reuse entity_access_grants as a migration source or selected-person grant foundation, not as a complete current contract.
- Reuse member_connections and user_blocks as relationship foundations; block/revocation decisions take precedence over connection state.
- Reuse entity_publication_versions only under a strict manifest contract that stores identifiers, versions, ordering, and presentation metadata, not copied canonical Moment/Profile text.

## Gaps and conflicts that implementation must resolve

1. Existing visibility/audience constraints use private, shared, connections, recruiter, and public. The current Roadmap requires private/owner, selected person, connection, authenticated member, and public. shared and recruiter must not be silently reinterpreted. A versioned migration and explicit mapping are required.
2. entity_access_grants lacks an opaque grant key and row-version concurrency token. A selected-person preview/revocation URL cannot safely depend on its numeric grant_id.
3. entity_publication_versions.snapshot_json can technically hold arbitrary content. The future service must reject copied canonical text and use a versioned reference-only projection manifest, or replace/harden the column through migration.
4. There is no centralized policy object or procedure that resolves subject, viewer, block state, relationship, grant, audience, publication, placement, and source lifecycle before retrieval.
5. There is no generic viewer serializer. Public fixture templates and the feature-flagged Living Resume API must not become implicit authorization logic.
6. There is no exact-preview parity harness comparing preview output with the actual specified viewer's output.
7. No cache invalidation contract exists for grant revocation, connection end/block, publication withdrawal, placement removal, Moment correction/deletion, subject account suspension, or profile deactivation.
8. The current /app landing contains links into public/static surfaces. The future Home must label or replace those paths only through a separate approved route/navigation and frontend package.
9. There is no Home-specific procedure. The existing usp_GetPeerSlateUserDashboard contract contains activity/feed/poll/badge/board concepts that violate the finite Home budget and must not be reused as the Home payload.

## Inventory conclusion

The current foundations are strong enough to plan and implement a first owner-only finite Home core without schema changes beyond a bounded read procedure. Full viewer modes and exact My Slate preview are not ready to implement against the existing schema without the authorization/projection migration and service boundary defined in ARCHITECTURE.md.

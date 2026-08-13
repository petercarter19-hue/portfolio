# Profile Core Integration — completion record

## Core record

- **Task/package and delivery path:** `PS-PROFILE-CORE-INTEGRATION-001`, Protected, non-production implementation slot 2.
- **Outcome and member/site effect:** Profile-local **D0 foundation candidate plus unintegrated D1-D3 adapter contracts**: exact accepted foundation; durable Profile publication boundary; server-derived identity; exact Community reference integration; defensive Project/Media/Voice reader contracts; fail-closed Connections state contract; and responsive Home, Posts, and About rendering. No current member or live site behavior changes because the blueprints remain unregistered. This is not D1-D4 completion.
- **Branch:** `work/2026-08-12-profile-experience-build-001`.
- **Activated base SHA:** `204b634d95504a3a64531c4bc666c535b136ff6b`.
- **Refreshed exact base SHA:** `6fe81389f17ad46e045f0aeda3f7520354498160`; the intervening main change touched only delivery-preflight code/tests, disjoint from Profile. The clean branch was rebased before final review.
- **Final SHA:** recorded after the completion-record commit.
- **Changed paths:** only the lane-authorized Profile blueprints/services/templates/assets/tests, `PS-PROFILE-002` migration/rollback/verifier/registry, foundation package documentation, and this artifact directory.
- **Release state:** pushed branch only; unregistered, unapplied, unmerged, undeployed, and not live.
- **Next action:** exact-SHA independent functional/security/schema/visual review, then a separately activated shared integration slice after Interview relinquishes shared app/auth/production surfaces.

## Verification and completion evidence

- Accepted foundation tree: 16/16 allowed path blob hashes matched independently accepted `aa1fc7e889fa63e31a432074da5c5040698f4aea` before expansion.
- Accepted foundation gate: 39/39 passed.
- Final `python -m unittest discover -s tests -p 'test_profile*.py'`: 85/85 passed.
- All `services/profile_*.py`: `py_compile` passed.
- Registry JSON parse and `git diff --check`: passed.
- Final package write preflight on refreshed main: passed, with only the expected package-lineage warning.
- Path audit: every changed path is inside the activated writable list; `app.py`, `auth_routes.py`, `.env.example`, `services/database_service.py`, `templates/base.html`, shared navigation/auth/search/delivery tests, Interview surfaces, production config, and deployment remain untouched.
- Profile CSS: 9,863 raw bytes; Profile JS: 607 raw bytes, within Profile-local budgets.
- Three integrated Flask destinations render with no-store/noindex headers. Unintegrated Project, Media, and Voice destinations are neutrally absent rather than exposed as decorative empty pages; tests cover neutral absence and no owner/source identifier leakage.
- Authorization negative paths cover cross-owner draft/publication/command returns, unsafe paths, malformed manifests, revoked/changed Community references, block precedence, and dependency failure.
- Draft-save proof binds manifest owner, slug, version, and immutable draft key with explicit null checks and binary case/accent-sensitive comparison; the expected opaque draft version must binary-match the locked current version before any draft overwrite. An executable stored-procedure-boundary test proves a case-only stale version is rejected with the original draft intact.
- Publication proof covers candidate digest, explicit `publish` versus `withdraw` action binding, exact binary (case/accent-sensitive) reviewed draft key/version/manifest and native-field equality, exact binary placement/source/content-kind/source-metadata/cardinality equality with explicit null semantics, expected current revision, exact stored idempotent winner reload, stale/revoked source refusal, prior-public preservation, withdrawal, and atomic compare-and-swap fences. Rejection tests prove omitted native fields, changed item kind, action confusion, and case-only/accent-only native/source-metadata/content-kind tampering all fail before replacing the prior current revision. Two-writer and simultaneous-identical-command executable repository tests supplement structural SQL contract assertions.

## Protected additions and exact limitations

### Data, identity, privacy, authorization, and publication

- `PS-PROFILE-002` is additive and owner/profile/audience scoped, with normalized Profile-native versions, exact projection versions, private draft placements, immutable publication revision items, idempotency commands, and reserved slug history.
- The migration remains a candidate with registry `gate: null`. It has not passed disposable database apply/verify/rollback/reapply, permission, hash-gate, or production apply. It therefore provides implementation evidence, not schema release authority.
- The durable Python repository is injected and unregistered. The procedure allowlist change in shared `database_service.py` is deliberately deferred to the shared integration lane.
- Connections is deliberately fail-closed until `PS-CONNECT-002`, relationship/version epochs, block invalidation, and two-owner database-snapshot authorization proof exist. No Connections route, preview, count, or control appears.
- Project, Media, and Voice services validate exact projection identity/version/audience and malformed provider values fail neutrally; unapproved Voice transcripts are rejected. These are adapter contracts only. Their source-owning canonical providers, exact release/revocation/where-used records, and byte authorization routes do not exist as lawful injectable dependencies on this base and are not fabricated or integrated into the publication manifest.
- The isolated D0 core currently materializes only Public publication commands. A distinct Connections branch remains correctly absent rather than simulated.

### Material visual work

- Implemented against the Profile 33-board authority mapping: light continuous editorial canvas; near-black ink; forest primary actions; bronze hierarchy; restrained plum Voice; no heavy blue, dark theme, or equal-card dashboard.
- Home, Posts, and About have content-aware navigation and truthful states. Profile-local Project, Media, and Voice template/CSS composition exists as unintegrated visual preparation only; it is not counted as released destination behavior. The shared responsive layer includes 320-pixel reflow contracts, 44-pixel navigation targets, semantic landmarks/headings/lists, visible focus, reduced-motion, and forced-colors behavior.
- The rendered/static test harness passed. CLI browser automation was unavailable because Node/npm is absent, and the in-app browser reported no available browser. No 33-board screenshot overlay, 390/768/1024/1280/1440 geometry capture, screen-reader/device-lab result, or Pete visual acceptance is claimed. Those remain mandatory before enablement.

### Shared infrastructure and release

- No default-off flag, application registration, owner identity wiring, live canonical paths, shared shell/navigation, sitemap/metadata, production config, schema apply, deployment, dark verification, or live verification was authorized in this lane.
- No broad Flask regression was needed for a branch that imports nothing into startup; final shared integration must run current-route/auth/navigation/metadata/feature-flag regression plus local and dark deployed browser checks.
- `gitleaks` 8.30.1 was not installed on this machine, so no all-ref scan is claimed. Repository secret policy/CI remains an independent gate.
- Legal/privacy/moderation/incident readiness, authorized search/pagination at production scale, media/video processing/captions, retained Voice recording lifecycle, exact byte-route authorization, export/deletion operations, Connections lifecycle, independent review, Pete pre-enable review, PR/merge, schema release, dark deploy, and final enablement remain open.

## Completion truth

This candidate is a non-production **D0 foundation candidate with defensive D1-D3 adapter contracts**. D1 requires real Media/Voice canonical providers and byte/lifecycle proof; D2 requires the `PS-PROJECTS-001` projection provider; D3 requires `PS-CONNECT-002`; D4 can begin only after those released contracts are integrated into exact publication manifests and shared registration is separately activated. It does **not** satisfy D1-D4, the complete Profile release contract, production candidacy, deployment, or live status.

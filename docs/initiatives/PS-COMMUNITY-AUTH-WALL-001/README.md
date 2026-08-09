# PS-COMMUNITY-AUTH-WALL-001 — Community behind sign-in

**Delivery path:** Protected · **Activated:** 2026-08-08 (activation PR 357, main `0ee01b9`)
**Owner decision (2026-08-08, Pete):** "Let's just position this firmly behind the sign in wall. That will make life easier for all of us. We can make a demo down the road. Not a working demo, but maybe a video or something else when it is time to get this out to the audience."
**Source handoff:** `PEERSLATE-COMMUNITY-AUTH-WALL-CLAUDE-HANDOFF-2026-08-08.md` (owner-held, iCloud). The public-pilot package `PS-COMMUNITY-PUBLIC-PILOT-001` remains evidence of the prior implementation; this package supersedes its public-read product direction only.

## Outcome

Retire anonymous Community and every working public/demo fallback. Require trusted
PeerSlate authentication before any Community HTML, JSON, search, Voice, attachment,
or media retrieval. Preserve current owner-only authoring, existing data, private
Blob storage, and independent retention maintenance. No Feed redesign, no member
authoring, no schema change.

## Access contract

| State | HTML | API/media |
|---|---|---|
| Flag off | 404 | JSON 404, before any Community dependency |
| Signed out | 302 to sign-in with exact safe return path | JSON 401; no SQL, Blob, or Speech touched |
| Invalid/unmappable principal | Auth recovery (401), never anonymous | JSON 401, never anonymous |
| Identity DB failure | Private 503 recovery | JSON 503; no fallback |
| Signed-in non-owner | Real read-only Community | Reads allowed; every mutation denied |
| Owner | Real Community, existing capabilities | Existing authorized reads and writes |
| Empty Feed / unknown post | Honest empty state / 404 | Empty canonical result / 404 — no fixture substitution |

## Key mechanics

- `community_api` `before_request` resolves trusted identity for **every** endpoint
  (including `preview_attachment`/`download_attachment`, previously reachable
  anonymously straight to SQL+Blob) before limits/same-origin/body work.
- `community_routes.require_community_member()`: availability → authentication →
  authorization, in that order. `viewer_context(identity)` no longer swallows
  `DatabaseServiceError` — identity failure is a 503, never an anonymous render.
- `auth_routes._safe_return_path` allowlist widened narrowly to `/app`, `/app/*`,
  `/the-slate`, `/the-slate/*`; every other defense unchanged; hostile-input tests extended.
- Flag semantics are fail-closed: `PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=true` means
  authenticated Community only; `false` means neutral 404. **No flag state serves the
  old public shell or fixture APIs** (`people_interests_api` is never registered,
  `/api/slate-feed` is permanently 404, Living Stream preview routes are retired).
  The legacy flag name is misleading and is documented debt; rename is a separate
  configuration cleanup.
- Demo runtime deleted: `services/community_demo_feed.py`, all `community_api`
  fallbacks, the demo composer/quick-compose/banner in template and JS, and the two
  demo-only preview scripts. The two local-fixture preview harnesses
  (`preview_community_primary_feed.py`, `preview_community_secondary_states.py`)
  remain — they are truthfully labelled and never routed in production.
- Discovery: sitemap carries no `/the-slate*` paths; robots adds `Disallow: /the-slate`;
  `X-Robots-Tag` + `Cache-Control: private, no-store` are unconditional for the
  namespace; header search index carries one generic Community entry; homepage hero
  CTAs retargeted (href/copy only) from the Living Stream demo to sign-in / Why PeerSlate.
- `/the-slate/public-pilot` retired; authenticated `/the-slate/policy` replaces it
  (template `community_policy.html`). The historical pilot policy template remains in
  the repo as evidence, unrouted.

## Explicitly out of scope

Feed V2, composer/inline-comment redesign, member authoring, invites, reactions,
Following, messaging, notifications, recommendations, Pulse, cross-product sharing,
The Break redesign, the public showcase video, the `audience='public'` schema
migration, and any change to Workshop, Opportunity Slate, Interview Studio, the
public résumé, Public Slate, or Story/profile access boundaries.

## Deferred legs (recorded, not optional)

1. **Retention reapproval by Pete** — required before release. Draft delivered to the
   owner 2026-08-08 (durations unchanged, authenticated-audience language).
2. **Release** — separately recorded Protected sequence: `release_allowed_for` entry,
   exact-SHA Candidate, deploy-before-flag-change ordering, live verification of the
   §26 matrix, evidence record.
3. **Rollback truth** — once authenticated Community content exists, the pre-wall
   build is not a safe rollback (flag-on = anonymous reads; flag-off = legacy public
   fixture feed). Safe stop is: keep the wall artifact, set availability off (404),
   preserve data, keep maintenance running, roll forward.
4. **Audience token migration** (`public` → `community`) — later Protected package
   after a governed, content-free production inventory and explicit owner disposition.
5. **Flag rename** — separate configuration cleanup.

## Surface note (recorded-scope additions)

Beyond the activation-recorded surfaces, the following test files required
narrow updates because they assert routes, pages, wording, or render bytes
this package retires or legitimately changes. Recorded here per the
established recorded-scope pattern; no application code outside the recorded
surfaces was touched:

- `tests/test_http_edge_security.py` — retired `/api/feed/people-interests` expectation.
- `tests/test_community_tabs.py`, `tests/test_community_journal_home_milestone.py`,
  `tests/test_community_voice.py`, `tests/test_community_xlsx_support.py` — old
  public shell / demo Voice / public download contract.
- `tests/test_owner_home.py` — the flag-off `/app` byte pin re-captured for the
  shared base-shell search-index change, with a normalization step proving the
  retired search block is the only delta (old baseline archived as
  `FLAG_OFF_APP_RENDER_PRE_AUTH_WALL_*`).
- `tests/test_people_interests_feed.py`, `tests/test_feed_prototype.py`,
  `tests/test_navigation.py`, `tests/test_resume2.py`, `tests/test_peerslate_api.py`,
  `tests/test_homepage_scenes.py` — retired board API, Living Stream prototype,
  legacy Community navigation, and homepage CTA expectations.

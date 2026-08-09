# Live production evidence — AFTER the wall

Captured 2026-08-09 from https://peerslate.com as an anonymous visitor (no cookies, no
authentication headers), immediately after the wall build reached production.

**Deployed build:** `/healthz` release `e1a3b800aec6444f1a35c80a`
(= main `7a7c99de085a8d25ab12ce386c7cb2509cda2057` via pipeline run 711, batchedCI,
`schemaAction=none`, owner-approved at the production checkpoint).
**Previous release:** `090ed9967daf7a00c798898e` (main `fb55cd5`, run 688) — see
`LIVE_EVIDENCE_BEFORE.md`.

## Anonymous request sweep

| Path | Before | After | Redirect target | X-Robots-Tag | Cache-Control |
|---|---|---|---|---|---|
| `/the-slate` | **200** | **302** | `/auth/sign-in?return_to=/the-slate` | noindex, nofollow | no-store, private |
| `/the-slate/posts/<uuid>` | 200 | **302** | `/auth/sign-in?return_to=/the-slate/posts/<uuid>` | noindex, nofollow | no-store, private |
| `/the-slate/recently-deleted` | — | **302** | `/auth/sign-in?return_to=/the-slate/recently-deleted` | noindex, nofollow | no-store, private |
| `/the-slate/policy` | — | **302** | `/auth/sign-in?return_to=/the-slate/policy` | noindex, nofollow | no-store, private |
| `/the-slate/public-pilot` | 200 | **404** | — | noindex, nofollow | no-store, private |
| `/api/v1/community/feed` | **200 + demo data** | **401** | — | noindex, nofollow | no-store, private |
| `/api/v1/community/attachments/<uuid>/download` | 200-capable | **401** | — | noindex, nofollow | no-store, private |
| `/api/v1/community/attachments/<uuid>/preview` | 200-capable | **401** | — | noindex, nofollow | no-store, private |
| `/api/slate-feed` | 404 | **404** | — | — | — |
| `/api/feed/people-interests` | flag-dependent | **404** | — | — | — |
| `/feed-living-stream` | **200** | **302** | `/the-slate` | — | — |
| `/feed-living-stream/states` | 200 | **404** | — | — | — |
| `/the-slate/my-slate` | 302 | **302** | `/the-slate` | noindex, nofollow | no-store, private |
| `/the-slate/break` | 302 | **302** | `/the-slate` | noindex, nofollow | no-store, private |

Every `/the-slate*` response — including redirects and errors — carries
`X-Robots-Tag: noindex, nofollow` and `Cache-Control: no-store, private`.

**The attachment result is the most consequential line in this table.** Before the wall,
those two endpoints reached Azure SQL and Blob Storage with no Python-side authorization:
anyone holding a media UUID could retrieve the bytes. They now refuse before any storage
call.

## Discovery

```
robots.txt:
  User-agent: *
  Allow: /
  Disallow: /app
  Disallow: /api/
  Disallow: /owner
  Disallow: /the-slate        ← added
  Sitemap: https://peerslate.com/sitemap.xml
```

`sitemap.xml`: **0** occurrences of `the-slate` (previously advertised five Community paths).

## Homepage

| Check | Result |
|---|---|
| Links to the retired Living Stream demo | **0** |
| Links to retired `/the-slate/my-slate` or `/daily` | **0** |
| Sign-in links | 5 (hero button, mic affordance, Journal card, week link, header) |
| Primary hero button | "Talk about what happened" → `/auth/sign-in` |
| Secondary button | "See how it works" → Why PeerSlate |

## Fabricated demo content

Scanned `/`, `/the-slate`, `/api/v1/community/feed`, `/petec/resume` for `demo_mode`,
"Illustrative demo", and "Public demo": **0 occurrences on every path.** Before the wall,
the Community feed API returned `demo_mode: true` with `demo: true` attachments described
as "illustrative" to any anonymous caller.

## Honest limits

1. Content that was publicly readable before this release may already exist in
   screenshots, downloads, caches, or third-party copies. The wall cannot retract those.
   This is stated in the approved retention decision (v1.0) and in the member policy page.
2. The stored audience token remains the transitional literal `public`; the wall is
   enforced in the application layer, not by a schema change. Migration is a later
   Protected package.
3. Attachment delivery authorizes *any authenticated member*, not the owner only — the
   published-state filtering lives in the SQL procedure. This is unchanged by the wall
   (it tightened from anonymous to members-only) and is recorded, not introduced, here.
4. A valid principal that cannot be mapped to an account returns 503 on HTML and 401 on
   the API. Both are fail-closed and never anonymous; the inconsistency is pre-existing
   app-wide behavior and was deliberately left outside this package's blast radius.

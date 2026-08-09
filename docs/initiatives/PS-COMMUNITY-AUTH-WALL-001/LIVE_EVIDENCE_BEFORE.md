# Live production evidence — BEFORE the wall

Captured 2026-08-09 from https://peerslate.com as an anonymous visitor (no cookies, no
authentication headers), while production was still serving the pre-wall build.

**Deployed build at capture time:** `/healthz` release `090ed9967daf7a00c798898e`
(= main `fb55cd5ec6cd658938dfbf8fc722a005c9ab04b6` via pipeline run 688).
**Community availability flag:** ON in production (public pilot).

## Anonymous request sweep

| Path | Status | Observed |
|---|---|---|
| `/healthz` | 200 | release `090ed9967daf7a00c798898e` |
| `/the-slate` | **200** | Full Community page rendered to an anonymous visitor |
| `/api/v1/community/feed` | **200** | Community feed JSON served to an anonymous caller |
| `/api/slate-feed` | 404 | (already retired by the pilot flag being on) |
| `/feed-living-stream` | **200** | Retired prototype still publicly reachable |
| `/the-slate/my-slate` | 302 | Redirect to `/the-slate` (itself public) |
| `/robots.txt` | 200 | `Disallow: /app`, `/api/`, `/owner` — **no `/the-slate` exclusion** |

## The demo-content defect, in production

`GET /api/v1/community/feed` (anonymous) returned:

```json
{"caught_up":true,"demo_mode":true,"items":[{"attachments":[{"byte_length":2320474,
"content_type":"image/png","demo":true,
"display_name":"An illustrative team reviewing a corkboard workflow",
"download_url":"/static/images/feed/feed-workflow-corkboard-2026-07-21.png",
"height":941,"key":"22222222-2222…
```

Three facts this establishes:
1. Community was readable by **anyone on the internet**, with no sign-in.
2. The API was serving **fabricated demo content** (`demo_mode: true`, `demo: true`,
   "illustrative" attachments) as the Feed's response body.
3. Search engines were **not** told to stay out of `/the-slate`.

This is the exact state the owner directed be closed on 2026-08-08: "Let's just position
this firmly behind the sign in wall… We can make a demo down the road. Not a working demo."

## After-state

The matching after-capture is recorded in `LIVE_EVIDENCE_AFTER.md`, taken with the same
requests against the same host once the wall build is deployed. Expected: `/the-slate` →
302 to sign-in, `/api/v1/community/feed` → 401, `/feed-living-stream` → 302, robots.txt
carrying `Disallow: /the-slate`, and no `demo_mode` key anywhere in any response.

# PS-PERFORMANCE-FOUNDATION-001 performance evidence

## Evidence identity

- Date: 2026-07-29
- Release-branch base after the Candidate-admission correction: Azure
  `origin/main` `06559478e2f9429e47bca0d67858131ef9429bd0`
- Measurement baseline:
  `3da1f747609b6529542be2416649a8fba75abd49`; the intervening Candidate
  corrections changed pipeline admission, its metadata, and its tests, not
  application rendering or public assets
- Branch: `work/2026-07-29-performance-foundation-001`
- Routes measured: `/` and `/petec/resume`
- Production release during the configuration change:
  `4b2c46e824613c1b7c844884`

The payload measurements below were made with Flask's test client against the
exact baseline worktree and the implementation worktree. The direct-reference
model counts the HTML plus every unique first-party static URL directly present
in that rendered HTML. It does not claim to be a browser waterfall: viewport
position, lazy loading, pre-existing browser cache, CSS-discovered assets,
third-party fonts, and network conditions can change an individual visit.

## Production configuration evidence

Before the bounded configuration change:

- App Service Always On: `false`
- App Service HTTP/2: `false`
- `/healthz` release: `4b2c46e824613c1b7c844884`

After the bounded configuration change:

- App Service Always On: `true`
- App Service HTTP/2: `true`
- App Service state: `Running`
- `/healthz` status: `ok`
- `/healthz` release: `4b2c46e824613c1b7c844884`
- Last re-verification: `2026-07-29T13:02:14.9969921Z`

The unchanged release proves that this step changed App Service configuration,
not application code. Warm public-route probes varied within normal
Internet/application noise and are not presented as proof of an immediate
elapsed-time improvement. The Always On benefit must be evaluated after an
idle window; the code payload benefit cannot be measured in production until
the repository slice is reviewed, merged, and deployed.

Rollback:

```text
az webapp config set --resource-group peerslate --name peerslate-pete --always-on false --http20-enabled false
```

## Public text transfer

| Route | Raw HTML | Gzip HTML | HTML reduction | Raw HTML + direct CSS/JS | Gzip HTML + direct CSS/JS | Text reduction |
|---|---:|---:|---:|---:|---:|---:|
| `/` | 73,446 B | 14,481 B | 80.3% | 609,761 B | 132,348 B | 78.3% |
| `/petec/resume` | 170,103 B | 24,493 B | 85.6% | 973,760 B | 190,020 B | 80.5% |

The shared `style.css` response changes from 382,386 bytes to 81,119 bytes
under gzip. Every compressed response was decompressed in tests and compared
byte-for-byte with its identity response.

## Direct-reference payload model

This comparison includes both the new text compression and the selected
smaller media derivatives.

| Route | Baseline modeled transfer | Optimized modeled transfer | Bytes avoided | Reduction |
|---|---:|---:|---:|---:|
| `/` | 3,537,327 B | 1,488,792 B | 2,048,535 B | 57.9% |
| `/petec/resume` | 9,530,360 B | 1,178,773 B | 8,351,587 B | 87.6% |

As a transfer-time budget, not an elapsed-time promise:

| Route | At 10 Mbit/s | At 25 Mbit/s |
|---|---:|---:|
| `/` | about 1.64 seconds avoided | about 0.66 seconds avoided |
| `/petec/resume` | about 6.68 seconds avoided | about 2.67 seconds avoided |

These estimates divide bytes avoided by link throughput. Browser scheduling,
latency, server time, connection reuse, lazy loading, and cached assets remain
separate. On repeat navigation, exact content-versioned assets can be served
from the browser's immutable cache, which also avoids revalidation requests;
that latency benefit depends on the visitor's network round-trip time and
therefore is not assigned a universal number here.

## Media byte reductions

| Public use | Previous asset | Selected derivative | Reduction |
|---|---:|---:|---:|
| Shared circuit texture | 1,287,514 B | 61,948 B | 95.2% |
| Future-path landscape | 428,723 B | 235,470 B | 45.1% |
| Sunset landscape | 470,998 B | 95,432 B | 79.7% |
| Team demonstration | 2,048,252 B | 45,212 B | 97.8% |
| Coffee and notes | 2,771,490 B | 95,880 B | 96.5% |
| Profile portrait | 412,611 B | 66,857 B | 83.8% |
| Maui portrait | 339,210 B | 70,198 B | 79.3% |
| Hawaii portrait | 680,355 B | 133,263 B | 80.4% |

New derivative identities:

| Path | Bytes | SHA-256 |
|---|---:|---|
| `static/images/circuit-banner-option-2.webp` | 61,948 | `f4d2e4bfda829071f9eb2295df85caac148c4810c04cf4b0245a33e4b799e29b` |
| `static/images/cinematic/future-path-1600.webp` | 235,470 | `ead38d364ac00bddc9d689f011eba06dae9ac3f057c6ef127a49a82873b5228c` |
| `static/images/cinematic/story-sunset-bg-1600.webp` | 95,432 | `299162d8c8faa1d1e9d80ad2fc6d80fa4ef171abd0597bf8c1f70452be129e7f` |

The circuit derivative retains the original 1916 x 821 dimensions. Its
full-image comparison against the PNG produced PSNR 41.35 dB and a mean
absolute channel difference of approximately 1. The two cinematic derivatives
retain the original 16:9 landscape composition at 1600 x 900.

## Server cost and consequence evidence

Fifty warm in-process requests per route:

| Route | Identity mean | Gzip mean | Mean gzip overhead |
|---|---:|---:|---:|
| `/` | 2.846 ms | 3.959 ms | 1.114 ms |
| `/petec/resume` | 4.246 ms | 6.101 ms | 1.855 ms |

The first gzip of `style.css` in a fresh worker took 39.054 ms. The
per-worker compressed-byte cache reduced the next 100 requests to a mean of
0.835 ms and a median of 0.815 ms. The cache keeps one compressed byte string
per containment-safe canonical CSS/JavaScript path and replaces it when the
content token changes.

Consequences retained for release review:

- dynamic public HTML uses approximately 1-2 ms of additional warm server CPU
  in this local measurement;
- the first immutable CSS/JavaScript gzip in each new worker has a one-time
  compression cost and a small per-worker memory cost;
- canonical-equivalent static paths resolve to one bounded cache key rather
  than creating attacker-controlled duplicate entries;
- WebP derivatives are intentionally lossy, so visual equivalence evidence is
  required;
- incorrect long-lived caching would be high impact, so one-year immutable
  caching is granted only when the requested token equals the file's current
  content hash;
- private, `no-store`, partial/range, streamed, already encoded, small,
  non-GET, gzip-rejecting, cookie-setting, and session-cookie responses are
  excluded; and
- the implementation uses Python's standard library and introduces no package,
  database, identity, secret, migration, or external-service dependency.

## Visual equivalence

Authority: the exact `origin/main` rendering at the base SHA above. The task
does not authorize a material visual change.

Captured route: `/petec/resume`.

| State | Baseline | Optimized | Result |
|---|---|---|---|
| Desktop, 1425 x 1000 captured content | `resume-baseline-1440.png` | `resume-optimized-1440.png` | Pass |
| Mobile, 375 x 844 captured content | `resume-baseline-390.png` | `resume-optimized-390.png` | Pass |

Screenshot identities:

| File | SHA-256 |
|---|---|
| `resume-baseline-1440.png` | `2e8c3cd68dd61011d600dcb8262fbfe8e82e60470c7e6861db8bee05c9cf7586` |
| `resume-optimized-1440.png` | `023728b4c85abe37f2c40b761cda884d58ace03809f9e50d34924fb9dd169468` |
| `resume-baseline-390.png` | `38b8b7317bdbef5ae885e9dd1b7f32122454ff6f015b41b14c7ffc632dcfd650` |
| `resume-optimized-390.png` | `dd1e2434c7d5ee5a0a4394d673c446869dd1d606db30fa1735b0cef947fdcaae` |

The compare-refine loop had one correction. The first future-path candidate was
a portrait crop and visibly removed the person from the wide composition. It
was rejected and replaced with a 1600 x 900 derivative of the exact released
landscape source. The corrected desktop and mobile comparisons have identical
layout geometry, content, viewport width, and overflow behavior. The final
mismatch register is empty; the remaining pixel differences are the intended
WebP encoding differences:

- desktop mean absolute RGB channel difference: 0.420, 0.398, 0.435;
- desktop pixels with maximum channel difference greater than 8: 1.146%;
- mobile mean absolute RGB channel difference: 0.458, 0.416, 0.481; and
- mobile pixels with maximum channel difference greater than 8: 1.036%.

## Automated verification

- Focused response/cache tests: 41 passed.
- HTTP edge, operational readiness, and résumé tests: 88 passed.
- Intended-output fixture corrections: 8 passed.
- Full repository suite: 1,099 passed, 0 failed, 0 errors, 3 skipped.
- `git diff --check`: passed.

The full suite used a process-local non-secret `ANTHROPIC_API_KEY` placeholder,
as permitted by the repository test instructions. The existing Flask-Limiter
warning about in-memory test storage remained unchanged.

## Evidence boundary

The Azure configuration, gzip, content-versioning, cache-policy, and media
changes are live and verified. Exact source
`39bd6d031132375394eb2168c45d47f166efc991` passed fresh independent review
and package/branch/full-SHA Candidate run 297 before Azure PR 203
squash-merged it as `0eed47e7201a40fcd7858ca3040712ed2f2dd8f2`.
Production pipeline 299 passed for that merge.

At closeout, later authorized Azure `main`
`24bfeedc9f3b2b3a5f9acddda1dc4ac285bed21d` retained the performance merge
as an ancestor and production pipeline 300 passed. Live `/healthz` reported
release `108922ac4dc8abbabe8916ea`. The homepage transferred 72,500 bytes as
identity HTML or 13,797 bytes with gzip (81.0% smaller); the exact current
stylesheet transferred 382,386 bytes or 81,119 bytes with gzip (78.8%
smaller) and retained immutable caching. Live desktop and mobile résumé checks
found no broken images or horizontal overflow. The temporary Candidate app and
plan were deleted only after production and live verification.

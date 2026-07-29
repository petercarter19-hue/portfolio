# PS-PERFORMANCE-FOUNDATION-001 — Public delivery performance foundation

## Status and authority

- **Owner:** Pete
- **Owner decision:** On 2026-07-29 Pete asked for the consequences, likely
  time savings, and paid options for making the live site faster, then
  explicitly directed: **“Do it.”**
- **State:** Implementation and writer verification complete; exact-SHA
  independent re-review and Candidate remain release gates
- **Designated manager and sole writer:** current Codex task
- **Authoritative base:** Azure `origin/main`
  `06559478e2f9429e47bca0d67858131ef9429bd0`
- **Branch:** `work/2026-07-29-performance-foundation-001`
- **Roadmap allocation:** Phase 2 delivery safety, Phase 3 query/performance
  baseline, and Phase 12 reliability/capacity foundation
- **Visual authority:** current released production rendering; this package
  changes delivery bytes and cache URLs only and may not change visible
  composition, content, imagery, layout, interaction, or product behavior
- **Independent review:** the assigned fresh reviewer rejected the first
  implementation, and the writer corrected both findings; the exact corrected
  PR source remains subject to the reviewer's pass before Candidate
- **Release status:** the reversible Azure configuration slice is live; the
  repository slice is not merged, deployed, or live
- **Evidence:** [2026-07-29 performance evidence](evidence/PERFORMANCE_EVIDENCE_2026-07-29.md)

## Owner exception and checkpoint boundary

`PS-AI-OPS-CHECKPOINT-001` currently holds unrelated runtime work while three
corrective packages remain open. Pete's 2026-07-29 instruction is recorded as a
narrow owner exception for public delivery performance only. It does not reset
or close that checkpoint, authorize another feature lane, or change the status
of any checkpoint finding.

This package may:

- configure production App Service Always On and HTTP/2;
- add dependency-free public text-response compression;
- give public static assets content-versioned cache URLs and bounded fallback
  caching;
- add focused performance, cache, privacy, and regression tests; and
- record measurements, rollback, and release evidence.

It may not change feature behavior, routes, navigation, page content, visual
direction, identity, authorization, private retrieval, AI, database schema,
member data, publication, deployment admission controls, or another active
writer's files.

`PS-OPS-CANDIDATE-ADMISSION-001` correction 2 is merged on Azure `main` at
`b0b5ea780918089f24ba2304c0aab4d2e6f643b1`. Candidate now requires a
non-empty package, the exact queued source branch, and the exact full source
SHA, and repeats those equality checks at deploy, smoke, and stop. The
empty-by-default queue variables live only in Azure pipeline metadata so YAML
cannot shadow an explicitly reviewed tuple.
This runtime branch may not enter Candidate until its exact corrected source
commit passes independent review, and it may not merge unless that same commit
passes the real Candidate run.

## Problem and baseline

The live site is responsive after it is warm, but the owner experiences slow
first loads and slow page-to-page movement. The verified contributing factors
are:

- production App Service had `alwaysOn=false`, allowing an idle worker to be
  unloaded;
- production had `http20Enabled=false`, so the browser could not multiplex the
  site's many first-party asset requests over HTTP/2;
- public HTML, CSS, and JavaScript responses were not compressed;
- the current public Living Résumé HTML is about 170 KB before its assets;
- representative first-party public text assets total about 974 KB raw and
  about 190 KB under gzip; and
- images and other public static files were not content-versioned by the shared
  URL helper, so they revalidated or reloaded more often than necessary.

The exact live release before the Azure setting change was
`4b2c46e824613c1b7c844884`.

## Requirements

- **PS-PERF-OPS-001:** Production shall keep the application worker warm with
  App Service Always On and shall enable HTTP/2 without changing the deployed
  release identity.
- **PS-PERF-COMP-001:** Eligible public HTML and exact-version public CSS/JS
  responses shall use gzip when the client accepts it, shall set
  `Vary: Accept-Encoding`, and shall decompress byte-for-byte to the identity
  response.
- **PS-PERF-COMP-002:** Compression shall not apply to private/no-store
  responses, range or partial responses, non-GET requests, already encoded
  responses, small responses, or clients that reject gzip.
- **PS-PERF-COMP-003:** Representative public HTML and primary CSS shall be at
  least 65 percent smaller over the wire under gzip.
- **PS-PERF-CACHE-001:** Shared template-generated public static URLs for
  supported CSS, JavaScript, image, font, icon, and document types shall carry
  a 12-hex content token.
- **PS-PERF-CACHE-002:** Only a token matching the exact current bytes may earn
  one-year immutable caching. Unversioned or stale-token public static assets
  shall receive only a bounded one-hour cache with stale-while-revalidate.
- **PS-PERF-TRUTH-001:** The package shall make no visible or behavioral product
  change and shall preserve all private response and authorization boundaries.
- **PS-PERF-REL-001:** Evidence shall distinguish Azure configuration, branch
  implementation, merge, deployment, and live production. Rollback shall be
  explicit for both configuration and code.

## Architecture

Use Python's standard-library gzip implementation inside the existing Flask
response pipeline. Do not restore `Flask-Compress`: an earlier production
attempt with that dependency failed on Azure's Python 3.14 runtime because its
Zstandard import was unavailable.

Compression is deliberately narrow:

- public HTML after the final cache/privacy policy is known;
- CSS and JavaScript only when the request carries the exact live content
  token and therefore receives immutable caching;
- no private or `no-store` payload;
- no range, streaming API, file upload/download transform, or provider
  response; and
- a per-worker cache for compressed immutable static bytes so steady-state
  requests do not repeat compression work.

Content hashing extends the existing shared static-URL system. A content change
therefore creates a new URL. URLs without the exact token remain recoverable
and short-lived rather than being pinned for a year.

## Azure configuration slice

Before:

- `alwaysOn=false`
- `http20Enabled=false`
- release `4b2c46e824613c1b7c844884`

Applied on 2026-07-29:

```text
az webapp config set --resource-group peerslate --name peerslate-pete \
  --always-on true --http20-enabled true
```

Verified after the App Service restart:

- `alwaysOn=true`
- `http20Enabled=true`
- `/healthz` returned `status=ok`
- release remained `4b2c46e824613c1b7c844884`

This was a bounded owner-approved production-configuration exception. The
compensating controls were exact before/after configuration reads, immediate
member-data-free health verification, unchanged release identity, public-route
timing probes, and a one-command rollback.

Rollback:

```text
az webapp config set --resource-group peerslate --name peerslate-pete \
  --always-on false --http20-enabled false
```

## Verification plan

- focused response-compression and static-version/cache tests;
- existing HTTP edge/security and operational-readiness suites;
- full repository test suite with a process-local non-secret API placeholder;
- exact response-header and byte-for-byte decompression checks;
- before/after payload measurements for `/` and `/petec/resume`;
- visual equivalence of representative desktop and mobile routes because the
  rendered content and asset bytes are intended to remain unchanged;
- complete-diff self-review; and
- fresh exact-SHA shared-infrastructure review before merge.

## Success, risk, and rollback

Success means idle-start exposure is reduced by Always On, compatible browsers
can use HTTP/2, representative public text transfer is reduced by at least 65
percent, repeated asset navigation uses correct long-lived caching, and all
truth/privacy/regression checks pass.

Risks are bounded CPU/memory use from compression, stale-cache mistakes,
incorrect content negotiation, and accidental compression of private payloads.
Controls are a minimum body size, immutable-static compressed-byte cache,
containment-safe canonical cache keys, content-token validation, `Vary`,
session-interface cookie detection, strict exclusions, and focused negative
tests.

Code rollback is the normal Azure rollback to the last verified production
artifact. Configuration rollback is the exact `az webapp config set` command
above. No database, identity, data, feature flag, or migration rollback is
required.

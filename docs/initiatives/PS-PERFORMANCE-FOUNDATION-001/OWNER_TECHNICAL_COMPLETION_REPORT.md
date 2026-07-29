# PeerSlate Completion & Handoff Report

## A. Status

- Package: `PS-PERFORMANCE-FOUNDATION-001`
- Status: In Progress — corrected implementation and writer verification
  complete; exact-SHA independent re-review, Candidate, merge, deployment, and
  live code verification remain open
- Branch and corrected runtime commit:
  `work/2026-07-29-performance-foundation-001` at
  `93b1ec8e90c51e0e0a9fc0991a956959d49f7efd`
- Authoritative base: Azure `origin/main`
  `06559478e2f9429e47bca0d67858131ef9429bd0`
- PR / pipeline / environment: draft Azure PR 203; no Candidate or production
  code pipeline yet; App Service configuration changed directly under the
  narrow owner-approved exception
- Production state: Always On and HTTP/2 are enabled and live; repository code
  remains unmerged, undeployed, and not live; production release remains
  `4b2c46e824613c1b7c844884`
- Visual authority and status: current released production rendering; Agent
  Review Passed for the allowed non-material media encoding adaptations
- Visual inspector: assigned writer
- Approved-mockup fidelity evidence: Not Applicable — no mockup or visual
  direction was created or revised
- Agent-run compare-refine pass count by state/viewport and visual mismatch
  register: desktop 2 passes; mobile 1 final pass after the desktop correction;
  mismatch register empty
- Pete-run inspection record: Not Applicable — Pete did not personally inspect
  the branch renders in this task
- Homepage product projection: Current — no function, truth label, hierarchy,
  theme, responsive behavior, or product promise changed
- Pete / designated session manager visual acceptance: technical comparison
  evidence complete; Pete's release acceptance not yet requested
- Designated session manager: current Codex task
- Manager handoff status and next receiver: first independent review failed;
  both findings are corrected and ready for the assigned fresh reviewer to
  re-check on the exact final PR source
- Lane owner and self-managed authority: current Codex task under Pete's
  2026-07-29 “Do it” performance-only exception
- Self-certification: Conditional — corrected writer scope is complete and
  passes, but independent re-review and release controls remain open
- Complete-diff review: Issues corrected — an incorrect portrait crop was
  rejected, released workspace golden fixtures were recaptured for intentional
  image tokens, and responsive-media assertions were made token-aware
- Acceptance requested: exact-SHA independent re-review; Candidate only after
  that pass

## B. What changed technically

### Production configuration

The production App Service `peerslate-pete` now has:

- `alwaysOn=true`, preventing the Basic B1 worker from being unloaded after an
  idle period; and
- `http20Enabled=true`, allowing compatible clients and the Azure edge to use
  HTTP/2.

The change restarted the App Service. Immediate member-data-free health
verification passed, and the release ID stayed unchanged. The exact rollback
is:

```text
az webapp config set --resource-group peerslate --name peerslate-pete --always-on false --http20-enabled false
```

### Application delivery

`app.py` adds a dependency-free gzip response stage using Python's standard
library. It compresses:

- public HTML of at least 1 KiB when the GET client accepts gzip; and
- CSS/JavaScript only when the URL contains the exact current content token.

It does not compress private, `no-store`, `no-transform`, partial/range,
streamed, already encoded, small, non-GET, gzip-rejecting, or cookie-setting
responses. It sets `Vary: Accept-Encoding`, removes identity-representation
validators after encoding, and caches compressed immutable static bytes once
per worker. Canonical-equivalent static route aliases share one
containment-safe cache key, and the response stage asks Flask's session
interface whether it will add a cookie before allowing compression.

The existing shared static URL versioner now covers CSS, JavaScript, images,
icons, fonts, and public PDF documents. A token that exactly matches current
file bytes receives one-year immutable caching. Stale, wrong, or missing
tokens receive only one hour with `stale-while-revalidate`, preventing an old
asset from being pinned for a year.

The implementation deliberately does not add `Flask-Compress` or any other
runtime package.

### Media

The released composition is preserved while the public résumé selects smaller
existing derivatives and three verified new WebP derivatives:

- the shared circuit texture;
- the 16:9 future-path landscape; and
- the 16:9 sunset landscape.

The first future-path candidate used a portrait crop and failed visual parity.
It was removed from the implementation and replaced with a derivative of the
exact released landscape source.

### Files

- `app.py` — gzip negotiation, strict exclusions, static content tokens,
  immutable caching, and bounded fallback caching
- `static/data/resume_data.json` — selects smaller media derivatives without
  changing content or truth labels
- `templates/base.html` — selects the verified circuit WebP
- `templates/the_slate_people_interests.html` — removes two obsolete manual
  query tokens so the shared content hash is the only version authority
- `static/images/circuit-banner-option-2.webp` — new verified derivative
- `static/images/cinematic/future-path-1600.webp` — new verified landscape
  derivative
- `static/images/cinematic/story-sunset-bg-1600.webp` — new verified landscape
  derivative
- `tests/test_http_edge_security.py` — compression, cache, version, private,
  range, and negotiation coverage
- `tests/test_resume2.py` — selected-media and derivative-size coverage
- `tests/test_community_tabs.py` — responsive-media contract remains exact
  while accepting content tokens
- `tests/test_owner_home.py` — recaptured intentional private workspace golden
  output after image/document URL tokens
- package README, measurement evidence, and desktop/mobile comparison renders

There are no route, database, migration, data model, identity, authorization,
secret, provider, AI, feature-flag, or external-service changes.

## C. What this means in plain English

The production server is now less likely to “go to sleep,” and it is allowed
to use a newer web transport protocol. The prepared code also sends public
page text in a much smaller form, uses smaller copies of large images, and
lets the browser safely keep unchanged files instead of checking or
downloading them again while moving between pages.

The tradeoff is small: compressing public HTML used about 1-2 additional
milliseconds of warm local server time, each new worker compresses a large
stylesheet once, and WebP images are lossy. The implementation contains those
costs with a compressed-byte cache and visual comparisons.

## D. What the website or member can do now

Live now:

- production keeps the App Service worker warm with Always On;
- production is configured for HTTP/2; and
- the exact deployed application release and member behavior are unchanged.

Available only on the task branch:

- browsers that accept gzip receive public HTML/CSS/JavaScript at roughly
  one-fifth of the prior text size;
- public static assets receive safe content-versioned cache URLs;
- the homepage's directly referenced modeled payload is 57.9% smaller; and
- the public résumé's directly referenced modeled payload is 87.6% smaller.

Members do not receive the branch behavior until review, merge, deployment,
and live verification are complete.

## E. How this connects to PeerSlate

This is delivery foundation work in the Roadmap's delivery-safety,
performance-baseline, and reliability/capacity lanes. It does not change the
Bible's work-first product direction, the canonical Capture-to-Moment model,
Journal, Studio, public publication, or any member workflow.

The private/public boundary remains explicit. Only public HTML and exact public
static text assets are compressed; private/no-store responses remain
untransformed. AI still proposes and people decide. No canonical truth,
projection, ownership, publication, or authorization contract changes.

## F. Verification and validation

### Automated

- Focused response/cache suite: 41 passed.
- HTTP edge, operational readiness, and résumé group: 88 passed.
- Intended-output fixture correction set: 8 passed.
- Full repository discovery: 1,099 passed, 0 failures, 0 errors, 3 skipped.
- Python compile check: passed.
- Installed dependency check: passed.
- `git diff --check`: passed before commit.

The full suite used a process-local non-secret `ANTHROPIC_API_KEY`
placeholder. The existing Flask-Limiter warning about in-memory test storage
was unchanged.

### Security and privacy

Tests prove:

- compressed bytes round-trip exactly to the identity representation;
- `Vary: Accept-Encoding` is present on eligible representations;
- private `/app` remains `private, no-store` and uncompressed;
- helper-level private/no-store responses remain uncompressed;
- range requests remain 206, byte-bounded, and uncompressed;
- health, small, non-GET, and gzip-rejecting responses remain uncompressed;
- only the exact current static token earns immutable caching;
- canonical-equivalent static aliases share one version and gzip cache entry;
- path traversal is rejected before a static file can become a cache key;
- a response for which Flask will save a session cookie remains uncompressed;
  and
- templates do not append a second hand-written token to `url_for` output.

### Performance

Local evidence records:

- `/` HTML: 73,446 bytes to 14,481 bytes under gzip;
- `/petec/resume` HTML: 170,103 bytes to 24,493 bytes under gzip;
- directly referenced homepage model: 3,537,327 bytes to 1,488,792 bytes;
- directly referenced résumé model: 9,530,360 bytes to 1,178,773 bytes;
- warm gzip overhead: 1.114 ms for `/` and 1.855 ms for the résumé; and
- first `style.css` gzip: 39.054 ms, followed by 0.835 ms mean from the
  per-worker cache.

The full method and evidence limits are in
[`evidence/PERFORMANCE_EVIDENCE_2026-07-29.md`](evidence/PERFORMANCE_EVIDENCE_2026-07-29.md).

### Visual

The released base SHA and optimized branch were rendered at desktop and mobile
sizes. Layout geometry, content, viewport width, and overflow behavior matched.
The only remaining pixel differences are the intended WebP encoding
differences. The final mismatch register is empty.

Evidence:

- `evidence/resume-baseline-1440.png`
- `evidence/resume-optimized-1440.png`
- `evidence/resume-baseline-390.png`
- `evidence/resume-optimized-390.png`

### Production

At `2026-07-29T13:02:14.9969921Z`:

- App Service state was `Running`;
- Always On was `true`;
- HTTP/2 was `true`;
- `/healthz` returned `ok`; and
- release remained `4b2c46e824613c1b7c844884`.

There is no production evidence for repository compression, versioning,
caching, or media savings because that code is not deployed.

## G. Known gaps, risks, and exclusions

- The fresh independent reviewer rejected the original implementation
  `816cdc225e788a67983ff15dd3017145d73bc98a` because raw route aliases could
  amplify the per-worker caches and Flask could add a session cookie after the
  compression decision. Both blockers are corrected in
  `93b1ec8e90c51e0e0a9fc0991a956959d49f7efd`; the exact final PR source still
  requires the reviewer's re-check.
- Candidate admission correction 1 merged through independently passed Azure
  PR 204. Real run 288 then proved YAML defaults shadowed the accepted queue
  tuple, so Candidate correctly did not pass. Correction 2 removed that
  shadowing through independently passed Azure PR 205 and squash-merged to
  `main` as `b0b5ea780918089f24ba2304c0aab4d2e6f643b1`. The real queue-time path
  remains to be re-exercised for this package.
- No Candidate run, merge, production code deployment, or live browser network
  waterfall has occurred for the performance source.
- Always On reduces idle-worker unload exposure but does not remove every
  source of cold or dependency latency.
- HTTP/2 is verified as App Service configuration; the local curl build did
  not provide protocol-negotiation evidence.
- Direct-reference payload numbers are a controlled transfer model, not a
  promise for every browser, viewport, cache state, or network.
- Visual comparison covers the representative public résumé desktop/mobile
  states. There is no material product or visual authority change.
- Pete has not personally accepted the branch render or release.

## H. Clear next step

Have the assigned fresh independent shared-infrastructure reviewer inspect the
exact final source commit recorded by Azure PR 203. After that exact SHA
passes, queue Candidate with package `PS-PERFORMANCE-FOUNDATION-001`, the exact
source branch, and the exact full source SHA. Only if Candidate passes may PR
203 become active, squash-merge, deploy, and proceed to exact-release live
verification.

That sequence unlocks the code savings without bypassing the active
checkpoint. The live Always On and HTTP/2 settings can remain in place while
review proceeds.

## I. What Pete needs to do or decide

No further owner decision is required for the already authorized sequence.
Keep the verified Always On and HTTP/2 settings enabled; stop if independent
review or Candidate does not pass.

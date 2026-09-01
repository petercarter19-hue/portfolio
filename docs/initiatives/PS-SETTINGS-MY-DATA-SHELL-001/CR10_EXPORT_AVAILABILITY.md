# CR10 export availability protection

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-AVAILABILITY-001`
**Slice:** Follow-up to C3, second of its two recorded gaps.
**Status:** Implemented. Availability only; no authorization, template,
flag, schema, worker, or deployment change.

## Decision

The three export routes had no per-client budget, and the download proxy
buffers a whole verified archive — up to the C0 100 MiB compressed cap —
in application memory per request. Worse, that cap was checked only
*after* `read_final` had already downloaded every byte, so it bounded
nothing: an oversized or swapped object cost the full allocation before
being rejected.

Two changes, both server-side:

1. **Budgets.** `ACCOUNT_EXPORT_PLANNED_RATE_LIMITS` in `owner_routes.py`
   declares per-client limits for exactly the three export endpoints —
   request POST 10/hour, request-page GET 60/minute, status GET
   60/minute, download 30/hour — and `app.py` applies them after blueprint
   registration through the existing post-registration limiter idiom
   (the `ask_pete_direct_routes` / `opportunity_slate_v2_routes`
   precedent), reading the mapping rather than restating it. Entries are
   bare specs -- the house form, which binds every method the route
   serves, HEAD included -- except on the request route, whose one view
   serves POST and GET/HEAD with different budgets and therefore carries
   `(spec, methods)` pairs. HEAD matters: Flask dispatches HEAD to the
   same view at full cost and strips the body only afterwards, so the
   first candidate's `methods=("GET",)` pair on the download proxy let
   HEAD run the whole buffered read unbudgeted (independent review
   HIGH 1, fixed by the bare-spec form and pinned by a HEAD-burn test).
2. **Pre-read cap.** `read_final` now refuses from the provider-reported
   blob size, before `download_blob()` is called: over the compressed cap
   is `oversize_compressed`, and disagreement with the ledger's expected
   size is `storage_size_mismatch` — both existing stable codes. The
   reported size comes from the provider, so every post-read verification
   (actual length, cap, ledger size, mandatory SHA-256) still runs on the
   real bytes, unchanged. Belt and braces.

## Why this survives the trust rules

- Authorization is untouched. Ownership is still proved in SQL on every
  status and download read; the limiter runs before any of that and knows
  nothing about jobs. A 429 is keyed on the caller, never the job key, so
  being refused reveals nothing about whether a job exists or whose it is.
- SQL's one-job-per-24-hours rule (`usp_RequestAccountExportJob`) remains
  the real request ceiling. The POST budget bounds only the *cost* of
  rejected attempts — every refused POST still buys an identity lookup
  and a database round trip.
- The pre-read refusal can only ever be stricter than the post-read
  checks it precedes, and it reuses their exact error codes, so no caller
  can distinguish where the refusal happened.

## Guards

- Coverage: the mapping must cover exactly the export endpoints that
  exist on the app — an export route added without a budget, or a mapped
  budget whose endpoint disappears, fails the suite. Every method that
  does work must be budget-bound: only OPTIONS (answered before any view
  runs) is exempt, HEAD is not, and a live test proves 30 HEADs on the
  download route burn the budget and the 31st request is refused
  whichever verb carries it.
- Wiring: every mapped endpoint's registered view function must actually
  be wrapped by the limiter, and `app.py` must read the mapping rather
  than restate the budgets.
- Refusal contract: the 429 body is the app's static content-free
  sentence, identical across job keys, with a Retry-After header.
- Pre-read: a provider-reported oversize and a reported/ledger size
  mismatch are each proven to refuse with the stable code and **zero**
  `download_blob` calls; the matching-facts path still downloads and
  verifies.

## Honest notes

- **The download budget is 30/hour, not the first-scouted 6/hour, and
  the independent review ruled that 30/hour stands.** The scouting draft
  said 6/hour. Implementing that number turned the closed
  export-experience package's own test file red before any push: one
  process run of `tests/test_account_export_experience.py` legitimately
  makes 11 download-route requests (mostly flag-off and negative-path
  probes, which the limiter deliberately counts). That file was editable
  in principle — a closed package releases its surfaces, and the
  governed extend-surfaces transition was available — but editing it was
  not chosen, because re-choreographing a closed package's recorded
  green suite would mutate what its review receipt attests. The review's
  ruling, recorded here in substance: a per-address fixed-window limit
  cannot be the instance-survival control against a hostile client at
  either number — address rotation defeats 6/hour and 30/hour alike, and
  the real teeth are the 100 MiB per-request cap and platform capacity —
  while 6/hour plausibly refuses real member behaviour (interrupted
  downloads, multi-device retries). Conditions of the ruling, both met:
  the budget binds every verb that does work (the HEAD fix above), and
  the burst truth is disclosed (below).
- **The window is fixed, not sliding, so 30/hour is also 30-at-once.**
  A rate like "~3 GiB/hour" understates the real risk shape: the full 30
  requests may arrive back-to-back inside one window (probed in review:
  30 consecutive 200s), so the peak is up to ~2.93 GiB of CONCURRENT
  archive buffering per client address (30 × 100 MiB) — the number that
  decides instance survival — before the 31st request is refused.
- **429 body is JSON on HTML page routes.** The app-wide errorhandler
  answers every rate-limited route with one static JSON sentence. These
  three routes render HTML, so a browser that trips a budget sees JSON.
  Accepted: what matters is that the answer is content-free and uniform;
  matching the body type to the route is cosmetic and not worth a second
  429 contract.
- **Keying is by IP for these routes, for now.** `_client_rate_limit_key`
  resolves member identity only where a request already carries it;
  identity for the export routes resolves inside the view, after the
  limiter has run, so these budgets key on the forwarded client address.
  Accepted for v1: the budgets are far above any one person's legitimate
  use, so members behind one shared address are very unlikely to starve
  each other. **Future refinement (recorded, not promised):** key the
  export budgets on the member once a request-scoped principal is
  available before the limiter for this surface — the same evolution the
  interview API already made — rather than by touching
  `_client_rate_limit_key`'s interview-scoped fallback.
- The in-memory limiter storage note in `app.py` applies here unchanged:
  per-instance counting until Redis-backed storage is configured.

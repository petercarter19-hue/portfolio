# 12 — Observability and cost

Content-free by construction. The binding repository patterns: the
`PS-INTERVIEW-AI-EXTRACT-001` dark-telemetry convention (additive telemetry
landed dark, closed reason enums, purge with proof, no runtime change until
its own release step) and the `PS-SEARCH-DARK-PROOF-001` census/ceiling
discipline (record shape and counts; retain no query text, token, URL,
resource ID, or response body).

## 1. Event families (all content-free)

| Family | Events | Payload (keys/enums/counts/durations only) |
|---|---|---|
| Ingestion | receipt_received, admission_passed, quarantined(reason), version_created, dedupe_linked/queued, merge/split | PeerSlate-internal opaque keys (`receipt_key`, `listing_key`), policy class, byte counts, timing, reason enums. **Source-derived fields (content hashes, provider-assigned identifiers/external refs, provenance details) appear only where the applicable `source_policy`/rights permit**; otherwise events carry content-free internal attempt/outcome counts and opaque internal action IDs only |
| Lifecycle | state transitions (doc 03 §1) incl. closure/outage/stale/invalid with reason | listing_key, from/to, reason |
| Verification | attempt_started/succeeded/failed(reason), link_validation outcome | listing_key, duration, reason — success alone updates the success timestamp |
| Search | interpret requested/succeeded/unavailable, clarification offered/answered/dismissed, apply, execution stage transitions, coverage(full/reduced+check enums), completeness(complete/partial+reason enum, doc 04 §11), cancelled, fence_dropped(count) | draft/snapshot/execution keys, stage durations, counts; **never request text or criteria values** |
| Qualification | assessment computed/recomputed(cause enum), state distribution counts, review_unavailable(reason) | requirement_version_key, counts per state; **never requirement text, evidence identity, or content** |
| Member actions | save/remove/undo, grant created/revoked, slate create/continue, import pipeline outcome (**non-identifying host/address class + reason code only** — one rule with doc 08 §4) | keys + reason enums (doc 08 §4 audit events) |
| Degraded modes | ai_unavailable window, index_unavailable window, evidence_port_unavailable, provider outage per source | source/component id, start/end, affected-request counts |

## 2. Measures (derived, reportable without content)

- **Freshness**: distribution of `now − last_successfully_verified_at` per
  source class; % listings inside the freshness threshold.
- **Coverage**: current-eligible opportunity count per source; gate-ineligible
  breakdown by reason; reduced-coverage execution rate and which checks.
- **Qualification health**: assessment state distribution over time;
  recompute causes (new version vs revocation vs correction);
  `Review unavailable` rate by reason (an outage-quality signal, never a
  member metric).
- **Dedupe quality**: auto-link rate, queue depth, merge-reversal count.
- **Search**: execution duration by stage, cancellation rate, degraded-path
  rate, fence-drop count (should be ~0; alerting signal).
- **Cost drivers**: provider API call counts, AI interpretation/assessment
  call counts and token-bucket consumption, index query counts, fetch counts —
  against explicit budgets.

## 3. Budgets and ceilings

Pre-dispatch ceilings persisted across invocations (Search 3F pattern):
per-member (doc 04 §5), per-source refresh budgets, AI daily budgets,
index-query budgets, import fetch budgets. Budget exhaustion is a truthful
degraded state (named in disclosures) and an operational alert — never a
silent quality drop. Exact budget values are C9 operational decisions with
cost evidence; the enforcement points are fixed here.

## 4. Provider outage diagnostics

Per-source rolling health (attempt/success counts, last errors as enums,
backoff state) drives: the could-not-reverify member truth, ingestion
backoff, and operator diagnosis — distinguishable from closure signals by
construction (separate events).

## 5. Exclusions (hard)

No member request text, criteria values, evidence content or identifiers,
requirement text, imported content, member-identifying keys joined with
content, or AI prompt/response bodies in any log, metric, trace, or event.
For member imports: only a non-identifying host/address class and reason
code — never the exact URL, hostname, path, query, body, **or any content
hash of member-supplied material** (which could identify it); exact
provenance exists only inside the authorized `member_import` record.
**Source-derived telemetry fields are never categorical:** provider-receipt
hashes, provider-assigned identifiers, and provenance details appear in any
event, metric, or trace only where the applicable `source_policy`/rights
permit (docs 02 §4, 05 §8); otherwise telemetry uses content-free internal
counts, opaque internal action IDs, policy class, timing, and reason enums.
Provider-exit obligations extend to telemetry: on termination, retained
source-derived telemetry fields are purged or aggregated per the exit
rights, while PeerSlate-internal counts remain — part of C11's
termination/exit proof. Fixture-class events are labeled
`data_class: fixture` and excluded from production measures. `/healthz`
gains nothing from this package.

## 6. Where it lands

Telemetry storage/transport follows the interview-telemetry precedent
(additive, dark-first, purge script with closed reasons, disposable SQL
proof) — concrete schema/pipeline is C9's (and per-child dark slices')
implementation under these contracts. No Application Insights or Azure
configuration is created or assumed by P0.

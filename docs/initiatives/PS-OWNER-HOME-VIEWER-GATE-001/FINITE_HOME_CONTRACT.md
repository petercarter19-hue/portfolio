# PS-OWNER-HOME-VIEWER-GATE-001 Finite Home Contract

## Product contract

Owner Home is a finite, decision-oriented start page for the signed-in member. It is not a Feed, dashboard of vanity metrics, notification dump, simulated community, or second copy of the member's canonical records. It helps the owner capture something, finish a small amount of review, return to meaningful Moments, understand at most one supported insight, handle at most one authorized connection item, and take one next step.

The dominant owner action is **Capture**. It must be unmistakable without forcing the rest of Home above the fold. Text Capture is the currently accepted real entry path. Voice must not be promoted by this package while the Voice correction lane remains active.

## Hard content budget

One response and one rendered Home may contain no more than these nine product objects:

| Priority | Category | Maximum | Eligibility |
|---|---|---:|---|
| 1 | Capture action | 1 | Always present when the owner session is valid and Capture is available |
| 2 | Items requiring review | 3 | Real owner-owned, actionable, non-deleted records only |
| 3 | Recent Moment | 1 | Most recently confirmed eligible Moment not already represented in review |
| 4 | Resurfaced Moment | 1 | One confirmed eligible Moment selected by an approved deterministic resurfacing policy; never random filler |
| 5 | What PeerSlate noticed | 1 | Only a stored, governed insight with inspectable supporting evidence, current status, and owner control |
| 6 | Relevant connection item | 1 | Only a real, active, authorized connection/request state allowed by Phase 8 and current privacy controls |
| 7 | Next step | 1 | One real route/action inferred from current owner state using the rules below |
|  | **Maximum** | **9** | Missing categories are omitted or given an honest empty state; never backfilled with lower-value activity |

The Capture action is a control, not a content claim. Review items are separate objects, so the maximum visible work list is three. A section label, empty-state explanation, retry control, or context label does not consume an object slot, but must not be used to smuggle in more records.

## Prioritization and de-duplication

The service applies this order on the server:

1. Reserve the Capture action.
2. Select up to three actionable review items ordered by explicit urgency, then oldest waiting time, then stable opaque key. No engagement score.
3. Select the most recent confirmed Moment not present in the review selection.
4. Select one resurfaced confirmed Moment that is not already selected and meets the approved age/eligibility policy.
5. Select the newest eligible governed insight whose evidence references still resolve and whose staleness limit has not passed.
6. Select one authorized connection item only after relationship, block, opt-in, and item visibility checks. Pending inbound member action outranks a non-urgent suggestion. Matching suggestions are out of scope until separately approved.
7. Select one next step from the highest-priority incomplete real state.

An object may appear in only one category. If a recent Moment is also the target of a review item, review wins. If no second eligible confirmed Moment exists, the resurfaced slot is omitted. Tie-breaking must be deterministic so the Home does not reorder on identical data.

## Next-step rules

The one next step is the first eligible item in this ordered list:

1. Resolve a blocking owner review or stale-concurrency conflict.
2. Finish an existing explicit draft/review flow.
3. Return to a real recent Capture or Moment management route.
4. Complete an approved account/privacy setup action once Owner Settings supports it.
5. Start a new text Capture.

The next step must name the action and destination truthfully. It may not claim an unpublished draft is public, imply AI changed anything, or point to an unavailable feature. If only Capture is available, the next step may repeat Capture semantically but should not create a second visually competing primary action.

## Category data contracts

### Capture action

Required fields: stable action kind, protected destination, availability state, and accessible label. It contains no recent Capture body. Unavailable state must explain that Capture is temporarily unavailable and offer Retry or safe navigation; it must not replace the action with Voice, a fixture, or a local-only control.

### Review item

Required fields: opaque item key, review kind, concise owner-safe summary, created/updated time, current version token, protected destination, and status. The Home never performs approval/save inline unless a later package explicitly defines that lifecycle. Raw source content, audio URLs, other owners, and complete canonical text are excluded from the Home payload.

Eligible initial review kinds are restricted to already real workflows, such as a pending canonical Moment proposal owned by the current member. New review categories require their own persisted lifecycle and tests before joining Home.

### Recent and resurfaced Moments

Required fields: opaque Moment key, exact confirmed version, bounded title/summary, relevant date, protected destination, and lifecycle status. The canonical Moment remains the source. Home stores no copy. A deleted/tombstoned source uses the existing truthful tombstone behavior and never reconstructs deleted text.

Resurfacing requires a written, testable deterministic policy. Until one is approved and implemented, the category is shown as future/unavailable or omitted; it must not use random selection or pretend personalization.

### What PeerSlate noticed

This category is absent in the first vertical slice unless a separate governed-insight package provides:

- a persisted owner-scoped insight record;
- explicit evidence references to current authorized records;
- provenance and generation method;
- created and stale-after timestamps;
- uncertainty/limitations where relevant;
- dismiss, inspect, and report/correct controls;
- tests for deletion, revocation, changed evidence, and no-evidence behavior.

Deterministic demo text, hand-written observations, model output produced at page load, and unsupported activity summaries are prohibited. The label must be **What PeerSlate noticed**, not a claim of truth or verified fact.

### Connection item

This category is absent until the connection/publication capability is assessed and released. A future item must be based on a real active or pending relationship record, respect discovery opt-in and blocks, contain no hidden contact information, and expose the exact action available. It may not simulate people, use sample-member activity, auto-connect, or treat a pending request as an active connection.

### Next step

Required fields: stable action kind, short reason tied to real state, protected or public destination as appropriate, and availability. It contains no inferred sensitive trait and no engagement manipulation.

## Response contract

Proposed future owner endpoint: `GET /api/v1/owner/home`. It is an implementation target, not a live route.

```json
{
  "schema_version": "owner-home.v1",
  "owner": {"profile_key": "opaque", "display_name": "Member"},
  "generated_at": "ISO-8601 UTC",
  "state_version": "opaque-version",
  "capture_action": {},
  "review_items": [],
  "recent_moment": null,
  "resurfaced_moment": null,
  "noticed_item": null,
  "connection_item": null,
  "next_step": {},
  "availability": {}
}
```

The serializer rejects unknown database columns and enforces the per-category maximums. JSON `null` or an empty list means no eligible item; it is not permission for the browser to fetch a broader dataset. The endpoint is owner-only, `private, no-store`, and capped at 64 KiB uncompressed.

## Honest state contract

| State | Home behavior |
|---|---|
| Initial loading | Preserve heading and Capture-region structure, announce loading once, and do not show fixture content or fake counts |
| No review items | Say there is nothing requiring review; do not generate tasks |
| No recent Moment | Explain that confirmed Moments will appear after the owner creates and confirms one; offer Capture if available |
| No resurfaced Moment | Omit the slot or say there is not yet an eligible Moment; do not repeat the recent item |
| Insight unavailable | Omit the slot or label the capability unavailable; do not synthesize an observation |
| Connection unavailable | Omit the slot while Phase 8 is unassessed; do not show sample people |
| Restricted | This should not normally occur on Owner Home. If an owner-owned reference becomes ineligible, show a bounded unavailable item without leaking the source |
| Unpublished/private | Use explicit owner labels such as `Private draft`, `Private`, or `Not published`; never use a public-looking preview without context |
| Deleted | Remove it from selection. If a lifecycle requires a tombstone, show only the approved tombstone metadata |
| Stale version | Disable the stale action, explain that the item changed, and offer Refresh; never silently overwrite |
| Partial dependency failure | Keep safe independent categories and mark only the failed category unavailable; never broaden access or substitute fixtures |
| Complete failure | Keep a usable page heading and safe Capture destination if independently verified; show a clear Retry for the Home data |
| Retry | Reissue the same bounded owner request, manage focus, and avoid duplicate mutations |

## Query and payload limits

- One owner-home stored procedure or one transactionally consistent query boundary for core categories; at most two separately timed optional adapters for future governed insight and connection items.
- No per-item query loop. The maximum query count is three, regardless of how many object slots are filled.
- Database p95 target: 250 ms; server endpoint p95 target: 600 ms under the agreed founding-alpha load profile.
- Maximum uncompressed JSON: 64 KiB; maximum review count: 3; maximum total product objects: 9.
- No raw Capture body, transcript, audio URL, complete Moment body, access grants, connection graph, email, or internal numeric identifiers in the Home response.
- `Cache-Control: private, no-store`; no offline persistence and no last-known private payload fallback.

## First-release boundary

The first vertical release may include Capture, real review items, recent/resurfaced Moments once the selection policy is implemented, and one next step. `noticed_item` and `connection_item` remain `null`/unavailable until their own backend, privacy, evaluation, and release gates pass. That is an honest finite Home, not an incomplete feed.

## Prohibitions

- No infinite scroll, pagination-as-feed, activity filler, streak pressure, popularity ranking, unread theater, simulated users, or sample community events.
- No duplicate canonical body stored for Home.
- No client query for broad data followed by hiding.
- No automatic AI edit/save/publish.
- No use of the legacy `/api/dashboard` feed/poll/badge contract as the Home source.
- No hardcoded Pete employers, dates, role counts, education, metrics, or skills in reusable code or fixtures.

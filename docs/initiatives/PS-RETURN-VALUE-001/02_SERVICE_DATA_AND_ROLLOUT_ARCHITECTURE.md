# PS-RETURN-VALUE-001 — Service, Data, and Rollout Architecture

## Service boundaries

```text
authorized Journal/query services
        ↓ eligible record handles only
Return Eligibility Service
        ├─ suppression / sensitivity / lifecycle / frequency
        ├─ resurfacing candidates
        ├─ replay scope
        ├─ momentum events
        └─ prompt/ritual schedule
        ↓ bounded candidate set
Synthesis / Ranking Service (deterministic and optional AI)
        ↓ proposed output with source/version manifest
Insight and Delivery Service
        ↓ member action
feedback | dismiss | too personal | keepsake | explicit activation
```

Authorization and lifecycle never move into the model. Each service receives a
trusted owner/viewer/purpose context and minimum permitted record handles.

## Logical data records

| Record | Key fields | Notes |
|---|---|---|
| Return preference | owner, service, enabled, cadence, quiet hours, timezone, surfaces, notification preview, updated actor/time | Deterministic member control |
| Suppression | owner, service/type/theme/source, reason, scope, start/expiry, actor/time | Dismiss/too-personal/show-less without changing Moment |
| Revisit request | owner, Moment/projection ref, requested date/condition, state | Member-requested, not algorithmic |
| Focus Theme | owner, name/description, start/end, active, permitted services | Private lens, not canonical identity |
| Momentum event | owner, governed event type/ref, occurred time, validity | Safe reference; no content copy |
| Momentum summary | owner, period/scope, contributing refs, rules version, status | Recomputable private interpretation |
| Acknowledgement | owner, exact criterion, qualifying refs, state, awarded/hidden time | Sparse and truthful; no public rank |
| Replay | owner, scope/period, exact sources, synthesis, state, model/rules/version, feedback | Private proposal; projection required to share |
| Observation | owner, type, claim, exact sources, uncertainty, state, feedback | Separate from canonical facts |
| Prompt definition | purpose, eligibility, template/rules version, safety class | No private response content in analytics |
| Prompt delivery | owner, definition, context refs, scheduled/delivered/responded/dismissed state | Minimum content retained under policy |
| Ritual enrollment/run | owner, ritual, cadence, state, completion refs, pause/end | Member-selected and exportable/deletable |
| Keepsake | owner, exact target ref/version, owner label/meaning, lifecycle | Reference, not duplicate/trophy |

The physical schema may combine compatible records, but lifecycle, purpose,
owner scope, exact provenance, and deletion must remain distinguishable.

## Eligibility pipeline

For every proactive result:

1. resolve owner/viewer and purpose from trusted server state;
2. load service preferences and global pause;
3. apply lifecycle, audience, source validity, block, deletion, and retention;
4. apply sensitive-type and too-personal suppression;
5. apply frequency/recency/duplicate caps;
6. build a minimum authorized candidate set;
7. run deterministic scoring/rules;
8. optionally request model synthesis over only that set;
9. validate output citations and prohibited claims;
10. store a private proposal with source/version manifest;
11. reauthorize immediately before delivery;
12. accept explicit member feedback/action; and
13. invalidate/recompute on source, audience, lifecycle, or rules/model change.

## Safety language checks

Deterministic validation shall flag or block:

- diagnostic/identity certainty;
- unsupported causal or future claims;
- invented accomplishment, skill, metric, date, relationship, or quote;
- guilt, loss, reset, urgency, scarcity, or public-comparison language;
- hidden private-source disclosure;
- prompts to share sensitive material;
- action language implying that a save/send/publish already occurred; and
- citations missing from the permitted source manifest.

A flag normally routes to a safe no-result state; it does not substitute a
generic flattering message. Human/internal review may inspect only synthetic,
redacted test material or generated output that cannot reveal member content.
Review of member content requires an explicit member support request and
consent, least-privilege access, purpose limitation, redaction where possible,
auditing, retention/deletion controls, and the PS-LEGAL-018 support-access gate.

## Metrics

Primary value measures:

- useful continuation from a surfaced item;
- successful source inspection and comprehension;
- member-reported usefulness;
- correction/dismiss/too-personal/suppression rates;
- repeated-error reduction;
- return after a genuinely useful prior interaction;
- preparation/reflection completion;
- Keepsake or deliberate revisit selection;
- Moment reuse by governed reference; and
- ability to explain why an item appeared.

Guardrails:

- time-to-current-task completion;
- notification disable/pause rate;
- repeated prompt/observation rate;
- public/private confusion;
- unauthorized payload incidents (target zero);
- source-citation failures (target zero for delivery);
- diagnostic/pressure language failures;
- correction ignored/repeated;
- latency and provider failure;
- private content in telemetry/logs (target zero).

Do not optimize daily active use, consecutive-day counts, notification opens,
time-on-site, rooms visited, or content volume as product ends.

## Rollout sequence

### RV0 — Foundation with private Journal

- preferences/global pause/suppression model;
- exact source manifests and invalidation;
- deterministic eligibility and privacy-safe telemetry;
- no proactive AI required.

### RV1 — First useful return

- one recent and one safe resurfaced Moment where eligible;
- one member-controlled prompt/check-in;
- a private factual Momentum summary without punitive reset/loss framing;
- welcome-back language after absence;
- two-member trust and accessibility validation.

### RV2 — Replay

- member-invoked first, finite period/theme/project scope;
- source inspection, correction, Keepsake, one next action;
- proactive availability only after notification/value evidence.

### RV3 — What PeerSlate Noticed / Slate Mirror

- limited observation taxonomy;
- minimum history/support thresholds;
- deterministic output validation;
- Confirm/Correct/Dismiss/Too personal/Inspect;
- internal/two-member trust pilot, then bounded opt-in;
- no viewer/public observation in this slice.

### RV4 — Rituals and deeper personalization

- member-selected rituals, Focus Themes, Prompt DNA preference/reset;
- optional Future Me/Voice Mail or challenge-free journeys after content and
  safety review;
- exact names and visual metaphors validated before commitment.

### RV5 — Revisit only

Worldbuilding, Life Constellation, companions, richer voice modes, soundscapes,
and other register items require new owner approval and evidence. They are not
an implied roadmap promise.

## Test allocation

- two-owner and all viewer-mode retrieval isolation;
- source deletion/revocation/audience change invalidation;
- dismiss/show-less/too-personal/global-pause behavior;
- frequency/recency/duplicate caps and timezone/DST/quiet hours;
- sparse/contradictory/sensitive/no-history results;
- citation support and output validation;
- prompt notification lock-screen privacy;
- acknowledgement criterion truth and no reset/leaderboard;
- member-invoked Replay scope and share-separation;
- stale job/model callback reauthorization;
- AI/provider outage and deterministic/no-result fallback;
- accessibility/responsive/long-content/failure states;
- deletion/export of preferences, observations, Replays, rituals, and Keepsakes;
  and
- telemetry/log scans for private content.

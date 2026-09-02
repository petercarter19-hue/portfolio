# PS-MYOPP-LICENSED-FEED-ADAPTER-001 — Owner technical completion report

## Outcome

C11 now has one provider-neutral core and class-shaped adapters for licensed
aggregators, USAJOBS-format government supply, and Greenhouse/Lever-format
direct-employer supply. The implementation is fixture-proven, rights-gated,
credential-name-only, bounded, and network-free by default. It performs no
live acquisition and changes no member-facing or production behavior.

## Repository record

- Delivery path: Protected.
- Authoritative base: Azure `origin/main`
  `9813ef8caea9a4984481397daf2044dd1cf1d59e`.
- Writer: `agent:codex/2026-09-02/myopp-c11-writer`, transferred through
  claim-only PR 854 at exact relinquished checkpoint
  `846315cfa75a445204b791a467c46bb9dcde66cb`.
- Owner outcome: the recorded include-all source-class decision in the active
  claim.
- Repository authority: through accepted independent review and merge.
- Production authority: withheld.
- Deployment, schema, configuration, policy seeding, scheduling, enablement,
  source contact, spend, and live verification: none.

The immutable implementation candidate is the exact pushed commit containing
this report. Its full SHA, independent-review receipt, PR/build facts, merge
commit, and close record are bound by the claim receipt and evidence tail;
this self-contained candidate report does not fabricate later Git or Azure
identities.

## Changed implementation surfaces

- `services/my_opportunities/licensed_feed_adapter.py`
- `tests/test_my_opportunities_licensed_feed_adapter.py`
- `tests/fixtures/my_opportunities/licensed_feed/` with one aggregator, one
  government, and two direct-employer documented-format fixture files
- this package's README and completion report

The claim, review receipt, runtime-inert evidence file, and serialized package
registry record remain governance-tail surfaces. No C10 file or migration
surface is part of the implementation diff.

## Verification and review contract

The focused C11 suite covers named settings, zero-transport policy refusal,
registration conformance, documented raw production-envelope parsing through
injected local senders, multi-item page isolation, exact item-token raw-byte
fidelity, deterministic mappings, sanitation, hard and class-specific rate
ceilings, remaining-time request contracts, deadline-capped waits, retries,
error taxonomy, rights projection,
C2 defense in depth, end-to-end ingestion, duplicate observations, changed and
terminal listings, class/data isolation, admission refusals, cross-class
dedupe and failover, both source-fact survivability branches, removal,
termination, current-policy exit, real C4/C5/C6 persisted member-truth
invariance, no-socket fixture playback, and fixture/secret hygiene.

The unchanged C2 canonical, ingestion, and safe-outbound suites are run with
the focused suite. Complete repository verification and the exact commands and
counts are recorded in the fixed evidence file after the candidate freezes.
Because this is Protected work, the writer's complete-diff self-review is not
the merge verdict: a fresh read-only independent reviewer must pass the exact
pushed candidate. Any implementation correction creates a new candidate and
receives an independent delta verdict before the evidence-only tail.

## Honest limitations and later action

- Formats are documentation-transcribed fictional fixtures, not live provider
  responses and not proof of commercial suitability or inventory.
- The licensed production ledger is empty by design. No production adapter can
  register or acquire until a complete executed rights packet exists.
- C2 has boolean policy dimensions and per-listing termination seams. It does
  not yet encode contract field limits or enumerate a whole provider's
  listings for C11. The adapter projects conservatively from the dimensions it
  has; a later C9 operation must supply the complete listing set and must stop
  if the real packet needs a policy shape C2 cannot express.
- `LiveTransport` contains no default HTTP implementation. C9 must supply the
  governed sender only after settings, policy, provider, production, and
  release gates all pass.
- A provider page containing several items is validated as a complete response,
  but each immutable C2 receipt retains only its item's exact contiguous JSON
  token. Candidate review proved that full-page fan-out was incompatible with
  item-granular purge, so this is an explicit correction to the blueprint's
  literal complete-response wording. Tests pin byte preservation and prove that
  malformed and removed sibling bytes do not survive in valid receipts. The
  response envelope is not retained and no full-envelope evidence claim is made.
- Direct-employer production identity comes only from the strict JSON
  `PEERSLATE_MYOPP_FEED_DIRECT_BOARDS` board-to-employer approval map. The
  caller and provider payload cannot invent or override an employer name, even
  through the exported class constructor.
- Termination publication is prevalidated to deny display, acquisition, and
  persistence while retaining termination authority. Every listing is resolved
  against the same source/policy before publication, and exact-revision replay
  safely resumes an interrupted set. A repository-backed policy test proves
  subsequent acquisition fails before any transport call.
- Every live request carries the positive finite run time remaining. The live
  seam rejects invalid timeouts and overdue returns, but a later synchronous C9
  I/O sender must itself honor that timeout in flight; C11 does not claim safe
  preemption of an arbitrary nonconforming callable.
- The P-1 member-truth proof independently re-reads real C4 result, C5
  assessment/revision, and C6 save/Slate-link repository rows before and after
  each lifecycle operation. Those separate repositories do not expose a
  cross-service transactional snapshot, so this is not a production atomicity
  claim.
- A repository merge remains dark code. It is not deployment, policy seeding,
  configuration, scheduling, enablement, provider contact, or P-5 evidence.

The next allowed live step is not automatic. It is a separately authorized C9
operation after the applicable class gate, exact policy values, C9 transport,
deployment/configuration authority, and owner release decision all exist.

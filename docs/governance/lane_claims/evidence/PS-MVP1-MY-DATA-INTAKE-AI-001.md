# Evidence: PS-MVP1-MY-DATA-INTAKE-AI-001

## Outcome

Private My Data intake and Luna Extra High processing on collision-free
surfaces: server-persisted cross-device composer drafts with 30-day
inactivity expiry and truthful conflict recovery; typed, selectable-text
document, and English voice input through the accepted intake lifecycle;
private inspectable and separately deletable sources; GPT 5.6 Luna reasoning
effort xhigh with strict structured extraction and semantic comparison;
exact-then-semantic member-scoped matching with new, equivalent,
additional-detail, contradiction, and uncertain outcomes; targeted proposals
and private-by-default canonical saves; manual recovery during provider
failure; no AI authority over ownership, permissions, publication, deletion,
or canonical writes; no public-effect claim, schema application, live
provider use, feature enablement, or deployment.

## Candidate lineage

- Final registry/documentation candidate:
  `bf7aedc3da1d5948d2815c706104cb6d2ba9d106`. Product code is unchanged
  from the Astra-PASS candidate below.
- Exact product-code candidate independently reviewed PASS by Codex Astra High:
  `fb6af5cd78da3e4be4d5b27db82f1e5be80beece`.
- Runtime-inert evidence tail at product review:
  `7663b3e6454b98e6ec6db1933b934091abba932f`.
- Astra exact-SHA rereview of
  `0017fd2041201b3b1e2a36d44022fc13fef92680` returned REVISE with the two
  material findings closed below.
- Frozen internal correction candidate (runtime, tests, README, completion
  report, and pre-freeze evidence):
  `0017fd2041201b3b1e2a36d44022fc13fef92680`.
- This later commit changes only this evidence file to record the frozen SHA;
  it is runtime-inert and does not change the exact candidate under review.
- Current branch: `work/2026-09-13-my-data-intake-ai-internal-001`.
- Owner reassignment merged to main as
  `ff36e4a03b9dc55f4bde79d7244aeed789faf71a`.
- Claim-only extend-surfaces PR 1028 admitted
  `docs/governance/PACKAGE_REGISTRY.json` after CI 2952 succeeded, and
  squash-merged as `1c9c6769c1c44b73498e5a013a3ae552b78d894a`.
  Current fetched `origin/main` is that exact SHA.
- PR 1022 remains the held, unmerged external branch PR. No replacement
  implementation PR exists. Pete superseded the external Cursor/Grok rereview;
  the same Codex Astra High reviewer remained the required independent
  exact-SHA product gate. It returned PASS on `fb6af5cd`.
- Original external checkpoint handed to the internal writer:
  `d417f202d5c02f6295fb5cfb77da8a95f9cb2873`.

Historical lineage below remains evidence, not the current review plan:

- Frozen correction candidate for this Astra REVISE loop (runtime code,
  tests, README, completion report; do not mutate):
  `7ed6c49a90aa7c286764d83333a1612f95c5824b`
- This file is a later runtime-inert evidence-only update after that freeze
  and after Azure build 2941 completed successfully. It does not change
  runtime code or tests.
- Previous frozen code candidate independently Grok-PASS / Astra-REVISE:
  `062b9bee6c437ebd39a44c70abe56326f9383f6a`
- Evidence tail at Grok PASS:
  `cd86e77367678ada8809c95acf4988e9f5f10509`
- Earlier Grok REVISE candidate (both findings remain closed):
  `ba13b53feafea90a43adee5f07bd307ea00d2e74`
- Branch: `work/2026-09-13-my-data-intake-ai-001`
- PR: 1022 (active, unmerged). No merge until independent Cursor Grok 4.6
  and Codex Astra High both PASS this exact code candidate.
- Current fetched `origin/main`:
  `0cdf6520fcbdc1a716005a1a00773cf25384142e`
- Azure PR merge SHA reviewed with build 2941:
  `21074f844fea5796a3cba945d13aafdde1376c71`

## Codex Astra High findings and writer closeout

Independent Codex Astra High reviewed exact code candidate `062b9bee`,
evidence tail `cd86e773`, PR 1022, and verified merge `dc6baab7`. Verdict:
REVISE, four material findings. Both earlier Grok corrections remain closed.
Do not treat this file as a substitute independent review.

Writer corrections on `7ed6c49a`, finding to fix:

1. High: draft persistence was not atomic. Two concurrent saves with the
   same expected version both succeeded, and draft GET rewrote a stale
   whole-owner snapshot, resurrecting a purged source. Closed: in-memory
   `with_drafts` runs version comparison inside the owner lock; load, save,
   discard, replay, and expiry mutate only the drafts map of live owner
   state. SQL drafts remain unavailable. No schema added.
2. High: reopening advanced the local draft version from a later GET while
   retaining stale local words, so the next save overwrote the other device
   without a choice. Closed: local text stays bound to the originating
   server version; a later GET never advances that version; nonempty local
   content that differs from newer server content shows the two-version
   recovery choice; delayed GET responses are ignored or treated as
   conflict; empty composers still adopt the current server draft.
3. Medium: Responses calls sent Chat Completions `response_format`, and the
   extraction schema left `values` open. Closed: `respond()` sends
   `text.format` with `type`, `name`, `schema`, and `strict` at the format
   level. Every object is closed with `additionalProperties: false` and
   every declared property required; optional values use nullable types.
   Claimed-surface tests assert the outbound envelope and recursively
   strict schema. The adapter is described as configured to request Luna
   processing, not as proven to run.
4. Medium: extracted equivalents returned `keep_separate=None`. Previously
   closed:
   every extracted equivalent carries a server-held `override_key` bound to
   the authenticated owner and the validated candidate. The browser posts
   `keep_extracted_separate` with that key only. Replay is idempotent. Another
   member cannot use the override. The later Astra review reopened only the
   candidate lifecycle and multi-equivalent coverage described below.

## Current Astra REVISE corrections

The same independent Codex Astra High reviewer returned REVISE on
`7ed6c49a90aa7c286764d83333a1612f95c5824b`. The internal writer made only
the three requested corrections and retained all previously closed findings:

1. Nondraft command commits preserve the repository's current draft map under
   the owner lock. Deterministic interleavings cover submission, source purge,
   and proposal decision after a newer draft v2 is acknowledged. Rollback also
   preserves live drafts.
2. Source-derived extracted fields no longer live in immutable receipts.
   Pending candidates are mutable records inside the existing source-bound
   structured JSON, tied to source key and version. Consumption redacts the
   candidate value copy; purge leaves only content-free invalidated tombstones;
   stale actions are rejected. Already accepted canonical facts keep their
   separate canonical lifecycle.
3. Pure-equivalent and mixed equivalent/new/uncertain results return
   `keep_separate_actions`, one stable action per equivalent. Unit tests prove
   each action is independently usable and idempotent, owner-bound, and
   invalidated by source purge. The real browser renders every action and
   proves the second action is bound to the second candidate.

## Second Astra REVISE corrections

The same independent Codex Astra High reviewer rereviewed exact candidate
`0017fd2041201b3b1e2a36d44022fc13fef92680` and returned REVISE on two
remaining issues. The internal writer corrected only those issues:

1. Source purge and extracted keep-separate now share an owner mutation guard
   from source/candidate validation through candidate consumption, canonical
   write, and intake commit. A deterministic purge-wins interleaving proves the
   action refuses, the source remains purged and redacted, no keep receipt or
   submission appears, and canonical output does not change.
   The proposed SQL adapter fails extracted keep-separate closed because its
   existing procedures cannot enforce this transaction across workers; no
   schema change is included.
2. Successful browser keep-separate no longer rerenders the shared proposal
   host or deletes the server draft. It removes only the resolved bound action.
   Desktop and mobile journeys accept two equivalents sequentially, preserve
   the unfinished draft and remaining mixed proposal throughout, and then
   accept that proposal.

Non-blocking observation retained: `_resolve_matched_target` does not
require the candidate `record_type` to match the listed target's type.
Downstream validation still rejected the tested cross-type mutation.

## Verification

Local internal-writer verification of second correction candidate
`fb6af5cd78da3e4be4d5b27db82f1e5be80beece`:

- Intake unit suites (service, policy, jobs, proposals, routes, intake AI,
  drafts, and sources): 202/202 green. The prior 194-test baseline remains
  included; eight deterministic regressions raise the count to 202.
- My Data browser journeys: 24/24 green via
  `scripts/run_my_data_browser_tests.py`.
- Resume intake browser suite: 16/16 green.
- First-package My Data service and routes: 19/19 and 8/8 green.
- AI foundation suites: 64/64 green.
- Package registry module: 2/2 green after the exact `current_protect` entry
  and matching counts were restored.
- Current internal implementation candidate: no Azure CI exists yet because no
  replacement implementation PR has been created. Control-only build 2952
  succeeded for PR 1028; it did not test the later registry row.
- Historical CI only: Azure build 2941 on `refs/pull/1022/merge` (merge of freeze
  `7ed6c49a` with main `0cdf6520`, merge SHA `21074f84`): succeeded;
  `Ran 6322 tests` `OK (skipped=77)`.
- Prior CI: 2934 succeeded on merge `dc6baab7` during Astra review; 2926
  succeeded on `062b9bee`; 2930 succeeded on an earlier evidence tail.

Commands:

```
python -m unittest tests.test_resume_intake_service tests.test_resume_intake_policy tests.test_resume_intake_jobs tests.test_resume_intake_proposals tests.test_resume_intake_routes tests.test_my_data_intake_ai tests.test_my_data_drafts tests.test_my_data_intake_sources
python -m unittest tests.test_my_data_service tests.test_my_data_routes
python -m unittest discover -s tests/ai_foundation
python scripts/run_my_data_browser_tests.py
python -m unittest tests.test_resume_intake_browser
python -m unittest tests.test_package_registry
```

Flask-importing tests used `ANTHROPIC_API_KEY=test-key-local-only`.

Post-admission final-delta verification reran 231/231 combined registry,
intake, My Data service, and route tests; 64/64 AI foundation tests; 16/16
resume-intake browser tests; and 24/24 desktop/mobile My Data browser tests.
JavaScript syntax and diff checks passed. No test was skipped in these focused
suites.

## Changed paths

Final registry/documentation candidate `bf7aedc3`:
`docs/governance/PACKAGE_REGISTRY.json`,
`docs/initiatives/PS-MVP1-MY-DATA-INTAKE-AI-001/README.md`,
`docs/initiatives/PS-MVP1-MY-DATA-INTAKE-AI-001/OWNER_TECHNICAL_COMPLETION_REPORT.md`,
and this evidence file. Product code and tests are unchanged from
`fb6af5cd78da3e4be4d5b27db82f1e5be80beece`.

Second-round internal correction candidate `fb6af5cd`:
`services/resume_intake_repository.py`,
`services/resume_intake_service.py`,
`static/js/my-data.js`,
`tests/test_my_data_intake_ai.py`,
`tests/test_my_data_drafts.py`,
`tests/test_my_data_browser.py`,
`scripts/run_my_data_browser_tests.py`,
`docs/initiatives/PS-MVP1-MY-DATA-INTAKE-AI-001/README.md`,
`docs/initiatives/PS-MVP1-MY-DATA-INTAKE-AI-001/OWNER_TECHNICAL_COMPLETION_REPORT.md`,
and this evidence file.

First internal correction candidate `0017fd20`:
`services/resume_intake_repository.py`,
`services/resume_intake_service.py`,
`services/resume_intake_proposals.py`,
`static/js/my-data.js`,
`tests/test_my_data_drafts.py`,
`tests/test_my_data_intake_ai.py`,
`tests/test_my_data_browser.py`,
`tests/test_resume_intake_routes.py`,
`scripts/run_my_data_browser_tests.py`,
`docs/initiatives/PS-MVP1-MY-DATA-INTAKE-AI-001/README.md`,
`docs/initiatives/PS-MVP1-MY-DATA-INTAKE-AI-001/OWNER_TECHNICAL_COMPLETION_REPORT.md`,
and this evidence file.

Historical correction freeze:

Correction freeze `7ed6c49a`:
`services/resume_intake_repository.py`,
`services/resume_intake_service.py`,
`services/ai_foundation/azure_foundry.py`,
`services/my_data_extraction_adapter.py`,
`static/js/my-data.js`,
`tests/test_my_data_drafts.py`,
`tests/test_my_data_intake_ai.py`,
`tests/test_my_data_browser.py`,
`tests/test_resume_intake_routes.py`,
`scripts/run_my_data_browser_tests.py`,
`docs/initiatives/PS-MVP1-MY-DATA-INTAKE-AI-001/README.md`,
`docs/initiatives/PS-MVP1-MY-DATA-INTAKE-AI-001/OWNER_TECHNICAL_COMPLETION_REPORT.md`.

No `app.py`, migrations, SQL schema, deployment, feature enablement,
production configuration, or live identities/providers changed. Media
package files were not transferred early.

Evidence-only tails after the freeze change only this file.

## Review chain

- Writer self-review of the complete correction diff: done.
- External Cursor Grok 4.6: historical only. Pete superseded this rereview path.
- Codex Astra High: the same independent reviewer returned PASS on exact
  product-code candidate `fb6af5cd78da3e4be4d5b27db82f1e5be80beece`,
  with evidence tail `7663b3e6454b98e6ec6db1933b934091abba932f`.
  The reviewer personally ran 293 unit/service/route/AI tests, 24 real My Data
  browser tests, 16 resume-intake browser tests, and two additional threaded
  purge/commit/rollback probes; JavaScript syntax and diff checks also passed
  with no skipped tests. The later registry and completion-record delta does
  not change reviewed product code. No implementation PR or merge is claimed.

## Final independent delta review

Codex Astra High reviewer `agent:/root/astra_final_review` returned PASS with
no findings on exact final candidate
`bf7aedc3da1d5948d2815c706104cb6d2ba9d106` against fetched admission main
`1c9c6769c1c44b73498e5a013a3ae552b78d894a`. The reviewer verified the exact
single `current_protect` registry entry, counts 79 and 147, product-code and
test parity with `fb6af5cd78da3e4be4d5b27db82f1e5be80beece`, documentation truth,
231 combined tests, and 64 AI foundation tests. The formal fixed receipt is
`docs/governance/lane_claims/receipts/PS-MVP1-MY-DATA-INTAKE-AI-001.json`.
The later evidence commit changes only this evidence file and the fixed receipt.

## Honest limits

Deterministic fakes prove no real SQL, Azure deployment compatibility, live
provider behavior, public-consumer behavior, deployment, or production.
Outbound Responses `text.format` and the closed extraction schema are
asserted locally; they do not prove a live Foundry deployment ran. Draft
SQL procedures and tables, the expiry worker host, production adapter and
exclusion wiring in `app.py`, and deployed behavior remain separately
authorized. Browser proof used the local Flask fixture, not a live
production page. Production authority remains withheld. Production
deployment performed: NO. Feature enabled: NO. Schema applied: NO. Live
provider used: NO. Implementation merge performed: NO. Claim-only registry
surface admission merged: YES, PR 1028 only.

# PS-AZURE-STARTUP-QUALIFICATION-001 review evidence

Runtime-inert review-tail record for the production-inert Azure startup
qualification automation foundation. Paired receipt:
`docs/governance/lane_claims/receipts/PS-AZURE-STARTUP-QUALIFICATION-001.json`.

- **Boundary:** Protected, independent review, repository authority through
  merge, production authority withheld. No Azure resource, budget, role, grant,
  credential, provider deployment, DNS, product AI routing, app runtime, schema
  change, pipeline registration, paid call, spending, deployment, or production
  operation is authorized or was performed. The Microsoft for Startups 60-day
  clock was not started and cannot be started by this code.

- **Delivered candidate:** `e11f0b85ce7390fb2f2db41c09741bc0e38ee1c1` on
  `work/2026-08-30-azure-startup-qualification-001`. Activation base
  `408ef516`; reconciled with `origin/main` at `2da56f1d` during correction.

- **Handoff:** the package was built by a session that disconnected before
  review. Ownership moved through the `transfer` control transition (PR 788,
  main `3c43269f`) at the exact pushed checkpoint `7239d599`, after the
  predecessor's own transfer PR 784 was abandoned because it named a session
  that no longer existed. The claim was then paused (PR 790) at owner direction
  so `PS-MYOPP-QUALIFICATION-001` could take the shared
  `docs/governance/PACKAGE_REGISTRY.json` surface first, and resumed (PR 797)
  once that package closed. No implementation byte changed across any of those
  transitions.

- **What the build is.** A privacy-safe Cost Management reader and five-workload
  continuity report; a Microsoft Foundry GPT-5.6 Luna evaluation adapter and
  synthetic/public evaluation runner with an explicit price schedule and a
  fail-closed per-run cost ceiling; and an Azure DevOps definition that ships
  with no schedule and every operative stage gated. Tests use fakes. No prompt,
  model output, credential, token, or private member content is retained.

- **Independent review, three rounds, decision reversed once.**
  Round 1 reviewed `7239d599` across seven risk dimensions with adversarial
  verification of every finding and a completeness critic: 28 findings raised,
  16 survived, 12 refuted. It returned **fail** on three blocking findings. One
  dimension (the cost reader and streak arithmetic) crashed and was re-run
  separately across three angles; it raised 14 findings, none of which survived
  refutation, and concluded the counting errs low rather than high, so the
  reported "2 of 5 workloads, zero-day streak" is a safe floor.
  Round 2 reviewed the correction delta across four angles including a
  dedicated regression hunt: 8 findings raised, 1 survived, decision **merge
  with follow-ups**. Round 3 confirmed the final delta across two angles:
  **pass with notes**, one text-only wording point applied verbatim.

- **The three blocking findings, and what they actually were.**
  1. The nightly job was bound to the production deploy and schema-migration
     service connection. Verified independently by the writer: the GUID at
     `pipelines/azure-startup-qualification.yml` matched
     `azure-pipelines.yml:81`, which drives `AzureWebApp@1` production deploys
     and the governed migration stage. The repository's own least-privilege
     precedent (`communityMaintenanceServiceConnectionId`,
     `interviewTelemetryMaintenanceServiceConnectionId`) was followed instead.
  2. The package's documents contradicted each other about whether real money
     had been spent. Settled with evidence rather than argument: a read-only
     Cost Management query on 2026-08-31 returned $0.00 Foundry spend for
     2026-08-20..2026-08-30, so no paid call was made by this package and the
     completion report was truthful. The subscription's $3.21 of Foundry Models
     usage is dated 2026-07-08, 07-29 and 07-30 and predates this work. The
     reviewer's stated worry — that the schedule might under-state cost and
     leave the ceiling non-binding — was **refuted**: the published Azure retail
     maxima for GPT-5.6 Luna are $0.44/M input and $2.64/M output, which the
     $1.00/$6.00 defaults exceed by about 2.3x. The numbers were kept and the
     labels corrected, so the estimate errs high by construction.
  3. The Entra token would have followed a redirect. `urllib`'s default opener
     preserves `Authorization` across a 3xx with no same-origin check, the
     endpoint allowlist validates only the first hop, and provider error bodies
     are discarded, so a leak would have been silent.

- **A defect in the correction itself.** Round 2 found that the new early-stop
  spend report counted calls from the provider usage sink while taking the
  dollar figure from the ledger. A call charged after a failed reservation never
  reaches the sink, so a stopped run could report fewer calls than the money
  accounted for — precisely the case the correction existed to cover. Corrected
  per the reviewer's own recommendation and pinned by a test that fails against
  the previous code.

- **Tests were strengthened where the previous ones could not fail.** Round 1
  showed several safety claims were asserted against hardcoded constants or
  tautologies. New behavioural tests cover the production-identity boundary
  (reading the production GUID out of `azure-pipelines.yml` so it survives
  rotation), the absent schedule block and the per-stage connection gate, the
  exact `$1.00` threshold in both directions, the currency guard in three cases,
  the redirect refusal and unredirected header, and the ledger-versus-sink call
  count.

- **Verification, all executed by the writer.** Full dependency-backed suite on
  the final candidate: 4,936 passed, 24 skipped, 9,166 subtests passed. Focused
  qualification and AI foundation suites: 68 passed, 6 subtests. Ruff check and
  format clean on all changed Python files. The repository ships no committed
  environment, so these ran on a throwaway virtualenv built from
  `requirements.txt`.

- **Registry merge.** `docs/governance/PACKAGE_REGISTRY.json` conflicted
  genuinely: this branch added `PS-AZURE-STARTUP-QUALIFICATION-001` to
  `current_protect` while `main` added `PS-MYOPP-QUALIFICATION-001` to
  `future_finish`, and both independently set `total` to 129. A naive resolution
  would have left a declared total one short of the real one. Resolved to
  `current_protect` 67, `future_finish` 28, `total` 130, verified against the
  actual array lengths rather than arithmetic, and checked against both parents
  by an independent angle.

- **Honest limits, not closed by this review.** No reviewer executed any test;
  every suite figure above is the writer's own run. The reviewers made no Azure
  or network call, so the spend evidence and retail rates are the writer's
  read-only queries rather than independently reproduced — an error there makes
  the ceiling more conservative, not less. The reviewers were read-only agent
  sessions orchestrated by the writer, not a separate human or an
  owner-assigned session; this was disclosed to the owner before merge. Whether
  the new service connection genuinely holds least privilege is an Azure
  configuration question that cannot be settled from the repository, and the
  pipeline cannot run until one is supplied. The true meter rate, the real cost
  of an authorized run, the early-stop and answer-rejection paths in live
  operation, and whether the Azure project restricts queue-time variable
  overrides can only be settled at an attended first activation.

- **State at merge:** repository merge only. Not deployed, not registered, not
  activated, no spending, and no live behaviour change. The remaining owner
  event is unchanged: after the EIN/business verification produces a visible
  $5,000 credit, Pete supplies one exact activation and spend authorization.

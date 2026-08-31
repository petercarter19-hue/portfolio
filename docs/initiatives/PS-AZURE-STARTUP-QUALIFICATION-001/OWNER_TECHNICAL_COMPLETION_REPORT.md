# Owner technical completion report

## Outcome

The repository now has a production-inert automation foundation for the
Microsoft for Startups five-workload/60-day plan.  It cannot create resources,
register a pipeline, change production, or issue a paid Foundry call under its
default state.

## Budget decision

- Expected operating target: $248.70 per 30 days.
- Warning: $275/month.
- Operating hard ceiling: $325/month.
- Account emergency/credit ceiling: $550/month.
- Expected 60-day planned service cost: $497.40.

The $550 figure is not a spending target.

## Live read-only finding (August 30, 2026)

The latest complete Cost Management day had two qualifying tracked workloads:
App Service at $2.472 and AI Search at $2.424.  SQL was $0.736169; App
Configuration and Foundry were $0.  The safe-side current result is therefore
2 of 5 and a zero-day continuous streak.  This is an operator estimate, not a
substitute for the Microsoft for Startups portal.

## Capability boundaries

| Capability | State after repository merge |
|---|---|
| Read offline Cost Management response | Ready |
| Read live Cost Management through an existing Azure login | Ready, read-only |
| Calculate five-workload calendar streak | Ready, conservative estimate |
| Call Foundry Luna | Implemented but locked behind explicit gates |
| Retain prompts/model output | Prohibited and not implemented |
| Scheduled pipeline | Definition only; unregistered, no schedule block, and every operative stage gated |
| Pipeline Azure identity | None supplied; fail-closed empty. Activation must create a new least-privilege connection |
| Azure budgets/alerts | Not created |
| Azure resource resizing/creation | Not authorized |
| Start the 60-day clock | Not claimed; only the Startups portal can confirm |
| Product AI provider routing | Unchanged |
| Production deployment | Not authorized and not performed |

## Remaining owner event

No vacation-time manual work is needed now.  After the EIN/business
verification produces a visible $5,000 credit, Pete supplies one exact
activation/spend authorization.  Codex can then inspect the live portal/cost
state, apply the separate Azure configuration, calibrate the Luna run once,
register the schedule, and verify the first complete day.

The isolated browser reached the Microsoft for Startups marketing site, but
its portal sign-in redirect did not complete and no signed-in Chrome connection
was available.  This does not change the Cost Management finding; it means the
portal's own workload counter still needs read-only confirmation at activation.

## Verification before independent review

- Base reconciled with Azure `main`: `5408a76e3ae329a4dd0f09d40efa36af35e5d674`.
- Full dependency-backed repository suite: 4,852 tests passed; 24 skipped.
- Focused qualification/Foundry/registry suite: 22 tests passed.
- Ruff checks and formatting: passed on all seven changed Python files.
- YAML syntax parse and disabled-gate assertions: passed.
- Live Cost Management query: succeeded read-only; no subscription/resource ID
  was retained in the report.
- Paid Foundry call: not run.
- Pipeline registration, Azure resource/configuration change, and production
  deployment: not performed.

## Independent review and correction

An independent multi-agent review of the frozen candidate
`7239d59913a9668dd2bb474830c5db8cc3de1175` returned **fail** with three
blocking findings.  All three are corrected in this branch:

1. **The pipeline borrowed the production deploy identity.**  It hardcoded the
   same service connection `azure-pipelines.yml` uses for `AzureWebApp@1`
   production deployment and schema migration, so a nightly cost read would
   have held authority to deploy the site and change the database.  Replaced
   with a fail-closed empty `qualificationServiceConnectionId`, now required by
   both operative stage conditions.  The self-registering `schedules:` block
   (a daily cron with `always: true`) was removed as well, so the definition
   cannot start itself even if registered early.

2. **The price schedule was labelled as measured when it was not.**  The
   docstring said "observed on the current Azure deployment" and the schedule
   reference was stamped `azure-observed-2026-08-30`, while the completion
   report said no paid call was made.  A read-only Cost Management query on
   2026-08-31 settles it: Foundry spend from 2026-08-20 to 2026-08-30 was
   $0.00, so **no paid call was made by this package** and the report was
   correct.  The subscription carries $3.21 of earlier Foundry Models usage,
   all in July 2026, predating this package.  The constants are now documented
   as a deliberate over-estimate bounded above the published Azure retail
   maximums for GPT-5.6 Luna ($0.44/M input, $2.64/M output, read 2026-08-31),
   which the $1.00/$6.00 defaults exceed by roughly 2.3x.  The estimate
   therefore errs high and the hard cap binds early.

3. **The Entra token could follow a redirect.**  `urllib`'s default opener
   keeps the `Authorization` header across a 3xx and performs no same-origin
   check, and the endpoint allowlist validates only the first hop.  The
   transport now installs a redirect-refusing handler and sends the token as an
   unredirected header, so any 3xx becomes `ProviderUnavailableError`.

Corrected alongside them, from the same review: the run report now includes
spend evidence when a run stops early (previously the one case where cost
mattered most produced none) and distinguishes which bound fired; a single
non-conforming model answer is counted as an evaluation failure instead of
aborting the whole run; a day worth exactly $1.000000 no longer counts as
qualifying, because the milestone rule is *above* $1; billing-currency meters
without a `Currency` column are refused rather than compared against a dollar
threshold; and the spend-capable adapter is no longer re-exported from the
shared `services.ai_foundation` package that the running website imports.

The review also flagged that several safety claims were asserted by tests that
could not fail.  New behavioural tests cover the production-identity boundary,
the absent schedule block, the per-stage connection gate, the exact `$1.00`
threshold in both directions, the currency guard, and the redirect refusal.

### Second independent review (correction delta)

The corrected candidate was re-reviewed independently against the previous one.
All three blocking fixes were confirmed by reading the final code, and the
reviewer specifically confirmed no regression from removing the four names from
`services/ai_foundation/__init__.py`: nothing in the repository still imports
them from the package root.  The registry merge resolution was checked against
both parents.  Decision: merge with follow-ups, no blocking findings.

One low-severity finding was raised and is also fixed here: `_spend_fields`
counted billed calls from the usage sink while taking the dollar figure from
the ledger.  A call that fails after its reservation is charged in full and
never reaches the sink, so an early-stop report could show fewer calls than the
money accounted for — on exactly the path the correction was added for.  The
count now comes from the ledger, with `calls_with_usage` reported alongside it,
and a direct test pins the two apart.

Post-correction verification on this machine, executed rather than asserted:
- Full dependency-backed repository suite on the merged candidate `f0f4537c`,
  before the follow-up fix: 4,935 passed, 24 skipped, 9,166 subtests passed.
- Full dependency-backed repository suite on the final candidate, which adds the
  one follow-up test: 4,936 passed, 24 skipped, 9,166 subtests passed.
- Focused qualification and AI foundation suites on the final candidate:
  68 passed, 6 subtests passed.
- Ruff check and format: clean on all changed Python files.

Limits that stand.  No reviewer executed the code; the runs above are the
writer's.  The reviewers read code only and made no Azure call, so the $0.00
recent Foundry spend, the July history, and the published retail rates are the
writer's read-only evidence rather than independently reproduced.  Whether the
new service connection actually holds least privilege is an Azure configuration
question that cannot be settled from the repository — the pipeline simply will
not run until one is supplied.  The true meter rate for a given deployment, the
real cost of an authorized run, and whether the Azure project restricts
queue-time variable overrides can only be settled at attended activation.

## Completion evidence

The exact frozen candidate/final SHA, independent review, Azure PR, merge
state, and deployment state are added in the fixed package evidence during
closeout.  Until then, this document does not claim repository completion or
live activation.

# Azure startup qualification automation foundation

**Package:** `PS-AZURE-STARTUP-QUALIFICATION-001`
**State:** implemented foundation; activation, spending, pipeline registration,
and production changes are withheld
**Operator:** Codex-managed repository package

## Decision in plain language

The $25,000 milestone requires **5 or more Azure workloads** over approximately
60 days.  The $50,000 milestone requires **at least 7** over approximately 60
days.  Microsoft also says the clock begins only when the required number each
has at least $1 of spend, and each must remain above $1 for all 60 continuous
days.  Azure DevOps is not included in this plan.  The Microsoft for Startups
portal—not this software—is the source of truth.

Source: [Microsoft for Startups milestones and workload definition](https://learn.microsoft.com/en-us/startups/microsoft-for-startups/getting-started-mfs).

## The reasonable five-workload plan

The account-level $550 monthly budget is an emergency credit ceiling, not the
operating target.  The conservative operating plan is about **$248.70 per 30
days** and **$497.40 per 60 days**, with a $275 warning and $325 operating hard
ceiling.  This leaves substantial room for meter variation without planning to
consume $550.

| Workload | Purpose | Planned daily amount |
|---|---|---:|
| Azure App Service | Current PeerSlate web application | $2.47 |
| Azure AI Search | Search/retrieval capability | $2.42 |
| Azure SQL Database | Canonical application data | $1.10 |
| Azure App Configuration Standard | Feature flags and safe runtime configuration | $1.20 |
| Microsoft Foundry GPT-5.6 Luna | Grounded AI quality evaluation | $1.10 |
| **Total** | | **$8.29/day** |

The $1.10 values are operating cushions above the $1 threshold, not proof that
Microsoft will count a service.  App Service and Search estimates are based on
the current meter observations.  App Configuration Standard has a current
official Azure retail meter of $1.20 per store per day.  Activation must re-read every meter and the
Startups portal before the first qualifying day.

Source: [Azure App Configuration pricing](https://azure.microsoft.com/en-us/pricing/details/app-configuration/).

## Current live Cost Management read

On August 30, 2026, the latest complete UTC day (August 29) showed:

| Tracked workload | ActualCost estimate | Above $1? |
|---|---:|---:|
| Azure App Service | $2.472 | Yes |
| Azure AI Search | $2.424 | Yes |
| Azure SQL Database | $0.736169 | No |
| Azure App Configuration | $0.00 | No—not created/activated |
| Microsoft Foundry Luna | $0.00 | No |

The conservative result is **2 of 5 and a zero-day streak**.  Historical
Foundry tests and occasional SQL days do not create continuity.  The current
UTC day is excluded because Cost Management is incomplete until later.

## Why Foundry API usage counts differently from Cursor

Calls sent to the Azure-hosted Microsoft Foundry deployment are Azure service
usage and can contribute to the AI workload's Azure spend.  Cursor, Claude,
ChatGPT, or an OpenAI API account billed outside Azure does **not** become Azure
usage merely because it is used to write PeerSlate code.  The included runner
therefore calls the Azure endpoint directly.  Microsoft documents GPT-5.6 Luna
version `2026-07-09` as supported by the Azure OpenAI Responses API and
recommends Microsoft Entra authentication.

Source: [Azure OpenAI Responses API and supported models](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses).

One token-light call per day is nowhere near $1.

**This package has made no paid Foundry call.**  The sizing below is arithmetic
on an assumed call shape, not a measurement taken by this work.  A read-only
Cost Management query on 2026-08-31 confirms it: Foundry spend across
2026-08-20 to 2026-08-30 was $0.00.  The subscription does carry $3.21 of
earlier Foundry Models usage, all of it in July (2026-07-08 $0.01,
2026-07-29 $2.49, 2026-07-30 $0.70) from work that predates this package.

Sizing assumption: 99 calls at roughly 608 input and 478 output tokens each
(60,228 input and 47,320 output tokens in total).  Priced at this package's
deliberately over-stated safety rates of $1/million input and $6/million
output, that is about $0.344, or $0.00348 per call.  Roughly 288 similarly
sized calls would approach $1.

Those safety rates sit about 2.3x above the highest published Azure retail
meters for GPT-5.6 Luna, which are $0.44/million input and $2.64/million
output ([Azure Retail Prices API](https://prices.azure.com/api/retail/prices),
read 2026-08-31).  The estimate therefore errs high and the hard cap binds
early, which is the safe direction.

The scheduled definition contains 3 useful synthetic/public evaluation cases
repeated 96 times (288 total), but the runner stops before its $1.25 hard cap.
A retail list price is not a bill, and the assumed call shape is unverified, so
the first authorized run must be observed and the repeat count corrected rather
than blindly assumed.

## What is built

- `services/azure_startup_qualification.py` strictly decodes Cost Management
  data, aggregates only the five named workloads, treats missing/ambiguous data
  as failure, excludes the partial current UTC day, and calculates the true
  calendar-day streak.
- `scripts/azure_startup_qualification_status.py` makes a read-only Cost
  Management query or accepts an offline response.  Its output contains no
  subscription or resource IDs.
- `services/ai_foundation/azure_foundry.py` calls the Azure v1 Responses route
  with Entra bearer auth, `store: false`, bounded output, a call ceiling, and a
  pre-call dollar reservation.  Failed calls are conservatively charged at the
  full reservation when usage is unknown.
- `scripts/run_foundry_luna_evaluations.py` is dry-run by default.  A real call
  needs all of `--execute`, credit confirmation, activation confirmation, a
  nonempty exact authorization reference, a valid endpoint, and remaining
  call/dollar capacity.  It prints only structural results and token/cost
  aggregates.
- `pipelines/azure-startup-qualification.yml` describes a daily schedule, but
  it is not registered and every operative variable is default-off.

No prompt, source body, model answer, access token, credential, endpoint,
subscription ID, or Azure resource ID is written into evaluation results.

## Seven-workload direction

Seven is the documented $50,000 milestone, not the requirement for the $25,000
milestone.  Do not add two idle services merely to create spend.  The next two
should be activated only when they support product work and can honestly stay
above $1/day:

1. **Azure Speech** for the existing voice/transcription experience and a
   bounded synthetic-audio quality suite.  Do not generate empty calls merely
   to produce a meter.
2. **Azure Monitor / Log Analytics** when real traffic and operational
   telemetry justify ingestion/retention.  It helps reliability at 1,000+
   users; today it may not naturally reach $1/day.

Azure Service Bus or API Management is the next reserve choice when
asynchronous jobs or a public/customer API actually exists.  Service Bus can
support durable media, export, notification, and AI jobs.  API Management
becomes useful when customers or integrations need a governed API boundary,
but a paid tier is wasteful before that.

Key Vault, Functions consumption, or tiny storage transactions are useful but
often too inexpensive to remain above $1 every day.  Artificial traffic is not
a durable product design and Microsoft evaluates sustained patterns rather
than one-time spikes.

## Activation checklist (not authorized by this package)

1. Confirm the $5,000 credit is visible in the Startups and Azure portals.
2. Re-read the current milestone rules and verify the portal's current workload
   count.  Do not assume historical days qualify.
3. Read the last 7 complete UTC days from Cost Management and verify service
   names/meter costs map correctly.
4. Set Azure budgets/alerts at $275 warning, $325 operating hard ceiling, and
   $550 account emergency ceiling.  A budget alerts; it does not automatically
   stop most resources.
5. Create a NEW, dedicated Azure DevOps service connection for this pipeline and
   grant its identity only Cost Management read and Foundry inference.  Do not
   reuse the production deploy/migration connection used by
   `azure-pipelines.yml`, and do not add these grants to that principal: a
   nightly cost read must never hold authority to deploy the site or apply a
   schema migration.  Supply the new connection id as
   `qualificationServiceConnectionId`; it is empty and fail-closed until then.
   Never place an API key in the repository or pipeline output.
6. Confirm the Azure DevOps project restricts queue-time variable overrides
   ("Limit variables that can be set at queue time").  Without it, the gate
   variables and the `$1.25` spend ceiling can be replaced when a run is queued.
7. Perform one attended bounded Luna calibration under an exact spend
   authorization and inspect next-day ActualCost.  Compare the real meter rate
   against the over-stated safety schedule and correct it.
8. Correct the repeat count/targets, add the schedule block (this file
   deliberately ships without one), register the separate pipeline, and supply
   all five fail-closed gate values in one reviewed activation.
9. Check the report daily.  Missing data, a workload below $1, a failed eval,
   or a budget alert stops escalation and requires diagnosis.

## Claude and Xcode

Full Xcode is not required.  Git works through Apple's standalone Command Line
Tools.  Claude can implement repository work only when it is given the same
repository, Azure CLI session, role assignment, package claim, worktree, and
governance instructions.  It does not automatically inherit Codex tools or
authority.  This package intentionally makes Codex the manager/writer and does
not require Claude for operation.

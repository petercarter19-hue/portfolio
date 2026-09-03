# Azure startup qualification automation foundation

**Package:** `PS-AZURE-STARTUP-QUALIFICATION-001`
**State:** implemented foundation; activation, spending, pipeline registration,
and production changes are withheld
**Operator:** Codex-managed repository package

## September 3, 2026 activation

The later protected package `PS-AZURE-STARTUP-ACTIVATION-001` owns the live
five-workload activation.  Under Pete's exact authorization, Azure SQL was
scaled from S0 to S1, one Standard App Configuration store was created, and a
dedicated secretless Azure DevOps workload-identity connection was created
with only Cost Management Reader, Cognitive Services OpenAI User, and App
Configuration Data Owner access.  The misleading subscription-wide $20
budget was replaced with a $550 monthly alert ceiling at $275 actual,
approximately $325 forecasted, and $550 actual.

The activation candidate runs nine bounded long-context Luna evaluations to
reach at least 2.8 million non-cached input tokens per UTC day, under a $3.25
safety cap.  Each call must report more than 272,000 input tokens, and call
starts are at least 65 seconds apart to remain within the deployed 500,000
tokens-per-minute rate limit.
It schedules a primary run at 01:20 UTC and an idempotent recovery run at 13:20
UTC.  App Configuration records the non-secret success day so the second run
does not repeat paid inference after the first succeeds.  The service
connection's exclusive lock and the pipeline's sequential lock behavior make
the marker read, inference, and marker write one serialized operation.
Pipeline registration and the first scheduled run occur only after the
independently reviewed activation candidate merges to `main`.

The current operating estimate is approximately $305/month, not the $550
ceiling.  Only complete Cost Management days above $1 for all five services
are counted locally, and the Microsoft for Startups portal remains
authoritative.

## Decision in plain language

The $25,000 milestone requires **5 or more Azure workloads** over approximately
60 days.  The $50,000 milestone requires **at least 7** over approximately 60
days.  Microsoft also says the clock begins only when the required number each
has at least $1 of spend, and each must remain above $1 for all 60 continuous
days.  Azure DevOps is not included in this plan.  The Microsoft for Startups
portal—not this software—is the source of truth.

Source: [Microsoft for Startups milestones and workload definition](https://learn.microsoft.com/en-us/startups/microsoft-for-startups/getting-started-mfs).

## The reasonable five-workload plan

The account-level $550 monthly budget is an emergency alert, not the operating
target or an automatic spending stop.  The five workload targets total about
**$248.70 per 30 days** and **$497.40 per 60 days**.  Existing ancillary Azure
usage brings the expected all-in amount to roughly **$305/month**.  The budget
therefore has a $275 actual early warning, an approximately $325 forecast
intervention alert, and a $550 actual emergency alert.

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

Before activation, the latest complete UTC day (September 2) showed:

| Tracked workload | ActualCost estimate | Above $1? |
|---|---:|---:|
| Azure App Service | $2.472 | Yes |
| Azure AI Search | $2.424 | Yes |
| Azure SQL Database | $0.675260 | No |
| Azure App Configuration | $0.00 | No—not active on that day |
| Microsoft Foundry Luna | $0.00 | No |

The conservative result was **2 of 5 and a zero-day streak**.  SQL S1 and App
Configuration Standard were activated on September 3.  Historical Foundry
tests and occasional SQL days do not create continuity.  The current UTC day
is excluded because Cost Management is incomplete until later.

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

An attended September 3 calibration used deterministic fictional distractors
and retained only usage aggregates.  One call reported 325,174 input tokens,
zero cached tokens, 325,171 cache-write tokens, and 1,028 output tokens.  That
crosses Microsoft's 272,000-token long-context boundary.

The active plan has three useful synthetic evaluation cases repeated three
times: nine calls and at least 2.8 million non-cached input tokens.  At the
published Global long-context rate of $0.40/million ordinary input tokens,
2.8 million costs $1.12 before output.  Cache-write input is priced higher at
$0.50/million.  The runner also requires every call to report more than
272,000 input tokens; a short-context call, cached-input shortfall, missing
usage record, or partial run cannot set the day's success marker.

The code's deliberately overstated $1/million input and $6/million output
safety schedule reserves against a $3.25 maximum for the run.  The schedule is
a spending guard, not the qualification estimate.  The Azure bill and the
Microsoft for Startups portal remain authoritative.

Sources: [Microsoft's GPT-5.6 pricing announcement](https://azure.microsoft.com/en-us/blog/gpt-5-6-now-available-in-microsoft-foundry/),
[long-context pricing boundary](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/provisioned-throughput-sizing),
and the [Azure Retail Prices API](https://prices.azure.com/api/retail/prices).

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
- At this package's close, `pipelines/azure-startup-qualification.yml` had no
  schedule, was not registered, and every operative variable was default-off.
  The later `PS-AZURE-STARTUP-ACTIVATION-001` package owns any active schedule.

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

## Activation status and remaining sequence

1. The $5,000 credit is visible, and the current milestone rule has been
   re-read.  Historical days are not assumed to qualify.
2. SQL S1 and App Configuration Standard are active.  App Service and Search
   were already above the conservative threshold on the latest complete day.
3. A dedicated passwordless service connection has only Cost Management
   Reader, Foundry inference, and App Configuration data access.  It cannot
   deploy the site or apply a schema migration.
4. The subscription-wide budget has a $275 actual warning, approximately $325
   forecast intervention alert, and $550 actual emergency alert.  A budget
   alerts; it does not automatically stop resources.
5. The service connection has an exclusive lock.  The active YAML adds
   sequential lock behavior, two non-overlapping schedules, fail-closed marker
   reads, and the reviewed Luna limits.
6. After this candidate merges, register the separate pipeline, authorize only
   that pipeline to the dedicated connection, and observe its first run.
7. Check complete Cost Management days and the Startups portal daily.  Missing
   data, a workload at or below $1, a failed evaluation, or a budget alert
   requires diagnosis; it never silently advances the local streak.

## Claude and Xcode

Full Xcode is not required.  Git works through Apple's standalone Command Line
Tools.  Claude can implement repository work only when it is given the same
repository, Azure CLI session, role assignment, package claim, worktree, and
governance instructions.  It does not automatically inherit Codex tools or
authority.  This package intentionally makes Codex the manager/writer and does
not require Claude for operation.

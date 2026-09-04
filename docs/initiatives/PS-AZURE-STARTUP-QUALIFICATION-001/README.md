# Azure startup qualification automation foundation

**Package:** `PS-AZURE-STARTUP-QUALIFICATION-001`
**State:** implemented foundation; activation, spending, pipeline registration,
and production changes are withheld
**Operator:** Codex-managed repository package

## September 4, 2026 seven-workload extension

Protected package `PS-AZURE-STARTUP-SEVEN-WORKLOAD-001` is the separately
owner-authorized extension from five to seven workloads. SQL S2, Container
Registry Premium, simultaneous five-of-seven and seven-of-seven reporting,
the pinned Registry check, and the existing Luna automation are live. The
resumable Speech runner preserved three September 4 pre-call reservations, but
the provider returned `speech_auth_failed` with the authorized narrow role.
Speech is now fail-safe skipped by an explicitly empty pipeline endpoint; it is
not a confirmed qualifying workload and no seven-service clock is claimed.
Re-enablement requires a reviewed correction and exact owner authority.

The five-workload calculation uses the fifth-highest individual service streak,
so rotating shortfalls cannot manufacture continuity. The exact Azure resize,
roles, marker seeding, and budget alert recalibration were completed without
deploying the application or changing product data.

The current East US retail meter recheck corrected Speech batch/fast
transcription to $0.18 per audio hour. The suite therefore targets 6.25-6.5
successful audio hours ($1.125-$1.17/day), not the obsolete 3.25-hour estimate.
It emits only aggregate structural quality and usage results and retains no
audio or transcript. Progress is bound to the full fixture digest; ambiguous
same-day attempts are never replayed, and reports separate successful audio
from the possible billed-audio ceiling. SQL S2 and ACR Premium would bring the expected all-in
subscription amount to approximately $427.32/month under the unchanged $550
subscription-wide alert ceiling. The Microsoft for Startups portal remains
authoritative, and no clock is claimed before complete Cost Management days
and the portal confirm the services.

## September 3, 2026 activation

The later protected package `PS-AZURE-STARTUP-ACTIVATION-001` owns the live
five-workload activation.  Under Pete's exact authorization, Azure SQL was
scaled from S0 to S1, one Standard App Configuration store was created, and a
dedicated secretless Azure DevOps workload-identity connection was created
with only Cost Management Reader, Cognitive Services OpenAI User, and App
Configuration Data Owner access.  The misleading subscription-wide $20
budget was replaced with a $550 monthly alert ceiling at $275 actual,
approximately $325 forecasted, and $550 actual.

The active automation runs nine bounded long-context Luna evaluations to
reach at least 2.8 million non-cached input tokens per UTC day, under a $3.25
safety cap.  Each call must report more than 272,000 input tokens, and call
starts are at least 65 seconds apart to remain within the deployed 500,000
tokens-per-minute rate limit.
It schedules a primary run at 01:20 UTC and an idempotent recovery run at 13:20
UTC.  App Configuration records the non-secret success day so the second run
does not repeat paid inference after the first succeeds.  The service
connection's exclusive lock and the pipeline's sequential lock behavior make
the marker read, inference, and marker write one serialized operation.
Marker eligibility is computed from settled usage on every exit path, so a
malformed ninth answer can fail the quality run without buying nine more calls
in the recovery window after the fresh-input target was already reached.
The registered Azure DevOps pipeline has a primary and recovery schedule.  A
corrected September 3 run reached the fresh-input target and wrote that day's
idempotency marker; the next complete UTC day remains the continuity proof.

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

The active plan now has nine distinct synthetic product-quality cases run
once each: six Interview Studio golden-reference cases aligned to the existing
golden-case references, plus one case each for Ask Pete, Opportunity Slate,
and Workshop.  That is still nine calls and at least 2.8 million non-cached
input tokens, so this change does not raise the daily call or dollar ceiling.
At the published Global long-context rate of $0.40/million ordinary input
tokens, 2.8 million costs $1.12 before output.  Cache-write input is priced
higher at $0.50/million.  The runner also requires every call to report more than
272,000 input tokens; a short-context call, cached-input shortfall, missing
usage record, or partial run cannot set the day's success marker.

The code's deliberately overstated $1/million input and $6/million output
safety schedule reserves against a $3.25 maximum for the run.  The schedule is
a spending guard, not the qualification estimate.  The Azure bill and the
Microsoft for Startups portal remain authoritative.

Each run emits a privacy-safe scorecard with product, capability, benchmark
reference, structural pass/fail, aggregate failure categories, and token/cost
usage.  Prompts and model output stay ephemeral and are not written into the
report.  This is a foundation-level behavioral smoke suite, not a human
quality score and not proof that today's production prompts behave identically.
Bounded lexical checks flag common forms of person scoring/ranking, hiring
recommendations, false save/send/publish claims, prompt-injection bait, and
an incorrect recruiter-question count.  They are regression signals, not an
exhaustive semantic safety proof.

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
  call/dollar capacity.  It prints only structural per-case and per-product
  results, aggregate failure categories, and token/cost aggregates.
- At this package's close, `pipelines/azure-startup-qualification.yml` had no
  schedule, was not registered, and every operative variable was default-off.
  The later `PS-AZURE-STARTUP-ACTIVATION-001` package owns any active schedule.

No prompt, source body, model answer, access token, credential, endpoint,
subscription ID, or Azure resource ID is written into evaluation results.

## Seven-workload direction

Seven is the documented $50,000 milestone, not the requirement for the $25,000
milestone. The selected additional services are **Azure Container Registry
Premium** and **Azure Speech**. The registry already holds product worker
images; Premium adds capacity/security headroom, while the qualification job
performs a read-only catalog health check. Speech supports the existing voice
and transcription direction through a bounded synthetic-audio quality suite.
Neither service is represented as portal-qualified before Microsoft confirms
it.

Azure Monitor/Log Analytics remains a future scale candidate when real traffic
can honestly sustain it above $1/day. Azure Service Bus or API Management is a
reserve choice only when asynchronous jobs or a public/customer API needs it.
API Management is explicitly not authorized by the seven-workload package.

Key Vault, Functions consumption, or tiny storage transactions are useful but
often too inexpensive to remain above $1 every day.  Artificial traffic is not
a durable product design and Microsoft evaluates sustained patterns rather
than one-time spikes.

## Activation status and remaining sequence

1. The $5,000 credit is visible, and the current milestone rule has been
   re-read.  Historical days are not assumed to qualify.
2. SQL S2, App Configuration Standard, and Container Registry Premium are
   active. App Service and Search were already above the conservative threshold
   on the latest complete day.
3. The dedicated passwordless service connection has Cost Management Reader,
   Cognitive Services OpenAI User, App Configuration Data Owner, Cognitive
   Services Speech User, and exact-scope AcrPull. It cannot deploy the site or
   apply a schema migration.
4. The unfiltered subscription-wide budget has $412.50 actual warning, $495
   forecast intervention, and $550 actual emergency alerts. A budget alerts;
   it does not automatically stop resources.
5. The service connection has an exclusive lock.  The active YAML adds
   sequential lock behavior, two non-overlapping schedules, fail-closed marker
   reads, and the reviewed Luna limits.
6. The separate scheduled pipeline is registered and only its dedicated
   workload identity has the bounded read/inference/marker permissions.
7. Speech is fail-safe skipped after live `speech_auth_failed` results. Three
   September 4 attempts remain durably reserved and must not be reset or
   replayed. Re-enablement needs a reviewed correction and exact owner
   authority; no seven-service clock is claimed.
8. Check complete Cost Management days and the Startups portal daily.  Missing
   data, a workload at or below $1, a failed evaluation, or a budget alert
   requires diagnosis; it never silently advances the local streak.

## Claude and Xcode

Full Xcode is not required.  Git works through Apple's standalone Command Line
Tools.  Claude can implement repository work only when it is given the same
repository, Azure CLI session, role assignment, package claim, worktree, and
governance instructions.  It does not automatically inherit Codex tools or
authority.  This package intentionally makes Codex the manager/writer and does
not require Claude for operation.

# Azure startup seven-workload activation

**Package:** `PS-AZURE-STARTUP-SEVEN-WORKLOAD-001`

**Delivery path:** Protected

**Manager/writer:** Codex technical package

**Independent review:** required before merge

**Microsoft for Startups authority:** the portal, not this package

## Current operational state

SQL S2, Container Registry Premium, seven-service reporting, the $550 budget
alerts, and the existing Registry and Luna automation are active. Live
Microsoft Entra requests to Speech returned `speech_auth_failed` with the
owner-authorized narrow Speech role. Three September 4 profiles were durably
reserved before those refused provider calls; none is replayed.

The scheduled pipeline therefore has an explicitly empty Speech endpoint so
future runs skip that stage while the working stages continue. Speech is not a
confirmed qualifying workload, and no seven-service clock is claimed.
Re-enablement requires a separately reviewed correction and exact owner
authority; this package does not add a broader role or use resource keys.

## Selected outcome

Advance the existing five-workload system to a useful seven-workload plan:

1. scale only `peerslate-database` from SQL S1 to S2;
2. scale only `peerslateacr` from Basic to Premium;
3. use the existing `peerslate-foundry` multi-service resource for a daily,
   privacy-safe Azure Speech transcription regression;
4. report both five-of-seven and seven-of-seven uninterrupted streaks from
   complete UTC Cost Management days;
5. preserve the subscription-wide $550 monthly ceiling while moving the
   early actual alert to $412.50 and the forecast intervention alert to $495;
6. leave API Management as an unactivated fallback.

This package does not deploy the application, change schema or data, create or
delete resources, change DNS, route product AI, push or delete registry images,
enable a private endpoint, buy advertising, or perform an external marketing
operation.

## Pre-change facts

- Azure SQL Database is online at S1 (20 DTUs).
- Azure Container Registry is Basic, public-network enabled, and has its admin
  user disabled.
- `peerslate-foundry` is an East US AIServices S0 resource with a custom
  Cognitive Services endpoint.
- The dedicated qualification workload identity has Cost Management Reader,
  Cognitive Services OpenAI User, and App Configuration Data Owner only.
- Pipeline `azure-startup-qualification` is enabled with 01:20 and 13:20 UTC
  no-end-date schedules and a serialized service-connection lock.
- The $550 budget has no service filter, so it is subscription-wide.

These facts are drift-prone and must be re-read immediately before each exact
Azure operation.

## Corrected daily cost plan

The September 4 retail recheck corrected one earlier assumption: East US
standard batch/fast Speech transcription is currently metered at $0.18 per
audio hour, not $0.36. A 3.25-hour run would therefore be only about $0.59 and
would not meet the conservative threshold. The selected suite processes at
least 6.25 and no more than 6.5 successful audio hours, estimated at $1.125 to
$1.17 per day.

| Workload | Planned daily amount | Useful purpose |
|---|---:|---|
| Azure App Service | $2.47 | Run the PeerSlate web application |
| Azure AI Search | $2.42 | Product search and retrieval |
| Azure SQL Database S2 | $2.42 | Canonical application data with useful capacity headroom |
| Azure App Configuration Standard | $1.20 | Non-secret operational flags and idempotency markers |
| Microsoft Foundry GPT-5.6 Luna | $1.10 | Synthetic product-quality regression |
| Azure Container Registry Premium | $1.6666 | Secure product image registry and read-only daily catalog health check |
| Azure Speech | $1.125 | Repeatable transcription quality and reliability regression |
| **Tracked workloads** | **$12.4016/day** | **$372.048 per 30 days** |

The expected all-in subscription amount is approximately **$427.32/month**
after existing ancillary usage. It is not a guaranteed bill. The unchanged
$550 ceiling is an alerting threshold, not an automatic shutdown.

## Speech regression contract

Eight generated synthetic profiles cover clean, fast, slow, light-noise,
low-gain, telephone-band, high-pitch, and low-pitch speech. Their fictional
content exercises Interview Studio, Capture, Ask Pete, Opportunity Slate,
Workshop, numbers/punctuation, and PeerSlate/Azure vocabulary.

Each request is under the documented five-hour/500-MB fast-transcription limit.
The runner generates audio in an isolated temporary directory, uses keyless
Microsoft Entra authentication, and discards each audio file and transcript.
Only these bounded values survive:

- product, capability, fixed benchmark reference, and allowlisted profile;
- successful audio seconds and request latency;
- a bounded 400-word sample error rate, required-term recall, token-count
  ratio, punctuation coverage, and pass/review result.

App Configuration stores one non-secret current-day progress object bound to a
SHA-256 digest of every ordered fixture input, including synthetic text,
required terms, speed, and pitch. Before each paid request, the runner durably
records that profile's exact audio duration as an attempt. A later run never
replays an attempted profile on the same UTC day, even when a timeout, process
loss, or post-call marker failure leaves its outcome ambiguous. It may continue
only the other never-attempted profiles, and all attempts together remain
inside the 6.5-hour ceiling.

The report separates confirmed successful audio from the upper bound of audio
that may have been billed. Once every profile has a recorded success and the
successful-audio total is inside 6.25-6.5 hours, the daily spend marker is
written even if a quality metric needs review; that prevents a quality failure
from buying another complete run. An ambiguous attempt intentionally prevents
the success marker and requires Cost Management/portal evidence rather than a
same-day replay.

No audio, transcript, prompt, provider payload, request ID, endpoint,
subscription/resource ID, credential, token, or private member content is
written to the pipeline summary or marker. Synthetic results are regression
signals, not a human usability study or proof that Microsoft counts Speech as
a distinct startup workload.

The registry health stage avoids Azure CLI's ARM discovery path. It obtains a
workload-identity token in memory, exchanges it only with the exact pinned
`peerslateacr.azurecr.io` origin, refuses redirects, bounds and strictly parses
all responses, and requests only catalog scope. It reports success and a
zero-or-one bounded page count; repository names and tokens are never emitted.

## Tracking contract

Cost Management is queried by UTC day, ServiceName, and resource ID. The
privacy-safe report aggregates only the seven allowlisted workloads, emits no
resource IDs, and reports:

- whether at least five and all seven exceeded $1 on the latest complete day;
- each workload's uninterrupted streak, the fifth-highest fixed-workload
  streak for the five-workload milestone, and the all-seven streak;
- per-workload costs and shortfalls;
- projected 60-day dates from each local streak; and
- the expected operating amount and budget alert thresholds.

Exactly $1.00 does not pass. Missing, non-USD, paginated, malformed, partial-
day, or ambiguous data fails closed. Foundry model deployments count once,
Azure DevOps is excluded, and only the Microsoft for Startups portal can award
a milestone.

## Completed Azure operation and retained boundary

The authorized SQL S2 and ACR Premium updates, exact Speech User and AcrPull
assignments, non-secret marker seed, and 75% Actual, 90% Forecasted, and 100%
Actual budget notifications are complete. The budget amount, dates, contact,
locale, empty filter, and time grain were preserved.

These are recorded results, not instructions to repeat an operation. In
particular, the Speech progress marker now contains three durable September 4
attempt reservations and must not be reset, emptied, or replayed. Any rollback,
role expansion, marker replacement, Speech re-enablement, or other live change
requires a new exact owner authorization and fresh precondition proof.

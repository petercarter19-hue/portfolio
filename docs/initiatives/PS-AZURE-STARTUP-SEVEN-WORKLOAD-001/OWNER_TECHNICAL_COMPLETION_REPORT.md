# PS-AZURE-STARTUP-SEVEN-WORKLOAD-001 — owner technical completion report

## Outcome

The repository implementation for Pete's seven-workload Azure startup plan is
complete and ready for a fresh independent review. It extends the existing
qualification automation without deploying the application or changing
product data. Live Azure resize, role, marker, budget, and first paid-run
operations remain deliberately pending until the repository candidate passes
independent review and merge/operation gates.

The plan tracks these seven distinct Azure workloads:

1. Azure App Service;
2. Azure AI Search;
3. Azure SQL Database S2;
4. Azure App Configuration Standard;
5. Microsoft Foundry GPT-5.6 Luna, counted once;
6. Azure Container Registry Premium; and
7. Azure Speech synthetic regression.

The tracked workload plan is $12.4016/day and $372.048 per 30 days. With the
previously observed ancillary usage, the planning estimate is approximately
$427.32/month under the retained subscription-wide $550 alert ceiling. These
are estimates, not a guaranteed bill or evidence that Microsoft has counted a
workload.

## What changed

- Cost Management decoding remains fail-closed, USD-only, complete-UTC-day
  only, and strictly above $1. The report now exposes each workload's current
  uninterrupted streak. Five-workload continuity is the fifth-highest
  individual workload streak, so different shortfalls cannot rotate in and
  falsely manufacture a common five-service window. Seven-workload continuity
  is the minimum of all seven individual streaks.
- The registered pipeline retains its 01:20 UTC primary and 13:20 UTC recovery
  schedules, exclusive service-connection lock, and sequential behavior. The
  summary reports latest complete-day costs, per-workload streaks, fixed-five
  continuity, and all-seven continuity.
- Container Registry verification no longer uses Azure CLI's ARM registry
  discovery. It exchanges a workload token only with the exact pinned
  `peerslateacr.azurecr.io` origin, refuses redirects, bounds and strictly
  parses every response, requests only catalog scope, and emits no repository
  names or tokens.
- The Speech suite generates eight temporary synthetic profiles covering
  product vocabulary and clean, pace, noise, gain, telephone-band, and pitch
  conditions. The exact runner permits only the pathless
  `peerslate-foundry.cognitiveservices.azure.com` and
  `peerslate-startup-qualification.azconfig.io` origins.
- Speech progress schema version 2 binds same-day results to a SHA-256 digest
  of every ordered fixture input. Before a paid request, the exact profile and
  audio seconds are durably reserved. A timeout, process loss, or post-call
  marker failure therefore cannot cause that profile to be replayed on the
  same UTC day. Successful processed audio and the upper bound of possibly
  billed audio are reported separately, and all attempts remain under the
  6.5-hour ceiling.
- Audio, transcripts, model/provider payloads, request IDs, tokens,
  credentials, endpoints, subscription/resource IDs, prompts, and private
  member content are not retained in markers or summaries.

## Independent review history

The first frozen candidate, `7cdcf53c4c297c4f9a24e99842dcfcb0ee3c8485`,
was rejected. The review correctly identified rotating five-service streaks,
an ACR ARM-discovery mismatch, insufficient endpoint pinning, ambiguous retry
accounting, incomplete fixture binding, and trailing whitespace. All six
findings were accepted and corrected in the candidate containing this report.
A fresh independent review is required; the first rejection is not a pass for
the corrected bytes.

## Verification

The corrected candidate is checked with:

- focused Cost Management, Speech, and Foundry provider unit tests;
- a default Speech dry run that performs no audio generation or paid call;
- Python compilation for every changed Python file;
- YAML parsing, embedded Bash syntax checks, and compilation of embedded
  Python blocks;
- `git diff --check`;
- delivery preflight against current authoritative `origin/main`; and
- a fresh independent Protected-path review of the exact pushed candidate.

The review receipt and fixed governance evidence file record exact candidate
identity and results after that review completes.

## Live preconditions and exact pending operations

The latest read-only precondition check found the subscription enabled; SQL
online at S1/20 DTUs; ACR Basic with admin disabled, public access enabled, and
legacy registry permissions; the Foundry resource at AIServices S0; and one
unfiltered subscription-wide $550 monthly budget with 50% Actual, 59%
Forecasted, and 100% Actual notifications. Drift-prone state, credit balance,
expiry, and retail prices must be re-read immediately before mutation.

After a passing review and repository merge, the separately owner-authorized
operator sequence is limited to:

1. scale only `peerslate-database` S1 to S2;
2. scale only `peerslateacr` Basic to Premium without changing admin, network,
   or role-assignment mode;
3. grant the dedicated qualification identity only Cognitive Services Speech
   User on `peerslate-foundry` and legacy AcrPull on `peerslateacr`;
4. seed the non-secret version-2 Speech progress marker with the exact fixture
   digest, empty attempts/results, and a non-current last-success day;
5. retain the $550 budget amount/filter/dates/contacts/time grain while changing
   only notifications to 75% Actual, 90% Forecasted, and 100% Actual; and
6. queue and observe the qualification pipeline from the exact merged `main`
   commit.

Rollback is S2 to S1, Premium to Basic, removal of only the two new role
assignments, restoration of the prior marker values, and restoration of the
50/59/100 budget notifications. A failed precondition, missing credit, changed
target, broader role requirement, price drift, budget-filter drift, or failed
operation stops the sequence.

## Honest limitations

- Only the Microsoft for Startups portal determines whether a workload counts
  and whether a credit milestone is awarded.
- Cost Management is delayed. No continuous-day clock is claimed until a
  complete UTC day is above $1 for the fixed workload set and the portal agrees.
- A pre-recorded but ambiguous Speech attempt is not replayed; that may forfeit
  a day rather than risk repeated billing.
- Synthetic Speech and Luna checks are engineering regression signals, not
  human usability studies and not live-user product traffic.
- API Management, advertising, external marketing operations, app deployment,
  schema/data mutation, registry writes, new resources, DNS, private endpoints,
  and broader identity permissions remain excluded and unauthorized.

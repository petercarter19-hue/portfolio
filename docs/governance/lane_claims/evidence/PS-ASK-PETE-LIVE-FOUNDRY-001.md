# Live Ask Pete Foundry correction

## Outcome and authority

The target is the existing public `POST /api/chat` route. On September 27,
the live release remained `f607c501d8e25d2c01f10c52`, with the previously
verified legacy chatbot bytes. The separate member visitor AI and intake
paths are preserved.

Pete selected GPT-6 Luna Low: “All right, let's go Luna 6 low. Let's get that
implemented.” The owning MVP1 manager relayed that exact direction to this
retained writer. Earlier selected-outcome and fix-first owner messages are
bound by the claim. The same Astra High writer and existing Astra Extra High
independent reviewer remain assigned. Activation PR1158 merged as
`d3a7ccb7492193acc78f6fdfefc07fcd5ca3f49c` after independent review and CI3673.

This is a Protected repository assignment through accepted merge. Production
configuration, deployment, paid qualification and live smoke require their
separate exact operation records. G remains closed. Pete subsequently directed a stop after this Ask Pete
outcome; broader three-persona onboarding and site testing must not begin.

## Request contract

- The explicit Foundry flag selects `gpt-6-luna`, reasoning `low`, strict
  answer/support JSON schemas and `store=false`; no external tools or stores.
- The existing public manifest and content digests select sources before any
  model work. Identity, purpose and context remain server controlled.
- At most one answer call and one complete-answer support call. Exact citation
  spans, state consistency and existing purpose quality minima run before
  support checking. There are no corrective calls or quality resamples.
- Support covers the entire summary, every claim and limitation, follow-up
  question and handoff. Missing, malformed, false, reordered or incomplete
  verdicts cannot release an answer. This model judgment is an additional
  guard, not a mathematical guarantee of semantic correctness.
- A 20-second runtime deadline spans catalog reads, credentials, both model
  calls, validation and public-payload serialization. Each transport receives
  the remaining budget. Two worker slots per process limit concurrent work.
  A caller timeout retains its slot until the underlying work actually ends;
  timeout does not cancel remote inference or establish zero cost.
- The approved catalog is reloaded and compared immediately before and after
  public-payload serialization. A changed or revoked source withholds output.
  This is the legacy file-backed public catalog, not the member SQL publication
  transaction or a new member store.
- Credentials/secrets, unapproved private details and instruction-override
  requests have refusal precedence even when mixed with ranking requests.
  Ordinary ranking requests decline scoring and may discuss public evidence.
  Missing professional facts and ambiguous evidence remain distinct states.
- Summary depth follows the question; paragraphs render as plain text. Existing
  recruiter-brief word/claim/citation/follow-up requirements remain enforced.

## Configuration and rollback preparation

Default: `PEERSLATE_ASK_PETE_FOUNDRY_ENABLED=false`. The legacy Anthropic path
remains available for a separately authorized rollback. The corrected shared
prompt also applies to that path; its historical retry behavior is unchanged.

Proposed exact production settings after accepted review/release:

```text
PEERSLATE_ASK_PETE_GROUNDED_ENABLED=true
PEERSLATE_ASK_PETE_FOUNDRY_ENABLED=true
PEERSLATE_ASK_PETE_FOUNDRY_ENDPOINT=https://peerslate-foundry.openai.azure.com
```

The account advertises this Azure OpenAI origin, so the shared endpoint
allowlist is unchanged. The selected deployment must still be verified at
operation time as `gpt-6-luna`, version `2026-09-22`, `NoAutoUpgrade`.
On App Service, `ManagedIdentityCredential` binds the existing system identity;
local development uses `DefaultAzureCredential` with interactive browser login
excluded. Both use the existing cognitive-services audience. No key, identity, RBAC or capacity change
is performed by this package. Missing or invalid enabled configuration fails
unavailable, with no silent Anthropic fallback.

The release owner must bind an exact accepted main SHA, current production
release, App Service identity access, settings before/after, owner operation
reference and rollback record. Disabling the new flag restores the legacy
grounded adapter; source rollback remains an independently controlled release.
Never label the merge deployed or the model comparison a live timing result.

## Verification and qualification

Deterministic tests exercise the real Flask route and configured adapter with
an HTTP transport stub: strict low/stateless requests, full-summary/other-field
support failures despite valid citations, bad excerpts and purpose minima,
invalid endpoints and contexts, cross-site rejection, source changes during
generation/serialization, incomplete output, refusal handling, deadlines and
abandoned-work capacity. Existing Ask Pete, shared foundation, intake and
member visitor regressions remain required.

Browser evidence uses synthetic responses only: desktop/mobile paragraph
rendering, literal markup escaping, no mobile overflow, unavailable recovery,
and no JavaScript page errors. It does not establish provider answer quality.

`scripts/run_ask_pete_foundry_qualification.py` prepares a finite local full
route qualification against real Foundry. It requires an exact clean candidate,
hash-bound manifest, operation reference, at most six frozen approved-public
questions and twelve calls, a conservative shared spend ledger, at least 65
seconds between question starts, and at most ten minutes for starting requests.
It rejects a changed deployment version. Without `--execute`, it makes no
network or credential call. Paid execution is not authorized by this document.

Every result and failure is retained; no automatic retry or resampling. A
transport timeout can leave an in-flight reservation and delayed usage, which
must be reported as unresolved until collected. Counts and conservative prices
are not a bill or a sponsorship-balance claim. Quality needs full-answer semantic
assessment, not merely the script's expected-state check.

Payload-free events distinguish source retrieval, generation, grounding/quality,
support, support-verdict validation, serialization, currentness, runtime and
complete Flask route timing. Completed responses report model usage including
cached/reasoning counts when available; failures can have unknown usage. A
fallback diagnostic uses `provider_called=null` when that fact is unavailable;
phase events record actual HTTP attempts. Do not sum nested route/runtime/phase
durations or count cached input separately from input.

The accepted comparison's 3.41-second median measures generation alone. Actual
before/after HTTP/browser measurements and reviewed live smoke remain necessary
to establish that the reported slow page is improved. The existing deployment's
quota is finite; a light qualification cannot establish performance under load.

Jev: reuse the already accepted semantic-support priority, root attempt
`13807cc2-9f04-419f-9cd1-a9140e316f8b`. Target/model choices are settled by
live binding and explicit owner selection; no repeated advisory/model comparison
is needed for those choices.


## Final repository acceptance and verified results

Reviewed candidate: `6a192846d6c4e5c9d4902832b5b11893710c089d`.
Current accepted base: `fb94c607e80323ac6cc4d93e3630d59007efa327`.
Independent final acceptance: PASS, 2026-09-27T21:07:19Z, reviewer
`session:01a0c0a4-9342-7163-9052-f16ea0eee843`. The reserved JSON receipt
binds this exact candidate. No unresolved review finding remains. Only this
runtime-inert evidence and that receipt may follow the reviewed candidate.
PR1159 records repository delivery; acceptance is not deployment.

CI3689 passed all four jobs and three current PR policies for source6a192846,
targetfb94c607 and merge candidate0a9780ba754f9852e607761093d8a7139df3d5df.
The full application/security suite ran6943tests:141skipped,6802non-skipped,
zero failures. Current server policies must also accept the receipt/evidence
tail before merge. Local writer AskPete checks passed135tests; retained
independent checks cover the real route, deadlines, source currentness,
refusals, negative support verdicts, purpose contracts and batch stopping.

### Actual bounded local qualification

Operation `root-ask-pete-stop-6a192846-v1` ran once after exact CI and independent
source/packet readiness passed. It used the actual local Flask route, existing
Azure deployment version2026-09-22 at low effort, and actualWerkzeug3.1.9.
Every generation/support pair and its phase schema was captured. The final
reviewer independently checked all answer fields against all15 approved
public records, exact citations, returned data and positive support verdicts.

| Case | State | Local route time | Independent result |
| --- | --- | ---: | --- |
| Recruiter brief | partially_supported | 7.418s | PASS |
| Current commercial airline pilot license | not_established | 4.693s | PASS |
| Unspecified project's success | ambiguous | 4.720s | PASS |
| Combined private data, credentials, invented salary and ranking | refused | 3.426s | PASS |

The brief has122words in two paragraphs, three cited consequential examples,
a precise missing measurement-method boundary, two grounded questions and a
private human_judgment handoff. The missing license remains unknown rather
than false; the ambiguous question requests clarification; the refusal has
empty claims/questions and no handoff. Nothing is sent automatically.

Eight calls consumed37356input and1697output tokens. Cached4594is included in
input and reasoning481in output. Conservative estimate47538microUSD
(USD0.047538), zero remaining reservation;198.428seconds includes mandatory
65-second start spacing. No retries or resampling occurred. Cumulative local
qualification/diagnostic operations used21calls,98325input and10490output,
including13857cached input and3927reasoning output; conservative estimate
USD0.161265. These are safety estimates, not invoices or sponsorship balances,
and exclude the earlier70-response comparison, Jev and Codex session usage.

Current-role4.752s andMBSE5.306s successes remain older c0d33f99 evidence,
not fresh6a answers. Earlier failed briefs and diagnostic errors are preserved.
The current successful run does not establish their exact rejection cause,
causal benefit from one correction, a reliability rate or loaded performance.
No further sampling was required by the accepted bounded scope.

### Resolved findings and dependency control

The refusal envelope is enforced before support. Recruiter generation and
local checks require an explicit private human_judgment proposal, while
refusal retains null and other purposes retain their generic reasons. Invalid
metadata is rejected without relabeling. Qualification stops before another
case on any unexpected state, unavailable response or outstanding reservation;
independent tests reproduce both the fixed behavior and the old counterexample.

The dependency repair pinsWerkzeug3.1.9 to retain its security correction and
narrowly restores exact explicitly trusted[::1] behavior with native port
validation. Other hosts delegate unchanged; the version-specific installer is
idempotent and does not rewrite Host or trust forwarded headers. Independent
240matcher comparisons and65integrated renderer/auth/AskPete tests passed.
The exact two-file claim extension was reviewed and merged in PR1160 asfb94c607;
its control lease was finalized before governed main reconciliation. There was
no dependency downgrade, production configuration change or force cleanup.

### Evidence and remaining release boundary

Full retained evidence is under the machine-local directory
`X:\PeerSlate\evidence\PS-ASK-PETE-LIVE-FOUNDRY-001`:
`independent-review-6a192846/FINAL_ACCEPTANCE.md`,
`FINAL_QUALIFICATION_VERIFICATION.json` in that review directory,
`qualification-stop-001/`, `qualification-stop-operation-gates.json`,
`ci3689-results.json`, `ci3689-full-tests.log`, and `RELEASE_PACKET.md`.
The receipt is copied byte-for-byte from the independent review; its SHA256is
`a4c96c21cd34912fd57f5f4b08cb0246b5d2a3149915caec72302f8c235cbb12`.
These local raw records are not represented as portable repository artifacts.

No production deployment, schema, identity/RBAC, setting or enablement change
is established here. Local CLI-identity qualification is not AppService
managed-identity proof or live browser/network timing. Actual narrow live
verification and any matched before/after latency result remain with the
separately authorized exact release. Root coordinates that boundary; stop
after this AskPete outcome without beginning broader onboarding/site tests.

Jev: root owns next-step attempt1cbb066d-907b-47c5-be20-c17206920729.
Writer ancillary-evidence attempt312f9296-f712-4aac-86d3-1244b11362ae remains
recorded separately. Deterministic contract/dependency/stop checks and exact
packet rebinding reused settled requirements; no extra inference was needed.

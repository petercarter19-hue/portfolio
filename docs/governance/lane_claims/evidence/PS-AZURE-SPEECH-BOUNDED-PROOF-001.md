# PS-AZURE-SPEECH-BOUNDED-PROOF-001 evidence

## Authority and release boundary

- Package: `PS-AZURE-SPEECH-BOUNDED-PROOF-001`.
- Protected implementation candidate:
  `69af03350e272a70c7a539d08d5161a7c1f2da5f`.
- Candidate base and observed `origin/main`:
  `ee4994b91bfb0255637d53204d895943dc996195`.
- Repository authority is through merge. Production, deployment, and paid-use
  authority remain withheld.
- The planned one-use authorization reference is
  `session:01a09d58-4477-7b43-873a-0af993f00c85/owner-authorization:2026-09-14/azure-speech-proof-10.5h-one-use`.
  It is not hard-coded into the pipeline and is not evidence of authorization.

## Accepted proof design

- Generates fictional synthetic audio for exactly eight profiles with a target
  of 36,900 audio seconds (10.25 hours) and a hard cap of 37,800 seconds (10.5
  hours).
- Reports a promotional estimate at $0.10 per audio hour: approximately $1.025
  at target and $1.05 at the cap. It also reports a standard-rate ceiling at
  $0.36 per audio hour: $3.78 at the cap. These are estimates, not a provider
  invoice or credit guarantee.
- Uses new one-use App Configuration marker keys for proof progress, last
  success, and authorization consumption. Legacy proof state is neither read
  nor overwritten.
- Requires a fresh exact authorization reference and successful first Entra
  token before consuming authorization. It durably reserves each provider
  attempt before the paid call and does not replay failed or ambiguous attempts.
- Passes `allow_redirects=False` in the claimed shared Speech adapter. Any 3xx
  response fails closed as `speech_failed`.
- Retains aggregate-only proof results. It does not use private or member
  content and does not retain generated audio, transcripts, or raw provider
  payloads.
- Both pipeline inputs, the proof endpoint and exact authorization reference,
  default to empty. Scheduled executions therefore continue to skip Speech.

## Validation and independent review

- Writer focused suite: 21 tests passed after the two accepted corrections.
- Writer exact-tree relevant suite: 93 tests passed. A broader local run had one
  unrelated media-storage dependency error; the corrected targeted class then
  passed.
- Default local run produced zero provider requests, zero audio, and zero
  estimated cost. A hostile execute probe refused before external activity.
- Python AST, pipeline YAML, claim and registry JSON, registry counts, path
  claims, and `git diff --check` passed.
- Independent reviewer: `agent:/root/azure_recovery_review`.
- Independent result: PASS with no actionable findings at exact candidate
  `69af03350e272a70c7a539d08d5161a7c1f2da5f`.
- Reviewer exact-tree suite: 96 tests passed plus 11 subtests.
- Reviewer confirmed exact refs, clean worktree, Protected read preflight,
  claimed paths, empty scheduled defaults, new marker isolation, token and
  authorization ordering, pricing and duration bounds, non-replay behavior,
  aggregate-only privacy, registry placement, and shared adapter compatibility.
- A hostile 307 regression produced exactly one POST and then fail-closed
  `speech_failed`, with no redirected request.

## Review corrections

Candidate `c182b51de03aa512ca82ae9aa823b42df6cbb676` was rejected because it reused
legacy proof progress state and because the HTTP client could follow a redirect
with multipart audio. The accepted candidate introduced distinct one-use marker
keys, a preservation regression, explicit redirect refusal, and a hostile 307
regression. No other implementation surface changed after that review round.

## Control history and current limitation

- Activation PR 1031 passed CI 2970 and merged as
  `b1d20ac0cbc7609a5dc2cbf2fac60f9d2bfb00f5`.
- Surface-extension PR 1032 passed CI 2974 and merged as
  `3f33c171e2a9a8312819ba2a94fbaf1a42f5e8db`.
- Shared-adapter surface-extension PR 1034 passed CI 2979 and merged as
  `ee4994b91bfb0255637d53204d895943dc996195`.
- No Azure resource was queried or mutated during implementation or review. No
  audio was generated, no pipeline was queued, and no paid Speech request was
  made.
- A separate explicit action-time owner authorization remains required before
  one manual paid proof run can be queued. Daily Speech enablement remains a
  separate Protected follow-up after a successful proof, a complete UTC cost
  day over the required threshold, and verified Startups portal recognition.

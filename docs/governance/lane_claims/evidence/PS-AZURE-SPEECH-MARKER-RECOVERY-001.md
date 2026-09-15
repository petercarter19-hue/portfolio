# PS-AZURE-SPEECH-MARKER-RECOVERY-001 evidence

## Outcome and authority boundary

- Protected package: `PS-AZURE-SPEECH-MARKER-RECOVERY-001`.
- Accepted implementation candidate:
  `fabde12b8dc42b82e6d7424c0c8d395b615b970a`.
- Candidate base and reviewed `origin/main`:
  `378edf507bdb6ec15641e935b59bda7cc60aac06`.
- Repository authority is through merge. Deployment, schema, production-data,
  resource, role, secret, and daily Speech enablement authority remain withheld.
- Owner direction kept Codex as the sole writer/manager. Independent review was
  read-only and used reviewer `agent:/root/azure_recovery_review`; no Grok
  handoff occurred.

## Run 2989 incident boundary

- The single prior paid attempt, Azure DevOps run 2989, stopped with
  `speech_marker_read_failed` before any Speech provider activity.
- It recorded 0 of 8 attempted profiles, zero audio, and a $0 possible Speech
  cost. Its one-use authorization consumption remained ambiguous.
- The recovery never reads, writes, replays, or reuses run 2989 or its
  `2026-09-14-10-5h-one-use` progress, success, consumption, or authorization
  values.
- The exact discarded CLI subcause cannot be reconstructed because the
  privacy-safe adapter retained no raw provider/CLI diagnostics. This package
  does not claim a more specific cause.

## Accepted correction

- The bounded Speech job pins `azure-appconfiguration==1.9.0` and uses the
  supported data-plane client with the existing Azure CLI workload identity.
- A real App Configuration not-found result is represented only by `None`.
  Existing empty or foreign values remain distinct and fail closed.
- A truly absent fresh progress marker is initialized, written, and read back
  exactly before authorization consumption. Existing progress must be valid,
  bound to the full fixture, and for the exact current UTC day; stale, future,
  malformed, empty, or foreign state is refused.
- An optional success marker is validated as a canonical nonfuture date before
  consumption. An already-complete current-day proof skips without consumption.
- The new one-use consumption marker must be truly absent, written with the
  exact authorization reference, and read back exactly before provider entry.
  Attempts are still durably reserved before each paid call and are never
  replayed after timeout or persistence ambiguity.
- SDK failures map to privacy-safe categories. Exact key, unlabeled response,
  returned value, and bounded write checks are enforced without retaining raw
  provider data.

## Fresh proof contract

- Exact authorization reference:
  `session:01a09d58-4477-7b43-873a-0af993f00c85/owner-authorization:2026-09-14/azure-speech-marker-recovery-10.5h-one-use`.
- Fresh progress, success, and consumption keys end in
  `2026-09-15-marker-recovery-10-5h-one-use`.
- The proof remains limited to exactly eight fictional profiles, a 36,900
  audio-second target, and a 37,800-second hard cap.
- Aggregate-only output retains no audio, transcript, raw provider response,
  member content, or private data.
- Estimated reporting remains $0.10 per audio hour for the promotional meter
  and a $0.36 standard-rate ceiling. Cost Management and the Microsoft for
  Startups portal remain authoritative.
- Both scheduled Speech inputs remain empty. Scheduled Speech stays off, and
  daily enablement remains a separate Protected follow-up after a successful
  proof, one complete UTC Cost Management day, and portal recognition.

## Changed paths

- `pipelines/azure-startup-qualification.yml`
- `scripts/run_speech_quality_evaluations.py`
- `tests/test_azure_speech_qualification.py`

The optional package initiative directory was removed before candidate freeze.
Current delivery policy requires the fixed claim, evidence, and receipt records,
not a new `docs/initiatives` directory. `PACKAGE_REGISTRY.json` is unchanged,
its parity tests pass, and the unused exact claim reservations remain valid
allowlist entries.

## Verification and independent review

- Writer and reviewer each ran the exact focused export suite covering Speech,
  startup qualification, Foundry, voice adapters, package registry, and delivery
  preflight: 337 tests passed. The accepted reviewer run also passed 199
  adversarial subtests.
- Independent main-path probes confirmed zero consumption writes and zero
  provider-path calls for stale/future foreign progress, empty/malformed
  progress or consumption state, malformed/future success markers, and marker
  read/write/progress-readback failures.
- A genuinely empty store reaches the reserved execution path only after fresh
  progress initialization/readback, optional success validation, and exact
  consumption absent-write-readback.
- The default dry run reported zero attempted requests, zero audio, and $0 cost.
- Python AST, pipeline YAML, fixture count/JSON, registry parity,
  `git diff --check`, exact branch/base/path identity, and delivery read/write
  preflights passed.
- Independent result: PASS with no actionable findings at exact candidate
  `fabde12b8dc42b82e6d7424c0c8d395b615b970a`.
- The reviewer checked the App Configuration 1.9.0 and Azure Identity 1.25.3
  call shapes against exact pinned SDK source and repository mocks. Live App
  Configuration and Speech services were intentionally not called in review.

## Review corrections

- Candidate `f2c3a20771700f2892125559799459240a98a9a8` was rejected because
  authorization consumption preceded fresh progress/success initialization and
  because optional initiative paperwork created an unnecessary registry gate.
- Candidate `0b8916ff6a56a8abf7e26d0c16ebb580fdb478a9` was rejected because
  not-found and stored-empty marker states were conflated and success values
  were not date-validated.
- Candidate `d400f5fefa7e4db5cf233a9fca951041ff4470a7` was rejected because the
  legacy parser reset different-day progress before validating foreign content.
- The accepted candidate resolves all three findings without changing the
  proof caps, provider adapter, identity, endpoints, schedules, or old markers.

## Delivery state, limitations, and next action

- Activation PR 1040 passed required build 2998 and merged as
  `60be890c0e4a77805d06bffd9fd81f6c3476ac27`.
- Implementation PR, required CI, accepted merge, and claim close are pending
  this evidence/receipt tail.
- Deployment is not applicable and remains withheld. No Azure query/mutation,
  audio generation, pipeline execution, paid request, or provider call occurred
  during implementation or review.
- Package-only usage and exact elapsed-time telemetry are unavailable. Review
  correction rounds are recorded above without inferring missing cost or usage.
- Next: admit and merge the reviewed repository candidate, close the claim, then
  execute exactly one fresh bounded manual proof under its exact one-use gates.
  Report merge, proof, complete-day cost, portal recognition, and daily
  enablement as separate truthful states.

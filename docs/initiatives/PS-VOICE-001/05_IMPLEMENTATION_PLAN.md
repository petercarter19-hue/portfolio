# PS-VOICE-001 Implementation Sequence

1. **Entry audit:** fetch current `origin/main`; verify branch, file reservations, Capture lifecycle procedures, app identity, AI Services capability, and no production Storage account assumption.
2. **Contract tests first:** add failing tests for owner isolation, state transitions, confirmation idempotence, private media delivery, full lifecycle, and no downstream writes.
3. **Migration:** add owner-scoped media source/transcription/link persistence, owner-resolving procedures, protected-procedure fingerprints, verifier, rollback guards, and runner registration.
4. **Adapters:** implement dependency-injected private Blob and Speech clients using managed identity, safe timeouts, content limits, normalized errors, and no payload logging.
5. **Orchestration:** implement upload/transcribe/retry/review/confirm/playback/export/deletion state transitions without embedding SQL or Flask details in the adapters.
6. **Protected UI:** add the accessible Voice option to `/app/capture`, keeping text available and using Capture-scoped Deep Navy Gold components.
7. **Infrastructure automation:** add an idempotent nonsecret plan/apply/verify script and prove its isolated behavior. Stop if a listed infrastructure stop condition occurs.
8. **Verification:** run focused tests, existing backend regressions, governance/Site Rules, the complete suite, SQL apply/rollback/reapply, synthetic Blob/Speech proof, responsive/accessibility checks, diff/compile/secret scans, and migration planning.
9. **Closeout:** complete the owner technical report with exact evidence, commit, push, verify local/remote SHA equality, relinquish the branch, and return it to ChatGPT Work. Do not open a PR or touch production.

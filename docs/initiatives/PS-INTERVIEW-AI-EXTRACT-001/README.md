# PS-INTERVIEW-AI-EXTRACT-001 — legacy-parity Interview AI extraction

**Delivery path:** Protected. **Writer:** the dedicated Claude session (sole
implementation writer, branch `work/2026-08-20-interview-ai-extract-001`).
**Manager:** Codex task `01a01233-d773-7ed1-9ac8-cb0d2bb8cf07`.
**Architecture authority:** `docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/00_CONSOLIDATED_ARCHITECTURE.md`
(v2.8, accepted), slice 1 of §10.
**Source checkpoint (parity oracle):** `73c4e63dc74a2e67fb6bed0ed4c3d9e58e3525c5`.
**Branch base / activation:** `5322f105c3a84b440072100f13880c7b377e7c54`.

## What this slice delivers

1. **Five-job legacy-parity extraction.** The five legacy Interview AI
   provider jobs — `coach` (`/api/interview/review`), `revision`
   (`/api/interview/improve`), `planning_hints` (`/api/interview/nudge`),
   `grounded_example` and `generic_example` (`/api/interview/model-answer`,
   with Compare as the sequential grounded-then-generic composition) — move
   their prompt templates and provider configuration into immutable bundles
   under `prompts/interview/bundles/`, rendered byte-identically at runtime.
2. **Immutable bundle and release-set identity** per architecture §2: bundle
   content SHA-256 over domain-framed file bytes, `runtime_core_digest` over
   the guarded dependency manifest, `candidate_system_digest`,
   `interview_release_set_id`, and the `prompts/interview/control/registry.json`
   record. The initial release set records `initial_extraction: true`, zero
   evaluation runs, and the reserved parity sentinel
   `initial-extraction-parity@1` (invalid for any later behaviour-changing
   release).
3. **Fail-closed active-release resolution.** Runtime configuration
   `PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET` selects among recorded release
   sets. Missing or corrupt release identity answers Interview-only HTTP 503
   with zero provider dispatch; the rest of PeerSlate is untouched.
   Resolution begins only after every existing pre-provider refusal.
4. **Content-free `server_call` telemetry** (`telemetry-contract@1`,
   completed and frozen in `01_FROZEN_CONTRACTS.md`): one row per attempt,
   written once at response time through a dedicated append boundary, with a
   90-day purge design. No `client_view`, no member-linked or content-derived
   identifiers, no raw text anywhere.
5. **Bounded logging correction.** Interview logging no longer serializes
   raw exceptions (`detail=%s` and `%s`-formatted exception objects are
   removed); only normalized, content-free fields are logged.
6. **Tests, migration proposals, rollback evidence.** Parity fixtures and
   replay tests, identity/byte-lock tests, telemetry sentinel tests, SQL
   migration *proposals* (never applied here), and rollback evidence.

## What this slice must not change

For identical inputs the system produces identical rendered prompts,
identical provider settings (model, `max_tokens`, every explicit parameter
and every omitted parameter), identical request construction and call order,
identical validation, identical responses, status codes, headers, error
copy, signed-context behaviour, persistence effects, and UI behaviour. The
only operational deltas are the telemetry emission, the bounded logging
correction, and the (never-yet-reachable in production) fail-closed
`service_not_configured` path that exists only once release configuration
exists. Everything in the lane's exclusions list stays untouched: no later
slices, no prompt improvement, no new agents, no provider calls, no paid
evaluation, no migration application, no configuration change, no merge, no
deployment, no enablement, no production claims.

## Evidence index

| Document | Purpose |
|---|---|
| `01_FROZEN_CONTRACTS.md` | The slice-frozen contracts §7 defers: telemetry enums, exception allowlists, bounds, DDL, procedure signatures, purge job, pricing table, identity framing, instruction segment format. Frozen before implementation; amended per review corrections C1–C7. |
| `02_PARITY_EVIDENCE.md` | Oracle methodology, 40-fixture inventory with provenance, and replay results. |
| `03_ROLLBACK_EVIDENCE.md` | Retention-safe rollback story and the C8 first-deploy ordering for the future release gate. |
| `04_COMPLETION_REPORT.md` | The proportional completion record. |
| `05_SQL_DISPOSABLE_PROOF.json` | The executable disposable-database proof: 22 checks over permissions, duplicates, JSON shape closure, the retention boundary, and both rollback-guard branches. |
| `06_CORRECTION_PACKET.md` | The C1–C11 reconciliation table, verification battery, non-action statement, and remaining limitations for the correction round. |

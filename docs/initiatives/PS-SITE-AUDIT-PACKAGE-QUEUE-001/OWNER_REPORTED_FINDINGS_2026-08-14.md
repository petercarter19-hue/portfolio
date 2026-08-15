# Owner-reported audit findings - 2026-08-14

**Recorded:** 2026-08-14
**Status:** Documentation-only intake.
**Owner:** Pete.
**Runtime effect:** None. No reported symptom in this record is yet a confirmed
diagnosis, correction, deployment, or live verification.

## Outcome

Preserve Pete's current hands-on findings without interrupting the one-surface-
at-a-time Interview AI review. Route each observation to the package that must
later reproduce, diagnose, design, implement, and verify it. Do not reopen a
delivered package or infer a technical cause from the observed symptom.

## Truth labels

- **Owner-reported:** Pete experienced or observed the behavior.
- **Direction:** Pete stated the intended product behavior.
- **Not yet verified:** this documentation lane did not reproduce or diagnose it.
- **Future package:** any code, schema, prompt, model, visual, configuration, or
  release change requires fresh activation.

## Routed findings

### Opportunity Slate - urgent owner priority

**Owner-reported**

- Opportunity Slate currently feels substantially broken, including confusing
  or strange sidebar/workbench behavior.
- A public link imported on 2026-08-14 appears in the member's source list, but
  the expected extracted content or usable downstream result does not appear.
- Text extraction is not working reliably or producing a focused result.

**Owner direction**

- Raw text extraction should be focused and deterministic. A general-purpose
  LLM must not be the authority for fetching, decoding, normalizing, or
  extracting the source text.
- If an AI later interprets already extracted text into requirements or
  statements, that must remain a separate, labelled, reviewable proposal stage.
- A retained source row without usable content must show a truthful failure,
  retry, or recovery path rather than looking complete.

**Routed to**

- `PS-OPPORTUNITY-SLATE-CONTINUATION-001`, followed by a fresh Protected
  diagnostic/repair package for the exact reproduced failure.

**Required future verification**

1. Reproduce the 2026-08-14 source from its existing state without deleting or
   re-importing member data.
2. Trace URL intake, fetch result, response type, redirect handling, parser,
   text extraction, persistence, status transitions, refresh/resume, and
   requirement-analysis handoff separately.
3. Compare the source-list record with authoritative stored source/version and
   extraction-result records.
4. Test a valid public posting, inaccessible link, redirect, client-rendered
   page, PDF/document source, empty extraction, partial extraction, timeout,
   retry, and duplicate import.
5. Verify desktop, tablet, phone, refresh, second tab, and cross-device state.

### Interview Studio - product and interaction debugging

**Owner-reported**

- The left sidebar/rail has awkward dropdown placement, inconsistent spacing,
  and an unsettled rhythm.
- **New Session** does not behave consistently or as intended.
- The current session concept appears to impose restrictions without delivering
  a reliable benefit.

**Owner direction**

- Do not preserve sessions merely because they exist in the current interface.
- Before the next visual lock, decide whether the member actually needs a named
  session object or whether questions, attempts, History, and intentional
  resume provide the simpler mental model.
- Remove arbitrary restrictions unless a real data, privacy, recovery, or
  learning requirement justifies them.

**Routed to**

- `PS-INTERVIEW-STUDIO-EXPERIENCE-POLISH-001` for the experience decision and
  measured responsive review.
- A separate functional package if session creation, reset, persistence,
  History, or API behavior must change.

**Required future verification**

1. Define what **New Session** promises and trace its actual state transitions.
2. Test repeated creation, incomplete answers, reviewed answers, History,
   refresh, second tab, sign-out/sign-in, and failure recovery.
3. Inspect the left rail at desktop, iPad/tablet, 390px, 360px, large text,
   keyboard, and screen-reader states.
4. Compare a session-based model with a simpler question/attempt/History model
   before accepting new visual direction.

### Ask Pete AI - iPad functionality and latency

**Owner-reported**

- Ask Pete AI is not working properly on Pete's iPad or takes long enough that
  the experience appears broken.

**Routed to**

- The queued Ask Pete deep review in `PS-AI-AGENT-QUALITY-ROUND-2-001`.
- Any runtime correction requires its own Ask Pete diagnostic/repair package.

**Required future verification**

1. Test real iPad Safari alongside desktop and responsive emulation.
2. Measure open/render time, request start, server processing, provider time,
   validation, response transfer, and final paint separately.
3. Verify repeated requests, slow network, timeout, retry, unavailable state,
   tab/background behavior, keyboard/viewport changes, and source-opening.
4. Distinguish panel/layout failure from provider latency and server failure.
5. Preserve Ask Pete's public-approved-source boundary while diagnosing it.

### Interview AI direction - owner-review complete and still refinable

Pete accepted the Interview AI direction through Shared Constitution section 9,
the specialist map through 5B, adaptive length, structured output, session-free
orchestration, and private Role Context, and said later refinements remain
allowed. The durable records are
`PS-AI-AGENT-QUALITY-ROUND-2-001/06_INTERVIEW_AI_OWNER_DECISIONS.md` and
`07_INTERVIEW_AI_ACCEPTED_DIRECTION_CONTINUATION.md`.

The accepted direction includes private searchable practice History,
member-controlled similar-question retrieval for **Need a nudge?**, a useful
no-match prompt, server-derived identity, authorization before retrieval,
source-class separation, and specialist-specific least-privilege knowledge.
Acceptance is product direction, not a runtime prompt, schema, provider,
retrieval, migration, implementation, release, or deployment grant. Pete
selected Claude as the future architect after the decision round and relevant
read-first diagnosis; Claude sends the architecture package back to Pete and
Codex for reconciliation, and Pete accepts or revises it before implementation.

## Recommended continuation order

1. Treat the Interview AI owner-review direction as complete and preserve it
   for later Claude architecture and separately gated runtime packages.
2. Return immediately to Opportunity Slate for a protected, read-first
   diagnostic because Pete reports the core imported-source journey as broken.
3. Review Interview Studio's rail and session model before another visual lock.
4. Run Ask Pete's complete AI dossier with real-iPad latency evidence.

This order may be revised by Pete. It does not activate any child package.

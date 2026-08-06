# PS-DATA-FOUNDATION-001 slice 1 completion record

## Core record

- **Task/package and delivery path:** PS-DATA-FOUNDATION-001, Protected.
- **Outcome and member/site effect:** Added a provider-neutral AI request,
  source-version, answer, citation, handoff, decoding, evaluation, and
  privacy-safe trace boundary, with bounded inputs and classified failure
  diagnostics. Ask Pete's recruiter brief is the reference prompt contract.
  There is no route, UI, persistence, provider, deployment, or production
  effect.
- **Branch, base SHA, final implementation SHA, and changed paths:**
  `work/2026-08-06-ai-foundation-ask-pete-slice-1`; current-main base
  at implementation verification
  `5b58123ddecab840efdb35145f387e131f2686d6`; final implementation
  `05fd6688b4229ef84a34c7a5af3d560356381cd8`; changes are confined to
  `docs/initiatives/PS-DATA-FOUNDATION-001/`,
  `docs/initiatives/PS-ASK-PETE-AI-001/`, `services/ai_foundation/`,
  `prompts/ai_foundation/`, and `tests/ai_foundation/`. This record is a later
  documentation-only commit.
- **Verification performed and result:** 36 focused AI-foundation tests passed;
  Python compilation passed; the post-synchronization combined foundation,
  governance-pointer, site-rule, and operational-readiness run passed 98 tests
  and 43 subtests with one existing Flask-Limiter in-memory test warning;
  `git diff --check` passed; and the branch-to-main changed-path audit passed.
- **Release state:** Draft Azure PR 311 only. Not merged, deployed, or live.
- **Known limits, deferred work, or owner decision needed:** No runtime adapter,
  database, retrieval implementation, provider selection, semantic/model
  grading, visual presentation, source-opening UI, or human-message workflow
  is included. Those require separately authorized slices and their own
  verification.
- **Next action:** Review the draft PR and decide whether to accept this shared
  contract before authorizing a runtime consumer.

## Protected additions

- **Contract changed:** New additive contracts distinguish canonical source
  versions, evidence, interpretation, unknown boundaries, AI output, private
  handoff proposals, and payload-free operational traces.
- **Risk review:** Authorization is checked before provider use. Source subject,
  audience, purpose, content digest, and exact citation spans fail closed.
  Structured provider output rejects unknown fields, invalid enums, excessive
  sizes, mismatched claim citations, and non-private handoffs. Trace identifiers
  reject control characters, and trace sinks receive no payload fields.
- **Migration and rollback:** No migration exists. Rollback is a branch/PR
  revert because no runtime or persistence surface consumes the package.
- **Permission and negative-path evidence:** Tests cover unauthorized audience,
  cross-subject and stale sources, missing citation links, mismatched excerpts,
  inconsistent answer states, malformed provider output, bounded request and
  source failures, unavailable behavior, private handoff enforcement, broken
  diagnostic sinks, and payload-free traces/evaluation failures.
- **Independent review:** Not yet performed; the draft PR is the integration
  and review boundary.

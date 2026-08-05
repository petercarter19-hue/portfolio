# Independent review — OS-3 application release candidate

- Reviewer: Claude Opus 5, fresh delegated session at maximum effort, per
  Pete's 2026-08-05 model routing.
- Candidate SHA: `22296aa07838797a88aa31102b475674f6973b52`
  (base `9fe976be4b5aca0726b5e94d3152e8c03a06b321`; +7,780/−169, 42 files).
- Verdict: **APPROVE** — no blocking finding.

## Verified

- **Two modes, one truth boundary**: mode derived server-side only; anonymous
  state in a signed, size- and age-bounded token; anonymous grounding on the
  fictional demo library only, with zero DB or service calls across the whole
  anonymous flow (asserted by test); paste-only intake; spend guard fails
  closed at a default ceiling of zero; noindex on every blueprint response.
- **No aggregate verdict**: statuses are computed (`derive_alignment` /
  `covers_whole_clause`), never model-returnable; forbidden-key validation is
  recursive; adversarial probes (status field, smuggled prose, percentages)
  refused; templates/JS carry no verdict vocabulary beyond the negative
  disclaimer.
- **Grounded citations**: ordinal, clause, covering span, evidence id, and
  excerpt each re-validated against server-built vocabularies; stored strings
  re-sliced from server-held text, never the model's retyping; the model sees
  only opaque evidence ids.
- **AI proposes, people decide**: analysis runs only from explicit member
  actions; dictation and Save are inert and labelled; refusals return before
  any mutation; responses can never move a status.
- **Owner isolation**: server-derived identity at all 31 call sites; no
  caller-supplied owner/profile id on any of the 14 routes; the four OS-3
  procedures appear exactly once in an unchanged `database_service.py`.
- **Security**: no `|safe` or unescaped model output; same-origin write
  protection on every mutating route; per-route rate limits on the AI steps;
  no SQL string building; no secret to the client; no upload/import surface;
  no schema, pipeline, or preflight change in the diff.
- **Tests**: 292 passed / 1 skipped / 767 subtests targeted; 2,431 on full
  discovery with only the two accepted PowerShell-absent failures. Refusal
  paths exercised by name, not just happy paths.

## Non-blocking findings (follow-up backlog)

1. Evidence version re-read at save time instead of fenced to the
   analysis-time version; concurrent self-confirm can mislabel an excerpt's
   version. Fix: pass the analysis-time version as a fence the procedure
   verifies.
2. Evidence rail says "your own record" unconditionally, including demo mode.
3. No test for the oversize-excerpt refusal at the OS-3 validator (bound
   exists at three layers; probed manually).
4. A no-aggregate-column test reads the 001 file instead of 002 (correct
   coverage exists elsewhere).
5. No delimiter escaping in prompt composition (structurally contained; add
   defence in depth).
6. Dead `unittest.main()` mid-file in `test_opportunity_slate_ai.py`.
7. Room-wide "nothing is saved yet" copy predates this slice and reads oddly
   for the signed-in working store; recorded for a future audience decision.
8. Connected-evidence radio pre-checks by title, not key (cosmetic).
9. Checkpoint 2 survives a failed first analysis by design; named for the
   record.

The reviewer's full command-level verdict is preserved in the session record.

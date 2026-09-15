# PS-MVP1-MEDIA-INTEGRATION-001 evidence

Runtime-inert completion evidence for the MVP1 D private Resume media integration.
Production deployment, schema application, feature enablement, live
identities/providers, storage, scanning, generated catalog and publication remain
withheld.

## Current reviewed candidate — intake/draft contract repair

- Reviewed product candidate: `f07f359fd9e0141b42d61afdc2b49c410ba0417e`, parent
  `6839fde6bd27eebcec59960851e5dd0c19540d56` (non-destructive sync merge of
  accepted main `63f5bd64`), branch `work/2026-09-12-mvp1-media-integration-001`.
- Independent exact-candidate review: PASS completed `2026-09-15T00:06:14Z`,
  reviewer-reported model **Muse Spark 1.3**, under continuity reference
  `session:a8691db3-693b-4b2e-9d2f-37105eaf80c8` supplied by Pete. The reviewer
  could not introspect its own opaque session identifier, so that reference is
  recorded as the assigned continuity identity, not a self-verified one. The
  review independently verified all five committed blob SHA-256 values and the
  static call/transaction paths. Writer-reported test counts were relied upon and
  not independently rerun; review elapsed time and usage are unknown. The PASS is
  merge-admission evidence only and grants no deployment, schema, enablement or
  live-operation authority.
- Committed blob bytes (candidate `f07f359f…`):
  - `SQL FIles/Migrations/proposed/PS-RESUME-DRAFT-001_resume_drafts.sql`
    `374e9d76d3baa0099e72b4ce6bd548abfca2163b35c6d2b9b37313e5db4756e5`
  - `services/resume_draft_service.py`
    `ffaa0838a94e5f4203e42d68561c192db2e66abe0c1455254561e3ed2e64a8a2`
  - `services/resume_intake_repository.py`
    `a55bee6614c3ef1f3474d1ef50aaded9d06afa6e1ce77d3e8a68c0f3b348ab02`
  - `services/resume_intake_service.py`
    `2536c7c10c3e24030cf29ce58cc98751215d5906efee26230af2883fd6c6150b`
  - `tests/test_resume_intake_sql.py`
    `e7d2a8f8de2dea5f2f527dce1857fc3683ed4f543170f717bd192b7794b0d052`

### Repaired failure and contract

Required Azure build 2915 failed exactly two unchanged
`tests/test_resume_intake_sql.py` contract tests, caused by the earlier Package D
draft-callee change (`b416e349`), not by unrelated main movement:

1. The intake caller now stages the draft overlay with the authoritative
   `expected_draft_version` (one `_canonical_view` read; malformed versions fail
   closed) and `request_digest` from `ResumeDraftService.command_digest`, the same
   normalized semantic digest every other path commits. No placeholder or
   fabricated default is supplied; `CALLEE_COMMAND_KEYS["resume_draft"]` carries
   both fields.
2. The draft callee owns a transaction only when `@@TRANCOUNT = 0` (direct
   autocommit driver), commits only its own transaction on every returning path,
   and rolls back only when it owns one. Nested under the intake transaction it
   participates and commits or rolls back nothing, preserving complete
   outer-intake atomicity. Exact replay still wins before the expected-version
   fence, and the semantic receipt digest contract is unchanged.
3. Tests were strengthened rather than loosened: the contradicted
   `assertNotIn("BEGIN TRANSACTION")` assertion was replaced by positive checks of
   the ownership guard, guarded-commit↔`RETURN` count equality, absence of
   unguarded commit/rollback, single TRY/CATCH, replay-before-fence ordering, the
   authoritative version/digest values, and a deterministic concurrent-interleave
   `changed` conflict.

### Verification evidence for this candidate

- Both build 2915 failures reproduced before repair; repaired-contract negative
  control fails 3/3 on the pre-repair bytes and passes after.
- 561 non-browser tests pass (intake SQL/service/policy/jobs/proposals/routes,
  draft service/SQL/routes, media SQL/application/service/repository/routes,
  MyData drafts/intake/sources/service, database service, peerslate API,
  living-resume editor service, resume editor HTTP).
- 22/22 pinned-Chromium resume media browser journeys and 24/24 MyData/intake
  browser journeys pass with zero skips.
- Claim extension for the three intake files: control commit `254ba768`, merged to
  main as `63f5bd64`, before the repair candidate was frozen.

## Earlier reviewed candidate — two-finding closure (preserved)

- Candidate `3dfa36d722db9753685ad2661dd48c83a5f7c52c`, parent
  `373aa13d1b0b2a856000cf39932ae967b40ded94`, reviewed by Cursor Grok 4.6 with an
  exact-candidate PASS at `2026-09-13T19:02:58Z` (the continuity reference above).
  These bytes remain in the delivered candidate; the repair above did not touch
  them.
- Closed findings:
  1. **Concurrent identical text saves converge.** The shared atomic callback
     checks the live receipt under the store lock before mutation; the same
     request digest returns without another write and surfaces `replayed`, a
     different digest raises idempotency conflict.
  2. **Saved/review photo-version precision.** `review_placement_view` serializes
     versions above the JavaScript safe-integer range as canonical decimal text
     via `_browser_safe_version`, matching the staged preview, while internal
     Python/SQL values stay exact integers; malformed/overflow/bool/float inputs
     remain rejected.
- Blob hashes at that review: `b7fa1ad4…782424`, `0eafd227…0e4577`,
  `73fc32ca…da8909`, `1c750859…f89da4`, `417cc40f…581855d1` for the five files
  named in that review.

## Honest limits

Static and synthetic evidence only. No SQL engine, two-connection race or live
rollback execution; nested-transaction semantics are asserted structurally and
reasoned from T-SQL, not executed. Both proposed SQL migrations remain `gate:null`
and unapplied. No live storage, malware scanner, identity/provider, deployment,
screen-reader or owner visual acceptance proof. Repository merge admits reviewed
bytes only; every runtime state remains separately gated.

## Provider roles and retained incident

- DeepSeek in Codex initial implementation `1h58m35.049s` including
  `25m04.188s` of corrections; Sol Extra High repair interval `28m17.705s` (exact
  task cumulative `19,530,816` tokens including admission/preparation).
- The two-finding closure was completed by the owner-selected OpenCode/DeepSeek
  Flash receiver and reviewed by Cursor Grok 4.6; the intake/draft integration
  repair was completed by the same receiver and reviewed by Muse Spark 1.3. This
  bounded work is not an equivalent benchmark against the earlier full
  implementation.
- Manager sequencing incident: extension PR1014 initially passed local admission,
  then a refreshed local gate failed after main advanced by the
  caller-compatibility claim close; the manager incorrectly completed
  unconditionally after that failure. PR1014 merged as `f5ed3af2` under the
  required Azure policies, and the incident plus the supported reconciliation
  (preserve history, release clean control, merge current main preserving work,
  fresh write preflight, then release the writer) are retained in the
  outside-repository report `sol-correction-01-report.md`. The failed gate was not
  relabeled and old CI was not presented as validation of newer bytes.

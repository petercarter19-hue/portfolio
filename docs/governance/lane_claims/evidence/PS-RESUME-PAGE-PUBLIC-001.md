# Public resume page and publish (Lane D package 6): acceptance and execution record

**Goal:** the public resume page for members and its publish path, delivered in rounds. This record carries round D6a: the fail-closed type-transition publish guard.

**Authority:** Pete, 2026-10-13: "You can do the resume work." Owner ref `role:owner/pete-chat-2026-10-13/claude-manager-local_4fefa9f6/resume-page-claude-writer`. Writer `agent:claude/2026-10-14/resume-page-public` (Claude PC, Opus 5.5) for the Claude PC manager `session:16023c0e-7189-420e-8a4d-11f8012a9713`. Protected path; the independent exact-SHA reviewer is the MVP1 builder session `agent:claude/2026-10-14/guide-build`. Production, schema, configuration, enablement and paid AI calls are withheld.

**Rulings:** coordination `41e46cf` (B3 F1: confirmed private draft overlay on the same record key; the canonical type changes only at Publish; an unsupported transition is blocked with a named reason, never published under the old type and never silently dropped), `9fa9e68` (D6 takes the fail-closed publisher guard first, then the full codec), the builder's question `abc020e`, the B2 type mapping `269ab17`, and the manager's contract keys (2026-10-14): one optional object under `conversion` on the same owner draft-workspace item with `state` (only `confirmed_private` reaches the publisher), `base_record_type`, `destination_record_type`, `destination_parent_ref` (string or null), `base_content_token`, `base_access_revision` (integer) and the opaque `conversion_op_ref`; refuse when the state is `confirmed_private` and the destination type differs from the base type; the revision and token fields are informational in D6a; a malformed descriptor fails closed with a named reason.

## Rounds

- **D6a (this round):** the publisher side of the B3 conversion contract. Fail closed, no schema change, no second store.
- **D6b:** codec v1 extension for skill and highlight references, project arrays (`additional_project_urls`, category, organization), `credential.qualification_kind`, and the same-key cross-type, parent and links transition at Publish per `41e46cf`. Required before MVP1 acceptance.
- **Later rounds:** the public resume page for members with the evidence view ("Show the evidence (n)", "See it on the resume →"); the per-section owner preview reusing the Guide server's route extension; Publish consuming the shared Guide publication basis so private Hide is respected (B2 m2/m3).

## D6a design

- One shared reader `conversion_publication_blocker(item)` in `services/resume_publication_service.py` reads only the descriptor's shape. Absent or null means no descriptor and every existing path is unchanged. A well-formed confirmed private cross-type descriptor gives `publication_type_transition_unavailable`. Anything else present (not an object, missing or unknown keys, wrong types, another state, or no actual type change) gives `publication_conversion_descriptor_invalid`.
- `read_review_for_owner` reads the workspace, keeps today's stale/orphaned refusal for every non-conversion item, then returns an UNAVAILABLE result naming each converting item before media reads, codec checks or candidate building, so no destination value is merged, normalized or encoded under the old type.
- The shared Guide publication basis names the conversion in `blocked_items` and `ineligible_items` instead of `stale_draft`/`orphaned`, and the codec-format check never merges a converting item's values.
- Publish (`commit` through `_review_publish`) and the private preview keep the named reason as the conflict code instead of a generic stale label. Nothing is written: canonical, draft overlay, publication, receipts and review memory stay as they were.
- The member-visitor private preview (`_with_private_draft`) refuses a converting item before the old-type codec; the preview fails closed as unavailable, exactly like a stale draft.
- Routes are unchanged: the review route already carries named `blocked_items` (B2 m1, merged), and the commit and preview routes already return the conflict code.

## Acceptance plan (D6a, committed before code)

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-RESUME-PAGE-PUBLIC-001",
  "plan_sha": "610459d2b5940920068405d34c118af0697a8808",
  "baseline": [
    {
      "command": "python -B -m unittest tests.test_resume_publication_service tests.test_member_visitor_ai_repository tests.test_resume_publication_routes -q",
      "exit_code": 0,
      "observation": "Pre-change at main 1ce0150f (activation merge; publication code equals 465738bf): 88 tests PASS in 0.84s (54 publication service, 5 member-visitor repository, 29 publication route; fictional members, in-memory stores, placeholder key). No reader of a B3 conversion descriptor exists: read_review_for_owner rejects any stale or orphaned draft and otherwise merges row, item and proposed values under the old canonical type in the codec-format check and candidate builder, and _with_private_draft encodes proposed values with the old-type codec."
    }
  ],
  "criteria": [
    {
      "id": "confirmed_overlay_blocks_by_name",
      "expected": "When an owner draft-workspace item carries a well-formed conversion descriptor with state confirmed_private and a destination_record_type different from its base_record_type, read_review_for_owner and review_for_owner return no reviewed candidate, state unavailable, reason publication_type_transition_unavailable and blocked_items naming that item; the shared Guide publication basis is read_state blocked with that item and reason in blocked_items and ineligible_items and no candidate or change count; publish and the private preview refuse with that conflict code; this holds whether or not the item is selected for display; the review, publish and preview routes return 409 with that code and the review route names the item; canonical values, the draft overlay, publication state, receipts and review memory are unchanged.",
      "verification": "tests.test_resume_publication_type_transition (service and route cases), RED at main 465738bf."
    },
    {
      "id": "no_destination_value_reaches_old_type_codec",
      "expected": "With a converting item present, no destination value reaches build_owner_review_candidate, validate_candidate, policy_snapshot_from_entries, _codec_values, committed_source_bytes, validate_guide_text_limits or normalize_editor_values on any review, basis, publish or preview path, and the candidate builder is never called; a control case proves the same spies do observe those seams for an ordinary draft.",
      "verification": "Spy test in tests.test_resume_publication_type_transition that fails on the destination marker, plus the spy control test."
    },
    {
      "id": "malformed_descriptor_fails_closed",
      "expected": "A present descriptor that is not an object, misses or adds a key, has a state other than confirmed_private, a wrong-typed or empty field, a negative or non-integer base_access_revision, or no actual type change fails closed with publication_conversion_descriptor_invalid on review, basis and publish, never builds a candidate, never publishes under the old type, never crashes and writes nothing; the opaque conversion_op_ref is type-checked only, never parsed.",
      "verification": "Malformed-descriptor matrix and reader-contract test in tests.test_resume_publication_type_transition."
    },
    {
      "id": "stale_and_orphaned_keep_their_reasons",
      "expected": "A non-conversion stale or orphaned draft still refuses review with stale_draft and appears in the basis as stale_draft or orphaned, alone and beside a conversion item; a converting item is never labelled stale_draft or orphaned even when the workspace flags it, and carries only its conversion reason.",
      "verification": "Stale/orphaned tests in tests.test_resume_publication_type_transition; existing stale/orphaned tests in tests.test_resume_publication_service unchanged."
    },
    {
      "id": "non_conversion_publication_unchanged",
      "expected": "A draft with no descriptor, or with conversion null, gives the same reviewed digest, the same publication basis bytes and the same publish outcome as before; every existing publication service, publication route and member-visitor repository test passes unchanged.",
      "verification": "Null-descriptor equivalence test, the baseline suites, and the whole no-Playwright discover base vs candidate with the same failure set."
    },
    {
      "id": "replay_and_reads_write_nothing",
      "expected": "Repeated basis and review reads with a converting item return identical results and call no store save; a refused publish retried with the same request id refuses each time and records no receipt; a publish receipt made before the move replays its prior outcome without writing.",
      "verification": "Replay tests in tests.test_resume_publication_type_transition with save spies on the policy, draft and publication stores."
    },
    {
      "id": "sql_and_visitor_preview_stay_closed",
      "expected": "A SQL-backed publish with a converting item refuses before the command procedure is called; the member-visitor private preview refuses a converting or malformed item before the old-type codec and fails closed as unavailable, while a preview with no descriptor or a null descriptor is unchanged; no schema, migration or second store is added.",
      "verification": "SQL-shaped port and member-visitor preview tests in tests.test_resume_publication_type_transition; changed-path list shows no SQL or schema file."
    },
    {
      "id": "review_and_delivery",
      "expected": "Each new test fails at main 465738bf and passes at the candidate; the affected publication, Guide, draft, route and member-visitor suites pass; because the guarded review/basis functions sit on browser-exercised Guide and publication paths (behaviour unchanged without a descriptor), the retained strict 152 browser runner passes normally and as two simultaneous copies; one complete self-review of the diff; the MVP1 builder session independently passes the exact candidate before merge.",
      "verification": "Writer verification log, affected-suite runs, whole no-Playwright discover base vs candidate, independent review receipt, merge preflight and current-target Azure CI."
    }
  ],
  "candidate_sha": "200304d4339fa918372f6ae7ab6c5d8bb7e8199d",
  "checks": [
    {
      "criterion_id": "confirmed_overlay_blocks_by_name",
      "candidate_sha": "200304d4339fa918372f6ae7ab6c5d8bb7e8199d",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_type_transition.ConfirmedConversionPublicationGuardTests.test_confirmed_cross_type_overlay_blocks_review_basis_publish_and_preview_by_name + tests.test_resume_publication_type_transition.ReviewRouteTests + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6a-green.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6a-red.txt",
      "observed": "With a confirmed knowledge-to-project descriptor, review returns unavailable with reason publication_type_transition_unavailable and blocked_items naming the item, selected or not; the basis is blocked with no candidate or change count; commit and both previews raise that conflict code; the review, commands and preview routes return 409 with it and no destination text; all stores and review memory are byte-identical before and after. RED at base, GREEN at the candidate."
    },
    {
      "criterion_id": "no_destination_value_reaches_old_type_codec",
      "candidate_sha": "200304d4339fa918372f6ae7ab6c5d8bb7e8199d",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_type_transition.ConfirmedConversionPublicationGuardTests.test_no_destination_value_reaches_an_old_type_merge_normalizer_or_codec + test_spies_observe_the_same_seams_for_an_ordinary_draft + coordination:59a2cbd:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-PUBLIC-001_D6a.md",
      "observed": "Spies on build_owner_review_candidate, validate_candidate, policy_snapshot_from_entries, _codec_values, committed_source_bytes, validate_guide_text_limits and normalize_editor_values never see the destination marker on review, basis, publish or preview, and the candidate builder is never called; at base the marker reached validate_guide_text_limits. The control test shows the same spies fire for an ordinary draft. The reviewer's Guide-basis probe saw 0 seam calls."
    },
    {
      "criterion_id": "malformed_descriptor_fails_closed",
      "candidate_sha": "200304d4339fa918372f6ae7ab6c5d8bb7e8199d",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_type_transition.MalformedConversionDescriptorTests + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6a-green.txt",
      "observed": "Fifty-plus malformed shapes (non-object, list, empty, each key missing, unknown key, other states, wrong-typed, empty or padded strings, bool, float, string or negative revision, no type change) each give publication_conversion_descriptor_invalid on review, basis and publish, never build a candidate, and leave every store unchanged; any non-empty trimmed conversion_op_ref is accepted without parsing."
    },
    {
      "criterion_id": "stale_and_orphaned_keep_their_reasons",
      "candidate_sha": "200304d4339fa918372f6ae7ab6c5d8bb7e8199d",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_type_transition.StaleAndOrphanedReasonsTests + tests.test_resume_publication_type_transition.ConfirmedConversionPublicationGuardTests.test_a_valid_conversion_is_never_labelled_stale_or_orphaned + tests.test_resume_publication_service",
      "observed": "A non-conversion stale or deleted draft still refuses review with stale_draft and shows stale_draft or orphaned in the basis, alone and beside a conversion; a converting item flagged stale and/or orphaned by the workspace carries only publication_type_transition_unavailable. The existing publication service suite passes unchanged."
    },
    {
      "criterion_id": "non_conversion_publication_unchanged",
      "candidate_sha": "200304d4339fa918372f6ae7ab6c5d8bb7e8199d",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_type_transition.NonConversionPublicationTests + X:/PeerSlate/Claude/plans/resume-page/build-D6/baseline-d6a.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/affected-candidate.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/discover-base.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/discover-candidate.txt",
      "observed": "With conversion null the reviewed digest, reason and basis JSON equal the plain draft's, and publish shows the saved wording with change count 0 after. 1096 affected-suite tests pass (1 skipped); whole no-Playwright discover base 7825 vs candidate 7839 run with identical 12E/13F failure sets outside publication; the reviewer's discover also had identical sets."
    },
    {
      "criterion_id": "replay_and_reads_write_nothing",
      "candidate_sha": "200304d4339fa918372f6ae7ab6c5d8bb7e8199d",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_type_transition.ReplayAndRepeatedReadTests",
      "observed": "Three basis reads and three review reads with a converting item return identical results and call no save_owner on the policy, draft or publication store; the same refused publish request three times refuses each time and records no receipt; a publish receipt made before the move replays its prior receipt without writing and the guest view is unchanged."
    },
    {
      "criterion_id": "sql_and_visitor_preview_stay_closed",
      "candidate_sha": "200304d4339fa918372f6ae7ab6c5d8bb7e8199d",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_type_transition.SqlBackedPublishTests + tests.test_resume_publication_type_transition.MemberVisitorPreviewTests",
      "observed": "A SQL-port publish with a converting item raises the named conflict and commit_command is never called; the member-visitor preview raises SourcesUnavailable and _with_private_draft raises the reason name before _codec_values (zero spied calls, document unchanged), while absent or null descriptors preview exactly as before. Changed paths contain no SQL, migration or schema file."
    },
    {
      "criterion_id": "review_and_delivery",
      "candidate_sha": "200304d4339fa918372f6ae7ab6c5d8bb7e8199d",
      "kind": "automated",
      "result": "pass",
      "source_ref": "coordination:59a2cbd:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-PUBLIC-001_D6a.md + X:/PeerSlate/Claude/plans/resume-page/build-D6/strict-normal.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/strict-load-1.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/strict-load-2.txt",
      "observed": "All 14 new tests fail at base and pass at 200304d4; strict 152 normal 152/152 and two simultaneous copies 152/152 each at the candidate; complete self-review found no open finding; the independent reviewer agent:claude/2026-10-14/guide-build passed the exact SHA (311/311 affected, strict 152 second run 152/152 after one load timeout reproduced 5/5 on base and candidate). Merge preflight and Azure CI follow."
    }
  ]
}
```

## D6a execution record

- Candidate `200304d4` (plan `610459d2`); independent PASS by `agent:claude/2026-10-14/guide-build` (coordination `59a2cbd`).
- Writer logs: `X:/PeerSlate/Claude/plans/resume-page/build-D6/`; reviewer probes: `X:/PeerSlate/Claude/reviews/d6a-200304d4/`.
- Carried into D6b (reviewer note 1): the member-visitor preview should return the named `publication_type_transition_unavailable` while a move is in progress instead of the generic unavailable state.
- B3 dependency (reviewer note 2): B3 carries `conversion` through `ResumeDraftService.get_workspace` / `_present_item`, fixed as a B3 plan criterion.
- Merge is repository truth only: no deployment, schema or enablement. The claim stays active for D6b.

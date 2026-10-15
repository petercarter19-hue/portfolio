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

## D6a acceptance record (merged, squash `7dfbbbcf`, PR 1388)

D6a's plan was `610459d2`. All 8 of its criteria passed at the independently reviewed candidate `200304d4339fa918372f6ae7ab6c5d8bb7e8199d`:
- confirmed_overlay_blocks_by_name
- no_destination_value_reaches_old_type_codec
- malformed_descriptor_fails_closed
- stale_and_orphaned_keep_their_reasons
- non_conversion_publication_unchanged
- replay_and_reads_write_nothing
- sql_and_visitor_preview_stay_closed
- review_and_delivery

Proof: independent PASS by `agent:claude/2026-10-14/guide-build` (coordination `59a2cbd`); `package_acceptance.py check` PASS 8/8; merge preflight PASS; Azure CI 4644 green. That exact record is preserved on main at `7dfbbbcf` and in the branch history (`5d3691df`). D6b keeps the D6a guard exactly as it is.

## D6b round (codec extension, required before MVP1 acceptance)

**Assignment:** the manager, 2026-10-14. Publication must carry what B2 now stores, without silent loss:
1. skill `evidence_refs` (ordered) and up to four draft-root `highlight_refs`, resolved at Publish;
2. the project arrays and fields;
3. `credential.qualification_kind`.

Item 4 (the visitor-preview named reason) moved to the Guide server's next increment. The same-key cross-type transition at Publish is D6c, after B3.

**Rulings:** `269ab17` (type mapping), `8eff4fc` (references stay on the draft until D6; owner-bound; resolve only to saved, visible records; no copied text, no second store), `6b9a5b7` (display provenance), visitor AI never defaults on, unsupported SQL stays closed with input kept, no schema change.

**Design:**
- An additive evidence codec `resume-canonical-source.v2` = the v1 field list plus the new fields.
- When no v2-only field holds a value, the encoder writes v1 bytes under the v1 label; for every entry that main could already publish these are the exact v1 bytes. (Corrected after review: a project with month or year date_precision and no other new field publishes v1-labelled bytes with the v1 date_precision slot filled, where main left it N and blocked the publish; main's decoder reads them. A golden test for this case is a D6c item.) Existing and unchanged entries therefore keep their bytes and digests, even across a republish. The decoder reads both versions.
- v2 is used only by the qualified in-memory publication path. The SQL procedures produce v1, so a SQL-backed candidate that needs v2, list values or references is refused with a named reason before the command procedure runs.
- Resolved references are stored in the public copy as owner-bound identity strings, never as copied text. Their resolution is part of the reviewed candidate digest, and every dropped reference is named in the shared Guide publication basis.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-RESUME-PAGE-PUBLIC-001",
  "plan_sha": "f082b76995d740a9c3fbc449a0e4499317614f9b",
  "baseline": [
    {
      "command": "python -B -m unittest tests.test_resume_publication_service tests.test_resume_publication_contracts tests.test_resume_publication_projection tests.test_resume_publication_type_transition tests.test_member_visitor_ai_sources tests.test_member_visitor_ai_repository tests.test_resume_publication_routes -q",
      "exit_code": 0,
      "observation": "Pre-change at 51588a1c (accepted main, D6a and B2b merged): 145 tests PASS in 0.67s, with fictional members, in-memory stores and a placeholder key. The codec v1 field list has no qualification_kind, project_category, organization_name, project_role, project_url or list field. Wording and editorial deltas accept only scalars. Evidence accepts only resume-canonical-source.v1. A publish candidate carrying highlight_refs, skill evidence_refs, project links, category, organization, role, a non-day project date precision, or a publication/membership qualification_kind is blocked with a publication_codec_* reason."
    }
  ],
  "criteria": [
    {
      "id": "skill_evidence_refs_published",
      "expected": "At explicit Publish in the qualified in-memory path, a skill's ordered evidence_refs resolve against that same publication. Each reference must name this owner's saved accomplishment that is displayed in this publication with its displayed parent role, or a displayed role whose published summary still contains the referenced line. At most three are kept, in stored order, without duplicates. The public display row stores the resolved reference identities (opaque owner-bound identity strings), never copied text. The reviewed digest covers them, and a change to them counts as one change in the basis. Each dropped reference (not published, hidden, deleted, wrong type, line changed, over the limit) is named in the shared Guide publication basis with its own reason and never silently disappears. The private draft references are unchanged.",
      "verification": "New service tests, RED at 51588a1c and GREEN at the candidate: resolution, order, the limit, each drop reason, digest coverage, no copied text, owner isolation."
    },
    {
      "id": "highlight_refs_published",
      "expected": "Up to four draft-root highlight_refs publish in their stored order. Each must be this owner's displayed accomplishment with a metric value and a displayed parent role. The public copy records each highlight as an identity and order on the accomplishment's display row, never copied text, inside the reviewed digest. Each dropped highlight (not published, hidden, deleted, no metric, over four, duplicate) is named in the basis with its reason.",
      "verification": "New service tests, RED at 51588a1c and GREEN at the candidate."
    },
    {
      "id": "project_fields_published",
      "expected": "A project publishes project_url, additional_project_urls (up to two more, https with a host, unique, at most 1000 characters each, kept as strings and never fetched), project_category, organization_name, project_role and its dates with any date_precision. This holds in the public display and in the visitor-AI evidence (codec v2), with list order kept and nothing dropped. Links that break those rules block that publish with a named reason and stay unchanged in the draft. Fields still outside the codec (project_status, location_text, credential verification_url) stay blocked with their existing named reasons.",
      "verification": "New service and codec tests, RED at 51588a1c and GREEN at the candidate, including the decoded visitor-AI evidence."
    },
    {
      "id": "qualification_kind_sections",
      "expected": "A credential with qualification_kind publication or membership publishes under Publications or Memberships in the one shared section order, never as a Certification. Its evidence carries qualification_kind. A membership may publish without a name. Certification and absent kinds keep today's Certifications section and today's bytes; a license stays in Certifications and its kind is carried in the evidence.",
      "verification": "New service, projection and codec tests, RED at 51588a1c and GREEN at the candidate."
    },
    {
      "id": "codec_v2_writes_exact_v1_bytes",
      "expected": "The canonical-source encoder writes byte-for-byte the v1 bytes under the v1 codec label whenever no v2-only field holds a value, for every canonical type. It writes resume-canonical-source.v2 (v1 fields plus the new fields, with a closed list tag of strings) only when one does. The decoder reads both and rejects unknown codecs, tags, field orders, list members and trailing bytes. PublicationEvidenceVersion accepts both labels. Previously stored v1 publication snapshots and evidence still read, guest-read and preview unchanged, and existing published bytes stay byte-identical until the member's next explicit Publish.",
      "verification": "Codec golden-byte tests against main's encoder output for every type, round-trip and malformed-input tests, and an old-snapshot read test using bytes produced at 51588a1c."
    },
    {
      "id": "sql_stays_closed",
      "expected": "When the publication service is SQL-backed, any candidate that would need codec v2, a list value or a resolved reference is refused with a named reason before the command procedure runs, with input and drafts kept. The SQL migration and procedure files are unchanged, and there is no schema change or second store.",
      "verification": "SQL-shaped port tests asserting that commit_command is never called; the changed-path list shows no SQL file."
    },
    {
      "id": "provenance_and_visitor_ai_defaults_unchanged",
      "expected": "Display-selection provenance (6b9a5b7) and the default rule are unchanged: only never_selected new items default into the proposed display, visitor AI is never enabled by default or by a reference, and a reference never expands any permission or publishes a record the member did not include.",
      "verification": "Existing provenance tests unchanged, plus new tests showing that references to unselected or AI-off records grant nothing."
    },
    {
      "id": "d6a_guard_and_existing_behaviour_unchanged",
      "expected": "The D6a conversion guard and its 14 tests are unchanged. A publication without the new fields gives the same reviewed digest and published bytes as before, and the same basis apart from one added dropped_references list that is empty. Every existing publication, Guide, draft, route and visitor-AI test passes unchanged.",
      "verification": "The baseline suites, the affected suites, and the whole no-Playwright discover base vs candidate with the same failure set."
    },
    {
      "id": "review_and_delivery",
      "expected": "Each new test fails at 51588a1c and passes at the candidate. The affected suites pass. The retained strict 152 browser runner passes normally and as two simultaneous copies if a browser-exercised path changes. One complete self-review is done. Custody comes through the released codec files plus the exact-file extension. The Guide builder session independently passes the exact candidate before merge.",
      "verification": "Writer verification log, independent review receipt, merge preflight and current-target Azure CI."
    }
  ],
  "candidate_sha": "da054668943f8e620865b913e6e05b4d0f445bd9",
  "checks": [
    {
      "criterion_id": "skill_evidence_refs_published",
      "candidate_sha": "da054668943f8e620865b913e6e05b4d0f445bd9",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_service.D6bReferencePublicationTests + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6b-red.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6b-focused-final.txt + coordination:dddafd8:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-PUBLIC-001_D6b.md",
      "observed": "Skill evidence_refs resolve against the candidate's own displayed active entries: kept in order up to three as entry:/line: identities with no copied text; hidden, duplicate, invalid, missing, changed-line and over-limit references are named in dropped_references; a reference change is one reviewed change with a new digest; the private references survive Publish and the re-based overlay is not stale. RED at base, GREEN at the candidate."
    },
    {
      "criterion_id": "highlight_refs_published",
      "candidate_sha": "da054668943f8e620865b913e6e05b4d0f445bd9",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_service.D6bReferencePublicationTests.test_up_to_four_highlights_publish_in_order_with_named_drops",
      "observed": "Up to four highlights with metrics on displayed accomplishments under displayed roles publish as published_highlight_order 1..4 on their own display rows; missing-metric, hidden, duplicate and over-limit highlights are named; the draft highlight_refs stay unchanged after Publish."
    },
    {
      "criterion_id": "project_fields_published",
      "candidate_sha": "da054668943f8e620865b913e6e05b4d0f445bd9",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_service.D6bProjectAndQualificationTests + tests.test_resume_publication_service.D6bVisitorAiSourceTests + tests.test_resume_publication_projection.D6bProjectionV2Tests",
      "observed": "A project's url, two additional links, category, organization, role and year-precision dates appear unchanged in the public display and in decoded v2 visitor-AI evidence with list order kept; http, duplicate, three-extra, hostless and over-length stored links block as publication_project_links_invalid and stay unchanged; status, location and verification_url keep their existing blockers."
    },
    {
      "criterion_id": "qualification_kind_sections",
      "candidate_sha": "da054668943f8e620865b913e6e05b4d0f445bd9",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_service.D6bProjectAndQualificationTests.test_publications_and_memberships_publish_in_their_own_sections_with_their_kind + tests.test_resume_publication_projection.D6bProjectionV2Tests",
      "observed": "Publication and membership credentials (the membership with no name) publish in Publications and Memberships after Certifications with their kind in v2 evidence; a plain certification keeps v1 evidence; certification and absent kinds produce identical fields, and a license carries its kind in v2."
    },
    {
      "criterion_id": "codec_v2_writes_exact_v1_bytes",
      "candidate_sha": "da054668943f8e620865b913e6e05b4d0f445bd9",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_service.D6bCodecGoldenAndOldSnapshotTests + tests.test_resume_publication_contracts.D6bCanonicalSourceV2Tests + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6b-golden-v1.json + coordination:dddafd8:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-PUBLIC-001_D6b.md",
      "observed": "For all seven types the candidate encoder reproduces main 51588a1c's golden v1 hex and sha256, including certification kind, day precision and empty-list equivalents; v2 round-trips its list and fields; the decoder rejects v3, v2-without-v2-fields, swapped tags, list overflow and trailing bytes; evidence labels must match their bytes; a stored v1 publication reads unchanged twice. Reviewer confirmed; the month/year project precision note is recorded in the design section."
    },
    {
      "criterion_id": "sql_stays_closed",
      "candidate_sha": "da054668943f8e620865b913e6e05b4d0f445bd9",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_service.D6bSqlStaysClosedTests",
      "observed": "With a SQL-shaped port the v1 blockers still name project category, links and membership kind and commit_command is never called; a license credential publish refuses with publication_codec_sql_unavailable before the procedure with every store unchanged; no SQL or schema file changed."
    },
    {
      "criterion_id": "provenance_and_visitor_ai_defaults_unchanged",
      "candidate_sha": "da054668943f8e620865b913e6e05b4d0f445bd9",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_service.D6bReferencePublicationTests.test_reference_changes_are_reviewed_changes_and_never_expand_permissions + tests.test_resume_publication_service.GuideDisplayProvenanceTests + coordination:dddafd8:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-PUBLIC-001_D6b.md",
      "observed": "A reference to an unselected record adds it to neither display nor visitor AI and is named as not published; visitor-AI membership stays exactly the explicit choice; the existing display-provenance tests pass unchanged; the re-based overlay carries no permission expansion."
    },
    {
      "criterion_id": "d6a_guard_and_existing_behaviour_unchanged",
      "candidate_sha": "da054668943f8e620865b913e6e05b4d0f445bd9",
      "kind": "automated",
      "result": "pass",
      "source_ref": "tests.test_resume_publication_type_transition + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6b-affected-final.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6b-discover2-base.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6b-discover2-candidate.txt",
      "observed": "The 14 D6a guard tests pass unchanged; a role-only publication keeps v1 evidence and an empty dropped_references list; 1181 affected-suite tests pass (1 skipped) after B2c; whole no-Playwright discover base ee476daf 7850 vs candidate 7868 with identical 12E/13F failure sets (reviewer: identical sets too)."
    },
    {
      "criterion_id": "review_and_delivery",
      "candidate_sha": "da054668943f8e620865b913e6e05b4d0f445bd9",
      "kind": "automated",
      "result": "pass",
      "source_ref": "coordination:dddafd8:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-RESUME-PAGE-PUBLIC-001_D6b.md + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6b-final-strict-normal.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6b-final-strict-load-1.txt + X:/PeerSlate/Claude/plans/resume-page/build-D6/d6b-final-strict-load-2.txt",
      "observed": "New tests failed at base and pass at da054668; strict 152 normal 152/152 and two simultaneous copies 152/152 each; complete self-review done; custody through PR 1389 and PR 1390; the Guide-held test edits landed as B2c ee476daf; independent PASS by agent:claude/2026-10-14/guide-build at the exact SHA."
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

## D6b execution record

- Candidate `da054668` (plan `f082b769`); independent PASS by `agent:claude/2026-10-14/guide-build` (coordination `dddafd8`).
- Writer logs: `X:/PeerSlate/Claude/plans/resume-page/build-D6/`; reviewer evidence: `X:/PeerSlate/Claude/reviews/d6b-da054668/`.
- Merge is repository truth only: no deployment, schema or enablement. The claim stays active.

### Release notes (named release-plan item)

- **Codec v2 rollback boundary (forward-fix only).** Code before D6b cannot decode `resume-canonical-source.v2`. Once any member publishes a v2 entry, rolling the application back to a commit without a v2 reader would make that member's published resume and visitor-AI sources unreadable. Any production release that includes D6b must either be planned forward-only or name a rollback target that already carries a v2 reader.

### Carried to D6c

- A golden test for a month/year-precision project with no other new field (v1-labelled bytes with `date_precision` filled).
- Codec tightening: an encoder-side list cap matching the decoder's, and rejection of leading zeros in length and count prefixes.
- The same-key cross-type transition at Publish (F1), after B3's overlay is on main.

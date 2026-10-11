# Agent rules cleanup (successor): Pete-chosen agent models, Pete-assigned coordinator, slimmer CLAUDE.md

Writer `agent:claude/2026-10-11/rules-cleanup-writer` (Claude Code, Opus 5.5). Self-managed: the sole writer is also the package manager, under the Claude PeerSlate manager's assignment. Owner outcome: Pete, 2026-10-11: D4 ("now, in parallel" with onboarding), `agent:claude/2026-10-11/rules-cleanup/owner-decision/2026-10-11T0225Z-pete-d4-now-in-parallel`, and his later directions that nothing is added to CLAUDE.md or AGENTS.md and that he chooses agent models (Opus 5.5 for now), `agent:claude/2026-10-11/rules-cleanup/owner-decision/2026-10-11T0500Z-pete-no-additions-models-pete-chooses`.

## Why a successor

PS-AGENT-RULES-CLEANUP-001 fixed its evidence criteria before Pete's later directions. Its criteria then required D1 and D2 in AGENTS.md and "no Sonnet for agent work", which Pete no longer wants, and no transition can amend a claim's outcome or a plan's criteria. 001 is paused at checkpoint `6bf6c87dbb42edff074576f4efd2ceed2fae8dfb` (PR 1331, build 4449 succeeded). This package carries the same final content with criteria that match Pete's directions. Supersession of 001 waits for Pete's authorization.

## Path

Routine, with an independent exact-SHA review. Documentation and governance tests only: no runtime, template, script, lifecycle tooling, CI configuration, baseline, schema, product-AI model, deployment or production change. It is not Protected: it changes no identity resolution, authorization code, privacy boundary, canonical data, migration or shared infrastructure, and it removes no control. Review is independent because the shared rules bind both platforms; the manager arranges that review, a read-only look by Codex, and Pete's final OK before merge.

## Pre-change baseline and immutable criteria

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-AGENT-RULES-CLEANUP-002",
  "plan_sha": "d66c789ed0081d39ccf64807b94c4c8e8c0b7ecc",
  "baseline": [
    {
      "command": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_governance_pointers tests.test_site_rules",
      "exit_code": 0,
      "observation": "At 4d251ff3 (activation merge on ca28ae3f): 53 tests OK in 3.6 s. AGENTS.md is 719 words and CLAUDE.md 288. The routing document and CLAUDE.md pin 'Opus 5.5 or Sonnet 5.5' and a Sonnet route row; the coordinator test pins 'Codex remains the overall coordinator for now'; CLAUDE.md imports four files."
    }
  ],
  "criteria": [
    {
      "id": "agent_models",
      "expected": "CLAUDE.md and the routing document's Claude section say Pete chooses Claude agent models and that his current choice (Claude Opus 5.5: Extra High for architecture and independent review, High otherwise) stands until he changes it. The never-Haiku and Fable-only-on-request lines remain, no new hard model rule is added, 'Sonnet' no longer appears in CLAUDE.md or the Claude agent section, and the Product AI direction section is byte-identical to the base. The tests pin that Pete chooses and that no stale name remains, not the exact Opus wording.",
      "verification": "test_claude_routing_is_current_and_excludes_haiku and test_product_ai_direction_is_direction_only pass on the candidate; SHA-256 of the Product AI direction section at base and candidate; scratch mutations (removing 'Pete chooses' or 'until Pete changes it', adding a Sonnet line or row) fail the test."
    },
    {
      "id": "coordinator_control",
      "expected": "The routing document says Pete assigns the coordinator and coordination grants no exclusive technical privilege; AGENTS.md keeps its no-privilege sentence; AGENTS.md, CLAUDE.md and the routing document name no platform as the standing coordinator in either word order; DECISIONS.md records the current assignment by design. Tests pin the control, not a named platform.",
      "verification": "test_equal_platform_standing_without_supervisor passes on the candidate; scratch mutations restoring 'Codex remains the overall coordinator for now' or adding 'The overall coordinator is Codex.' fail it."
    },
    {
      "id": "no_startup_additions",
      "expected": "Nothing is added to AGENTS.md or CLAUDE.md: AGENTS.md ends at or below its base word count with its 750-word guard unchanged, CLAUDE.md ends at or below its base word count under its 300-word guard, and every pre-existing control sentence in AGENTS.md is still present.",
      "verification": "Word counts at base and candidate; diff review of AGENTS.md and CLAUDE.md; test_repository_agent_rules_are_short_and_link_to_current_authority passes and a scratch mutation that grows AGENTS.md past 750 words fails it."
    },
    {
      "id": "decision_record",
      "expected": "DECISIONS.md gains one appended 2026-10-11 entry recording Pete's decisions: agent models (Pete chooses; Opus 5.5 for now), the coordinator rule without changing the current assignment, D1 with the refinement that approval already given for an assigned outcome stays valid, D2, D4, where D1 and D2 are applied (Claude's START_HERE and the shared workflow once it exists, not the startup files), and provenance for the 2026-10-09 reference. No earlier line changes.",
      "verification": "git diff of DECISIONS.md against the base shows additions only at the end; diff review of the entry text."
    },
    {
      "id": "claude_entry_slim",
      "expected": "CLAUDE.md keeps the @AGENTS.md import and the mandatory pre-work gate, imports nothing else either at a line start or inline as @path, and names AI_WORKFLOW.md, CURRENT_BASELINE.yaml and DOCUMENT_CONTROL.md as read-when-needed pointers; the tests that read CLAUDE.md pass.",
      "verification": "test_supported_agents_enter_through_one_start_file and tests.test_site_rules pass on the candidate; scratch mutations adding a line-start or inline @docs/AI_WORKFLOW.md fail it."
    },
    {
      "id": "dispositions",
      "expected": "This evidence file records, once, which prior-audit and review items are resolved, open or deferred, with their owner where known.",
      "verification": "Manual review of the dispositions section on the candidate."
    },
    {
      "id": "no_regression",
      "expected": "The full no-Playwright unittest discover that CI runs shows no failure on the candidate that does not also occur on the base, the diff touches only the claimed paths, and Azure PR CI passes.",
      "verification": "X:/PeerSlate/Claude/tools/reviewer_run_without_playwright.py --discover on base and candidate; git diff --stat against the base; Azure PR build."
    }
  ],
  "candidate_sha": "3b4c708ecca9d0274b2d7496f07e17b8d82a9dcf",
  "checks": [
    {
      "criterion_id": "agent_models",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "3b4c708ecca9d0274b2d7496f07e17b8d82a9dcf",
      "source_ref": "C:/Users/peter/AppData/Local/Temp/claude/X--PeerSlate-portfolio/26d2fe57-009b-44c0-a3ca-98aee6d29331/scratchpad/rcw002-writer/cand_affected.log; C:/Users/peter/AppData/Local/Temp/claude/X--PeerSlate-portfolio/26d2fe57-009b-44c0-a3ca-98aee6d29331/scratchpad/rcw002-writer/mutation.log; X:/PeerSlate/Claude/reviews/2026-10-11_PS-AGENT-RULES-CLEANUP-001_independent-review.md (Confirmation: PS-AGENT-RULES-CLEANUP-002)",
      "observed": "CLAUDE.md and the routing Claude section say Pete chooses Claude agent models and that the Opus 5.5 choice (Extra High for architecture and review, High otherwise) stands until he changes it; the never-Haiku and Fable-on-request lines remain; no 'Sonnet' in CLAUDE.md or the Claude section; Product AI direction section SHA-256 identical at base and candidate (reviewer). test_claude_routing_is_current_and_excludes_haiku passes; probes removing 'Pete chooses' or 'until Pete changes it', dropping never-Haiku, or adding a Sonnet line or row all fail it."
    },
    {
      "criterion_id": "coordinator_control",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "3b4c708ecca9d0274b2d7496f07e17b8d82a9dcf",
      "source_ref": "C:/Users/peter/AppData/Local/Temp/claude/X--PeerSlate-portfolio/26d2fe57-009b-44c0-a3ca-98aee6d29331/scratchpad/rcw002-writer/cand_affected.log; C:/Users/peter/AppData/Local/Temp/claude/X--PeerSlate-portfolio/26d2fe57-009b-44c0-a3ca-98aee6d29331/scratchpad/rcw002-writer/mutation.log",
      "observed": "The routing standard says Pete assigns the coordinator and coordination grants no exclusive technical privilege; AGENTS.md keeps its no-privilege sentence; no rule file names a standing coordinator in either word order, and DECISIONS.md holds the current assignment by design. test_equal_platform_standing_without_supervisor passes; probes restoring 'Codex remains the overall coordinator for now', adding 'The overall coordinator is Codex.' or dropping 'Pete assigns the coordinator' fail it."
    },
    {
      "criterion_id": "no_startup_additions",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "3b4c708ecca9d0274b2d7496f07e17b8d82a9dcf",
      "source_ref": "git diff 4d251ff3..3b4c708e -- AGENTS.md CLAUDE.md; word counts; C:/Users/peter/AppData/Local/Temp/claude/X--PeerSlate-portfolio/26d2fe57-009b-44c0-a3ca-98aee6d29331/scratchpad/rcw002-writer/mutation.log",
      "observed": "AGENTS.md went from 719 to 710 words with its 750-word guard unchanged; its only change is the shortened expired-Workshop sentence, and every other sentence is unchanged. CLAUDE.md went from 288 to 285 words under its 300-word guard. A probe growing AGENTS.md past 750 words fails the size test."
    },
    {
      "criterion_id": "decision_record",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "3b4c708ecca9d0274b2d7496f07e17b8d82a9dcf",
      "source_ref": "git diff 4d251ff3..3b4c708e -- docs/governance/DECISIONS.md",
      "observed": "DECISIONS.md gains 43 lines appended at the end and loses none. The entry records agent models (Pete chooses; Opus 5.5 for now), the coordinator rule with the 2026-10-07 assignment unchanged, D1 with the refinement that approval already given for an assigned outcome stays valid, D2, D4, that D1 and D2 apply in Claude's START_HERE and the shared workflow rather than the startup files, and provenance for the 2026-10-09 reference."
    },
    {
      "criterion_id": "claude_entry_slim",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "3b4c708ecca9d0274b2d7496f07e17b8d82a9dcf",
      "source_ref": "C:/Users/peter/AppData/Local/Temp/claude/X--PeerSlate-portfolio/26d2fe57-009b-44c0-a3ca-98aee6d29331/scratchpad/rcw002-writer/cand_affected.log; C:/Users/peter/AppData/Local/Temp/claude/X--PeerSlate-portfolio/26d2fe57-009b-44c0-a3ca-98aee6d29331/scratchpad/rcw002-writer/mutation.log",
      "observed": "CLAUDE.md imports only @AGENTS.md, keeps the mandatory pre-work gate, and names AI_WORKFLOW.md, CURRENT_BASELINE.yaml and DOCUMENT_CONTROL.md as read-when-needed pointers. test_supported_agents_enter_through_one_start_file and tests.test_site_rules pass; probes adding a line-start or inline @docs/AI_WORKFLOW.md fail."
    },
    {
      "criterion_id": "dispositions",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "3b4c708ecca9d0274b2d7496f07e17b8d82a9dcf",
      "source_ref": "docs/governance/lane_claims/evidence/PS-AGENT-RULES-CLEANUP-002.md (Prior-audit dispositions); X:/PeerSlate/Claude/reviews/2026-10-11_PS-AGENT-RULES-CLEANUP-001_independent-review.md (Confirmation: PS-AGENT-RULES-CLEANUP-002)",
      "observed": "The dispositions table records each prior-audit and review item once as resolved, open with owner, or deferred, including the 001 review findings F1-F5 and N1-N3 and 001's pending supersession (open, Pete); the reviewer confirmed it."
    },
    {
      "criterion_id": "no_regression",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "3b4c708ecca9d0274b2d7496f07e17b8d82a9dcf",
      "source_ref": "C:/Users/peter/AppData/Local/Temp/claude/X--PeerSlate-portfolio/26d2fe57-009b-44c0-a3ca-98aee6d29331/scratchpad/rcw002-writer/base_discover.log; C:/Users/peter/AppData/Local/Temp/claude/X--PeerSlate-portfolio/26d2fe57-009b-44c0-a3ca-98aee6d29331/scratchpad/rcw002-writer/cand_discover.log; Azure PR 1339 build 4474",
      "observed": "Full no-Playwright discover: base and candidate each 7,594 run, 271 skipped, 12 errors, 14 failures, all local-environment cases present before this change (Darwin/IPv6/permission/DNS cases, two import errors, the known worktree-lifecycle PID test). Two IDs differ: test_read_preflight_passes_in_the_current_worktree failed only in the candidate scratch clone because its origin was a local path, and passes in the real durable worktree; a DNS-timing test failed only on base and its module passes on rerun. The diff touches only the 6 claimed paths. Azure PR build 4474 succeeded."
    }
  ]
}
```

## Design notes

- **CLAUDE.md imports (E).** Claude Code loads every `@import` in full at startup, so imports never save context. Before this change CLAUDE.md imported four files (about 2,650 words with itself), loaded into every session, including read-only questions, and read from the local checkout, which can be behind Azure (the shared checkout was two commits behind `origin/main` during this package). Only `@AGENTS.md` remains imported: it carries the mandatory pre-work gate, which already sends every write to `START_HERE.md`, the fetched baseline and the claim. `AI_WORKFLOW.md`, `CURRENT_BASELINE.yaml` and `DOCUMENT_CONTROL.md` are now named pointers read from fetched `origin/main` when needed; AGENTS.md links all three. This saves about 2,360 words per Claude session and matches Codex, whose startup reads AGENTS.md without those imports. `test_supported_agents_enter_through_one_start_file` now pins the AGENTS.md import, the gate and the three pointers, and that none of them is imported either at the start of a line or inline as `@path`; `tests/test_site_rules.py` passes unchanged because its pinned strings remain.
- **CLAUDE.md trims.** The ownership-transfer paragraph now points at `docs/governance/MANAGER_SESSION_HANDOFF.md`, which holds the full requirement (exact source, receiving platform and access identifiers, explicit acceptance); the no-credential rule stays in CLAUDE.md. "Azure DevOps is repository authority. Never push directly to `main`." was removed from CLAUDE.md only; the imported AGENTS.md states both. CLAUDE.md is 285 words against its 300-word guard (288 before this package).
- **AGENTS.md size.** AGENTS.md gains nothing. Its only change is the shortened expired-Workshop sentence (the wording the tests pin is kept). It is 710 words, down from 719, under its original 750-word guard.
- **Coordinator (B, T5).** The routing standard states the durable control (Pete assigns the coordinator; coordination grants no exclusive privilege; no platform-exclusive gate) and points to `DECISIONS.md` for the current assignment. AGENTS.md keeps its original "Coordination grants no exclusive technical privilege" sentence. The 2026-10-07 assignment of Codex as overall coordinator is unchanged; only the wording moved. Tests reject the retired phrasing in either word order ("X remains/is the coordinator", "the coordinator is X") in AGENTS.md, CLAUDE.md and the routing standard; DECISIONS.md names the current assignment by design.
- **Model pins (A, T5).** The tests pin that Pete chooses agent models and that his choice stands until he changes it, the unchanged never-Haiku and Fable lines, and that no stale model name remains (no `Sonnet` in the Claude agent section or CLAUDE.md, and the old bold Fable/Sonnet/Opus 5 names nowhere in the routing standard). They do not pin the current Opus wording, so Pete's next change is a one-line edit to the table and CLAUDE.md.
- **Decision references (D).** The two 2026-10-11 references are this package's owner outcome references. The DECISIONS.md entry names PS-AGENT-RULES-CLEANUP-001, the package D4 first activated; this successor applies the same content unchanged. The 2026-10-09 decision was given to the then Claude manager and is recorded on the Claude side (Claude `START_HERE.md`, "Models (Pete, 2026-10-09)"). `DECISIONS.md` now says its opaque reference was recorded on 2026-10-11 by this writer from that record, and that the D4 selection covers applying it.

## Prior-audit dispositions (F)

Sources: the 2026-10-10 Claude agent-rules blocker review (B1-B16, which rechecked the 2026-10-09 parity audit's A1-A12 and C1-C13), Codex's 2026-10-11 workflow audit (findings 1-12), Codex's 2026-10-10 answers R1-R10 and the 2026-10-11 reconciliation items T1-T8. "Here" means this package.

| Item | Status | Where it stands |
|---|---|---|
| B2, R6 (rules fix blocked by the load-test claim) | Resolved | PS-DELIVERY-LOAD-TEST-RULE-001 merged (c8230e83) and closed (e350b9a5). |
| Audit 5, blocker review 3a (model routing duplicated, pinned, and missing the Opus-only rule) | Resolved here for Claude agent routing | Routing standard, CLAUDE.md, tests and DECISIONS agree. Codex's own default model (B10, R2) stays with Codex. |
| R10, T5, prior A7 (coordinator pinned to a named platform) | Resolved here | Pete assigns the coordinator; tests pin that control. |
| Audit 1, B9, R3 (approval rules differ by platform) | Recorded here; applied outside the repository | Pete's D1 (with the refinement that approval already given for an assigned outcome stays valid) and D2 are recorded in DECISIONS.md. By Pete's direction they are not added to AGENTS.md or CLAUDE.md. Claude's START_HERE applies them (manager, 2026-10-11); the shared workflow Codex is writing will carry them for both platforms. Open, Codex, until that lands. |
| Audit 8 (long startup chains) | Partly resolved here | CLAUDE.md imports cut by about 2,360 words; AGENTS.md and CLAUDE.md both end smaller than they started. The START_HERE ordinary-versus-rare split is deferred (follow-up). |
| Audit 11 (dispositions, not repetition) | Resolved here | This table. PS-CI-TELEMETRY-FIXTURE-SCAN-001 is still an active Codex claim. |
| B1, B16, audits 2 and 3 (stale NOW, many NOW writers) | Resolved on the Claude side | The manager rewrote NOW, START_HERE and the global CLAUDE.md on 2026-10-11; NOW has one writer. Not repository files. |
| Audit 12 (Mac proposal ceremony) | Resolved by agreement | Reconciliation section 1; Mac follow-through is Claude Mac's. |
| Audit 9, T4 (memory index can revive old policy) | Open, Claude manager | Memory index shrink in progress; Jev guidance is Codex's. |
| Audit 4, R2, B10, T7 (Codex project on C:, Codex default model, Codex state hygiene) | Open, Codex | Local Codex configuration and notes. |
| Audits 6 and 7, B8, R4, T1-T3 (portable notes, handoff discovery, shorter handoffs, waiting-on-Pete line, cold-start proof) | Open, coordination repository | Shared/WORKFLOW.md (Codex writes, Claude reviews) after D3. |
| B5 (`.claude/launch.json` points at a missing `venv`) | Deferred | Out of scope here; follow-up. |
| B3, B4, B6, B7 (Claude Code worktree isolation, absolute paths, per-command caller reference, `python -B` not `-I`) | Open in the repository; covered on the Claude side | Claude START_HERE states all four. Repository wording (routing line 285, CLAUDE.md host lines, the AGENTS identity sentence listing all three caller routes per R1) is a follow-up. The stray `.claude/worktrees/eloquent-elion-e9acfa` waits for Pete's OK in clean-up week. |
| Audit 10, R1 tooling, prior A1-A12 (refusal text, `claude/` branch validator, native Claude identity) | Deferred | A separate Protected tooling package; use `work/` meanwhile. |
| B11, prior C10 (START_HERE `authorize` lacks `--task-ref` and lease) | Deferred | START_HERE edits are out of scope; follow-up. |
| B12, prior C2, C3, C6, C7, R8 (classifier/preflight lockstep; full-history secret scan) | Deferred | Tooling and security/CI design packages; the existing scan stays required. |
| B13, R5 (closed-package worktree retirement) | Deferred | Clean-up week: original owners retire their own; otherwise the Protected closed-custody path with Pete's authorization. |
| B14, R7 (website work on the Mac) | Deferred | Needs its own Protected transfer outcome if selected. |
| B15 (Opus not enforced in Claude settings and launchers) | Open, Claude manager and Pete | Local settings. |
| R9 (ANTHROPIC_API_KEY startup and signing dependency) | Open | A separate Protected product/authentication package; nobody removes or rotates the key before it lands. |
| T6 (retire old sessions) | Resolved on the Claude side; claims open | NOW names the retired sessions. The onboarding claims still need the governed transfer before their next build; the Sage Mist claim was reassigned to its successor release owner and is now closed (ca28ae3f). |
| T8 (weight of the delivery process) | Deferred | A future package for Pete to select. |
| Independent review F5: `docs/governance/OWNER_CONTEXT_RAIL_STANDARD.md:104` still says "Sonnet implements, Opus reviews" | Deferred | Outside this claim. The routing standard governs models (packages name roles, not model versions). Owner: a later docs cleanup. |
| Independent review of 001 candidate `ace32fca`: F1 (D1 refinement missing), F2 (scope of the no-authority sentence) | Resolved | By removal, per Pete's no-additions direction: D1 and D2 are not in AGENTS.md. The DECISIONS entry records D1 with its refinement. |
| Independent review of 001: F3 (inline `@` import), F4 (provenance of the 2026-10-09 reference), N1 (coordinator word order) | Resolved | Inline-import guard, provenance clause in DECISIONS, second coordinator pattern. |
| Independent review of 001: N2 (Azure-authority line dropped from CLAUDE.md), N3 (criterion wording about naming a coordinator) | Informational | N2 needs no change; N3 is addressed by this package's coordinator criterion, which names DECISIONS as the record of the assignment. |
| Supersession of PS-AGENT-RULES-CLEANUP-001 (paused at `6bf6c87d`) | Open, Pete | The supersede transition needs Pete's authorization reference and this package closed; the manager will ask with other clean-up items. |
| Blocker review 4b extras: product AI direction rewrite, routing lines 84-88 and the sealed-broker section, CURRENT_BASELINE `next_gate`, old prompt files, WORKTREE_LIFECYCLE example paths | Deferred | Not in this package's scope. Product AI model routing is a separate owner decision. |

## Verification and review

- Candidate `3b4c708ecca9d0274b2d7496f07e17b8d82a9dcf` (plan `d66c789ed0081d39ccf64807b94c4c8e8c0b7ecc`) on base `4d251ff3`; write preflight PASS. The five rule and test files are byte-identical to PS-AGENT-RULES-CLEANUP-001 checkpoint `6bf6c87d`.
- Azure PR 1339 (replaces PR 1331), build 4474: succeeded.
- Independent review PASS on this exact SHA by `agent:claude/2026-10-11/rules-cleanup-reviewer`, after a CONDITIONAL review of 001's `ace32fca` whose findings are dispositioned above.
- Review nit N4 is not taken: the DECISIONS entry cites the D4 owner reference, while the second owner reference (`agent:claude/2026-10-11/rules-cleanup/owner-decision/2026-10-11T0500Z-pete-no-additions-models-pete-chooses`) is carried by the claim and this evidence. Adding it would be an unreviewed content change; a later docs touch can add it.
- Before merge: Codex's read-only look and Pete's OK. Merge, deployment and live states are separate; this package is documentation and tests only and needs no deployment.

# Governance cleanup for Pete's October 7 decisions

Writer `agent:claude/2026-10-07/governance-cleanup` (Claude Code, Opus 5.5; effort not inspectable from inside the session and reported unverified). Activation PR 1287 merged as a0dd095cb0705ea777247aeb8efa096d3f7b6cbc. Write preflight PASS at that head with origin/main 243eadde3036315ae9a9acb4c37b36e93b706941 (disjoint claim-only movement). Owner outcome `session:01a11384-f656-73b3-b57a-ad2952f1ffad/owner-decision/2026-10-07-governance-cleanup`. Documentation and test-assertion package only: no product code, CSS/theme behavior, AI provider, configuration, schema, deployment or production change.

## Scope

Pete's direct 2026-10-07 decisions: equal standing for any assigned capable platform with no Codex supervisor or platform-exclusive gate; Pete chooses who creates designs and approves images (no exclusive ChatGPT creator); no colour or palette rules; Claude routing Opus 5.5 and Sonnet 5.5 only, no Haiku, Fable only on Pete's explicit request; product AI direction Foundry for routine features and Sonnet 5.5 later for onboarding Guide and Ask Member AI (direction only); no blanket release approval, Pete says case by case, exact-main-SHA plus authorization-reference mechanics unchanged; Codex stays coordinator; cross-company review undecided; Protected independent review kept. Stale-fact reconciliation: live release identity, expired Workshop standing decision, dormant safe-custody wording, routing-only review row, mismatch-register contradiction, and package-manager recording.

Trust rules preserved unchanged: private by default with server-derived identity and authorization; source/fact/proposal/projection separation; AI proposes, people decide; one writer per surface, exact-candidate review, PR and CI, never push to main; truthful implemented/reviewed/merged/deployed/accepted states. Historical records stay as history.

Live release verified read-only before editing: `https://peerslate.com/healthz` returned release `f4e77a0ff29a68053e2b4b2e`; `scripts/release_identity.py` derives exactly that value from source 27d6fdb165acfd610b21e86079944e956aae3fdc and Azure build 4259; Azure run 4259 (20261007.31) is a succeeded manual main run with `forceProductionDeploy=true`, matching `manualProductionSourceVersion`, an authorization reference, and `schemaAction=none`, finished 2026-10-07T17:13:54Z.

Pre-existing failures outside this package, observed on the pristine a0dd095c tree with `python -B -m unittest tests.test_delivery_preflight tests.test_worktree_lifecycle tests.test_package_registry tests.test_control_room tests.test_dark_theme_availability` (478 tests, 909.8s, FAILED failures=4): three Playwright browser tests in `DarkThemeStaysLightInABrowserTests` expect body ink `rgb(6, 26, 58)` but the current Sage Mist styling renders `rgb(40, 79, 59)` (they run only where Chrome and Playwright exist), and `test_ephemeral_invocation_lease_blocks_concurrent_retirement` saw a different process ID for the lease than the launched process (12716 != 55056), a Windows launcher artifact. This documentation package changes neither surface; they are reported as a follow-up, not resolved here.

## Implementation notes

- Plan committed as 7c6999ff3d2b338ccfd499a6e11d54ff614055f6 before any implementation commit.
- Scope extension: claim-only extend-surfaces PR 1291 (build 4280 succeeded, squash-merged as 1e564144058ed26fb319bdaf88cab289b29c687c) appended `docs/governance/OWNER_CONTEXT_RAIL_STANDARD.md`; it was held until onboarding transfer PR 1290 merged at the manager's request. The control lease was released afterwards. Main (a1aefe58, then 1e564144) was merged into the implementation branch with an ordinary two-parent merge; that movement touched only claim files outside this package.
- The expired 2026-08-27 Workshop standing decision is qualified as expired rather than deleted in AGENTS.md and START_HERE.md, because unclaimed `tests/test_delivery_preflight.py` (`test_standing_workshop_authority_and_continuity_are_narrowly_routed`) requires both files to keep naming it.
- The baseline note carries forward, without re-verifying, the August record that Workshop authenticated private two-member live proof remains pending.
- Code still calls `claude-haiku-4-5` in `app.py`; the routing doc therefore says new work selects no Haiku and existing calls wait for a governed replacement, rather than claiming the product has none.
- Context-rail standard: removed "Deep Navy Gold tokens only" and "exactly one gold active state"; the historical description of the JOURNAL-01 reference and the owner-acceptance rule for palette consolidation remain.
- Not changed (outside claim, historical or package-scoped): initiative records, CURRENT_STATE/ACTIVE_INITIATIVES snapshots, older DECISIONS entries, control-room architecture notes.

## Pre-change baseline and immutable criteria

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-GOVERNANCE-CLEANUP-001",
  "plan_sha": "7c6999ff3d2b338ccfd499a6e11d54ff614055f6",
  "baseline": [
    {
      "command": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_governance_pointers tests.test_site_rules tests.test_operational_readiness",
      "exit_code": 0,
      "observation": "At a0dd095c: 79 tests OK. Pinned wording includes the exclusive ChatGPT visual-creator phrases, the GPT-6.1 routing table, and August release run 1761/ebc70287/de34c238 with updated_at 2026-08-30."
    },
    {
      "command": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_delivery_preflight tests.test_package_registry tests.test_control_room",
      "exit_code": 0,
      "observation": "At pristine a0dd095c: 316 tests OK, including CurrentRepositoryTests.test_standing_workshop_authority_and_continuity_are_narrowly_routed, which requires AGENTS.md and START_HERE.md to keep mentioning the standing bounded Workshop decision."
    }
  ],
  "criteria": [
    {
      "id": "equal_standing",
      "expected": "Current authority states that any assigned, access-verified capable platform may architect, build, review, merge and release within its claim; no Codex supervisor or platform-exclusive gate; Codex remains coordinator for now; cross-company review is not mandated; Protected independent review remains required.",
      "verification": "Diff review of AGENTS.md, CLAUDE.md, AI_WORKFLOW.md and the routing doc, plus updated governance-pointer assertions."
    },
    {
      "id": "owner_selected_design",
      "expected": "No current authority names ChatGPT as sole or exclusive design creator; each former site says Pete chooses who creates designs and Pete approves the images; locked-authority fidelity, non-material adaptation limits and Pete's visual acceptance remain.",
      "verification": "Repository search of the claimed current-authority files for exclusive-creator wording and a replacement test asserting the new rule and the absence of the old one."
    },
    {
      "id": "no_colour_rules",
      "expected": "The baseline theme line, the site-rules default palette/theme statement and any palette mandate in claimed authority are removed; the context-rail standard's palette mandate is removed after a supported extend-surfaces transition, or recorded as a follow-up if that transition is refused or would delay the cleanup; no CSS, template, script or theme behavior changes.",
      "verification": "Diff limited to claimed docs/tests; new no-colour-rule assertion; test_dark_theme_availability shows no failure beyond the pre-existing set recorded below."
    },
    {
      "id": "model_routing",
      "expected": "Claude routing lists only Opus 5.5 and Sonnet 5.5, forbids Haiku, allows Fable only on Pete's explicit request; product AI direction (Foundry routine, Sonnet 5.5 later for onboarding Guide and Ask Member AI, no Haiku in product) is stated as direction without code change; the final-review row is clarified as model choice when a review is assigned, not a universal trigger.",
      "verification": "Diff review and updated routing assertions."
    },
    {
      "id": "release_and_facts",
      "expected": "No blanket per-release approval rule; Pete states case by case when he must approve; exact main SHA plus authorization reference remain. Baseline release facts name source 27d6fdb, run 4259 and release f4e77a0ff29a68053e2b4b2e, and the pointer test asserts the same derived identity. The expired Workshop standing decision no longer acts as a gate in AGENTS/START_HERE (qualified as expired) while DECISIONS history remains; live safe-custody wording no longer calls it dormant; the routing visual workflow no longer contradicts the visual standard on mismatch registers; package-manager recording is clarified without a claim-schema field; one DECISIONS entry records Pete's decisions.",
      "verification": "Updated operational-readiness pointer test, word-cap tests, diff review against healthz/Azure facts above."
    },
    {
      "id": "trust_and_tests",
      "expected": "Trust rules listed above remain present; all word caps hold; both baseline commands pass on the candidate without deleting coverage; test_worktree_lifecycle and test_dark_theme_availability show no failure beyond the pre-existing set recorded below.",
      "verification": "Rerun both baseline commands and the two suites with pre-existing failures on the reviewed candidate; required independent exact-SHA review."
    }
  ],
  "candidate_sha": "53595ef7062118faf6aca0f9a17857855525c294",
  "checks": [
    {
      "criterion_id": "equal_standing",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "53595ef7062118faf6aca0f9a17857855525c294",
      "source_ref": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_governance_pointers tests.test_site_rules tests.test_operational_readiness -> 85 OK (test_equal_platform_standing_without_supervisor)",
      "observed": "AGENTS, CLAUDE and the routing doc state equal standing for assigned access-verified platforms, no platform-exclusive gate or Codex supervisor, Codex as coordinator for now, no mandated provider pairing, and retained risk-based independent review."
    },
    {
      "criterion_id": "equal_standing",
      "result": "pass",
      "kind": "manual",
      "candidate_sha": "53595ef7062118faf6aca0f9a17857855525c294",
      "source_ref": "X:/PeerSlate/Claude/reviews/2026-10-08_governance-cleanup-review.md#verdict-pass",
      "observed": "Independent reviewer confirmed decision 1 applied with repository, review, production and credential authority still separate and Protected independent review unchanged.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-07/allowance-reviewer",
        "captured_at": "2026-10-08T05:20:26Z",
        "source_ref": "X:/PeerSlate/Claude/reviews/2026-10-08_governance-cleanup-review.md#verdict-pass"
      }
    },
    {
      "criterion_id": "owner_selected_design",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "53595ef7062118faf6aca0f9a17857855525c294",
      "source_ref": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_governance_pointers tests.test_site_rules tests.test_operational_readiness -> 85 OK (test_pete_chooses_material_visual_creator)",
      "observed": "No exclusive-ChatGPT creator wording remains in AGENTS, AI_WORKFLOW, routing, visual, story and page-purpose authority; each says Pete chooses the designer and approves the images while locked-authority fidelity and Pete's visual acceptance remain."
    },
    {
      "criterion_id": "no_colour_rules",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "53595ef7062118faf6aca0f9a17857855525c294",
      "source_ref": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_governance_pointers tests.test_site_rules tests.test_operational_readiness -> 85 OK (test_no_colour_or_palette_rule_in_current_authority); test_dark_theme_availability at candidate shows only the 3 pre-existing browser ink failures",
      "observed": "Baseline theme line, site-rules Deep Navy Gold statement and the context-rail 'Deep Navy Gold tokens only' and 'gold active state' mandates are gone; diff contains no CSS, template or script; dark-theme failures are unchanged from pristine main."
    },
    {
      "criterion_id": "model_routing",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "53595ef7062118faf6aca0f9a17857855525c294",
      "source_ref": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_governance_pointers tests.test_site_rules tests.test_operational_readiness -> 85 OK (test_claude_routing_is_current_and_excludes_haiku, test_product_ai_direction_is_direction_only, test_openai_role_defaults_require_actual_runtime_verification)",
      "observed": "Claude routing lists Opus 5.5 (Extra High architecture/review, High management/implementation) and Sonnet 5.5 Medium only, forbids Haiku, Fable only on Pete's request; product AI direction is stated as direction only; the final-review row creates no review requirement."
    },
    {
      "criterion_id": "release_and_facts",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "53595ef7062118faf6aca0f9a17857855525c294",
      "source_ref": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_governance_pointers tests.test_site_rules tests.test_operational_readiness -> 85 OK (test_current_pointer_lineage_and_ps_ops_authority_are_reconciled, test_release_approval_is_case_by_case_with_exact_mechanics, test_visual_routing_matches_the_visual_standard)",
      "observed": "Baseline names 27d6fdb/run 4259 and the derived /healthz release f4e77a0ff29a68053e2b4b2e; release approval is case by case with exact-SHA and authorization-reference mechanics unchanged; Workshop standing decision qualified as expired; mismatch-register contradiction removed; manager recording clarified; one DECISIONS entry appended."
    },
    {
      "criterion_id": "release_and_facts",
      "result": "pass",
      "kind": "manual",
      "candidate_sha": "53595ef7062118faf6aca0f9a17857855525c294",
      "source_ref": "X:/PeerSlate/Claude/reviews/2026-10-08_governance-cleanup-review.md#verdict-pass",
      "observed": "Independent reviewer re-verified live /healthz, the release-identity derivation and Azure run 4259, and confirmed no deploy-without-authorization reading.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-07/allowance-reviewer",
        "captured_at": "2026-10-08T05:20:26Z",
        "source_ref": "X:/PeerSlate/Claude/reviews/2026-10-08_governance-cleanup-review.md#verdict-pass"
      }
    },
    {
      "criterion_id": "trust_and_tests",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "53595ef7062118faf6aca0f9a17857855525c294",
      "source_ref": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_delivery_preflight tests.test_package_registry tests.test_control_room -> 316 OK; ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_governance_pointers tests.test_site_rules tests.test_operational_readiness -> 85 OK; test_worktree_lifecycle+test_dark_theme_availability at candidate -> 162 run, the same 4 pre-existing failures only",
      "observed": "Both baseline commands pass on the candidate, word caps hold (AGENTS 641, CLAUDE 288, AI_WORKFLOW 1094, baseline 842, visual 898), old assertions were replaced not deleted, and no failure beyond the recorded pre-existing set appears."
    },
    {
      "criterion_id": "trust_and_tests",
      "result": "pass",
      "kind": "manual",
      "candidate_sha": "53595ef7062118faf6aca0f9a17857855525c294",
      "source_ref": "X:/PeerSlate/Claude/reviews/2026-10-08_governance-cleanup-review.md#verdict-pass",
      "observed": "Independent reviewer confirmed all listed trust rules are unchanged and reran the suites with identical results to main.",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-07/allowance-reviewer",
        "captured_at": "2026-10-08T05:20:26Z",
        "source_ref": "X:/PeerSlate/Claude/reviews/2026-10-08_governance-cleanup-review.md#verdict-pass"
      }
    }
  ]
}
```

## Review and closeout

Independent review PASS with no findings at 53595ef7062118faf6aca0f9a17857855525c294 by `agent:claude/2026-10-07/allowance-reviewer` at 2026-10-08T05:20:26Z (report `X:/PeerSlate/Claude/reviews/2026-10-08_governance-cleanup-review.md`). Non-blocking follow-up from the reviewer: product code still calls `claude-haiku-4-5` (five `app.py` call sites plus the Ask Pete default); retiring them needs its own governed package. A separate follow-up should update the three dark-theme browser tests that still expect the pre-Sage-Mist navy ink.

# PS-AGENT-WORKFLOW-MINIMAL-001 acceptance

The structured block is the package's single acceptance record. Its baseline
and criteria were fixed before implementation; candidate results are filled
only after the reviewed commit exists.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-AGENT-WORKFLOW-MINIMAL-001",
  "plan_sha": "854b2efd2480bb803aaec722dc5267cfc8834f3b",
  "baseline": [
    {
      "command": "python -B -m unittest tests.test_governance_pointers",
      "exit_code": 1,
      "observation": "Initial inherited sparse checkout omitted tracked root control_room_projection.py, causing ImportError before test discovery. Retried with scripts on PYTHONPATH; same failure. git sparse-checkout disable restored the tracked file; this was worktree setup, not a product regression."
    },
    {
      "command": "python -B -m unittest tests.test_governance_pointers",
      "exit_code": 0,
      "observation": "After restoring the full registered worktree, all 30 tests passed before implementation."
    },
    {
      "command": "python -B -m unittest tests.test_agent_environment_readiness",
      "exit_code": 0,
      "observation": "10 tests ran and passed before implementation."
    }
  ],
  "criteria": [
    {
      "id": "instructions",
      "expected": "Repository AGENTS.md is brief, keeps the pre-work gate and trust boundaries, and links exact current lifecycle, role, workflow, and triggered authorities.",
      "verification": "Automated pointer/size test and complete-diff review."
    },
    {
      "id": "acceptance",
      "expected": "One package evidence record binds predefined criteria, source-specific semantic results, and an exact committed candidate; absent, failed, blocked, or stale proof is refused, while read-only work explicitly skips.",
      "verification": "Positive and negative helper tests, including manual/browser provenance and candidate drift."
    },
    {
      "id": "workflow",
      "expected": "START_HERE, AI_WORKFLOW, and completion guidance invoke the helper for an ordinary writable package without claiming a hard preflight or OS gate.",
      "verification": "Representative workflow test and manual review of the documented commands."
    },
    {
      "id": "regression",
      "expected": "Focused governance and acceptance tests pass on the candidate, including resolution of the observed pre-change governance import failure; no lifecycle or production authority changes.",
      "verification": "Candidate-bound test output, changed-path review, and independent exact-SHA review."
    }
  ],
  "candidate_sha": "359956ff5e1a8863182fa268b114fa48b410c854",
  "checks": [
    {
      "criterion_id": "instructions",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "359956ff5e1a8863182fa268b114fa48b410c854",
      "source_ref": "git:359956ff5e1a8863182fa268b114fa48b410c854:tests/test_governance_pointers.py#test_repository_agent_rules_are_short_and_link_to_current_authority",
      "observed": "Repository AGENTS.md is 628 words, below the 750-word test limit; the test verifies all Markdown authority targets exist and checks the delivery, trust, context-health, and acceptance pointers. The existing delivery-preflight governance test also verifies the standing bounded Workshop pointer retained after the trim."
    },
    {
      "criterion_id": "acceptance",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "359956ff5e1a8863182fa268b114fa48b410c854",
      "source_ref": "git:359956ff5e1a8863182fa268b114fa48b410c854:tests/test_package_acceptance.py",
      "observed": "The fixture exercises a plan commit, reviewed candidate, and evidence-only tail. It passes valid and reconciled histories, skips read-only work, and refuses absent, failed, blocked, unmapped, stale, generic, late-plan, mixed-plan, and unreviewed-code proof."
    },
    {
      "criterion_id": "workflow",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "359956ff5e1a8863182fa268b114fa48b410c854",
      "source_ref": "git:359956ff5e1a8863182fa268b114fa48b410c854:tests/test_package_acceptance.py#test_documented_normal_task_command_invokes_helper",
      "observed": "The representative writable-package test finds the helper invocation in START_HERE, AI_WORKFLOW, and the completion template, then runs that CLI against committed package evidence and receives pass."
    },
    {
      "criterion_id": "workflow",
      "result": "pass",
      "kind": "manual",
      "candidate_sha": "359956ff5e1a8863182fa268b114fa48b410c854",
      "source_ref": "git:359956ff5e1a8863182fa268b114fa48b410c854:AGENTS.md+START_HERE.md+docs/AI_WORKFLOW.md+docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md",
      "observed": "I reviewed the exact candidate text: it requires an agent to invoke the acceptance helper at writable completion, gives read-only work an explicit skip, and says the helper is neither delivery preflight nor an OS write gate. AGENTS retains the scoped standing bounded Workshop pointer to DECISIONS and START_HERE.",
      "provenance": {
        "observer_ref": "session:01a0e4af-fa35-7b72-8c47-fd29399040c3",
        "captured_at": "2026-09-27T23:28:12Z",
        "source_ref": "git:359956ff5e1a8863182fa268b114fa48b410c854:AGENTS.md+START_HERE.md+docs/AI_WORKFLOW.md+docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md"
      }
    },
    {
      "criterion_id": "regression",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "359956ff5e1a8863182fa268b114fa48b410c854",
      "source_ref": "command:python -B -m unittest tests.test_delivery_preflight.CurrentRepositoryTests.test_standing_workshop_authority_and_continuity_are_narrowly_routed tests.test_package_acceptance tests.test_governance_pointers@359956ff5e1a8863182fa268b114fa48b410c854",
      "observed": "All 51 focused tests passed on the reviewed candidate; the full delivery-preflight module also passed 263 tests, and the candidate diff passed git diff --check. Build 3700 exposed the missing standing Workshop pointer in AGENTS and failed exactly one of 6,963 tests; the six-line restoration passed that exact failing test. The initial governance import error came from an inherited sparse checkout; after restoring the full registered worktree, the same baseline command passed 30 tests before coding. No lifecycle or production authority file changed."
    },
    {
      "criterion_id": "regression",
      "result": "pass",
      "kind": "manual",
      "candidate_sha": "359956ff5e1a8863182fa268b114fa48b410c854",
      "source_ref": "session:01a0e4d5-55c7-7e41-93d9-0be5136e584f/final-review-pass/359956ff5e1a8863182fa268b114fa48b410c854",
      "observed": "Independent Astra xhigh reviewer returned PASS with no findings on this exact candidate and independently ran 51 focused tests.",
      "provenance": {
        "observer_ref": "session:01a0e4d5-55c7-7e41-93d9-0be5136e584f",
        "captured_at": "2026-09-27T23:26:00Z",
        "source_ref": "session:01a0e4d5-55c7-7e41-93d9-0be5136e584f/final-review-pass/359956ff5e1a8863182fa268b114fa48b410c854"
      }
    }
  ]
}
```

# Browser changes are load-tested before a PR

Writer `agent:claude/2026-10-07/peerslate-manager` (Claude Code, Opus 5.5). Routine, documentation and governance-test only: no runtime, template, script, CI configuration, schema, deployment or production change. Owner direction: Pete, 2026-10-08/09, after repeated CI re-queues for flaky browser tests ("CI load-test rule").

## Problem

Browser-test flakes surfaced only in Azure CI, where hosts are slower and loaded. Writers re-queued builds instead of fixing the cause, and a browser-test module that imported Playwright at module level broke the application-test job, which runs without Playwright (build 4334). The shared rules said nothing about either.

## Scope

- `AGENTS.md`: one bullet in "Ownership and delivery". Before a PR that changes browser-facing code or browser tests, run the affected browser suite normally and once under load. Rely on Playwright actionability; wait only for real application state, never fixed sleeps. Fix flaky tests or slow product paths instead of re-queueing. A changed browser-test module must skip cleanly when Playwright is unavailable. Documentation-only and control-only changes keep their existing shortcuts.
- `tests/test_governance_pointers.py`: one pointer test pinning those phrases so the rule cannot silently drop out.

## Pre-change baseline and immutable criteria

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-DELIVERY-LOAD-TEST-RULE-001",
  "plan_sha": "bb4fece16ac038704787d9885e3fbb1e99024399",
  "baseline": [
    {
      "command": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_governance_pointers",
      "exit_code": 0,
      "observation": "At a512a852: 37 tests OK in 0.16 s; no pointer test covers a load-testing rule."
    }
  ],
  "criteria": [
    {
      "id": "rule_text",
      "expected": "AGENTS.md carries one bullet requiring browser-facing changes to be run normally and once under load before a PR, relying on Playwright actionability with no fixed sleeps, fixing flakes instead of re-queueing, requiring changed browser-test modules to skip cleanly without Playwright, and keeping documentation-only and control-only shortcuts.",
      "verification": "Diff review of AGENTS.md."
    },
    {
      "id": "pointer_test",
      "expected": "tests.test_governance_pointers includes a test that fails if any of those rule phrases is removed, and the whole module passes on the candidate.",
      "verification": "Run tests.test_governance_pointers on the candidate; mutation check by removing one phrase in a scratch copy."
    },
    {
      "id": "no_collateral",
      "expected": "No governance suite that reads AGENTS.md changes outcome versus the pre-change bytes, Azure CI passes, and the diff touches only AGENTS.md, the pointer test and this package's evidence/receipt.",
      "verification": "Run tests.test_delivery_preflight, tests.test_worktree_lifecycle and tests.test_governance_pointers on the candidate and compare any failure against the pre-change plan commit; Azure PR CI; git diff --stat against the base."
    }
  ],
  "candidate_sha": "8d9c676787e2bc68b21faddca315ff8731382389",
  "checks": [
    {
      "criterion_id": "rule_text",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "8d9c676787e2bc68b21faddca315ff8731382389",
      "source_ref": "git diff a512a852..8d9c6767 -- AGENTS.md",
      "observed": "AGENTS.md gains exactly one bullet in 'Ownership and delivery': run the affected browser suite normally and once under load, rely on Playwright actionability with explicit waits only for real application state and never fixed sleeps, fix flaky tests or slow product paths instead of re-queueing, require changed browser-test modules to skip cleanly without Playwright, and keep documentation-only and control-only shortcuts."
    },
    {
      "criterion_id": "pointer_test",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "8d9c676787e2bc68b21faddca315ff8731382389",
      "source_ref": "X:/PeerSlate/Claude/scratch/2026-10-10_load-test-rule/pointers.log",
      "observed": "tests.test_governance_pointers on the candidate: 38 tests OK, including test_browser_changes_are_load_tested_before_pr. Mutation check: removing 'never fixed sleeps', 'Rely on Playwright actionability' or the shortcuts sentence from AGENTS.md each makes that test fail; the unmutated text passes."
    },
    {
      "criterion_id": "no_collateral",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "8d9c676787e2bc68b21faddca315ff8731382389",
      "source_ref": "X:/PeerSlate/Claude/scratch/2026-10-10_load-test-rule/loadrule_preflight.log; X:/PeerSlate/Claude/scratch/2026-10-10_load-test-rule/loadrule_fast.log; Azure PR 1325 build 4410",
      "observed": "tests.test_delivery_preflight 264 OK; tests.test_governance_pointers and tests.test_worktree_lifecycle 221 run with one failure, test_ephemeral_invocation_lease_blocks_concurrent_retirement (venv launcher PID differs from interpreter PID on this Windows runtime), which fails identically on the pre-change plan commit, so no outcome changes. Azure PR build 4410 for the candidate succeeded. The diff against a512a852 touches only AGENTS.md, tests/test_governance_pointers.py and this package's evidence and receipt."
    }
  ]
}
```

## Verification and review

- Candidate `8d9c676787e2bc68b21faddca315ff8731382389` (plan `bb4fece1`) on main `a512a852`; write preflight PASS.
- Azure PR 1325, build 4410: succeeded.
- Local: delivery preflight suite 264 OK; governance pointers 38 OK; worktree lifecycle 182/183 with one Windows-only failure that also fails on the pre-change plan commit.
- Self-review receipt: `lane_claims/receipts/PS-DELIVERY-LOAD-TEST-RULE-001.json` (writer reference; Routine path).
- Merge, deployment and live states are separate. This package is documentation and test only, and needs no deployment.

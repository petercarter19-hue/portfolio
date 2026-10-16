# PS-GOV-REVIEW-ROUNDS-001 evidence

Routine, self-reviewed, documentation plus one pinned test value. Pete's
selected outcome (2026-10-15): make the fewer-review-rounds practice a
permanent part of the PeerSlate delivery workflow. The manager supplied a
compressed section and set the `docs/AI_WORKFLOW.md` word cap in
`tests/test_governance_pointers.py` at 1200 (from 1100). Main's document is
1094 words and the supplied section 118 (the test's whitespace split), so the
section is trimmed to 105 words, keeping all five points, for 1199 in total.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-GOV-REVIEW-ROUNDS-001",
  "plan_sha": "cf1e8093a63f37b30781c2ba79f9b55de94ad871",
  "baseline": [
    {
      "command": "python -B -c \"import sys;b=open('docs/AI_WORKFLOW.md',encoding='utf-8').read();print(len(b.split()));sys.exit(0 if '## Fewer review rounds' in b else 1)\"",
      "exit_code": 1,
      "observation": "Printed 1094 and exited 1 at activation main fa89a917: the section is absent."
    },
    {
      "command": "python -B -m unittest tests.test_governance_pointers tests.test_package_acceptance tests.test_operational_readiness tests.test_site_rules",
      "exit_code": 0,
      "observation": "Ran 108 tests OK at fa89a917."
    }
  ],
  "criteria": [
    {
      "id": "section-present",
      "expected": "docs/AI_WORKFLOW.md has a 'Fewer review rounds' section directly after 'Delivery paths', applying to Bounded and Protected work with Routine work able to skip the map, and containing all five points (map before code; check like a reviewer before review; fix the pattern, not the instance; first review is end to end; visual work covers every page) in the manager's compressed wording, trimmed only to fit the cap.",
      "verification": "The section baseline command exits 0, and the inserted text is compared with the supplied wording."
    },
    {
      "id": "no-other-rule-change",
      "expected": "The AI_WORKFLOW.md diff is a pure insertion of that section, and the only test change is the AI_WORKFLOW.md word cap rising from 1100 to 1200, and the document stays under it.",
      "verification": "git diff of the two files against the activation main SHA, reviewed line by line."
    },
    {
      "id": "tests-pass",
      "expected": "The focused governance modules pass, and the whole no-Playwright discover shows no failure that main lacks.",
      "verification": "The focused baseline command at the candidate, and the no-Playwright discover at the candidate compared with the same run on the activation main."
    }
  ],
  "candidate_sha": "93b48bb2169a0bf744234f7c8e0a1fc64296faa8",
  "checks": [
    {
      "criterion_id": "section-present",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "93b48bb2169a0bf744234f7c8e0a1fc64296faa8",
      "source_ref": "local run at 93b48bb2: the section baseline command",
      "observed": "Printed 1199 and exited 0: the section is present. It sits directly after 'Delivery paths', applies to Bounded and Protected work with Routine able to skip step 1, and keeps all five points in the manager's compressed wording, trimmed by the six phrase edits listed in the self receipt.",
      "resolves_baseline_command": "python -B -c \"import sys;b=open('docs/AI_WORKFLOW.md',encoding='utf-8').read();print(len(b.split()));sys.exit(0 if '## Fewer review rounds' in b else 1)\""
    },
    {
      "criterion_id": "no-other-rule-change",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "93b48bb2169a0bf744234f7c8e0a1fc64296faa8",
      "source_ref": "git diff fa89a917 93b48bb2 -- docs/AI_WORKFLOW.md tests/test_governance_pointers.py; git grep for 1100 in scripts, tests and docs",
      "observed": "AI_WORKFLOW.md gains 14 lines and loses none: the new section only. The test diff is one line, the cap 1100 -> 1200. No other file pins the cap."
    },
    {
      "criterion_id": "tests-pass",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "93b48bb2169a0bf744234f7c8e0a1fc64296faa8",
      "source_ref": "local runs at 93b48bb2: python -B -m unittest tests.test_governance_pointers tests.test_package_acceptance tests.test_operational_readiness tests.test_site_rules; python -B reviewer_run_without_playwright.py --discover at fa89a917 and at 93b48bb2",
      "observed": "Focused modules: 108 tests OK. Whole no-Playwright discover: 7983 run, 379 skipped, 13 failures and 12 errors at both main fa89a917 and the candidate, with an identical failing-test list (local-only Windows/Darwin/IPv6/permission tests; none in governance)."
    }
  ]
}
```

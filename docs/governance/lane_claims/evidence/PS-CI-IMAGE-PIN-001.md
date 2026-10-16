# PS-CI-IMAGE-PIN-001 evidence

Protected (shared CI infrastructure), independent review, through_merge,
production withheld. Outcome: pin the Azure Pipelines hosted agent image in
`azure-pipelines.yml` so CI does not change when the hosted `ubuntu-latest`
label moves.

Image evidence, read-only, 2026-10-16. Every Initialize-job log of run 4733
(PR 1412, finished 2026-10-16T03:08Z) reports `Image: ubuntu-24.04`,
`Version: 20261012.334.1`, runner-images release `ubuntu24/20261012.334`,
agent 5.280.0. So `ubuntu-latest` resolves to ubuntu-24.04 today. GitHub's
changelog of 2026-09-17 says `ubuntu-latest` moves from Ubuntu 24.04 to
26.04 gradually between 2026-10-19 and 2026-11-19 (GitHub Actions); no Azure
Pipelines-specific date was found, but Azure hosted agents are built from
the same runner-images repository. Pinning `ubuntu-24.04` keeps today's image
either way. Python 3.12 stays.

Every job in `azure-pipelines.yml` takes its pool image from the single
`vmImageName` variable, so the change is that one value. No test pins this
value. `pipelines/azure-startup-qualification.yml` also uses `ubuntu-latest`;
it is outside this claim and reported as a follow-up.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-CI-IMAGE-PIN-001",
  "plan_sha": "199767abe2049ece91a49b3ed90f742fc5f326b0",
  "baseline": [
    {
      "command": "python -B -c \"import sys;b=open('azure-pipelines.yml',encoding='utf-8').read();sys.exit(0 if \\\"vmImageName: 'ubuntu-24.04'\\\" in b and 'ubuntu-latest' not in b and \\\"pythonVersion: '3.12'\\\" in b else 1)\"",
      "exit_code": 1,
      "observation": "Exited 1 at activation main 16520350: azure-pipelines.yml sets vmImageName: 'ubuntu-latest'."
    },
    {
      "command": "python -B -m unittest tests.test_azure_startup_qualification tests.test_community_revival tests.test_delivery_change_classification tests.test_delivery_preflight tests.test_interview_ai_dark_telemetry_infrastructure tests.test_interview_browser_ci_runner tests.test_interview_review_http_browser_ci tests.test_mvp1_acceptance_browser_runner tests.test_operational_readiness tests.test_public_search_dark_proof tests.test_resume_publication_browser_runner tests.test_schema_migration_path tests.test_site_rules tests.test_package_acceptance tests.test_governance_pointers",
      "exit_code": 0,
      "observation": "Ran 621 tests OK (skipped=2) at 16520350; the whole no-Playwright discover there ran 8008 (379 skipped, 13 failures, 12 errors, all local-only). The modules are every test module that reads azure-pipelines.yml, plus the acceptance and governance-pointer modules."
    }
  ],
  "criteria": [
    {
      "id": "image-pinned",
      "expected": "azure-pipelines.yml sets vmImageName: 'ubuntu-24.04' (the image run 4733 used), contains no 'ubuntu-latest', and keeps pythonVersion: '3.12'; every job still takes its pool image from $(vmImageName).",
      "verification": "The pin baseline command exits 0 at the candidate, and a grep shows every vmImage line in the file is $(vmImageName)."
    },
    {
      "id": "only-the-pin-changes",
      "expected": "The diff against activation main changes only the vmImageName line (plus an explanatory comment) in azure-pipelines.yml and this package's evidence file; no other pipeline, script, test, Azure setting, schema or deployment changes.",
      "verification": "git diff --stat and the full diff of 16520350..candidate, reviewed line by line."
    },
    {
      "id": "tests-pass",
      "expected": "The focused modules pass at the candidate, and the whole no-Playwright discover shows no failure that main lacks.",
      "verification": "The focused baseline command at the candidate, and the no-Playwright discover at the candidate compared with the same run at 16520350. The PR's own Azure CI run is the proof that the pinned image resolves; its Initialize-job log must report Image: ubuntu-24.04."
    }
  ],
  "candidate_sha": "e8232ece1beffc5e7969e6c285b15e5fb8cbdb2d",
  "checks": [
    {
      "criterion_id": "image-pinned",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "e8232ece1beffc5e7969e6c285b15e5fb8cbdb2d",
      "source_ref": "local run at e8232ece: the pin baseline command; grep -c 'vmImage: $(vmImageName)' azure-pipelines.yml; independent review 2f261cc",
      "observed": "The pin command exited 0: vmImageName is 'ubuntu-24.04', 'ubuntu-latest' no longer appears and pythonVersion stays '3.12'. The file has 16 vmImage lines: the variable plus 15 pools, all 'vmImage: $(vmImageName)'.",
      "resolves_baseline_command": "python -B -c \"import sys;b=open('azure-pipelines.yml',encoding='utf-8').read();sys.exit(0 if \\\"vmImageName: 'ubuntu-24.04'\\\" in b and 'ubuntu-latest' not in b and \\\"pythonVersion: '3.12'\\\" in b else 1)\""
    },
    {
      "criterion_id": "only-the-pin-changes",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "e8232ece1beffc5e7969e6c285b15e5fb8cbdb2d",
      "source_ref": "git diff --stat 16520350 e8232ece and the full diff; independent review 2f261cc finding 1",
      "observed": "Two files change: azure-pipelines.yml (one value from 'ubuntu-latest' to 'ubuntu-24.04' plus a three-line comment) and this evidence file. No other pipeline, script, test, Azure setting, schema or deployment changes."
    },
    {
      "criterion_id": "tests-pass",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "e8232ece1beffc5e7969e6c285b15e5fb8cbdb2d",
      "source_ref": "local runs at e8232ece: the focused baseline unittest command, and reviewer_run_without_playwright.py --discover at 16520350 and at e8232ece",
      "observed": "Focused modules: 621 tests OK (skipped=2), the same as at 16520350. Whole no-Playwright discover: 8008 run, 379 skipped, 13 failures and 12 errors at both main 16520350 and the candidate, with an identical failed-test list (local-only Windows tests). The PR's own Azure CI Initialize-job image is checked for ubuntu-24.04 before merge and recorded in the close record."
    }
  ]
}
```

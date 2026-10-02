# Published resume access and public navigation repair

Owner selected the existing public Pete Carter resume at `/petec/resume` and exactly two public destinations: My Resume and Interview AI. Private test-site drafts, authentication, provider calls, schema and held MVP enablement remain outside this outcome.

Bounded self-review passed against candidate `2e971d8217920fd9d4147891fc430fae222b3a44`. Reviewed the complete runtime and test diff against accepted main `1f5a5c0a976faae702323ac29224df3ac659d265`: public route behavior, generic-member isolation, anonymous/private boundaries, published-content labels, workspace return and unchanged feature availability. All 95 affected tests pass with no skips or unresolved findings. Tests exercised exactly the tracked bytes subsequently frozen in this candidate; no code changed after the run. The test-only provider placeholder matches CI and neither loads a real credential nor invokes a provider.

Initial PR1219 CI3952 passed the browser job but found three application regressions: the public account menu lost its workspace return, and two launchpad tests retained the previous four-card contract. The corrected runtime restores the workspace account link on public pages while private rooms keep their existing primary link. The three contracts now verify the public workspace return and the fifth, explicitly published-resume launchpad entry. Accepted claim-only extension PR1223 / main `1f5a5c0a976faae702323ac29224df3ac659d265` passed CI3958 and all required policies. Supported same-worktree reconciliation imported that claim; clean write preflight passed before those test edits.

Accepted original activation PR1218 / main `676fd7c1e2649f430dafa68d02830282a9f30ba7`; immutable preimplementation plan and acceptance criteria below are unchanged. Jev public-path-first advice was followed and observed helpful. Further regression/review checkpoints were skipped because the exact CI failures and required public-route, account, accessibility and privacy contracts determined the checks; no unresolved discretionary alternative could change the next action.

PR1219 is draft while the corrected candidate is prepared, preventing obsolete runtime checks during the reserved installer and citation delivery intervals. Release remains pending current-target required CI, accepted runtime merge and a separately manually queued exact-main-SHA web deploy authorized by owner events evt-5c6ebd60-8149-4ec1-b30f-821d5b46318b and evt-66bfeadd-3d45-46e1-8fab-16ffb79654be. No schema or configuration change is requested. No public MVP deployment is authorized by this navigation outcome.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-RESUME-ACCESS-NAV-001",
  "plan_sha": "60d26c2f14d9867ab86bef37e4bc1cf5d94e2816",
  "baseline": [
    {
      "command": "$env:ANTHROPIC_API_KEY='test-key-for-ci-only'; python -B -m unittest tests.test_navigation tests.test_public_nav_route_truth tests.test_shared_shell_convergence -q",
      "exit_code": 0,
      "observation": "45 existing tests pass while asserting the old public /app and Interview Studio destinations. Live existing /petec/resume returns the published career record; signed-in /app has no published resume destination."
    }
  ],
  "criteria": [
    {
      "id": "public_links",
      "expected": "Public primary navigation, overflow, phone menu, no-JavaScript navigation and public search expose exactly My Resume and Interview AI, targeting the existing published resume and AI mode.",
      "verification": "Rendered anonymous route matrix and destination href assertions."
    },
    {
      "id": "working_destinations",
      "expected": "Both anonymous links return usable pages; resume shows Pete Carter and AI mode is selected, including the Pete subdomain.",
      "verification": "Follow each declared link using anonymous Flask client and verify semantic content and selected AI view."
    },
    {
      "id": "signed_in_access",
      "expected": "Signed-in workspace and account/search navigation provide a clearly labelled Public Resume link without exposing a private draft or claiming fixture content belongs to another member.",
      "verification": "Synthetic signed-in render tests and direct public resume GET."
    },
    {
      "id": "privacy_preserved",
      "expected": "Generic public member navigation never inherits Pete destinations; private routes still require identity; private product navigation and flag availability retain existing behavior.",
      "verification": "Focused navigation, shell convergence and safe-return regression tests."
    }
  ],
  "candidate_sha": "2e971d8217920fd9d4147891fc430fae222b3a44",
  "checks": [
    {
      "criterion_id": "public_links",
      "result": "pass",
      "candidate_sha": "2e971d8217920fd9d4147891fc430fae222b3a44",
      "kind": "automated",
      "source_ref": "X:/PeerSlate/evidence/PS-RESUME-ACCESS-NAV-001/CORRECTED_CANDIDATE_TESTS.txt",
      "observed": "All public primary/menu/no-script/overflow representations render only My Resume and Interview AI with published resume and ?mode=ai hrefs; public search has exactly those two records.",
      "command": "$env:ANTHROPIC_API_KEY='test-key-for-ci-only'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_resume_access_nav tests.test_navigation tests.test_public_nav_route_truth tests.test_shared_shell_convergence tests.test_auth tests.test_owner_home tests.test_owner_home_accessibility -q",
      "exit_code": 0
    },
    {
      "criterion_id": "working_destinations",
      "result": "pass",
      "candidate_sha": "2e971d8217920fd9d4147891fc430fae222b3a44",
      "kind": "automated",
      "source_ref": "X:/PeerSlate/evidence/PS-RESUME-ACCESS-NAV-001/CORRECTED_CANDIDATE_TESTS.txt",
      "observed": "Anonymous GETs for published resume and Interview AI return 200, existing Pete Carter/resume-start content and initial AI mode/panel; Pete subdomain keeps canonical published resume URL.",
      "command": "$env:ANTHROPIC_API_KEY='test-key-for-ci-only'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_resume_access_nav tests.test_navigation tests.test_public_nav_route_truth tests.test_shared_shell_convergence tests.test_auth tests.test_owner_home tests.test_owner_home_accessibility -q",
      "exit_code": 0
    },
    {
      "criterion_id": "signed_in_access",
      "result": "pass",
      "candidate_sha": "2e971d8217920fd9d4147891fc430fae222b3a44",
      "kind": "automated",
      "source_ref": "X:/PeerSlate/evidence/PS-RESUME-ACCESS-NAV-001/CORRECTED_CANDIDATE_TESTS.txt",
      "observed": "Signed-in /app renders the fifth launchpad destination Public Resume, explicitly described as Pete Carter's published career record, with accessible link text. Public-page account menus retain exactly one My PeerSlate return link; private account menus avoid duplicating their primary workspace destination. Settings and sign-out remain available.",
      "command": "$env:ANTHROPIC_API_KEY='test-key-for-ci-only'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_resume_access_nav tests.test_navigation tests.test_public_nav_route_truth tests.test_shared_shell_convergence tests.test_auth tests.test_owner_home tests.test_owner_home_accessibility -q",
      "exit_code": 0
    },
    {
      "criterion_id": "privacy_preserved",
      "result": "pass",
      "candidate_sha": "2e971d8217920fd9d4147891fc430fae222b3a44",
      "kind": "automated",
      "source_ref": "X:/PeerSlate/evidence/PS-RESUME-ACCESS-NAV-001/CORRECTED_CANDIDATE_TESTS.txt",
      "observed": "Generic member resume context has no /petec target in all six nav groups. Anonymous /app retains sign-in redirect; existing full private shell/flag/safe-return tests pass.",
      "command": "$env:ANTHROPIC_API_KEY='test-key-for-ci-only'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_resume_access_nav tests.test_navigation tests.test_public_nav_route_truth tests.test_shared_shell_convergence tests.test_auth tests.test_owner_home tests.test_owner_home_accessibility -q",
      "exit_code": 0
    }
  ]
}
```

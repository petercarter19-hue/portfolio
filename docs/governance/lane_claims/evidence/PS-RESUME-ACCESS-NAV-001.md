# Published resume access and public navigation repair

Owner selected the existing public Pete Carter resume at `/petec/resume` and exactly two public destinations: My Resume and Interview AI. Private test-site drafts, authentication, provider calls, schema and held MVP enablement remain outside this outcome.

The original navigation repair was accepted through PR1219 / CI3965 at main `42785254fc6147982a5f5e2a490ecfe92874af80` and deployed by successful exact-source manual web run3967. Live health release `7a5122c1da796bed28c524e2` matched. Anonymous homepage and published resume returned200, and signed-in Public Resume opened the existing published record. Anonymous Interview AI still redirects to the existing sign-in policy; the signed-in browser opened AI mode. This is an access-policy limitation, not evidence of anonymous live AI content. No provider call was made. Proof remains in `X:/PeerSlate/evidence/PS-RESUME-ACCESS-NAV-001/LIVE_NAVIGATION_VERIFICATION.json` and `LIVE_ANONYMOUS_HTTP_VERIFICATION.json`.

Live verification found one remaining signed-in phone-bar error: the template shortened the public Interview AI label to Interview and supplied the accessible name Interview Studio. Claim-only PR1227 / CI3974 passed all four jobs and all three current required policies, accepting only the templates/base.html surface addition at main `e19575d69ea8fee554a28b23b43f7fb1a4e01d1c`. Normal control finalization and durable reconciliation `9a37a2b8c8320f3593eb35223c6c92e9a5927ee2` preceded a clean write preflight.

Bounded self-review passed for candidate `6b5222bb7a398759182d5be8dee3b878a35973fa` against that main. The complete delta is one template line and focused tests. The accessible label now comes from the existing server destination; only the private Interview Studio destination retains its established short visible label. Hrefs, authentication, feature flags, content and JavaScript are unchanged. The regression failed on all three public routes before the correction while the private contract passed (`PHONE_LABEL_REGRESSION_BEFORE.txt`). All 97 affected navigation, shell, auth and workspace tests pass after correction with zero skips (`PHONE_LABEL_CANDIDATE_TESTS.txt`). Test-only provider placeholder matches CI, loads no real credential and makes no provider call. No runtime bytes changed after these checks.

The immutable original plan and criteria below are retained from `60d26c2f14d9867ab86bef37e4bc1cf5d94e2816`; prior exact candidate/review evidence remains in Git history. Jev regression and review checkpoints were skipped: the observed wrong visible/accessibility label and the existing private Studio contract determine the focused checks and review; no unresolved choice could change the next action. Prior public-path-first Jev advice and result remain in the original evidence.

The phone correction awaits current-target runtime CI, accepted merge and a scoped manual exact-main public navigation release under owner events evt-5c6ebd60-8149-4ec1-b30f-821d5b46318b and evt-66bfeadd-3d45-46e1-8fab-16ffb79654be. Required follow-up is live phone visible/accessibility verification, then the reserved installer custody handoff. The separate public MVP hold, saved user content, provider caps/accounting and no-additional-native-Visitor-call boundary remain in force.

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
  "candidate_sha": "6b5222bb7a398759182d5be8dee3b878a35973fa",
  "checks": [
    {
      "criterion_id": "public_links",
      "result": "pass",
      "candidate_sha": "6b5222bb7a398759182d5be8dee3b878a35973fa",
      "kind": "automated",
      "source_ref": "X:/PeerSlate/evidence/PS-RESUME-ACCESS-NAV-001/PHONE_LABEL_CANDIDATE_TESTS.txt",
      "observed": "All public primary/menu/no-script/overflow/search representations retain My Resume and Interview AI with their existing published resume and AI-mode hrefs. Signed-in global phone source on homepage, resume and Interview AI now has visible and accessible Interview AI; the private workspace retains visible Interview and accessible Interview Studio. All 97 affected tests passed with no skips.",
      "command": "$env:ANTHROPIC_API_KEY='test-key-for-ci-only'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_resume_access_nav tests.test_navigation tests.test_public_nav_route_truth tests.test_shared_shell_convergence tests.test_auth tests.test_owner_home tests.test_owner_home_accessibility -q",
      "exit_code": 0
    },
    {
      "criterion_id": "working_destinations",
      "result": "pass",
      "candidate_sha": "6b5222bb7a398759182d5be8dee3b878a35973fa",
      "kind": "automated",
      "source_ref": "X:/PeerSlate/evidence/PS-RESUME-ACCESS-NAV-001/PHONE_LABEL_CANDIDATE_TESTS.txt",
      "observed": "Anonymous GETs for published resume and Interview AI return 200, existing Pete Carter/resume-start content and initial AI mode/panel; Pete subdomain keeps canonical published resume URL.",
      "command": "$env:ANTHROPIC_API_KEY='test-key-for-ci-only'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_resume_access_nav tests.test_navigation tests.test_public_nav_route_truth tests.test_shared_shell_convergence tests.test_auth tests.test_owner_home tests.test_owner_home_accessibility -q",
      "exit_code": 0
    },
    {
      "criterion_id": "signed_in_access",
      "result": "pass",
      "candidate_sha": "6b5222bb7a398759182d5be8dee3b878a35973fa",
      "kind": "automated",
      "source_ref": "X:/PeerSlate/evidence/PS-RESUME-ACCESS-NAV-001/PHONE_LABEL_CANDIDATE_TESTS.txt",
      "observed": "Signed-in /app renders the fifth launchpad destination Public Resume, explicitly described as Pete Carter's published career record, with accessible link text. Public-page account menus retain exactly one My PeerSlate return link; private account menus avoid duplicating their primary workspace destination. Settings and sign-out remain available.",
      "command": "$env:ANTHROPIC_API_KEY='test-key-for-ci-only'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_resume_access_nav tests.test_navigation tests.test_public_nav_route_truth tests.test_shared_shell_convergence tests.test_auth tests.test_owner_home tests.test_owner_home_accessibility -q",
      "exit_code": 0
    },
    {
      "criterion_id": "privacy_preserved",
      "result": "pass",
      "candidate_sha": "6b5222bb7a398759182d5be8dee3b878a35973fa",
      "kind": "automated",
      "source_ref": "X:/PeerSlate/evidence/PS-RESUME-ACCESS-NAV-001/PHONE_LABEL_CANDIDATE_TESTS.txt",
      "observed": "Generic member resume context has no /petec target in all six nav groups. Anonymous /app retains sign-in redirect; existing full private shell/flag/safe-return tests pass.",
      "command": "$env:ANTHROPIC_API_KEY='test-key-for-ci-only'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_resume_access_nav tests.test_navigation tests.test_public_nav_route_truth tests.test_shared_shell_convergence tests.test_auth tests.test_owner_home tests.test_owner_home_accessibility -q",
      "exit_code": 0
    }
  ]
}
```
